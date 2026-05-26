---
name: kod-fabrikasi
description: AI destekli yazılım fabrikası — NotebookLM + Graphify + Git hook'ları + Faz Bazlı Geliştirme (Phase-based Development) iş akışını yönetir. v2.0 itibariyle proje yönetim dosyaları `.claude/{context,decisions,archives,references}/` alt klasör konvansiyonunu kullanır; kök dizin temiz kalır. KULLANICI faz başlatmak, faz bitirmek, bundle/paketleme yapmak, NotebookLM senkronu, kod haritası (graphify), git hook kurulumu, roadmap/memory/QA raporu güncelleme istediğinde MUTLAKA bu skill'i kullan. Ayrıca kullanıcı "yeni proje kurulumu", "kod fabrikası kur", "FAZ_PROMPT", "faz raporu", "post-commit otomasyonu", "Drive senkronu", "NotebookLM kaynak yükleme" gibi konulardan bahsettiğinde — açıkça "skill" demese bile — bu skill'i devreye al.
allowed-tools: Read, Glob, Grep, Bash, Edit, Write
---

# Kod Fabrikası (v2.0)

**Üç parçalı bir yazılım fabrikası:** `bundle.py` (Drive + NotebookLM ayna senkronu) + `Graphify` (AST tabanlı mimari harita) + `git post-commit hook` (her commit'te ikisini otomatik tetikler). Yapay zeka asistanı bunun üstünde **6 adımlı Faz Bazlı Geliştirme** akışını yürütür.

Sonuç: Geliştirici sadece kod yazıp commit atar; mimari harita ve NotebookLM otomatik güncel kalır. NotebookLM projeyi "bilen" bir danışmana dönüşür, Claude/Antigravity her fazı aynı disiplinle (önce onay, sonra kod) uygular.

**v2.0 değişikliği**: Proje yönetim `.md` dosyaları artık projenin kök dizinini kirletmiyor — hepsi `.claude/` altında konuya göre gruplanıyor (bkz. **Klasör Konvansiyonu** bölümü).

---

## 🗂️ Klasör Konvansiyonu (v2.0)

```text
<proje-root>/
├── README.md                                  # Sadece bu standart dosya kökte kalır
├── pubspec.yaml / go.mod / package.json / ... # Standart paket dosyaları
├── .claude/
│   ├── CLAUDE.md                              # Proje kuralları (faz arşivleme vb.)
│   ├── kod-fabrikasi.config.json              # Skill konfigürasyonu
│   ├── context/
│   │   ├── MEMORY.md                          # Kalıcı teknik kararlar, acı dersler
│   │   └── GRAPHIFY_NOTES.md                  # Graphify çıktısı yorumları (opsiyonel)
│   ├── decisions/
│   │   └── FAZ_PROMPT.md                      # Faz çalışma promptu / iş akışı
│   ├── archives/
│   │   ├── ROADMAP.md                         # Yol haritası, fazların listesi
│   │   ├── NOTEBOOKLM_SUMMARY.md              # NotebookLM için kısa özet
│   │   ├── PHASE_TEMPLATE.md                  # Faz raporu şablonu
│   │   └── PHASE_NN_<konu>.md                 # Tamamlanan fazların raporları
│   ├── references/
│   │   ├── KNOWN_BUGS.md                      # Bilinen hatalar kataloğu
│   │   └── QA_REPORTS.md                      # Test/kalite raporları
│   ├── skills/                                # (opsiyonel) proje-specific skill kopyaları
│   └── archives bundle çıktıları & cache      # (gitignore'da olabilir)
├── bundle.py                                  # Auto-discovery: yukarıdaki klasörleri tarar
├── Makefile                                   # bundle / graphify / setup-hooks
├── setup-hooks.sh                             # Git hook kurulum scripti
└── (kaynak kod: lib/, src/, ...)
```

**Kural:** Kök dizinde yapay zeka yönetim `.md` dosyası bırakma (README.md hariç). Yeni proje için `init.sh` bu yapıyı otomatik oluşturur. Eski projelerde `kod-fabrikasini migrate et` denildiğinde root'taki ROADMAP/MEMORY/QA/vs. dosyaları yukarıdaki konumlara taşınır.

---

## ⚙️ İlk Kontrol: Bu projede kurulu mu?

Skill devreye girdiğinde **HER ZAMAN** önce projenin durumunu kontrol et:

```bash
test -f .claude/kod-fabrikasi.config.json && echo "CONFIG_VAR" || echo "CONFIG_YOK"
test -f bundle.py && echo "BUNDLE_VAR" || echo "BUNDLE_YOK"
test -f .git/hooks/post-commit && echo "HOOK_VAR" || echo "HOOK_YOK"
test -d .claude/archives && echo "STRUCT_V2" || echo "STRUCT_V1"
```

- **CONFIG_VAR + BUNDLE_VAR + HOOK_VAR + STRUCT_V2** → Sistem hazır ve modern. Kullanıcının isteğine göre 6 adımlı faz akışına geç.
- **STRUCT_V1** ama dosyalar mevcutsa → v1 → v2 migration öner: kullanıcıya sor "kök dizini temizleyip dosyaları `.claude/` altına taşıyayım mı?". Onaylanırsa [references/kurulum-rehberi.md](references/kurulum-rehberi.md) `--migrate-v2` bölümünü uygula.
- **CONFIG_YOK** → Sistem kurulu değil. Kullanıcıya sor: "Bu projeye Kod Fabrikası kurulumu yapayım mı?" Onaylarsa `scripts/init.sh` ile interaktif kurulum başlat.
- **CONFIG_VAR ama BUNDLE_YOK/HOOK_YOK** → Eksik kurulum. `scripts/init.sh --repair` ile eksikleri tamamla.

---

## 📋 6 Adımlı Faz Akışı (Phase-based Workflow)

Kullanıcı "faza başla / sıradaki faz / FAZ_PROMPT" derse veya tek satırlık tetikleyici yazarsa **MUTLAKA** bu 6 adımı sırayla uygula. **Adım 2 ASLA atlanmaz** — kullanıcı onayı olmadan koda dokunma.

```text
0. Faz seç        → .claude/archives/ROADMAP.md'deki ilk [ ] (tamamlanmamış) faz
1. Bağlam topla   → .claude/archives/ROADMAP.md
                  + .claude/context/MEMORY.md
                  + .claude/references/QA_REPORTS.md
                  + .claude/references/KNOWN_BUGS.md
                  + (gerekirse) notebooklm ask + graphify-out/
2. Plan + ONAY    → ⚠️ Kullanıcı onayı olmadan koda dokunma
3. Uygula + test  → Yıkıcı işlemden önce yedek; testleri yeşil yap
4. Faz raporu     → .claude/archives/PHASE_NN_<konu>.md
                    (şablon: .claude/archives/PHASE_TEMPLATE.md — birebir uygula)
5. Dökümanlar     → ROADMAP (durum [x]) + MEMORY (öğrenilenler)
                  + QA_REPORTS (sorunlar) + NOTEBOOKLM_SUMMARY (kısa özet)
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
| --- | --- |
| `drive_folder_path` | `bundle.py` çıktısının yazılacağı Drive klasörü |
| `notebook_id` | NotebookLM hedef notebook |
| `python_bin` | `notebooklm-py` paketinin kurulu olduğu Python tam yolu (PATH varsayma!) |
| `graphify_bin` | Graphify binary tam yolu |
| `framework` | `flutter` / `go` / `php-laravel` / `python` / `node` / `none` — `pre-commit` test komutu seçimi |
| `phase_files` | Faz akışının okuduğu dosyaların yolları (v2 default: `.claude/archives/ROADMAP.md`, `.claude/context/MEMORY.md`, `.claude/references/QA_REPORTS.md`, `.claude/references/KNOWN_BUGS.md`) |
| `sync_dirs` | Drive'a + NotebookLM'e birebir aynalanacak klasörler (varsayılan `[".claude/archives", "graphify-out"]`) |
| `critical_docs` | İSTEĞE BAĞLI override; boş bırakılırsa `bundle.py` `.claude/{context,decisions,archives,references}/*.md` auto-discover yapar |

Config şeması ve örnek: [assets/kod-fabrikasi.config.example.json](assets/kod-fabrikasi.config.example.json)

---

## 🧰 Çalıştırılabilir Yardımcılar (`scripts/`)

| Script | Ne yapar |
| --- | --- |
| [scripts/init.sh](scripts/init.sh) | İnteraktif kurulum: 4 soru sorar, config dosyası üretir, `.claude/{context,decisions,archives,references}/` klasörlerini ve PHASE_TEMPLATE.md'yi oluşturur, `bundle.py`/`Makefile`/`setup-hooks.sh` template'lerini proje root'a kopyalar. `--repair` ile eksik dosyaları tamamlar. `--migrate-v2` ile eski yapıdan yeni yapıya geçiş. |
| [scripts/bundle.py](scripts/bundle.py) | Config'i okur, kodu paketler, Drive'a yazar, NotebookLM'i Drive klasörüyle **birebir aynalar**. `.claude/` alt klasörlerinden auto-discover. |
| [scripts/setup-hooks.sh](scripts/setup-hooks.sh) | Config'teki `framework`'e göre `pre-commit` (test) ve `post-commit` (graphify + bundle) hook'larını üretir. |
| [scripts/Makefile](scripts/Makefile) | `make bundle` / `make graphify-update` / `make end-phase` / `make setup-hooks` komutları. |

**Hepsi config-driven** — hiçbir hardcoded path yok. Proje değiştiğinde sadece `.claude/kod-fabrikasi.config.json` değişir.

---

## 📚 Derin Referanslar (gerektiğinde oku)

Aşağıdaki dosyaları **konuya göre** oku, başta hepsini değil:

| Dosya | Ne zaman oku |
| --- | --- |
| [references/workflow.md](references/workflow.md) | Faz başlatırken, plan sunarken, faz raporu yazarken |
| [references/kurulum-rehberi.md](references/kurulum-rehberi.md) | Yeni projede kurulum yaparken, init.sh çalıştırırken, v1→v2 migration yaparken |
| [references/notebooklm-graphify.md](references/notebooklm-graphify.md) | NotebookLM ile etkili sorgu, Graphify ile etki analizi gerektiğinde |
| [references/faz-raporu-sablonu.md](references/faz-raporu-sablonu.md) | `.claude/archives/PHASE_NN_*.md` yazarken (şablon birebir uygulanır) |
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
8. **`.claude/archives/` dışında faz raporu yazma** — eski `reports/fazNN_*.md` yapısı v2'de kaldırıldı. `PHASE_NN_<konu>.md` formatı + `.claude/archives/` zorunlu. `sync_dirs`'e dahil olmayan dosyalar NotebookLM'e gitmez.
9. **Kök dizine yönetim dosyası bırakma** — README.md hariç hiçbir AI yönetim `.md`'si root'ta olmamalı. v1 projelerde migrate et.
10. **`bundle.py`'yi "sadeleştireyim" diye yeniden yazma** — geçmişte 10 tuzağa düşülerek olgunlaştı, [references/tuzaklar.md](references/tuzaklar.md) okumadan dokunma.

---

## 🔄 Mental Model — Kim Ne Yapar

| Parça | Ne yapar | Dosya yazar mı? | Faz yapar mı? |
| --- | --- | --- | --- |
| **`.claude/archives/ROADMAP.md`** | Fazların listesi + durum tablosu | — | — |
| **Claude / Antigravity** | Kod yazar, faz raporu yazar, ROADMAP/MEMORY/QA günceller | ✅ | ✅ |
| **NotebookLM** | Projeyi okumuş danışman — soru sorarsın, cevap verir | ❌ Asla | ❌ Asla |
| **Graphify** | Yapısal harita ("X, Y'yi çağırıyor") — refactor öncesi etki analizi | ❌ Asla | ❌ Asla |
| **bundle.py** | Kodu paketler, Drive'a yazar, NotebookLM'i Drive ile birebir aynalar | ✅ (Drive'a) | ❌ |
| **post-commit hook** | Her commit sonrası Graphify + bundle'ı tetikler | — | — |

**Kullanıcı sana iş söyler — NotebookLM'e değil.** NotebookLM cevap verir, iş yapmaz.

---

## 🗣️ Sürüm, Köken ve Güncelleme

Bu skill **GitHub'da yayında**: https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi

**Sürüm:** v2.0 — `.claude/` alt klasör konvansiyonu. v1 root-bazlı yapıdan geçiş için `init.sh --migrate-v2`.

**Kurulum (yeni makineler için):**
```bash
git clone https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi.git ~/.claude/skills/kod-fabrikasi
```

**Güncelleme:**
```bash
cd ~/.claude/skills/kod-fabrikasi && git pull
```

Köken: projeye özgü `OtoLog/.claude/skills/kod-fabrikasi/`'den proje-bağımsız, config-driven hale getirilerek `~/.claude/skills/kod-fabrikasi/` altına taşındı. v2.0'da klasör konvansiyonu temizlendi. Her proje kendi `.claude/kod-fabrikasi.config.json`'unu tutar. Detaylı kullanım: [README.md](README.md), sürüm geçmişi: [CHANGELOG.md](CHANGELOG.md), katkı kuralları: [CONTRIBUTING.md](CONTRIBUTING.md).
