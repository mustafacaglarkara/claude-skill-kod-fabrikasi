# .credentials/ — kimlik bilgileri (git DIŞI, Claude OKUYAMAZ)

Bu klasör `.gitignore`'da ve `.claude/settings.json` `deny` listesindedir. Betikler (`.claude/scripts/ajans/*.py`) buradaki `.env` dosyasını kendileri okur; değerleri hiçbir çıktıya yazmaz.

## Dosyalar

- `.env` — `env.example`'dan kopyalayın:
  - `CLOUDFLARE_API_TOKEN` — API Token (Global API Key DEĞİL). Önerilen izinler: Zone:Read, Zone Settings:Edit, DNS:Edit, Cache Purge:Purge, Zone WAF:Edit, Analytics:Read, SSL and Certificates:Read, Page Rules:Read, Account › Cloudflare Pages:Read, Account Settings:Read. "Zone Resources" ile yalnızca ajansın yönettiği zone'lara kısıtlayın. Silme izni vermeyin.
  - `CLOUDFLARE_ACCOUNT_ID` — Pages komutları için (dashboard › hesap › sağ sütun).
  - `PAGESPEED_API_KEY` — Google Cloud › PageSpeed Insights API (anahtarsız kota çok düşük).
  - `YOUTUBE_API_KEY` — Google Cloud › YouTube Data API v3.
  - `GOOGLE_APPLICATION_CREDENTIALS` — service account JSON yolu (varsayılan: bu klasördeki `service-account.json`).
- `service-account.json` — Google Cloud service account anahtarı. Search Console'da her mülke, GA4'te her property'ye bu hesabın e-postasını "Görüntüleyici/Kısıtlı" olarak ekleyin. API'ler: Search Console API, Analytics Data API etkin olmalı.

## Güvenlik

- Dosyaları paylaşmayın, Drive/NotebookLM'e yüklemeyin (paket yalnızca git'in izlediği dosyalardan oluşur; bu klasör hiç girmez).
- Token'ı yenilediğinizde eskisini Cloudflare'de iptal edin.
- `kf.py secret-scan` bu klasörü görmez; yanlışlıkla başka yere kopyalanmış değerleri yakalar.
