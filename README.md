# UcuzBilet Avcisi

Google Flights uzerinden **en ucuz nereye gidebilirim** sorusuna cevap arayan yerel uygulama.

Konum: `Documents/ucuzbilet.online`

Surum: `app/version.py` icindeki `BETA_BUILD` — her canliya cikista +1 artirin (ornek: beta 1.03, beta 1.04, ... beta 1.10, beta 1.11).

## Ozellikler

- **Kalkis:** ulke, sehir (tum havalimanlari) veya tek havalimani
- **3 arama modu:**
  - **Belirli gidis + X gun kalis** — kesin tarihle destinasyon taramasi
  - **Tarih araliginda en ucuz** — verilen aralikta N gunluk en ucuz rotalar
  - **Esnek (deal haritasi)** — Google Explore firsat listesi (hizli)
- **Filtreler:** bolge (Avrupa, Amerika…), Star Alliance / Oneworld / SkyTeam, aktarma, max fiyat
- Kayitli aramalar ve gecmis sonuclar

## Baslatma

`UcuzBilet-Avcisi.bat` dosyasina cift tiklayin veya:

```powershell
cd $env:USERPROFILE\Documents\ucuzbilet.online
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Tarayici: http://127.0.0.1:8787

## Mod secimi

| Mod | Ne zaman |
|-----|----------|
| Esnek | Hizli fikir almak icin; Google'in deal listesi |
| Belirli gidis + X gun | "4 Temmuz gidis, 5 gun kal, nereye ucuz?" |
| Tarih araligi | "4-20 Temmuz arasi 5 gunluk en ucuz destinasyonlar" |

## Not

Google Flights resmi API sunmuyor; veriler Google Explore / fast-flights uzerinden alinir. Fiyatlar anlik degisebilir.

## Render (ucretsiz)

1. Projeyi GitHub'a push edin (`data/places.json`, `regions.json`, `explore_destinations.json` dahil).
2. [render.com](https://render.com) → **New** → **Blueprint** → repoyu secin (`render.yaml` otomatik algilanir).
   - veya **New Web Service** → Docker → repoyu secin, plan: **Free**.
3. Deploy bitince gecici adres: `https://ucuzbilet-online.onrender.com`
4. **Onemli:** Render servis adi `ucuzbilet` olamaz (baskasinda). Settings → servis adi **`ucuzbilet-online`** olmali; DNS hedefi o zaman `ucuzbilet-online.onrender.com` olur — `ucuzbilet.onrender.com` degil.
5. Asil domain **`ucuzbilet.online`** icin Render → **Custom Domains** → `ucuzbilet.online` + `www.ucuzbilet.online` ekleyin.
6. Domain saglayicinizda Render'in gosterdigi kayitlari girin (servis adi dogruysa hedef **`ucuzbilet-online.onrender.com`**):
   - **CNAME** `www` → `ucuzbilet-online.onrender.com`
   - **CNAME / ANAME / ALIAS** `@` → ayni hedef (veya Render'in verdigi **A** kaydi `216.24.57.1`)
   - Cloudflare kullaniyorsaniz proxy kapali (DNS only) olmali.

**Ucretsiz plan sinirlari:**
- 15 dk kullanilmazsa uyur; ilk acilis 30-60 sn surebilir.
- Kayitli aramalar restart'ta silinir (kalici disk yok).
- **Ucus fiyat taramasi** modu calisir; **Esnek harita** Render'da kapali (bellek).
- Deploy hatasi olursa Render **Logs** sekmesine bakin; son commit'i **Manual Deploy** ile cekin.
