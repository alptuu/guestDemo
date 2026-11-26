"""
LangGraph node/tool'larında kullanmak için basit veri erişim katmanı.

Örnek:
    from data_loader import MisafirVeri
    veri = MisafirVeri("data")
    gb = veri.genel_bakis("H01", "2026-11-26T13:00")       # hastane bazında
    gb_kat = veri.genel_bakis("H01", "2026-11-26T13:00", kat=3)
    mudur = veri.sorumlu("H01")
    veri.is_istem_ac("H01", "KAFE", 0.27, "2026-11-26T13:00")
"""
import csv
import json
from datetime import datetime
from pathlib import Path

TUR_KISA = {"KAFE": "kafe", "TEMIZLIK-ODA": "temizlik_oda", "TEKNIK HIZMETLER": "teknik"}


def _oku(yol):
    with open(yol, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _sayi(v):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


class MisafirVeri:
    def __init__(self, klasor="data"):
        self.k = Path(klasor)
        self.config = json.loads((self.k / "config.json").read_text(encoding="utf-8"))
        self.hastaneler = _oku(self.k / "hastaneler.csv")
        self.sorumlular = {r["hastane_id"]: r for r in _oku(self.k / "sorumlular.csv")}
        self.snapshots = [{k: _sayi(v) for k, v in r.items()}
                          for r in _oku(self.k / "genel_bakis_snapshots.csv")]
        self.talepler = _oku(self.k / "talepler.csv")
        self.hastalar = _oku(self.k / "hastalar.csv")
        self._is_istem_yolu = self.k / "is_istemler.csv"

    def snapshot_zamanlari(self):
        """Genel Bakış ekranının güncellendiği zamanlar (10 dk'da bir)."""
        return sorted({s["zaman"] for s in self.snapshots})

    def genel_bakis(self, hastane_id, zaman, kat="TUMU"):
        """Verilen zamandaki (veya hemen öncesindeki) Genel Bakış görüntüsü."""
        kat = str(kat)
        adaylar = [s for s in self.snapshots
                   if s["hastane_id"] == hastane_id and str(s["kat"]) == kat and s["zaman"] <= zaman]
        return max(adaylar, key=lambda s: s["zaman"]) if adaylar else None

    def gecikme_orani(self, hastane_id, talep_turu, zaman, kat="TUMU"):
        gb = self.genel_bakis(hastane_id, zaman, kat)
        return gb[f"{TUR_KISA[talep_turu]}_gecikme_orani"] if gb else None

    def geciken_talepler(self, hastane_id, talep_turu, zaman):
        """O anda aktif ve gecikme eşiğini aşmış talepler (bildirim içeriği için)."""
        t = datetime.fromisoformat(zaman)
        sonuc = []
        for r in self.talepler:
            if r["hastane_id"] != hastane_id or r["talep_turu"] != talep_turu:
                continue
            bas = datetime.fromisoformat(r["olusturma_zamani"])
            bit = datetime.fromisoformat(r["tamamlanma_zamani"]) if r["tamamlanma_zamani"] else None
            if bas <= t and (bit is None or bit > t):
                bekleme = (t - bas).total_seconds() / 60
                if bekleme > int(r["gecikme_esigi_dk"]):
                    sonuc.append({**r, "bekleme_dk": round(bekleme, 1)})
        return sorted(sonuc, key=lambda x: -x["bekleme_dk"])

    def sorumlu(self, hastane_id):
        return self.sorumlular.get(hastane_id)

    def is_istem_ac(self, hastane_id, talep_turu, kpi_degeri, zaman, aciklama=""):
        mevcut = _oku(self._is_istem_yolu)
        alanlar = ["is_istem_id", "olusturma_zamani", "hastane_id", "talep_turu", "kpi_adi", "kpi_degeri",
                   "esik", "uyari_seviyesi", "bildirilen_kisi", "durum", "aciklama"]
        kayit = {
            "is_istem_id": f"IS{len(mevcut) + 1:04d}",
            "olusturma_zamani": zaman,
            "hastane_id": hastane_id,
            "talep_turu": talep_turu,
            "kpi_adi": "Gecikme Oranı (%)",
            "kpi_degeri": kpi_degeri,
            "esik": self.config["kpi_alarm_esigi"],
            "uyari_seviyesi": 1,
            "bildirilen_kisi": self.sorumlu(hastane_id)["ad_soyad"],
            "durum": "Açık",
            "aciklama": aciklama,
        }
        with open(self._is_istem_yolu, "a", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=alanlar).writerow(kayit)
        return kayit
