# Yol Haritası — Kod Fabrikası skill'i

Skill'in kendi gelecek planı (projelerin ROADMAP'i değil). Her madde: neden, ne gerekir, karar durumu. Öncelik P0 (sıradaki sürüm) / P1 / P2 (fikir). Tamamlananlar CHANGELOG'a taşınır.

## Durum özeti

| Sürüm | Tema | Durum |
| --- | --- | --- |
| 3.0 | Ajan ekibi + faz hafızası + `kf.py` | ✅ 2026-11-20 |
| 3.1 | Dijital ajans profili + API betikleri + plugin güçlendirmeleri | ✅ 2026-11-20 |
| 3.2 | Finans katmanı (B: ajans/şirket finans operasyonu) | 🟡 planlandı, karar bekliyor |
| 3.3 | `finans` profili (A: finansal yazılım projeleri) | ⬜ fikir |
| 3.4 | Depo / stok yönetimi katmanı (`depo` departmanı) | 🟡 planlandı |
| — | Piyasa/yatırım analizi (C) | ⬜ düşük öncelik |

Kurulumun ilk sorusu "hangi departmanlar için?" (`kf.py init --department ...`): `yazilim` ve `ajans` hazır; `muhasebe` ve `depo` seçilince config'e yazılır (`departments`), `check`/`selftest` "katman bekliyor" gösterir, katman yayımlanınca `kf.py repair` ekler. Yeni departman eklemek = `DEPARTMENTS` sözlüğüne giriş + profil/katman kodu + bu dosyada bölüm.

## P1 — 3.2: Finans katmanı (ajans/şirket finans operasyonu)

Neden: ajans profili müşteri bazlı çalışıyor; fatura, tahsilat, kampanya bütçesi ve kârlılık aynı müşteri klasörüne doğal olarak oturur. Mevcut `ajans` profiline `finance` bloğu olarak eklenir; ayrı profil gerekmez.

Gerekenler:
- Ajanlar (hepsi salt okunur, para hareketi başlatmaz): `finans-analisti` (nakit akışı, gecikmiş alacak, müşteri bazlı kârlılık; `data` plugin'i varsa SQL/dashboard), `fatura-asistani` (taslak fatura ve hatırlatma metni; göndermez), `butce-denetcisi` (kampanya planı bütçesi ↔ gerçek harcama; `reklam-stratejisti` ile eşleşir).
- Betikler (`.claude/scripts/finans/`): Paraşüt/Logo/QuickBooks **okuma** API'si (`invoices`, `receivables`), banka ekstre CSV ayrıştırıcı (banka formatları konfigürasyonla), TCMB kur (`kur_cek.py`), e-fatura durum sorgusu. Hepsi `--client <slug>`, `--out`; kimlikler `.credentials/.env`.
- Veri: `finance/` (ajans geneli) ve `clients/<slug>/finance/` (sözleşme, fatura geçmişi, bütçe). Sınıflama: ticari sır; paket (`bundle`) ve NotebookLM'e **girmez** (`bundle.skip_prefixes` varsayılanına eklenir).
- Güvenlik: transfer, ödeme, fatura gönderimi, iade = DENY (betikte hiç uygulanmaz); `ask` yalnızca okuma kotası yüksek komutlar. Kişisel finansal veri (IBAN, TCKN) rapor çıktısında maskelenir (`_ortak.mask` genişler).
- Hafıza: aylık finans raporu `faz-arsivcisi` ile müşteri README'sine; ADR örneği "ADR: faturalar yalnızca X aracından kesilir".
- Tuzaklar: para için `float` yok (`Decimal`), yuvarlama kuralı tek yerde, KDV dahil/hariç karışıklığı, dönem kapanışı sonrası değişiklik.
- Karar bekleyen: hangi muhasebe aracı (Paraşüt / Logo / diğer), banka ekstre formatı, kimin görebileceği (ajans içi rol ayrımı).

## P2 — 3.3: `finans` profili (finansal yazılım projeleri)

Neden: fintech, ödeme, muhasebe, e-fatura entegrasyonu geliştiren projelerde yazılım profili yetmez; uyum ve mutabakat kapıları gerekir.

Gerekenler:
- Ajanlar: `finans-uzmani` (muhasebe kuralları, KDV, e-fatura/e-arşiv, BDDK/MASAK/PCI-DSS; alan uzmanı kalıbı), `uyum-denetcisi` (KVKK + PCI + denetim izi + yetki ayrımı; `reviewer`'a ek, zorunlu), `mutabakat-testcisi` (çift kayıt dengesi, yuvarlama, idempotency, çift gönderim testleri; `tester`'a ek). `guvenlik-inceleyici` ve `mimar` çekirdeğe girer.
- Config varsayılanları: `high_risk_areas = payments, ledger, migrations, auth`; `live_write_commands` ödeme sağlayıcı canlı çağrıları; sandbox → canlı geçiş `ask`.
- Betikler: `ledger_check.py` (defter dengesi, boşluklu fatura numarası, negatif stok), `kur_cek.py`, ödeme sağlayıcı sandbox doğrulayıcı (webhook imzası, idempotency anahtarı).
- Tuzaklar: float para, çift gönderim, zaman dilimi/dönem sınırı, geri alınamaz migration, test verisinde gerçek kart/TCKN, loglanan PAN.
- Settings: deny canlı ödeme/iade/transfer komutları ve prod bağlantı dizesi okuma; ask sandbox→canlı.
- Faz raporu şablonuna "uyum kontrol listesi" bölümü.

## P1 — 3.4: Depo / stok yönetimi katmanı (`depo` departmanı)

Neden: ajans ve yazılım dışında kullanıcının işletme tarafı; stok, sipariş ve sayım verisi ERP/e-ticaret sistemlerinde duruyor, raporlama ve anomali tespiti tekrar eden iş.

Gerekenler (taslak; karar bekliyor):
- Ajanlar (salt okunur; stok hareketi yazmaz): `stok-analisti` (devir hızı, ölü stok, yeniden sipariş noktası, ABC analizi), `siparis-takipcisi` (geciken/eksik sipariş, tedarikçi performansı), `sayim-denetcisi` (sayım ↔ sistem farkı, fark nedenleri raporu). Yazan tek ajan: `rapor-yazari` (yalnızca `depo/reports/`).
- Betikler (`.claude/scripts/depo/`): ERP/e-ticaret **okuma** API'si (Logo/Netsis/Mikro, Shopify/WooCommerce/Trendyol stok uçları; konfigürasyonla seçilir), barkod/SKU eşleme CSV, sayım dosyası ayrıştırıcı, yeniden sipariş hesaplayıcı (`--out`, `--json`).
- Veri: `depo/` (stok politikası, tedarikçi listesi, sayım kayıtları); kişisel veri yok ama ticari sır: paket/NotebookLM dışında (`bundle.skip_prefixes`).
- Güvenlik: stok düzeltme, sipariş oluşturma, fiyat değişikliği = DENY (betikte uygulanmaz); yalnızca rapor ve öneri. Dış sisteme yazan her şey insan onaylı, ERP arayüzünden.
- Hafıza: haftalık stok raporu `faz-arsivcisi` ile; "ölü stok eşiği %X" gibi kararlar ADR.
- Tuzaklar: birim dönüşümü (koli/adet), negatif stok, çoklu depo toplamı, tarih dilimi, SKU varyant karışıklığı.
- Karar bekleyen: hangi ERP/e-ticaret, çoklu depo var mı, sayım sıklığı, kimin görebileceği.

## P2 — Piyasa / yatırım analizi (C)

Ajansın işiyle ilgisi düşük; istenirse ayrı skill (`piyasa-analizi`) daha doğru: veri kaynakları (borsa API, TCMB), portföy risk, yatırım tavsiyesi vermeme kuralı, raporlama. Kod fabrikasının ajan/hafıza altyapısını kullanır, profil olarak eklenmez.

## P1 — Plugin güçlendirmeleri (3.1'de başladı; sürdürülecek)

- Katalog (`kf.py plugins`) her sürümde güncellenir: Anthropic kataloğundaki yeni plugin'ler (örn. `writing-skills`, `design`, `data`) ilgili ajana eşlenir.
- `--preload` seçeneği: sık kullanılan tek skill'i `skills:` frontmatter ile ön yükleme (token maliyeti ölçülerek).
- Plugin MCP sunucuları (Cloudflare, Ahrefs, Similarweb) için okuma/yazma ayrımı: yazma `ask`.
- Ölçüm: aynı brif plugin'li ve plugin'siz ajanla koşulup kalite/token farkı `QA_REPORTS`'a yazılır; etkisiz eşlemeler katalogdan çıkarılır.

## P2 — Diğer fikirler

- `kf.py doctor`: selftest + plugin + kimlik + ağ (Cloudflare/GSC erişimi) tek komut.
- Ajans: müşteri aylık rapor paketi (`kf.py rapor --client x --ay 2026-11`: GSC + GA4 + CWV + Cloudflare + kampanya sonuçları → tek Markdown/PDF).
- Ajans: `site-denetcisi` için erişilebilirlik (WCAG) kontrolü (`design:accessibility-review` plugin'i ya da axe-core).
- Çoklu dil: `references/en/` paralel dizin (CONTRIBUTING'de söz verildi).
- `migrate` için v3.0 → v3.1 otomatik `profile`/`skill_dir` ekleme (şu an `repair` yapıyor; yeterli).
