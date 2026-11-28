import os
from pathlib import Path
import pandas as pd 
from django.shortcuts import render
from langchain_ollama import ChatOllama
from pydantic import BaseModel
from typing import Literal
from langgraph.graph import StateGraph, START, END
import json
from datetime import date

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = REPO_ROOT / "misafir_yonetimi_data" / "data" / "talepler.csv"

REQUESTS_DF = pd.read_csv(CSV_PATH,encoding="utf-8-sig", sep=",",)

SERVICE_CONFIG = {
    "cafe":         {"label": "Kafe Talepleri",    "threshold": 0.20, "source": "cafe_requests", "talep_turu": "KAFE"},
    "housekeeping": {"label": "Oda ve Temizlik",   "threshold": 0.20, "source": "hk_requests",   "talep_turu": "TEMIZLIK-ODA"},
    "technical":    {"label": "Teknik Hizmet",     "threshold": 0.20, "source": "tech_requests", "talep_turu": "TEKNIK HIZMETLER"},
}

# The guest state that will be used throughout the graph 
class GuestState(BaseModel):
    service_type: Literal["cafe", "housekeeping", "technical"]
    grouped_requests: dict | None = None   # {hastane_id: {kat: DataFrame}}
    late_requests: dict | None = None      # {hastane_id: {kat: {"latency_percentage": float, "guests": [hasta_id, ...]}}}
    manager_notified: dict | None = None   # {hastane_id: {kat: {hasta_id: bool}}}
    tracking: dict | None = None           # {hastane_id: {kat: {hasta_id: bool}}}
    message: dict | None = None  

def route(state: GuestState) -> Literal["notify", "stop"]:
    th = SERVICE_CONFIG[state.service_type]["threshold"]
    for kat_data in (state.late_requests or {}).values():
        for info in kat_data.values():
            if info["latency_percentage"] / 100 >= th:
                return "notify"   # en az bir hastane+kat eşiği aştıysa tek karar: notify
    return "stop"

def fetch_requests(state: GuestState) -> dict:
    """service_type'a karşılık gelen talep_turu'na göre REQUESTS_DF'i filtreler,
    ardından hastane_id, sonra kat'a göre gruplar.

    Dönüş: {"grouped_requests": {hastane_id: {kat: DataFrame}}}
    """
    talep_turu = SERVICE_CONFIG[state.service_type]["talep_turu"]
    filtered_df = REQUESTS_DF[REQUESTS_DF["talep_turu"] == talep_turu]

    grouped = {}
    for hastane_id, hastane_df in filtered_df.groupby("hastane_id"):
        grouped[hastane_id] = {
            int(kat): kat_df
            for kat, kat_df in hastane_df.groupby("kat")
        }
    return {"grouped_requests": grouped}

def calc_delay_ratio(state: GuestState):

    late_results = {}
    for hastane_id, kat_data in state.grouped_requests.items():
        for kat, df in kat_data.items():
            late_guests = df[df["gecikti_mi"] == True]
            latency_percentage = round(( len(late_guests) / len(df)) * 100,2)

            late_results.setdefault(hastane_id, {})[int(kat)] = {
                    "latency_percentage": latency_percentage,
                    "guests": late_guests["hasta_id"].tolist(),
                    }
            
            print(f"Hastane: {hastane_id}, Kat: {kat}, Talep gecikme yüzdesi: {latency_percentage}")

    return {"late_requests":late_results}

def notify_manager(state: GuestState) -> dict:
    th = SERVICE_CONFIG[state.service_type]["threshold"]
    manager_notified = {}

    for hastane_id, kat_data in (state.late_requests or {}).items():
        for kat, info in kat_data.items():
            if info["latency_percentage"] / 100 < th:
                continue   # bu hastane+kat eşiği aşmadı, atla
            df = state.grouped_requests[hastane_id][kat]
            for hasta_id in info["guests"]:
                diyabetik = bool(df.loc[df["hasta_id"] == hasta_id, "diyabetik_hasta"].iloc[0])
                manager_notified.setdefault(hastane_id, {}).setdefault(kat, {})[hasta_id] = True
                print(f"Yönetici bilgilendirildi: {hastane_id} - Kat {kat} - Hasta {hasta_id} (Diyabetik: {diyabetik})")
                
    return {"manager_notified": manager_notified}

def stop_tracking(state: GuestState) -> dict:
    tracking = {}
    for hastane_id, kat_data in (state.late_requests or {}).items():
        for kat, info in kat_data.items():
            for hasta_id in info["guests"]:
                tracking.setdefault(hastane_id, {}).setdefault(kat, {})[hasta_id] = False
    return {"tracking": tracking}



# The graph structure
builder = StateGraph(GuestState)
builder.add_node("fetch", fetch_requests)
builder.add_node("calc", calc_delay_ratio)
builder.add_node("notify", notify_manager)
builder.add_node("stop", stop_tracking)

builder.add_edge(START, "fetch")
builder.add_edge("fetch", "calc")
builder.add_conditional_edges("calc", route)
builder.add_edge("notify", END)
builder.add_edge("stop", END)
graph = builder.compile()


# Günlük rapor graph'ı: saat 18:00'a kadar yapılan işleri LLM ile mesaja çevirir.
# Çalıştırma zamanını (18:00) dışarıdaki bir zamanlayıcı belirler: daily_graph.invoke(DailyReportState())
DAILY_REPORT_MODEL = os.environ.get("DAILY_REPORT_MODEL", "llama3.1")

DAILY_REPORT_PROMPT = """Sen bir hastane misafir hizmetleri asistanısın.
Sana verilen JSON, belirtilen saate kadar o gün yapılan işlerin özetidir.
Bu veriyi yöneticilere gönderilecek kısa, kibar ve Türkçe bir gün sonu mesajına dönüştür.
Kurallar: Yalnızca JSON'daki rakamları kullan; rakam uydurma, tahmin etme.
Her servis (kafe, oda-temizlik, teknik) için tamamlanan, bekleyen ve geciken sayılarını belirt,
en çok geciken hastane/katı vurgula. En fazla 8 satır; madde işareti kullanabilirsin."""


class DailyReportState(BaseModel):
    report_date: str | None = None   # "YYYY-MM-DD"; None ise bugün
    cutoff_hour: int = 18
    stats: dict | None = None
    report_message: str | None = None


def collect_daily_stats(state: DailyReportState) -> dict:
    day = pd.Timestamp(state.report_date or date.today().isoformat())
    cutoff = day + pd.Timedelta(hours=state.cutoff_hour)

    df = REQUESTS_DF.copy()
    df["_created"] = pd.to_datetime(df["olusturma_zamani"])
    df["_done"] = pd.to_datetime(df["tamamlanma_zamani"])
    df = df[(df["_created"] >= day) & (df["_created"] <= cutoff)]

    # gecikti_mi gün sonu (22:00) itibarıyla hesaplı olduğundan gecikme kesim saatine göre yeniden bulunur.
    done = df["_done"].notna() & (df["_done"] <= cutoff)
    wait_min = df["sure_dk"].where(done, (cutoff - df["_created"]).dt.total_seconds() / 60)
    df = df.assign(_done_flag=done, _late=wait_min > df["gecikme_esigi_dk"])

    stats = {
        "tarih": str(day.date()),
        "saat": f"{state.cutoff_hour:02d}:00",
        "toplam_talep": len(df),
        "servisler": {},
    }
    for cfg in SERVICE_CONFIG.values():
        sub = df[df["talep_turu"] == cfg["talep_turu"]]
        stats["servisler"][cfg["label"]] = {
            "toplam": len(sub),
            "tamamlanan": int(sub["_done_flag"].sum()),
            "bekleyen": int((~sub["_done_flag"]).sum()),
            "geciken": int(sub["_late"].sum()),
            "diyabetik_hasta_talebi": int(sub["diyabetik_hasta"].sum()),
        }

    worst = df[df["_late"]].groupby(["hastane_id", "kat"]).size().sort_values(ascending=False).head(3)
    stats["en_cok_geciken"] = [{"hastane": h, "kat": int(k), "geciken": int(n)} for (h, k), n in worst.items()]
    return {"stats": stats}


def write_daily_report(state: DailyReportState) -> dict:
    llm = ChatOllama(model=DAILY_REPORT_MODEL, temperature=0.2)
    response = llm.invoke([
        ("system", DAILY_REPORT_PROMPT),
        ("human", json.dumps(state.stats, ensure_ascii=False)),
    ])
    return {"report_message": response.content}


daily_builder = StateGraph(DailyReportState)
daily_builder.add_node("collect_daily", collect_daily_stats)
daily_builder.add_node("daily_report", write_daily_report)
daily_builder.add_edge(START, "collect_daily")
daily_builder.add_edge("collect_daily", "daily_report")
daily_builder.add_edge("daily_report", END)
daily_graph = daily_builder.compile()