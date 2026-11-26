"""
Misafir Yönetimi - Sahte Veri Seti Üretici
------------------------------------------
Asistan uygulaması üzerinden gelen KAFE / TEMİZLİK-ODA / TEKNİK HİZMETLER
taleplerini simüle eder ve "Genel Bakış" ekranının 10 dakikada bir
güncellenen anlık görüntülerini (snapshot) hesaplar.

Çalıştırma:  python generate_data.py   (seed sabit -> her seferinde aynı veri)
"""
import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
random.seed(SEED)
OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

GUN = datetime(2026, 11, 26)
SIM_BASLANGIC = GUN.replace(hour=7)
SIM_BITIS = GUN.replace(hour=22)
SNAPSHOT_BASLANGIC = GUN.replace(hour=8)
SNAPSHOT_ARALIK_DK = 10

# Dokümandaki eşikler
GECIKME_ESIGI_DK = {"KAFE": 45, "TEMIZLIK-ODA": 60, "TEKNIK HIZMETLER": 60}
KPI_ALARM_ESIGI = 0.20  # Gecikme Oranı >= %20 -> 1. uyarı + iş istem

TALEP_TURLERI = ["KAFE", "TEMIZLIK-ODA", "TEKNIK HIZMETLER"]
TUR_KISA = {"KAFE": "kafe", "TEMIZLIK-ODA": "temizlik_oda", "TEKNIK HIZMETLER": "teknik"}

# Dokümanda listelenen diyabetik tanılar
DIYABETIK_TANILAR = (
    "Z83.3 Z13.1 Y42.3 T38.3 P70.2 P70.1 P70.0 O24.9 O24.4 O24.3 O24.2 O24.1 O24.0 "
    "O24 N25.1 N08.3 M14.2 H36.0 H28.0 G63.2 G59.0 E23.2 E15 E14.9 E14.8 E14.7 E14.6 "
    "E14.5 E14.4 E14.3 E14.2 E14.1 E14.0 E14 E13.9 E13.8 E13.7 E13.6 E13.5 E13.4 E13.3 "
    "E13.2 E13.1 E13.0 E12.9 E12.8 E12.7 E12.6 E12.5 E12.4 E12.3 E12.2 E12.1 E12.0 E12 "
    "E11.9 E11.8 E11.7 E11.6 E11.5 E11.4 E11.3 E11.2 E11.1 E11.0 E11 E10.9 E10.8 E10.7 "
    "E10.6 E10.5 E10.4 E10.3 E10.2 E10.1 E10.0 E10"
).split()
# Sık görülen diyabetik tanılar (daha gerçekçi dağılım için)
SIK_DIYABETIK = ["E11.9", "E11.6", "E10.9", "E11.4", "E14.9", "O24.4", "E11.2"]
DIGER_TANILAR = [
    "I10", "J18.9", "K35.8", "N39.0", "I21.9", "M17.1", "K80.2", "J44.1", "S72.0",
    "I50.0", "C50.9", "K29.7", "R10.4", "A09.9", "I63.9", "N20.0", "J45.9", "Z96.6",
]

HASTANELER = [
    # senaryo: hangi talep türünde, hangi saat aralığında hizmet yavaşlıyor
    {"hastane_id": "H01", "hastane_adi": "Merkez Hastanesi", "kat_sayisi": 5, "yatak_per_kat": 24,
     "doluluk": 0.85, "yavaslama": [("KAFE", 11.5, 14.0, 2.6), ("KAFE", 18.0, 19.5, 2.0)]},
    {"hastane_id": "H02", "hastane_adi": "Kuzey Hastanesi", "kat_sayisi": 4, "yatak_per_kat": 20,
     "doluluk": 0.80, "yavaslama": [("TEKNIK HIZMETLER", 13.0, 17.0, 2.4)]},
    {"hastane_id": "H03", "hastane_adi": "Sahil Hastanesi", "kat_sayisi": 3, "yatak_per_kat": 18,
     "doluluk": 0.75, "yavaslama": [("TEMIZLIK-ODA", 9.0, 11.0, 2.2)]},
]

MUDURLER = [
    {"hastane_id": "H01", "rol": "Destek Hizmetleri Müdürü", "ad_soyad": "Ayşe Demir",
     "eposta": "ayse.demir@ornek-hastane.test", "telefon": "+90 555 000 0101"},
    {"hastane_id": "H02", "rol": "Destek Hizmetleri Müdürü", "ad_soyad": "Mehmet Kaya",
     "eposta": "mehmet.kaya@ornek-hastane.test", "telefon": "+90 555 000 0202"},
    {"hastane_id": "H03", "rol": "Destek Hizmetleri Müdürü", "ad_soyad": "Zeynep Arslan",
     "eposta": "zeynep.arslan@ornek-hastane.test", "telefon": "+90 555 000 0303"},
]

ADLAR = ["Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim", "Murat", "Emre",
         "Can", "Fatma", "Ayşe", "Emine", "Hatice", "Zeynep", "Elif", "Merve", "Selin", "Deniz",
         "Gül", "Kemal", "Osman", "Burak", "Ceren", "Esra", "Yusuf", "Ömer", "Sevgi", "Leyla", "Arda"]
SOYADLAR = ["Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Yıldırım", "Öztürk", "Aydın",
            "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan", "Çetin", "Kara", "Koç", "Kurt", "Özkan", "Şimşek"]

DETAYLAR = {
    "KAFE": ["Çay", "Türk kahvesi", "Filtre kahve", "Su (0,5 L)", "Meyve suyu", "Tost",
             "Simit", "Ayran", "Bitki çayı", "Kurabiye", "Sandviç", "Çorba"],
    "KAFE_DIYABETIK": ["Şekersiz bitki çayı", "Diyabetik kurabiye", "Şekersiz filtre kahve",
                       "Su (0,5 L)", "Ayran", "Tam buğday sandviç"],
    "TEMIZLIK-ODA": ["Oda temizliği", "Banyo temizliği", "Çarşaf değişimi", "Havlu talebi",
                     "Çöp boşaltma", "Ekstra battaniye", "Yastık talebi", "Refakatçi koltuğu hazırlığı"],
    "TEKNIK HIZMETLER": ["TV çalışmıyor", "Klima arızası", "Aydınlatma arızası", "Musluk damlatıyor",
                         "Hasta yatağı ayar arızası", "Priz çalışmıyor", "Wi-Fi bağlantı sorunu",
                         "Hemşire çağrı butonu arızası", "Kapı kilidi sorunu"],
}

# Saatlik talep yoğunluğu (hasta başına saatlik talep olasılığı çarpanı)
def yogunluk(tur, saat):
    if tur == "KAFE":
        if 8 <= saat < 10: return 1.4
        if 11.5 <= saat < 14: return 2.2
        if 15 <= saat < 17: return 1.3
        if 18 <= saat < 20: return 1.8
        return 0.6
    if tur == "TEMIZLIK-ODA":
        if 8 <= saat < 12: return 1.6
        if 12 <= saat < 18: return 1.0
        return 0.5
    # teknik
    if 9 <= saat < 18: return 1.0
    return 0.5

TABAN_ORAN = {"KAFE": 0.11, "TEMIZLIK-ODA": 0.035, "TEKNIK HIZMETLER": 0.022}  # hasta/saat
# Normal şartlarda hizmet süresi (dk): (ortalama, std)
HIZMET_SURESI = {"KAFE": (22, 9), "TEMIZLIK-ODA": (32, 12), "TEKNIK HIZMETLER": (38, 15)}


def saat_ondalik(dt):
    return dt.hour + dt.minute / 60


def hizmet_suresi(hastane, tur, olusturma, hasta_turu):
    ort, std = HIZMET_SURESI[tur]
    carpan = 1.0
    s = saat_ondalik(olusturma)
    for (y_tur, bas, bit, kat) in hastane["yavaslama"]:
        if y_tur == tur and bas <= s < bit:
            carpan = kat
    if hasta_turu == "VIP":
        carpan *= 0.75  # VIP talepler öncelikli
    sure = max(4, random.gauss(ort * carpan, std * carpan))
    # küçük olasılıkla "unutulmuş" talep
    if random.random() < 0.005:
        sure += random.uniform(40, 120)
    return sure


def yaz_csv(ad, satirlar, alanlar):
    with open(OUT / ad, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=alanlar, extrasaction="ignore")
        w.writeheader()
        w.writerows(satirlar)


# ---------------------------------------------------------------- hastalar
hastalar = []
hasta_no = 1
for h in HASTANELER:
    for kat in range(1, h["kat_sayisi"] + 1):
        for yatak in range(1, h["yatak_per_kat"] + 1):
            if random.random() > h["doluluk"]:
                continue
            diyabetik = random.random() < 0.18
            tanilar = random.sample(DIGER_TANILAR, k=random.randint(1, 2))
            if diyabetik:
                tanilar.insert(0, random.choice(SIK_DIYABETIK) if random.random() < 0.8
                               else random.choice(DIYABETIK_TANILAR))
            yatis = GUN - timedelta(days=random.randint(0, 9), hours=random.randint(0, 23))
            # Bazı hastalar gün içinde taburcu olur (aktif yatan sayısı değişsin)
            taburcu = None
            if random.random() < 0.08:
                taburcu = GUN.replace(hour=random.randint(10, 17), minute=random.choice([0, 15, 30, 45]))
            hastalar.append({
                "hasta_id": f"P{hasta_no:04d}",
                "hastane_id": h["hastane_id"],
                "kat": kat,
                "oda_no": f"{kat}{yatak:02d}",
                "ad_soyad": f"{random.choice(ADLAR)} {random.choice(SOYADLAR)}",
                "hasta_turu": "VIP" if random.random() < 0.12 else "Normal",
                "yatis_tanilari": ";".join(tanilar),
                "diyabetik_hasta": diyabetik,
                "yatis_zamani": yatis.isoformat(timespec="minutes"),
                "taburcu_zamani": taburcu.isoformat(timespec="minutes") if taburcu else "",
            })
            hasta_no += 1

hastane_map = {h["hastane_id"]: h for h in HASTANELER}


def aktif_mi(hasta, t):
    yatis = datetime.fromisoformat(hasta["yatis_zamani"])
    tb = hasta["taburcu_zamani"]
    return yatis <= t and (not tb or datetime.fromisoformat(tb) > t)


# ---------------------------------------------------------------- talepler
talepler = []
talep_no = 1
dakika = SIM_BASLANGIC
while dakika < SIM_BITIS:
    s = saat_ondalik(dakika)
    for p in hastalar:
        if not aktif_mi(p, dakika):
            continue
        for tur in TALEP_TURLERI:
            olas = TABAN_ORAN[tur] * yogunluk(tur, s) / 60  # dakikalık olasılık
            if random.random() >= olas:
                continue
            olusturma = dakika + timedelta(seconds=random.randint(0, 59))
            h = hastane_map[p["hastane_id"]]
            sure = hizmet_suresi(h, tur, olusturma, p["hasta_turu"])
            tamam = olusturma + timedelta(minutes=sure)
            if tur == "KAFE" and p["diyabetik_hasta"]:
                detay = random.choice(DETAYLAR["KAFE_DIYABETIK"])
            else:
                detay = random.choice(DETAYLAR[tur])
            talepler.append({
                "talep_id": f"T{talep_no:05d}",
                "hasta_id": p["hasta_id"],
                "hastane_id": p["hastane_id"],
                "kat": p["kat"],
                "oda_no": p["oda_no"],
                "hasta_turu": p["hasta_turu"],
                "diyabetik_hasta": p["diyabetik_hasta"],
                "talep_turu": tur,
                "talep_detayi": detay,
                "olusturma_zamani": olusturma.isoformat(timespec="seconds"),
                "tamamlanma_zamani": tamam.isoformat(timespec="seconds") if tamam <= SIM_BITIS else "",
                "gecikme_esigi_dk": GECIKME_ESIGI_DK[tur],
                "_olusturma": olusturma,
                "_tamam": tamam,
            })
            talep_no += 1
    dakika += timedelta(minutes=1)

# Gün sonu (22:00) itibarıyla durum
for t in talepler:
    if t["_tamam"] <= SIM_BITIS:
        t["durum"] = "Tamamlandı"
        sure_dk = (t["_tamam"] - t["_olusturma"]).total_seconds() / 60
    else:
        t["durum"] = "Bekliyor"
        sure_dk = (SIM_BITIS - t["_olusturma"]).total_seconds() / 60
    t["sure_dk"] = round(sure_dk, 1)
    t["gecikti_mi"] = sure_dk > t["gecikme_esigi_dk"]


# ---------------------------------------------------------------- genel bakış snapshot'ları
def snapshot(hastane_id, kat, t):
    hs = [p for p in hastalar if p["hastane_id"] == hastane_id and (kat == "TUMU" or p["kat"] == kat)
          and aktif_mi(p, t)]
    hs_ids = {p["hasta_id"] for p in hs}
    aktif = [r for r in talepler if r["hasta_id"] in hs_ids and r["_olusturma"] <= t < r["_tamam"]]
    yatan = len(hs)
    row = {
        "zaman": t.isoformat(timespec="minutes"),
        "hastane_id": hastane_id,
        "kat": kat,
        "yatan_hasta_sayisi": yatan,
        "talebi_olan_hastalar": len({r["hasta_id"] for r in aktif}),
        "toplam_talep": len(aktif),
    }
    for tur in TALEP_TURLERI:
        k = TUR_KISA[tur]
        tur_aktif = [r for r in aktif if r["talep_turu"] == tur]
        geciken = [r for r in tur_aktif
                   if (t - r["_olusturma"]).total_seconds() / 60 > GECIKME_ESIGI_DK[tur]]
        hasta_say = len({r["hasta_id"] for r in tur_aktif})
        row[f"{k}_hasta_sayisi"] = hasta_say
        row[f"{k}_hasta_orani"] = round(hasta_say / yatan, 4) if yatan else 0
        row[f"{k}_bekleyen"] = len(tur_aktif) - len(geciken)
        row[f"{k}_geciken"] = len(geciken)
        row[f"{k}_gecikme_orani"] = round(len(geciken) / len(tur_aktif), 4) if tur_aktif else 0
    return row


snapshots = []
t = SNAPSHOT_BASLANGIC
while t <= SIM_BITIS:
    for h in HASTANELER:
        snapshots.append(snapshot(h["hastane_id"], "TUMU", t))
        for kat in range(1, h["kat_sayisi"] + 1):
            snapshots.append(snapshot(h["hastane_id"], kat, t))
    t += timedelta(minutes=SNAPSHOT_ARALIK_DK)

# ---------------------------------------------------------------- beklenen akış (test için referans)
# Akış şemasına göre: hastane bazında Gecikme Oranı >= %20 ise uyarı + iş istem, değilse takip durur.
beklenen = []
for s in snapshots:
    if s["kat"] != "TUMU":
        continue
    for tur in TALEP_TURLERI:
        oran = s[f"{TUR_KISA[tur]}_gecikme_orani"]
        if oran >= KPI_ALARM_ESIGI:
            beklenen.append({
                "zaman": s["zaman"], "hastane_id": s["hastane_id"], "talep_turu": tur,
                "gecikme_orani": oran, "aksiyon": "UYARI_VE_IS_ISTEM",
                "bildirilecek": "Destek Hizmetleri Müdürü",
            })

# ---------------------------------------------------------------- yaz
yaz_csv("hastaneler.csv",
        [{k: h[k] for k in ("hastane_id", "hastane_adi", "kat_sayisi", "yatak_per_kat")} for h in HASTANELER],
        ["hastane_id", "hastane_adi", "kat_sayisi", "yatak_per_kat"])
yaz_csv("sorumlular.csv", MUDURLER, ["hastane_id", "rol", "ad_soyad", "eposta", "telefon"])
yaz_csv("hastalar.csv", hastalar, list(hastalar[0].keys()))
talep_alanlari = ["talep_id", "hasta_id", "hastane_id", "kat", "oda_no", "hasta_turu", "diyabetik_hasta",
                  "talep_turu", "talep_detayi", "olusturma_zamani", "tamamlanma_zamani", "durum",
                  "sure_dk", "gecikme_esigi_dk", "gecikti_mi"]
yaz_csv("talepler.csv", talepler, talep_alanlari)
yaz_csv("genel_bakis_snapshots.csv", snapshots, list(snapshots[0].keys()))
yaz_csv("beklenen_aksiyonlar.csv", beklenen,
        ["zaman", "hastane_id", "talep_turu", "gecikme_orani", "aksiyon", "bildirilecek"])
yaz_csv("is_istemler.csv", [],
        ["is_istem_id", "olusturma_zamani", "hastane_id", "talep_turu", "kpi_adi", "kpi_degeri",
         "esik", "uyari_seviyesi", "bildirilen_kisi", "durum", "aciklama"])

with open(OUT / "config.json", "w", encoding="utf-8") as f:
    json.dump({
        "gun": GUN.date().isoformat(),
        "snapshot_aralik_dk": SNAPSHOT_ARALIK_DK,
        "gecikme_esigi_dk": GECIKME_ESIGI_DK,
        "kpi_alarm_esigi": KPI_ALARM_ESIGI,
        "diyabetik_tanilar": DIYABETIK_TANILAR,
    }, f, ensure_ascii=False, indent=2)

print(f"hastalar: {len(hastalar)}  talepler: {len(talepler)}  snapshot: {len(snapshots)}  "
      f"beklenen aksiyon: {len(beklenen)}")
