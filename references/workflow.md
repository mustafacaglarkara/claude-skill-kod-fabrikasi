# Faz Bazlı Geliştirme — 6 Adımlı Detaylı İş Akışı

Bu dosya, Claude / Antigravity'nin **her yeni faza başlarken** uygulayacağı standart yönergedir. SKILL.md'deki 6 adımın ayrıntılı versiyonudur.

---

## Tetikleyici cümleler

Kullanıcı şu cümlelerden birini söylediğinde 6 adımı sırayla uygula:

- "FAZ_PROMPT'u oku ve sıradaki fazı başlat."
- "Faz N'i başlat."
- "Sıradaki faz nedir, başlayalım."
- "Roadmap'teki ilk fazı yap."

---

## Adım 0 — Sıradaki fazı belirle

- Config'teki `phase_files.roadmap` dosyasını oku (varsayılan: `ROADMAP.md`).
- "Faz Durumu Özeti" tablosuna veya checkbox listesine bak.
- ✅ / `[x]` olmayan **ilk** faz hedef fazdır. Kullanıcı belirli bir faz istediyse onu al.
- Birden fazla aday varsa kullanıcıya seçim sun.

## Adım 1 — Bağlam topla

Hem yereldeki gerçek kaynakları oku **hem de** gerekirse NotebookLM'e danış:

**Yerel dosyalar (asıl doğru kaynak):**
- `phase_files.roadmap` — fazın tanımı
- `phase_files.memory` — geçmiş teknik kararlar
- `phase_files.qa` — bilinen sorunlar
- `phase_files.known_bugs` — açık buglar (varsa)

**NotebookLM (geniş/kesişen sorular için):**
```bash
notebooklm ask "Faz N kapsamında hangi modüller ve dosyalar etkilenir?"
notebooklm ask "QA_REPORTS ve MEMORY'ye göre Faz N'de dikkat edilecek bilinen sorunlar neler?"
```

**Etki analizi (refactor riski varsa):**
- `graphify-out/GRAPH_REPORT.md` — en bağımlı/kırılgan modüller
- `graphify-out/graph.html` — interaktif bağımlılık grafiği (kullanıcının açması gerekir)

> ⚠️ **Çelişki olursa yereldeki dosyalar esastır.** NotebookLM son commit'ten bir adım geride olabilir.

## Adım 2 — Plan sun ve ONAY al ⚠️ Zorunlu durak

Kullanıcıya net bir paket sun:

1. **Yapılacaklar listesi** (sıralı, somut)
2. **Etkilenecek dosyalar** (path listesi)
3. **Riskler ve geri-alma (rollback) planı**
4. **Tahmini iş süresi**

> ⚠️ **ROADMAP kuralı:** Plan ≠ uygulama yetkisi. Kullanıcıdan **açık onay** al ("onaylıyorum", "devam et", "evet"). Onay olmadan koda dokunma. Belirsiz cevapta tekrar sor.

## Adım 3 — Uygula

- Yalnızca onaylanan adımları uygula.
- **Yıkıcı işlemden** (DB schema, migration, toplu silme, force-push) önce **doğrulanmış yedek** al.
- Bittiğinde testleri çalıştır — config'teki `framework`'e göre:
  - `flutter` → `flutter test`
  - `go` → `go test ./...`
  - `php-laravel` → `php artisan test`
  - `python` → `pytest`
  - `node` → `npm test`
- Test başarısızsa **düzelt veya raporda dürüstçe belirt**. Yeşil olmadan fazı kapatma.

## Adım 4 — Faz raporu yaz

- `reports/fazNN_<kisa_isim>.md` dosyası oluştur (NN = iki haneli; örn. `faz01_veritabani_temizligi.md`).
- Şablonu birebir uygula: [faz-raporu-sablonu.md](faz-raporu-sablonu.md)
- Bu klasör `bundle.py` tarafından otomatik NotebookLM'e yüklenir.

## Adım 5 — Dökümanları güncelle

- **ROADMAP.md** — fazın durumunu `[x]` yap; "Faz Durumu Özeti" tablosunu ve tarihini güncelle; çıkış kriterlerini işaretle; sıradaki fazı 🟡 Aktif yap.
- **MEMORY.md** — bu fazda öğrenilen kalıcı kalıpları, kararları, tuzakları ekle.
- **QA_REPORTS.md** — çözülen sorunları kapat, yeni keşfedilenleri ekle.
- **NOTEBOOKLM_SUMMARY.md** (varsa) — güncel proje durumunun kısa özetini yenile.
- Gerekiyorsa `docs/` altındaki ilgili kullanım rehberlerini güncelle.

> 🎯 **Kritik alışkanlık:** Dökümanları **commit'ten önce** güncelle. NotebookLM'in en iyi cevap verdiği kaynaklar bunlar — kod değil, bağlam.

## Adım 6 — Commit & otomatik senkronizasyon

```bash
git add -A
git commit -m "Faz N: <faz başlığı>"
```

Commit mesajı formatı:
- Türkçe başlık: `"Faz 12.3: Drift schema migration"`
- Veya conventional: `"feat: Faz 12.3 — Drift schema migration"`
- Hangisi seçilirse proje boyunca tutarlı kalsın.

**post-commit hook otomatik çalışır:**
1. Graphify haritası güncellenir
2. `bundle.py` çalışır → kod paketlenir → Drive'a yazılır → NotebookLM Drive ile birebir eşitlenir

Kullanıcıya hatırlat: **NotebookLM web arayüzünde "Yenile (Refresh)" butonuna basın** — yoksa sohbet eski koda göre cevap verir.

---

## Kurallar (her fazda geçerli)

1. **Önce onay, sonra kod.** Adım 2 atlanamaz.
2. **Her faz bitip doğrulanmadan sıradakine geçilmez.**
3. **Yıkıcı işlem = önce doğrulanmış yedek.**
4. **Doğru kaynak yereldeki dosyalardır;** NotebookLM yardımcı/danışma katmanıdır.
5. **Her faz; faz raporu + döküman güncellemesi + commit ile kapanır.** Üçü de yapılmadan faz "bitmiş" sayılmaz.
6. **Commit mesajı tutarlı format** kullanır ve faz numarasını içerir.
7. **Runtime doğrulamayı atlama** — çalıştıramadığın şeyi "yeşil" gösterme.

---

## Mikrofazlama (Faz X.Y)

Büyük bir faz birden fazla pakete bölünebilir:
- Faz 12 → Faz 12.1, 12.2, 12.3...
- Her mini-paket bittiğinde **ayrı commit** at (kullanıcı tercih ediyorsa, [[feedback_commit_per_phase]] anısına bakar).
- Her mini-paket için **ayrı faz raporu zorunlu değil** — paket büyükse yaz, küçükse ana faz raporuna ekle.

---

## Hata senaryoları

- **Test geçmiyor ama kullanıcı "devam et" diyor:** Faz raporuna "Testler kırmızı: <neden>, fix sonraki fazda" notu ekle ve commit at. Yeşil göstererek geçme.
- **NotebookLM yanıt vermiyor:** Sorun değil — yereldeki dosyalar esas. Faz tamamlanır, NotebookLM bir sonraki başarılı senkronla yakalar.
- **post-commit hook çakıyor:** `python_bin` yanlış kuruludur (Tuzak #3). Config'i kontrol et, [tuzaklar.md](tuzaklar.md)'a bak.
- **Kullanıcı onay vermeden devam etmemi istiyor:** "Onaysız ilerleyemem, plan üzerinde ne değiştirelim?" diye sor. Bu kural durağan değil.
