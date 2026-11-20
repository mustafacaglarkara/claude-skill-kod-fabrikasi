# .credentials/ — kimlik dosyaları (git DIŞI, Claude OKUYAMAZ)

Bu klasör `.gitignore`'da ve `.claude/settings.json` `deny` listesindedir. **API anahtarları burada değil, proje kökündeki `.env.dev` dosyasındadır** (şablon: `.env.dev.example`); betikler (`.claude/scripts/ajans/*.py`) `.env.dev`'i kendileri okur, değerleri hiçbir çıktıya yazmaz. Buraya yalnızca dosya biçimindeki kimlikler konur.

## Dosyalar

- `service-account.json` — Google Cloud service account anahtarı (GSC + GA4). Search Console'da her mülke, GA4'te her property'ye bu hesabın e-postasını "Görüntüleyici/Kısıtlı" olarak ekleyin. API'ler: Search Console API, Analytics Data API etkin olmalı. Farklı bir yol kullanıyorsanız `.env.dev` → `GOOGLE_APPLICATION_CREDENTIALS`.
- (eski) `.env` — v3.1 öncesi anahtar dosyası; hâlâ okunur ama yeni anahtarlar `.env.dev`'e.

## `.env.dev` anahtarları (ajans)

`CLOUDFLARE_API_TOKEN` (scoped token; izinler `references/cloudflare.md`), `CLOUDFLARE_ACCOUNT_ID` (Pages), `PAGESPEED_API_KEY`, `YOUTUBE_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`.

## Güvenlik

- Dosyaları paylaşmayın, Drive/NotebookLM'e yüklemeyin (paket yalnızca git'in izlediği dosyalardan oluşur; bu klasör ve `.env.dev` hiç girmez).
- Token'ı yenilediğinizde eskisini Cloudflare'de iptal edin.
- `kf.py secret-scan` `.env*` değerlerinin izlenen dosyalara sızmadığını her commit'te denetler.
