# Misafir Yönetimi – Sahte Veri Seti

26.11.2026 tarihli, 3 hastane için tek günlük simülasyon (07:00–22:00).
`python generate_data.py` aynı seed ile veriyi baştan üretir.

## Dosyalar (`data/`)

| Dosya | İçerik |
|---|---|
| `hastaneler.csv` | 3 hastane (H01 Merkez, H02 Kuzey, H03 Sahil), kat ve yatak sayıları |
| `sorumlular.csv` | Her hastanenin Destek Hizmetleri Müdürü (bildirim alıcısı) |
| `hastalar.csv` | 199 yatan hasta: kat, oda, **Hasta Türü** (Normal/VIP), yatış tanıları (ICD-10), **Diyabetik Hasta** bayrağı, yatış/taburcu zamanı |
| `talepler.csv` | 552 asistan uygulaması talebi: **Talep Türü** (KAFE / TEMIZLIK-ODA / TEKNIK HIZMETLER), detay, oluşturma/tamamlanma zamanı, durum, süre, gecikme eşiği |
| `genel_bakis_snapshots.csv` | **Genel Bakış ekranı**, 10 dk'da bir (08:00–22:00), hastane (`kat=TUMU`) ve kat bazında |
| `beklenen_aksiyonlar.csv` | Akış şemasına göre hangi kontrolde uyarı + iş istem açılması gerektiği (graph'ı test etmek için doğru cevaplar) |
| `is_istemler.csv` | Boş "İş İstem" tablosu; graph buraya kayıt ekler |
| `config.json` | Eşikler, snapshot aralığı, diyabetik tanı listesi |

## Genel Bakış kolonları

Her talep türü için önek: `kafe_`, `temizlik_oda_`, `teknik_`

- `yatan_hasta_sayisi`, `talebi_olan_hastalar`, `toplam_talep`
- `<tür>_hasta_sayisi`, `<tür>_hasta_orani` → talebi olan hasta / yatan hasta
- `<tür>_bekleyen`, `<tür>_geciken`
- `<tür>_gecikme_orani` → **KPI** = geciken / o türdeki aktif talep

## Hesaplama varsayımları

- **Aktif talep**: zaman `t`'de oluşturulmuş ve henüz tamamlanmamış talep.
- **Geciken**: aktif ve beklemesi eşiği aşan talep. Kafe için 45 dk, temizlik-oda ve teknik için 60 dk.
- **Alarm**: hastane bazında `gecikme_orani >= 0.20` olunca 1. uyarı gider ve iş istem açılır. Oran %20'nin altındaysa takip durur.

## Gömülü senaryolar

| Hastane | Senaryo | Beklenen alarm saatleri |
|---|---|---|
| H01 | Öğle (11:30–14:00) ve akşam (18:00–19:30) kafe yoğunluğu | Kafe ≈ 12:50–15:40, 19:50–20:10 (ayrıca sabah 09:40–10:40) |
| H02 | Öğleden sonra teknik ekip yavaşlıyor | Teknik ≈ 15:20–18:10 |
| H03 | Sabah temizlik yığılması | Temizlik ≈ 10:40–12:20 |

Bunlara ek olarak az sayıda rastgele gecikme var. Aktif talep sayısı azken tek bir geciken talep oranı yükseltebiliyor, bu da gerçek hayattaki gürültüyü taklit ediyor.

## LangGraph'ta kullanım

```python
from data_loader import MisafirVeri
veri = MisafirVeri("data")

for zaman in veri.snapshot_zamanlari():          # 10 dk'lık döngü
    for h in veri.hastaneler:
        oran = veri.gecikme_orani(h["hastane_id"], "KAFE", zaman)
        if oran >= veri.config["kpi_alarm_esigi"]:
            geciken = veri.geciken_talepler(h["hastane_id"], "KAFE", zaman)
            veri.is_istem_ac(h["hastane_id"], "KAFE", oran, zaman,
                             aciklama=f"{len(geciken)} geciken kafe talebi")
```
