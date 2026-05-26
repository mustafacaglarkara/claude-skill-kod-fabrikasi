# Yeni Projede Kod Fabrikası Kurulumu

Bu rehber, **Kod Fabrikası**'nı yeni bir projede sıfırdan kurma adımlarıdır. `scripts/init.sh` çoğu adımı otomatize eder, ama burada her adımın **ne yaptığı** ve **neden** olduğu açıklanır.

---

## 0. Önce kullanıcıya 4 soru sor

Kuruluma başlamadan **dur ve sor**. `init.sh` da bu 4 soruyu sorar:

1. **Google Drive senkron klasör yolu** — `bundle.py` çıktıyı buraya yazacak (Drive masaüstü uygulaması bunu buluta yükler). Örn: `/Users/<kullanici>/Library/CloudStorage/GoogleDrive-<email>/Drive'ım/DEV_PROJELERI/<proje>`
2. **NotebookLM notebook ID'si** — yoksa `notebooklm create "Proje Adı"` ile oluştur, dönen UUID'yi kullan.
3. **Python yolu** — `notebooklm-py` paketinin kurulu olduğu Python (`which python3` ile bul; macOS'ta genelde `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`).
4. **Projenin framework'ü** — `flutter` / `go` / `php-laravel` / `python` / `node` / `none`. `pre-commit` test komutu buna göre seçilir.

Bu 4 bilgi olmadan config dosyası eksik doldurulur.

---

## 1. Bağımlılıkları kur (kullanıcıdan onay alarak)

```bash
# Mimari haritalayıcı
python3 -m pip install graphifyy

# NotebookLM API + tarayıcı eklentisi
python3 -m pip install "notebooklm-py[browser]"
playwright install chromium

# Google hesabıyla NotebookLM'e giriş (tarayıcı açılır)
notebooklm login

# Doğrula
notebooklm list
graphify --version
```

> ⚠️ `notebooklm-py` **hangi Python'a kurulduysa** `bundle.py` o Python ile çalışmalı (bkz. [tuzaklar.md](tuzaklar.md) — Tuzak #3).

---

## 2. `scripts/init.sh` ile interaktif kurulum

`~/.claude/skills/kod-fabrikasi/scripts/init.sh` proje root'undan çalıştırılır:

```bash
cd <proje-root>
bash ~/.claude/skills/kod-fabrikasi/scripts/init.sh
```

`init.sh` ne yapar:

1. 4 soruyu sorar (yukarıdaki).
2. `.claude/kod-fabrikasi.config.json` üretir.
3. Skill'in `scripts/` altındaki `bundle.py`, `Makefile`, `setup-hooks.sh` template'lerini **proje root'a** kopyalar.
4. `.gitignore`'a `graphify-out/`, `__pycache__/`, `.claude/settings.local.json` ekler (yoksa).
5. Kullanıcıya sonraki adımları söyler: `git init` (gerekirse) → `make setup-hooks` → `make bundle`.

**`--repair` modu:** Mevcut bir projede config var ama bazı dosyalar eksikse:
```bash
bash ~/.claude/skills/kod-fabrikasi/scripts/init.sh --repair
```
Sadece eksik dosyaları tamamlar, mevcut config'i bozmaz.

---

## 3. Git hook'larını kur

```bash
git init           # repo değilse
make setup-hooks   # pre-commit + post-commit hook'ları üretir
```

`make setup-hooks` aslında `bash setup-hooks.sh` çalıştırır. `setup-hooks.sh` config'ten `framework`'ü okur ve uygun `pre-commit` (test) ve `post-commit` (graphify + bundle) hook'ları üretir.

---

## 4. Kritik dökümanları oluştur (yoksa)

Aşağıdaki dosyaları kök dizinde boş iskelet olarak oluştur:

- `ROADMAP.md` — fazların listesi + "Faz Durumu Özeti" tablosu
- `MEMORY.md` — teknik kararlar, öğrenilen kalıplar
- `QA_REPORTS.md` — testler, bilinen sorunlar
- `NOTEBOOKLM_SUMMARY.md` — proje durumu kısa özet
- `GRAPHIFY_NOTES.md` — kendi mimari gözlemlerin (opsiyonel)
- `reports/` — faz raporlarının yazılacağı klasör (`mkdir -p reports`)

Bu isimler config'teki `critical_docs` ve `phase_files`'da listelidir. Farklı isim istersen önce config'i değiştir.

---

## 5. İlk eşitleme ve doğrulama

```bash
make bundle                # ilk eşitleme: Drive + NotebookLM dolar
notebooklm source list --notebook <NOTEBOOK_ID>
# Çıktıda her başlık BENZERSİZ olmalı (çift kaynak yoksa OK)
```

**Beklenen çıktı:**
- `tum_kodlar.txt` — tüm kaynak kod tek dosyada
- `ROADMAP.md`, `MEMORY.md`, `QA_REPORTS.md` — Drive'a kopyalanmış
- `reports/`, `graphify-out/` — alt klasör olarak Drive'da

Eğer NotebookLM'de çift kaynak görüyorsan bir kez daha `make bundle` çalıştır — düzeltilmiş kod id bazında temizler.

---

## 6. Kullanıcıya ilk faz akışını öğret

Sistem hazır. Kullanıcıya günlük döngüyü göster:

```text
Kod yaz → ROADMAP/MEMORY/QA güncelle → git commit
                                          │
                            post-commit ──┤
                                          ├─ graphify (mimari harita)
                                          └─ bundle.py (Drive + NotebookLM ayna)

Faz başlatmak için: "FAZ_PROMPT'u oku ve sıradaki fazı başlat."
```

---

## Kurulum kontrol listesi (Claude bunu tamamlamadan "bitti" deme)

- [ ] Kullanıcıdan 4 bilgi alındı (Drive yolu, Notebook ID, Python yolu, framework)
- [ ] `graphifyy` + `notebooklm-py` kuruldu, `notebooklm login` yapıldı
- [ ] `init.sh` çalıştırıldı, `.claude/kod-fabrikasi.config.json` oluştu
- [ ] `bundle.py`, `Makefile`, `setup-hooks.sh` proje root'una kopyalandı
- [ ] `.gitignore`'a `graphify-out/`, `__pycache__/` eklendi
- [ ] `make setup-hooks` çalıştırıldı, hook'lar kuruldu
- [ ] Kritik dökümanlar (ROADMAP, MEMORY, QA_REPORTS) ve `reports/` klasörü mevcut
- [ ] `make bundle` çalıştı; `notebooklm source list` çıktısında **çift kaynak yok**
- [ ] [tuzaklar.md](tuzaklar.md)'daki 10 tuzaktan hiçbirine düşülmedi
