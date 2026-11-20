# {{CLIENT_NAME}} — müşteri dosyası

Slug: `{{CLIENT_SLUG}}` · Domain: {{CLIENT_DOMAIN}} · Eklendi: {{DATE}}

## Durum

| Alan | Durum | Not |
| --- | --- | --- |
| Marka kılavuzu | ⬜ doldurulacak | `brand-guide.md` |
| Personalar | ⬜ doldurulacak | `personas.md` |
| GSC erişimi | ⬜ | service account mülke eklendi mi |
| GA4 erişimi | ⬜ | property id config'te mi |
| Cloudflare zone | ⬜ | token bu zone'u görüyor mu (`cloudflare_ops.py check --client {{CLIENT_SLUG}}`) |
| Son site denetimi | — | `audits/` |
| Aktif kampanya | — | `campaigns/` |

## Klasörler

- `brand-guide.md`, `personas.md` — ajanların ilk okuduğu kaynak
- `campaigns/<YYYY-MM>-<ad>/` — plan.md (reklam-stratejisti), metinler (metin-yazari), denetim notu (marka-denetcisi kararı), sonuç
- `content/` — blog, senaryo, e-posta
- `seo/reports/` — gsc/ga4/pagespeed çıktıları (betikler `--out` ile yazar)
- `audits/` — site-denetcisi raporları
- `research/` — rakip analizleri
- `youtube-research/` — transkript ve yorum dosyaları (NotebookLM kaynağı)
- `infra/` — cloudflare-log.md (yazma işlemleri kaydı), DNS/hosting notları (erişim bilgisi DEĞİL)

## Günlük

- {{DATE}} Müşteri dosyası açıldı.

## Öğrenilenler (ne işe yaradı / yaramadı)

- (henüz yok)
