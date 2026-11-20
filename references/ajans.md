# Dijital Ajans Profili — İş Akışları, İzolasyon, QA Kapısı

`kf.py init --profile ajans` (ya da mevcut v3 projede `kf.py profile ajans`) çekirdek ekibi korur (kesifci, gelistirici, tester, reviewer, faz-arsivcisi) ve üstüne ajans katmanını kurar. Faz hafızası, hook'lar, graphify, Drive/NotebookLM aynı şekilde çalışır. Kaynak: dijital ajans orkestrasyon raporu ve yapılandırma belgesi (2026-11); adlar ekip konvansiyonuna göre Türkçeleştirildi (`copywriter` → `metin-yazari`, `brand-guardian` → `marka-denetcisi`, `seo-technician` → `seo-teknisyeni`, `competitor-analyst` → `rakip-analisti`, `web-developer` → çekirdek `gelistirici`, `account-archivist` → çekirdek `faz-arsivcisi`; eklenenler: `site-denetcisi`, `cloudflare-operatoru`, isteğe bağlı `reklam-stratejisti`).

## Üç ilke (brif yazarken her seferinde)

1. **Müşteri izolasyonu**: her brif `MÜŞTERİ: <slug>` satırı taşır; `DOKUNMA:` listesine `clients/<diğer-slug>/**` yazılır. `marka-denetcisi` 6. maddede çapraz sızıntıyı arar. Bir brifte iki müşteri olmaz; karşılaştırma gerekiyorsa iki ayrı salt okunur ajan + ana oturum birleştirir.
2. **QA kapısı**: üreten ajan kendi işini onaylamaz. Metin → `marka-denetcisi` (ONAY / DÜZELTME / RED). Site/kod → `tester` + `site-denetcisi`. Cloudflare yazma → PLAN → kullanıcı onayı → `--yes`. "Teslim edildi" yalnızca kapı geçildiyse yazılır.
3. **Token ekonomisi**: ham veri ajana gitmez; betikler (`.claude/scripts/ajans/`) filtrelenmiş Markdown özeti üretir ve `--out` ile müşteri klasörüne yazar. Ajan özeti okur, yorumlar.

## Ekip (ajans katmanı)

| Ajan | Model / effort | Yazar | Ne için | Kapı |
| --- | --- | --- | --- | --- |
| `metin-yazari` | sonnet / medium | yalnızca `clients/<slug>/campaigns|content` | reklam, sosyal, e-posta, blog, video senaryosu | → `marka-denetcisi` |
| `marka-denetcisi` | sonnet / high, maxTurns 40 | ❌ | marka tonu, yasaklı kelime, platform politikası, iddia doğruluğu, kanca, sızıntı | kendisi kapıdır |
| `seo-teknisyeni` | sonnet / medium, maxTurns 60 | ❌ (betikler `--out` yazar) | GSC/GA4/PageSpeed → öncelikli aksiyon listesi | — |
| `rakip-analisti` | sonnet / medium, maxTurns 60 | ❌ | rakip hiyerarşi/schema/içerik boşluğu, YouTube transkript → NotebookLM | — |
| `site-denetcisi` | sonnet / medium, maxTurns 60 | ❌ | teslim öncesi / yayın sonrası / periyodik site testi | kendisi kapıdır |
| `cloudflare-operatoru` | sonnet / medium, maxTurns 40 | dosya ❌, API ✅ (`--yes`) | zone sağlığı, purge, redirect, DNS, WAF, dev-mode, under-attack | PLAN → onay |
| `reklam-stratejisti` (isteğe bağlı) | sonnet / medium, maxTurns 40 | ❌ | kanal/bütçe/huni/UTM/test planı | — |

Landing page, tema, GTM/piksel kodu çekirdek `gelistirici`'ye gider (opus; onaylı plan, `tester`, `reviewer`), sonra `site-denetcisi` canlıda doğrular. Kampanya arşivi ve müşteri `README.md` günlüğü `faz-arsivcisi` tarafından güncellenir (planlama belgeleri kuralı müşteri README'lerini de kapsar).

## Müşteri çalışma alanı

```text
clients/<slug>/
├── README.md            # durum tablosu, günlük, öğrenilenler (faz-arsivcisi yazar)
├── brand-guide.md       # ton, yasaklı kelimeler, CTA, rakipler, kanallar (kullanıcı doldurur)
├── personas.md          # hedef kitle, acı noktaları, itirazlar
├── campaigns/<YYYY-MM>-<ad>/   plan.md (reklam-stratejisti) · metinler (metin-yazari) · denetim.md (marka-denetcisi kararı) · sonuc.md
├── content/             # blog, senaryo, e-posta
├── seo/reports/         # gsc/ga4/pagespeed çıktıları (betik --out)
├── audits/              # site-denetcisi raporları (<tarih>-site.md, -cwv.md, -cloudflare.md)
├── research/            # rakip analizleri
├── youtube-research/    # transkript + yorum (NotebookLM kaynağı)
└── infra/cloudflare-log.md   # yazma işlemleri kaydı (betik ekler)
shared/copywriting-frameworks.md · shared/ad-policies.md   # ortak kütüphane
.credentials/.env · service-account.json                   # git dışı, Claude okuyamaz; betikler okur
```

Config: `agency.clients[]` → `slug, name, domain, cloudflare_zone, gsc_site, ga4_property, pagespeed_urls`. Ekleme: `kf.py client add --slug x --name "X" --domain x.com [--zone] [--gsc sc-domain:x.com] [--ga4 123] [--url https://x.com/]`. Betikler `--client x` ile bu değerleri alır.

## Akışlar

### A. Kreatif üretim (reklam / sosyal / e-posta / video)

1. Bağlam: `clients/<slug>/brand-guide.md`, `personas.md`; varsa son `research/` ve `seo/reports/` (hangi sorgu/sayfa?). NotebookLM içgörüsü varsa brife kopyala (ajan NotebookLM'e erişmez).
2. (Büyük kampanya) `reklam-stratejisti` → plan.md; kullanıcı kararları (bütçe, kanal) → onay.
3. Plan + **ONAY** (kanal, varyant sayısı, persona, teklif, hedef URL, dosya adı).
4. `metin-yazari` brifi:
   ```text
   MOD: BUILD · MÜŞTERİ: <slug> · HEDEF: <tek cümle>
   KANAL/FORMAT: Meta birincil metin + başlık ×3 varyant; persona: <ad>; çerçeve: PAS
   TEKLİF (doğrulanmış): ... · HEDEF URL: ... · YASAKLI: brand-guide §Yasaklı
   İÇGÖRÜLER: <NotebookLM/rakip/SEO alıntıları>
   ÇIKTI: clients/<slug>/campaigns/2026-11-<ad>/meta-v1.md
   DOKUNMA: clients/<diğer>/**, shared/**, .claude/**
   ```
5. `marka-denetcisi` brifi: dosya yolu, slug, platform. Karar DÜZELTME/RED → bulgular `dosya:satır` ile **yeni** `metin-yazari`'ya; sonra tekrar `marka-denetcisi` (yalnızca değişen varyantlar).
6. Kullanıcıya: varyantlar, denetçi kararı, doğrulanması gereken iddialar, yer tutucular. `faz-arsivcisi` → müşteri README günlüğü + `denetim.md`.

### B. SEO raporu / "trafik neden düştü"

1. `seo-teknisyeni` brifi: slug, soru, dönem, istenen modlar. Ajan betikleri `--out clients/<slug>/seo/reports/<tarih>-<mod>.md` ile çalıştırır.
2. Rapor: aksiyon tablosu (öncelik · sayfa/sorgu · yapılacak · kim). Ana oturum teyit eder (rakam betik çıktısında var mı).
3. Aksiyonlar dağıtılır: title/description → `metin-yazari` (+ `marka-denetcisi`); teknik/schema → plan + ONAY → `gelistirici` → `tester` → `site-denetcisi`; yayın sonrası `cloudflare-operatoru purge --urls` (ask).
4. Kimlik yoksa betik açık hata verir; ajan "doğrulanamadı" yazar. Kurulum: `.credentials/README.md`.

### C. Site denetimi (yaptığımız siteleri test etme)

Tetikleyici: "siteyi kontrol et", "teslim öncesi", "yayına aldık", aylık periyodik.

1. `site-denetcisi` brifi: slug/URL, tür (teslim öncesi → `--crawl 30 --links`; periyodik → `--crawl 15`; tek sayfa), önceki denetim dosyası (karşılaştırsın).
2. Rapor: TESLİME HAZIR / DÜZELTME / YAYINLANAMAZ; kritikler; düzeltme listesi (kim). Ana oturum kritikleri teyit eder (`curl -sI`).
3. Kod düzeltmesi varsa: plan + ONAY → `gelistirici` (projede kaynak varsa `dosya:satır`) → `tester` → **yeni** `site-denetcisi` yalnızca kırmızı maddeler için.
4. Cloudflare bulguları (`check` ❌/⚠️) → `cloudflare-operatoru` PLAN → onay → `--yes`.
5. Teslim öncesi insan kontrol listesi (betik ölçemez): formlar gerçekten e-posta gönderiyor mu, ödeme test modu kapalı mı, analytics/piksel gerçek ID mi, yasal sayfalar (KVKK, çerez), 404/500 tasarımı, mobil gerçek cihaz.

### D. Rakip analizi ve içerik boşluğu

`rakip-analisti` → `site_audit.py --competitor` (rakip + müşteri sayfası) → tablo → ilk 3 içerik önerisi → ONAY → `metin-yazari` (blog) / `gelistirici` (yeni sayfa + schema) / `seo-teknisyeni` (hedef sorgu, `inspect`).

### E. YouTube araştırması (NotebookLM)

1. `rakip-analisti`: `youtube_fetch.py --search "<konu>" --max 10 --out clients/<slug>/youtube-research` (ya da `--channel @rakip`, `--video URL`). Çıktı `<id>.md` + `_index.md`.
2. Ana oturum / kullanıcı: dosyaları NotebookLM'e kaynak ekler (notebooklm MCP `source_add` ya da `notebooklm source add`; proje notebook'u yerine müşteriye özel notebook önerilir: izolasyon).
3. Üç soru: "ilk 30 saniyede hangi kanca teknikleri?", "yorumlarda en çok yakınılan / istenen ne?", "rakiplerin değinmediği 3 kritik konu?". Cevaplar brife kopyalanır.
4. `metin-yazari` → Shorts kurgusu, ana video senaryosu, SEO uyumlu başlık/açıklama → `marka-denetcisi`.

### F. Cloudflare operasyonu

Ayrıntı: [cloudflare.md](cloudflare.md). Kısa: okuma serbest; yazma = PLAN (`--yes`'siz) → kullanıcıya göster → onay → `--yes` (settings `ask` tekrar sorar; beklenen). `purge-all`, `dns delete`, zone silme: ilk ikisi yalnızca kullanıcı açıkça isterse (dns delete Claude için DENY), zone silme hiç yok.

## Faz hafızası ile ilişki

Ajans işleri de faz/adım olarak PROGRESS'e girer ("Faz 7: Müşteri A Kasım kampanyası"), kararlar ADR'ye ("ADR-014: Müşteri A için Meta yerine Google Performance Max"), müşteri bazlı günlük `clients/<slug>/README.md`'ye. `faz_hafiza.py` hook'u oturum başında müşteri listesini ve son çalışma dosyalarını yükler. Kampanya sonuçları (`sonuc.md`) ve "Öğrenilenler" bölümü sonraki brifin girdisidir.

## Sık hatalar

- Brifte müşteri slug'ı yok → ajan yanlış klasöre yazar. Şablonu kullan.
- `marka-denetcisi` atlanıp "küçük düzeltme" diye teslim → politika ihlali hesap kapatır. Kapı esnemez.
- Betik çıktısını ajana yapıştırmak yerine ajana "çalıştır" demek doğru; ama aynı betiği aynı parametreyle iki ajan çalıştırmasın (kota).
- `--yes`'i plan göstermeden kullanmak: `ask` kuralı sorar ama kullanıcı ne olduğunu bilmeden "evet" der. Önce PLAN.
- NotebookLM proje notebook'una müşteri verisi yüklemek: müşteriler arası sızıntı. Müşteri başına notebook.
