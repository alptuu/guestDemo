import contextlib
import io
import json
import logging
import threading
import time

import pandas as pd
from django.utils import timezone

from .models import GraphRun
from .workflow import REPO_ROOT, REQUESTS_DF, SERVICE_CONFIG, GuestState
from .workflow import graph as guest_graph

logger = logging.getLogger(__name__)

DATA_DIR = REPO_ROOT / "misafir_yonetimi_data" / "data"

# Node'lar print ile çıktı üretir; stdout geçici olarak yakalandığı için çalıştırmalar sıralanır.
_RUN_LOCK = threading.Lock()

NODE_INFO = {
    "fetch": ("Veri Çekme", "Talepleri servis türüne göre filtreler, hastane ve kat bazında gruplar."),
    "calc": ("Gecikme Hesabı", "Her hastane/kat için geciken talep yüzdesini hesaplar."),
    "route": (
        "Yönlendirme",
        "Eşiği aşan en az bir hastane/kat varsa yönetici bildirimine, yoksa takibi durdurmaya yönlendirir.",
    ),
    "notify": ("Yönetici Bildirimi", "Eşiği aşan katlardaki geciken taleplerin hastaları için yöneticiyi bilgilendirir."),
    "stop": ("Takibi Durdur", "Hiçbir kat eşiği aşmadı; geciken hastaların takibi kapatılır."),
}

PIPELINE = ["fetch", "calc", "route", "notify", "stop"]


def _read_csv(name):
    return pd.read_csv(DATA_DIR / name, encoding="utf-8-sig")


_reference_cache = {}


def reference_data():
    if not _reference_cache:
        hospitals = _read_csv("hastaneler.csv").to_dict("records")
        managers = _read_csv("sorumlular.csv").to_dict("records")
        _reference_cache["hospitals"] = {h["hastane_id"]: h["hastane_adi"] for h in hospitals}
        _reference_cache["managers"] = {m["hastane_id"]: m for m in managers}
        _reference_cache["patients"] = _read_csv("hastalar.csv")
    return _reference_cache


def service_choices():
    return [
        {
            "key": key,
            "label": cfg["label"],
            "talep_turu": cfg["talep_turu"],
            "threshold_pct": round(cfg["threshold"] * 100, 2),
            "rows": int((REQUESTS_DF["talep_turu"] == cfg["talep_turu"]).sum()),
        }
        for key, cfg in SERVICE_CONFIG.items()
    ]


def _pct(late, total):
    return round(late / total * 100, 1) if total else 0.0


def _bar_scale(values, threshold_pct):
    """Çubukları eşik çizgisi her zaman görünür kalacak şekilde ölçekler."""
    return (max([*values, threshold_pct]) * 1.25) or 1


def blueprint():
    return [{"node": n, "label": NODE_INFO[n][0], "description": NODE_INFO[n][1], "state": "idle"} for n in PIPELINE]


def dashboard_stats():
    ref = reference_data()
    df = REQUESTS_DF
    patients = ref["patients"]

    services = []
    for key, cfg in SERVICE_CONFIG.items():
        sub = df[df["talep_turu"] == cfg["talep_turu"]]
        late = int(sub["gecikti_mi"].sum())
        services.append(
            {
                "key": key,
                "label": cfg["label"],
                "total": len(sub),
                "late": late,
                "pct": _pct(late, len(sub)),
                "threshold_pct": round(cfg["threshold"] * 100, 2),
            }
        )

    hospitals = []
    for hid, name in ref["hospitals"].items():
        h_df = df[df["hastane_id"] == hid]
        cells = []
        for key, cfg in SERVICE_CONFIG.items():
            sub = h_df[h_df["talep_turu"] == cfg["talep_turu"]]
            pct = _pct(int(sub["gecikti_mi"].sum()), len(sub))
            cells.append({"label": cfg["label"], "pct": pct, "breached": pct / 100 >= cfg["threshold"]})
        hospitals.append(
            {
                "id": hid,
                "name": name,
                "patients": int((patients["hastane_id"] == hid).sum()),
                "requests": len(h_df),
                "cells": cells,
                "manager": ref["managers"].get(hid),
            }
        )

    hours = pd.to_datetime(df["olusturma_zamani"]).dt.hour
    hourly = []
    peak = 1
    for hour in range(int(hours.min()), int(hours.max()) + 1):
        in_hour = df[hours == hour]
        counts = [int((in_hour["talep_turu"] == cfg["talep_turu"]).sum()) for cfg in SERVICE_CONFIG.values()]
        peak = max(peak, sum(counts))
        hourly.append({"hour": f"{hour:02d}", "counts": counts, "total": sum(counts)})
    for item in hourly:
        item["segments"] = [
            {"label": cfg["label"], "key": key, "count": count, "height": round(count / peak * 100, 1)}
            for (key, cfg), count in zip(SERVICE_CONFIG.items(), item["counts"])
        ]

    late_total = int(df["gecikti_mi"].sum())
    for item in services:
        scale = _bar_scale([s["pct"] for s in services], item["threshold_pct"])
        item["bar"] = round(item["pct"] / scale * 100, 1)
        item["marker"] = round(item["threshold_pct"] / scale * 100, 1)
    return {
        "total_requests": len(df),
        "late_requests": late_total,
        "late_pct": _pct(late_total, len(df)),
        "patient_count": len(patients),
        "diabetic_count": int(patients["diyabetik_hasta"].sum()),
        "hospital_count": len(ref["hospitals"]),
        "services": services,
        "hospitals": hospitals,
        "hourly": hourly,
    }


def _patient_rows(grouped, mapping, names):
    """{hastane: {kat: {hasta_id: bool}}} yapısını, talep detaylarıyla zenginleştirilmiş satırlara açar."""
    rows = []
    for hid, floors in (mapping or {}).items():
        for kat, patients in floors.items():
            df = grouped[hid][kat]
            for hasta_id in patients:
                late = df[(df["hasta_id"] == hasta_id) & (df["gecikti_mi"])]
                wait = late["sure_dk"].max()
                rows.append(
                    {
                        "hastane_id": hid,
                        "hastane_adi": names.get(hid, hid),
                        "kat": int(kat),
                        "hasta_id": hasta_id,
                        "oda_no": int(late["oda_no"].iloc[0]),
                        "diyabetik": bool(late["diyabetik_hasta"].iloc[0]),
                        "late_requests": len(late),
                        "details": ", ".join(dict.fromkeys(late["talep_detayi"])),
                        "max_wait": None if pd.isna(wait) else round(float(wait), 1),
                    }
                )
    return rows


def _execute(service_type):
    """Graph'ı stream ederek her ajan (node) adımını, süresini ve konsol çıktısını toplar."""
    state, raw_steps = {}, []
    buffer = io.StringIO()
    cursor = 0
    started_at = timezone.now()
    t0 = last = time.perf_counter()

    with _RUN_LOCK, contextlib.redirect_stdout(buffer):
        for chunk in guest_graph.stream(GuestState(service_type=service_type), stream_mode="updates"):
            for node, update in chunk.items():
                now = time.perf_counter()
                text = buffer.getvalue()
                raw_steps.append(
                    {"node": node, "duration_ms": round((now - last) * 1000, 1), "log": text[cursor:].splitlines()}
                )
                cursor = len(text)
                state.update(update or {})
                last = time.perf_counter()

    return state, raw_steps, started_at, round((last - t0) * 1000, 1)


def build_payload(service_type):
    cfg = SERVICE_CONFIG[service_type]
    threshold_pct = round(cfg["threshold"] * 100, 2)
    ref = reference_data()
    names = ref["hospitals"]

    state, raw_steps, started_at, duration_ms = _execute(service_type)
    grouped, late = state["grouped_requests"], state["late_requests"]
    decision = next(s["node"] for s in raw_steps if s["node"] in ("notify", "stop"))

    floors = []
    for hid, floor_data in late.items():
        for kat, info in floor_data.items():
            floors.append(
                {
                    "hastane_id": hid,
                    "hastane_adi": names.get(hid, hid),
                    "kat": int(kat),
                    "total": len(grouped[hid][kat]),
                    "late": len(info["guests"]),
                    "pct": info["latency_percentage"],
                    "breached": info["latency_percentage"] / 100 >= cfg["threshold"],
                }
            )
    breached = [f for f in floors if f["breached"]]
    scale = _bar_scale([f["pct"] for f in floors], threshold_pct)
    for f in floors:
        f["bar"] = round(f["pct"] / scale * 100, 1)
    threshold_marker = round(threshold_pct / scale * 100, 1)
    top = max(floors, key=lambda f: f["pct"]) if floors else None

    notified = _patient_rows(grouped, state.get("manager_notified"), names)
    stopped = _patient_rows(grouped, state.get("tracking"), names)
    breached_hospitals = list(dict.fromkeys(f["hastane_id"] for f in breached))
    recipients = [ref["managers"][h] for h in breached_hospitals if h in ref["managers"]] if decision == "notify" else []

    facts = {
        "fetch": [
            ("Filtre", f"talep_turu = {cfg['talep_turu']}"),
            ("Talep", sum(len(df) for kats in grouped.values() for df in kats.values())),
            ("Hastane", len(grouped)),
            ("Kat grubu", len(floors)),
        ],
        "calc": [
            ("Hesaplanan kat grubu", len(floors)),
            ("Eşik", f"%{threshold_pct:g}"),
            ("Eşiği aşan", len(breached)),
            ("En yüksek", f"{names.get(top['hastane_id'], top['hastane_id'])} / Kat {top['kat']} (%{top['pct']:g})" if top else "—"),
        ],
        "route": [
            ("Karar", "notify" if decision == "notify" else "stop"),
            (
                "Gerekçe",
                f"{len(breached)} hastane/kat eşiği aştı." if breached else "Hiçbir hastane/kat eşiği aşmadı.",
            ),
        ],
        "notify": [
            ("Bildirilen hasta", len(notified)),
            ("Diyabetik hasta", sum(r["diyabetik"] for r in notified)),
            ("Bildirilen yönetici", ", ".join(r["ad_soyad"] for r in recipients) or "—"),
        ],
        "stop": [("Takibi kapatılan hasta", len(stopped))],
    }
    deltas = {
        "fetch": {hid: {int(k): len(df) for k, df in kats.items()} for hid, kats in grouped.items()},
        "calc": late,
        "route": {"decision": decision, "breached": [f"{f['hastane_id']}/Kat {f['kat']}" for f in breached]},
        "notify": state.get("manager_notified"),
        "stop": state.get("tracking"),
    }

    steps = []
    for raw in raw_steps:
        steps.append({**raw, "facts": facts[raw["node"]], "delta": deltas[raw["node"]]})
        if raw["node"] == "calc":
            steps.append(
                {
                    "node": "route",
                    "duration_ms": None,
                    "log": [],
                    "facts": facts["route"],
                    "delta": deltas["route"],
                }
            )
    for step in steps:
        step["label"], step["description"] = NODE_INFO[step["node"]]

    path = ["fetch", "calc", "route", decision]
    payload = {
        "service_type": service_type,
        "label": cfg["label"],
        "talep_turu": cfg["talep_turu"],
        "threshold_pct": threshold_pct,
        "threshold_marker": threshold_marker,
        "decision": decision,
        "started_at": started_at.isoformat(),
        "duration_ms": duration_ms,
        "pipeline": [
            {"node": n, "label": NODE_INFO[n][0], "state": "done" if n in path else "skipped"} for n in PIPELINE
        ],
        "steps": steps,
        "floors": floors,
        "notified": notified,
        "stopped": stopped,
        "recipients": recipients,
        "kpis": {
            "total_requests": sum(f["total"] for f in floors),
            "late_requests": sum(f["late"] for f in floors),
            "floors": len(floors),
            "breached_floors": len(breached),
            "notified_patients": len(notified),
            "diabetic_patients": sum(r["diyabetik"] for r in notified),
        },
    }
    # JSONField'e yazılanla ekranda gösterilenin aynı olması için (int anahtarlar vb.) önce serileştiriyoruz.
    return json.loads(json.dumps(payload, default=str, ensure_ascii=False))


def run_and_record(service_type, user=None):
    """Graph'ı çalıştırır ve sonucu (hata dahil) GraphRun olarak kaydeder."""
    try:
        payload = build_payload(service_type)
    except Exception as exc:  # noqa: BLE001 - hata da çalıştırma geçmişine yazılır
        logger.exception("Graph çalıştırması başarısız: %s", service_type)
        return GraphRun.objects.create(
            user=user,
            service_type=service_type,
            status=GraphRun.STATUS_ERROR,
            error=f"{type(exc).__name__}: {exc}",
            payload={"service_type": service_type, "label": SERVICE_CONFIG[service_type]["label"]},
        )

    kpis = payload["kpis"]
    return GraphRun.objects.create(
        user=user,
        service_type=service_type,
        decision=payload["decision"],
        duration_ms=payload["duration_ms"],
        breached_floors=kpis["breached_floors"],
        notified_count=kpis["notified_patients"],
        payload=payload,
    )
