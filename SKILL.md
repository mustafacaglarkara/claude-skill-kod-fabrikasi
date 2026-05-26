---
name: kod-fabrikasi
description: AI destekli yazılım fabrikası — NotebookLM + Graphify + Git hook'ları + Faz Bazlı Geliştirme (Phase-based Development) iş akışını yönetir. KULLANICI faz başlatmak, faz bitirmek, bundle/paketleme yapmak, NotebookLM senkronu, kod haritası (graphify), git hook kurulumu, roadmap/memory/QA raporu güncelleme istediğinde MUTLAKA bu skill'i kullan. Ayrıca kullanıcı "yeni proje kurulumu", "kod fabrikası kur", "FAZ_PROMPT", "faz raporu", "post-commit otomasyonu", "Drive senkronu", "NotebookLM kaynak yükleme" gibi konulardan bahsettiğinde — açıkça "skill" demese bile — bu skill'i devreye al.
allowed-tools: Read, Glob, Grep, Bash, Edit, Write
---

# Kod Fabrikası

**Üç parçalı bir yazılım fabrikası:** `bundle.py` (Drive + NotebookLM ayna senkronu) + `Graphify` (AST tabanlı mimari harita) + `git post-commit hook` (her commit'te ikisini otomatik tetikler). Yapay zeka asistanı bunun üstünde **6 adımlı Faz Bazlı Geliştirme** akışını yürütür.

Sonuç: Geliştirici sadece kod yazıp commit atar; mimari harita ve NotebookLM otomatik güncel kalır. NotebookLM projeyi "bilen" bir danışmana dönüşür, Claude/Antigravity her fazı aynı disiplinle (önce onay, sonra kod) uygular.

---

## ⚙️ İlk Kontrol: Bu projede kurulu mu?

Skill devreye girdiğinde **HER ZAMAN** önce projenin durumunu kontrol et:

```bash
test -f .claude/kod-fabrikasi.config.json && echo "CONFIG_VAR" || echo "CONFIG_YOK"
test -f bundle.py && echo "BUNDLE_VAR" || echo "BUNDLE_YOK"
test -f .git/hooks/post-commit && echo "HOOK_VAR" || echo "HOOK_YOK"
```

- **CONFIG_VAR + BUNDLE_VAR + HOOK_VAR** → Sistem hazır. Kullanıcının isteğine göre 6 adımlı faz akışına geç (aşağıda).
- **CONFIG_YOK** → Sistem kurulu değil. Kullanıcıya sor: "Bu projeye Kod Fabrikası kurulumu yapayım mı?" Onaylarsa [references/kurulum-rehberi.md](references/kurulum-rehberi.md) yönergesine göre `scripts/init.sh` ile interaktif kurulum başlat.
- **CONFIG_VAR ama BUNDLE_YOK/HOOK_YOK** → Eksik kurulum. `scripts/init.sh --repair` ile eksikleri tamamla.

---

## 📋 6 Adımlı Faz Akışı (Phase-based Workflow)

Kullanıcı "faza başla / sıradaki faz / FAZ_PROMPT" derse veya tek satırlık tetikleyici yazarsa **MUTLAKA** bu 6 adımı sırayla uygula. **Adım 2 ASLA atlanmaz** — kullanıcı onayı olmadan koda dokunma.

```
0. Faz seç        → ROADMAP.md'deki ilk [ ] (tamamlanmamış) faz
1. Bağlam topla   → ROADMAP/MEMORY/QA + (gerekirse) notebooklm ask + graphify
2. Plan + ONAY    → ⚠️ Kullanıcı onayı olmadan koda dokunma
3. Uygula + test  → Yıkıcı işlemden önce yedek; testleri yeşil yap
4. Faz raporu     → reports/fazNN_<isim>.md (şablon: references/faz-raporu-sablonu.md)
5. Dökümanlar     → ROADMAP (durum [x]) + MEMORY (öğrenilenler) + QA_REPORTS (sorunlar)
6. Commit         → "Faz N: <başlık>" — post-commit hook NotebookLM'i otomatik eşitler
```

**Detaylı iş akışı:** [references/workflow.md](references/workflow.md)

---

## 🗂️ Config Dosyası — Tüm Proje-Spesifik Değerler Burada

Skill çağrıldığında **HER ZAMAN** önce config'i oku:

```bash
cat .claude/kod-fabrikasi.config.json
```

Config içeriğinden öğreneceklerin:

| Alan | Ne için |
|---|---|
| `drive_folder_path` | `bundle.py` çıktısının yazılacağı Drive klasörü |
| `notebook_id` | NotebookLM hedef notebook |
| `python_bin` | `notebooklm-py` paketinin kurulu olduğu Python tam yolu (PATH varsayma!) |
| `graphify_bin` | Graphify binary tam yolu |
| `framework` | `flutter` / `go` / `php-laravel` / `python` / `node` / `none` — `pre-commit` test komutu seçimi |
| `critical_docs` | `bundle.py`'nin paketin başına ekleyeceği proje hafıza dosyaları |
| `sync_dirs` | Drive'a + NotebookLM'e birebir aynalanacak klasörler (varsayılan `["reports", "graphify-out"]`) |
| `phase_files` | Faz akışının okuduğu dosyaların yolları (`roadmap`, `memory`, `qa`, `known_bugs`) |

Config şeması ve örnek: [assets/kod-fabrikasi.config.example.json](assets/kod-fabrikasi.config.example.json)

---

## 🧰 Çalıştırılabilir Yardımcılar (`scripts/`)

| Script | Ne yapar |
|---|---|
| [scripts/init.sh](scripts/init.sh) | İnteraktif kurulum: 4 soru sorar, config dosyası üretir, `bundle.py`/`Makefile`/`setup-hooks.sh` template'lerini proje root'a kopyalar. `--repair` ile eksik dosyaları tamamlar. |
| [scripts/bundle.py](scripts/bundle.py) | Config'i okur, kodu paketler, Drive'a yazar, NotebookLM'i Drive klasörüyle **birebir aynalar**. |
| [scripts/setup-hooks.sh](scripts/setup-hooks.sh) | Config'teki `framework`'e göre `pre-commit` (test) ve `post-commit` (graphify + bundle) hook'larını üretir. |
| [scripts/Makefile](scripts/Makefile) | `make bundle` / `make graphify-update` / `make end-phase` / `make setup-hooks` komutları. |

**Hepsi config-driven** — hiçbir hardcoded path yok. Proje değiştiğinde sadece `.claude/kod-fabrikasi.config.json` değişir.

---

## 📚 Derin Referanslar (gerektiğinde oku)

Aşağıdaki dosyaları **konuya göre** oku, başta hepsini değil:

| Dosya | Ne zaman oku |
|---|---|
| [references/workflow.md](references/workflow.md) | Faz başlatırken, plan sunarken, faz raporu yazarken |
| [references/kurulum-rehberi.md](references/kurulum-rehberi.md) | Yeni projede kurulum yaparken, init.sh çalıştırırken |
| [references/notebooklm-graphify.md](references/notebooklm-graphify.md) | NotebookLM ile etkili sorgu, Graphify ile etki analizi gerektiğinde |
| [references/faz-raporu-sablonu.md](references/faz-raporu-sablonu.md) | `reports/fazNN_*.md` yazarken (şablon birebir uygulanır) |
| [references/tuzaklar.md](references/tuzaklar.md) | `bundle.py`/`setup-hooks.sh` düzenlerken, sistemi "iyileştirmeye" kalkışırken — geri dönüş yapma riskini önler |

---

## 🚫 ASLA YAPMA (kısa özet — detaylı tuzaklar: [references/tuzaklar.md](references/tuzaklar.md))

1. **NotebookLM kaynaklarını başlığa göre dict'leme** — `{s.title: s.id}` aynı başlıktan birden fazlasını gizler, çiftler birikir. Her zaman liste olarak dolaş, id bazında sil.
2. **`python3` PATH varsayma** — `notebooklm-py` belirli bir Python'a kuruludur, hook'lar sınırlı PATH ile çalışır. Config'teki `python_bin` TAM YOL kullan.
3. **`collect_drive_sources` boş döndüğünde NotebookLM'i temizleme** — güvenlik freni (zaten kodda var) — kaldırma. Boş klasör tüm kaynakları silmemeli.
4. **`copytree(dirs_exist_ok=True)` kullanma** — eski dosyalar hedefte birikir. Önce `rmtree`, sonra `copytree` ile **birebir** ayna.
5. **Alt klasör dosyalarında çakışan başlık** — `a/rapor.md` ile `b/rapor.md` ikisi de "rapor.md" olur, biri diğerini ezer. Göreli yolu `__` ile düzleştir (`a__rapor.md`).
6. **Büyük HTML/JSON yükleme** — `graphify-out/graph.html` (~8MB) NotebookLM'i boğar. `NOTEBOOKLM_ALLOWED_EXTENSIONS` sadece `.md/.txt/.pdf` — genişletme.
7. **Adım 2'yi atlayıp koda dalma** — kullanıcı onayı olmadan kod değişikliği YOK.
8. **`reports/` dışında faz raporu yazma** — `sync_dirs`'e dahil olmayan dosyalar NotebookLM'e gitmez.
9. **Runtime doğrulamayı atlayıp "yeşil" yazma** — bağımlılık yoksa faz raporuna dürüstçe "runtime doğrulama bekliyor" yaz.
10. **`bundle.py`'yi "sadeleştireyim" diye yeniden yazma** — geçmişte 10 tuzağa düşülerek olgunlaştı, [references/tuzaklar.md](references/tuzaklar.md) okumadan dokunma.

---

## 🔄 Mental Model — Kim Ne Yapar

| Parça | Ne yapar | Dosya yazar mı? | Faz yapar mı? |
|---|---|---|---|
| **ROADMAP.md** | Fazların listesi + durum tablosu | — | — |
| **Claude / Antigravity** | Kod yazar, faz raporu yazar, ROADMAP/MEMORY/QA günceller | ✅ | ✅ |
| **NotebookLM** | Projeyi okumuş danışman — soru sorarsın, cevap verir | ❌ Asla | ❌ Asla |
| **Graphify** | Yapısal harita ("X, Y'yi çağırıyor") — refactor öncesi etki analizi | ❌ Asla | ❌ Asla |
| **bundle.py** | Kodu paketler, Drive'a yazar, NotebookLM'i Drive ile birebir aynalar | ✅ (Drive'a) | ❌ |
| **post-commit hook** | Her commit sonrası Graphify + bundle'ı tetikler | — | — |

**Kullanıcı sana iş söyler — NotebookLM'e değil.** NotebookLM cevap verir, iş yapmaz.

---

## 🗣️ Sürüm, Köken ve Güncelleme

Bu skill **GitHub'da yayında**: https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi

**Kurulum (yeni makineler için):**
```bash
git clone https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi.git ~/.claude/skills/kod-fabrikasi
```

**Güncelleme:**
```bash
cd ~/.claude/skills/kod-fabrikasi && git pull
```

Köken: projeye özgü `OtoLog/.claude/skills/kod-fabrikasi/`'den proje-bağımsız, config-driven hale getirilerek `~/.claude/skills/kod-fabrikasi/` altına taşındı. Tüm projelerde otomatik kullanılabilir. Her proje kendi `.claude/kod-fabrikasi.config.json`'unu tutar. Detaylı kullanım: [README.md](README.md)
