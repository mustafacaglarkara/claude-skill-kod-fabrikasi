# Cloudflare Entegrasyonu — Tam Değerlendirme ve Kullanım

Araç: `.claude/scripts/ajans/cloudflare_ops.py` (yalnızca stdlib; Cloudflare API v4 + GraphQL Analytics). Ajan: `cloudflare-operatoru`. Kimlik: `.credentials/.env` → `CLOUDFLARE_API_TOKEN` (+ `CLOUDFLARE_ACCOUNT_ID` Pages için). Claude token'ı hiç görmez; betik okur, hiçbir çıktıya yazmaz.

## Neden API (dashboard yerine)

- Çok müşteri: her zone için aynı sağlık kontrolü tek komutla (`check --client x`), rapor dosyaya.
- Değişiklik ↔ yayın bağı: SEO/metin güncellemesi yayına alınınca yalnızca değişen URL'ler purge edilir; dashboard'da "purge everything" refleksi origin'i yorar.
- Denetim izi: her yazma `clients/<slug>/infra/cloudflare-log.md`'ye tarih + komut + sonuç olarak düşer.
- Güvenlik: scoped token + settings.json `ask`/`deny` + betik içi `--yes` zorunluluğu = üç katman.

## Token nasıl oluşturulur (bir kez, insan yapar)

Cloudflare dashboard → My Profile → API Tokens → Create Token → Custom. Önerilen izinler:

| Kapsam | İzin | Ne için |
| --- | --- | --- |
| Zone | Zone: Read | `zones`, zone id çözümü |
| Zone | Zone Settings: Edit | `check`, `settings`, `setting set`, `dev-mode`, `under-attack` |
| Zone | DNS: Edit | `dns list/add/update` (delete Claude için DENY) |
| Zone | Cache Purge: Purge | `purge`, `purge-all` |
| Zone | Zone WAF: Edit | `firewall list/add/remove`, `redirect` (ruleset API) |
| Zone | SSL and Certificates: Read | `ssl`, `check` |
| Zone | Analytics: Read | `analytics`, `security-events` |
| Zone | Page Rules: Read | `pagerules` |
| Zone | Bot Management: Read (planda varsa) | `check` → Bot Fight Mode satırı |
| Account | Cloudflare Pages: Read | `pages list/deployments` |
| Account | Account Settings: Read | hesap id çözümü |

Zone Resources: **Include → Specific zone** ile yalnızca ajansın yönettiği zone'lar. Zone silme, kullanıcı/üyelik izni **verme**. Token'ı `.credentials/.env`'e yaz; `kf.py selftest` dosyanın git'te olmadığını doğrular.

Doğrulama: `python .claude/scripts/ajans/cloudflare_ops.py zones` → listede müşteri zone'ları görünmeli.

## Komut matrisi

| Komut | Tür | settings.json | Betik kapısı |
| --- | --- | --- | --- |
| `zones`, `check`, `settings`, `dns list`, `ssl`, `analytics`, `security-events`, `firewall list`, `redirect list`, `pagerules`, `pages list/deployments` | okuma | serbest | — |
| `purge --urls/--prefixes/--tags/--hosts` | yazma (geri alınamaz ama zararsız) | ask | `--yes` |
| `purge-all` | yazma (origin yükü) | ask | `--yes`; yalnızca kullanıcı açıkça isterse |
| `redirect add/remove` | yazma (SEO etkisi) | ask | `--yes`; önce `redirect list` (döngü) |
| `dns add/update` | yazma (erişilebilirlik) | ask | `--yes`; önce `dns list`; TTL/proxy planda |
| `setting set`, `dev-mode`, `under-attack` | yazma (ayar) | ask | `--yes`; geri alma planı raporda |
| `firewall add/remove` | yazma (erişim engeli) | ask | `--yes`; ifade `log` ile önce test |
| `dns delete` | silme | **deny** (Claude) | insan terminalden `--yes` ile |
| zone silme | — | uygulanmadı | dashboard |

`--yes` olmadan her yazma komutu yalnızca **PLAN** basar ve çıkar (dry-run). Ajan önce PLAN'ı raporlar, ana oturum kullanıcıya gösterir, onay gelince aynı komut `--yes` ile. settings `ask` o anda bir kez daha sorar; bu çift onay bilinçlidir.

`Bash(*cloudflare_ops.py purge*)` gibi kurallar komutun ortasında joker kullanır; Claude Code sürümünüz ortada `*` desteklemiyorsa (`/permissions` ekranında kural "geçersiz" görünür) kuralı `Bash(python *)` yerine tam yol önekiyle yazın: `Bash("C:\...\python.exe" .claude/scripts/ajans/cloudflare_ops.py purge*)`. `kf.py selftest` kuralın varlığını kontrol eder, geçerliliğini edemez: ilk kullanımda bir purge komutunun gerçekten sorulduğunu gözle teyit edin.

## `check` ne ölçer ve nasıl yorumlanır

| Satır | İyi | Neden önemli |
| --- | --- | --- |
| SSL modu | `strict` | `flexible` = origin'e HTTP → karma içerik/yönlendirme döngüsü; `full` = sertifika doğrulanmaz. `strict`'e geçmeden origin sertifikası geçerli olmalı (`ssl`), yoksa 526. |
| Universal SSL | aktif | Sertifika yoksa HTTPS çalışmaz (yeni zone'da 15 dk sürebilir). |
| Always Use HTTPS / Automatic HTTPS Rewrites | on | SEO: HTTP → HTTPS tek adımda; karma içerik düzeltmesi. |
| Min TLS / TLS 1.3 | ≥1.2 / on | Güvenlik tarayıcıları ve PCI. |
| HSTS | on, max-age ≥ 6 ay | Tarayıcı HTTPS'i zorlar; `includeSubDomains` alt alanlar HTTPS'siz ise kırar: önce doğrula. |
| DNSSEC | active | DNS sahteciliğine karşı; registrar'da DS kaydı gerekir. |
| Development Mode | off | **On ise cache kapalı**; biri açıp unutursa origin yükü ve yavaşlık. |
| Cache Level / Browser TTL | aggressive / makul | Statik site/landing page için en büyük hız kazancı. |
| Brotli / HTTP/3 / Early Hints | on | CWV (LCP) için bedava kazanç. |
| Security Level | medium | `under_attack` unutulursa tüm ziyaretçiler challenge görür (dönüşüm düşer). `essentially_off` bot istilasına açık. |
| Bot Fight Mode | on | Kötü bot trafiği; Pro+ planda Super Bot Fight Mode. |
| Özel WAF kuralı / Yönlendirme kuralı | sayı | Envanter; beklenmedik kural = birinin "geçici" dokunuşu. |
| Apex proxy | proxy'li | Proxy'siz A kaydı = gerçek IP açık, WAF/cache devre dışı. (E-posta/MX kayıtları doğal olarak proxy'siz.) |
| Rocket Loader | off | JS sırasını değiştirir; GTM/piksel/animasyon kırar. Açık ise test edilmiş olmalı. |
| Email Obfuscation | on | Sayfadaki e-postaları bot'lardan gizler. |

Önerilen yeni site standardı: `ssl strict`, `always_use_https on`, `automatic_https_rewrites on`, `min_tls_version 1.2`, `tls_1_3 on`, `brotli on`, `http3 on`, `early_hints on`, `security_level medium`, `browser_check on`, `development_mode off`, `rocket_loader off`, HSTS (alt alanlar HTTPS ise) → her biri `setting set --key <ayar> --value <değer>`.

## Tipik senaryolar

```bash
P=".claude/scripts/ajans/cloudflare_ops.py"
python $P check --client musteri-a --out clients/musteri-a/audits/2026-11-20-cloudflare.md
python $P analytics --client musteri-a --days 7            # yayın sonrası trafik akıyor mu, cache oranı
python $P security-events --client musteri-a --hours 24    # saldırı mı, bot mu, hangi yol
python $P purge --client musteri-a --urls https://musteri-a.com/ https://musteri-a.com/hizmetler/   # PLAN
python $P purge --client musteri-a --urls https://musteri-a.com/ https://musteri-a.com/hizmetler/ --yes
python $P redirect add --client musteri-a --from /eski-hizmet --to https://musteri-a.com/hizmetler/yeni --status 301 --preserve-query
python $P redirect add --client musteri-a --from /blog/ --to https://musteri-a.com/yazilar/ --wildcard   # /blog/* → tek hedef
python $P dns add --client musteri-a --type CNAME --name www --content musteri-a.pages.dev --proxied
python $P setting set --client musteri-a --key always_use_https --value on
python $P under-attack on --client musteri-a            # saldırı; iş bitince: under-attack off --restore medium
python $P firewall add --client musteri-a --expression '(ip.geoip.country ne "TR" and http.request.uri.path contains "/wp-login")' --action managed_challenge --description "wp-login TR dışı challenge"
python $P pages deployments --project musteri-a-site --n 3   # Pages'te son dağıtım başarılı mı
```

Site taşıma (yeni site yayına alma) sırası: `dns list` (mevcut) → yeni origin/Pages hazır ve `curl --resolve` ile test edildi → `dns update` (TTL kısa) → `check` → `purge-all --yes` (bir kez, yeni içerik) → `site_audit.py --client x --crawl 30 --links` → `analytics --days 1` → 24 saat sonra `dev-mode off` ve `security-events`.

## Sınırlar ve bilinçli dışarıda bırakılanlar

- **Workers/Pages deploy** betikte yok: `wrangler deploy` / `wrangler pages deploy` proje build zincirine aittir; settings `ask`'ta. Betik yalnızca dağıtım durumunu okur.
- **Zone oluşturma/silme, üyelik, fatura**: dashboard. Yanlışlıkla silme riski > otomasyon faydası.
- **Bulk Redirects (hesap düzeyi listeler)**: binlerce yönlendirme için dashboard/CSV; betik zone düzeyi dinamik yönlendirme (ruleset) kullanır — 125 kural/zone (Free) sınırı var; aşarsa Bulk Redirects.
- **Load balancer, Spectrum, Access, Tunnel**: ajans siteleri için nadir; gerekirse `settings`/`cf_try` kalıbıyla eklenir (tuzaklar: yazma komutu = `write_guard` + `audit` zorunlu).
- **GraphQL verisi** Free planda 7 gün / saatlik; `analytics --days 30` kısa dönebilir.
- Oran limiti: 1200 istek / 5 dk / kullanıcı; `check` ~8 istek. Çok müşteriyi döngüde kontrol ederken sorun olmaz.

## Hata kodları (sık)

| HTTP / kod | Anlam | Yap |
| --- | --- | --- |
| 400 6003/6111 | Authorization başlığı bozuk | token boş/yanlış biçim; `.env` değeri tırnaksız mı |
| 403 9109 / 10000 | token bu zone'a/izne sahip değil | token izin/zone kapsamı; `check` okunamayan satırı "okunamadi" yazar |
| 404 zone | isim yanlış ya da token kapsam dışı | `zones` ile liste |
| 526 (siteyi ziyaret) | `strict` ama origin sertifikası geçersiz | `ssl` ile paket; origin'de geçerli sertifika ya da Origin CA |
| 1015 / 429 | oran limiti | bekle; döngüde `sleep` |
| ruleset 20021/20012 | ifade sözdizimi | ifadeyi dashboard "Expression editor"da doğrula |
