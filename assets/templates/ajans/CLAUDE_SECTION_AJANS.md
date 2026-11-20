
**Dijital ajans profili.** Müşteriler `{{CLIENTS_DIR}}/<slug>/` altında izole; her brif TEK müşteri söyler, ajan başka müşterinin klasörünü açmaz. Üreten ajan kendi işini onaylamaz: metin → `marka-denetcisi` ONAY olmadan teslim edilmez; site → `site-denetcisi` raporu olmadan "yayına hazır" denmez. Araçlar `python .claude/scripts/ajans/<betik>.py --client <slug>`; kimlikler `{{CREDENTIALS_DIR}}/.env` (Claude okumaz, betik okur).

| Durum | Ajan |
| --- | --- |
| Reklam/sosyal/e-posta/blog/video metni (onaylı brif) | `metin-yazari` (yalnızca `{{CLIENTS_DIR}}/<slug>/campaigns|content`) |
| Her metin tesliminden önce marka + politika + iddia denetimi | `marka-denetcisi` (zorunlu; salt okunur) |
| GSC/GA4/PageSpeed verisi, trafik düşüşü, CTR açığı, aylık SEO raporu | `seo-teknisyeni` (betikleri çalıştırır; salt okunur) |
| Rakip site/YouTube analizi, içerik boşluğu | `rakip-analisti` (salt okunur; youtube_fetch → NotebookLM) |
| Site teslim öncesi / yayın sonrası / periyodik denetim | `site-denetcisi` (site_audit + pagespeed + cloudflare check) |
| Cache purge, yönlendirme, DNS, SSL/WAF ayarı, trafik/saldırı | `cloudflare-operatoru` (önce PLAN, sonra `--yes` = kullanıcı onayı) |
| Landing page, tema, GTM/piksel kodu | `gelistirici` → `tester` → `site-denetcisi` |
{{AGENCY_OPTIONAL_ROWS}}

Müşteriler: {{CLIENT_LIST}} (`kf.py client add --slug ... --name ... --domain ...` ile ekle).
