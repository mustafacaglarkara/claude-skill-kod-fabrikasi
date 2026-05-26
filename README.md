# Kod Fabrikası — Claude Code Skill (v2.0)

> **EN:** AI-powered software factory for Claude Code. NotebookLM + Graphify + Git hooks + Phase-based Development workflow, all driven by a single per-project config. Portable across all your projects. Documentation and skill content are in Turkish.
>
> **v2.0:** Project management `.md` files now live under `.claude/{context,decisions,archives,references}/` — root stays clean. See [CHANGELOG.md](CHANGELOG.md) for migration from v1.

**TR:** AI destekli yazılım fabrikası. NotebookLM + Graphify + Git hook'ları + Faz Bazlı Geliştirme iş akışını her projende aynı disiplinle yürütür. Tek bir `.claude/kod-fabrikasi.config.json` üzerinden tüm proje-spesifik değerleri tutar — bir kere kur, her yerde çalıştır.

**v2.0 değişikliği:** Proje yönetim `.md` dosyaları artık root'u kirletmiyor. ROADMAP/MEMORY/QA gibi dosyalar `.claude/{context,decisions,archives,references}/` altında gruplanıyor. Faz raporları `.claude/archives/PHASE_NN_<konu>.md` formatında. v1 → v2 migration için bkz. [CHANGELOG.md](CHANGELOG.md).

---

## ⚡ Hızlı Başlangıç (komutları unutsan da olur)

### 1. Skill'i bir kerelik kur

```bash
git clone https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi.git ~/.claude/skills/kod-fabrikasi
```

### 2. Yeni bir projeye girdiğinde

```bash
cd <yeni-proje>
bash ~/.claude/skills/kod-fabrikasi/scripts/init.sh   # 4 soru sorar, her şeyi kurar
make setup-hooks                                       # git hook'ları (pre-commit + post-commit)
make bundle                                            # ilk Drive + NotebookLM eşitlemesi
```

### 3. Faz başlat (Claude'a tek satır)

```text
"FAZ_PROMPT'u oku ve sıradaki fazı başlat."
```

Claude 6 adımlı disiplinle çalışır: bağlam topla → plan sun → **onay bekle** → uygula + test → faz raporu yaz (`.claude/archives/PHASE_NN_*.md`) → ROADMAP/MEMORY/QA güncelle → commit. Post-commit hook NotebookLM'i otomatik eşitler.

### 4. v1 projelerinden v2'ye geçiş

Eski projende `ROADMAP.md`, `MEMORY.md` vs. root'ta mı? [CHANGELOG.md](CHANGELOG.md) → "Migration Rehberi (v1 → v2)" bölümü tek tek komutları gösterir.

---

## 📦 Ön Gereksinimler

```bash
# Mimari haritalayıcı
python3 -m pip install graphifyy

# NotebookLM API + tarayıcı eklentisi
python3 -m pip install "notebooklm-py[browser]"
playwright install chromium

# Google hesabıyla NotebookLM'e giriş (bir kerelik)
notebooklm login
```

Doğrulama:
```bash
notebooklm list
graphify --version
```

> ⚠️ `notebooklm-py` **hangi Python'a kuruluysa** `init.sh` o Python'un tam yolunu sorar (PATH varsaymak hook'larda patlar — bkz. [Tuzak #3](references/tuzaklar.md)).

---

## 🏗️ Skill Yapısı

```text
~/.claude/skills/kod-fabrikasi/
├── SKILL.md                          # Frontmatter + 6 adımlık iş akışı özeti
├── references/                       # Level-3: gerektiğinde yüklenir
│   ├── workflow.md                   # Faz akışı detayı
│   ├── kurulum-rehberi.md            # Yeni proje kurulumu
│   ├── notebooklm-graphify.md        # Etkili kullanım
│   ├── faz-raporu-sablonu.md         # Rapor şablonu + örnek
│   └── tuzaklar.md                   # 10 kritik tuzak (geçmişten damıtılmış)
├── scripts/
│   ├── init.sh                       # İnteraktif kurulum (4 soru)
│   ├── bundle.py                     # Config-driven; Drive + NotebookLM ayna senkron
│   ├── Makefile                      # bundle / graphify-update / end-phase / setup-hooks
│   └── setup-hooks.sh                # Framework-aware (flutter/go/php/python/node/none)
└── assets/
    └── kod-fabrikasi.config.example.json
```

`init.sh` projeyi şu hale getirir:

```text
<proje-root>/
├── .claude/kod-fabrikasi.config.json   # tüm proje-spesifik değerler burada
├── bundle.py                            # config'ten okur
├── Makefile                             # config'ten okur
├── setup-hooks.sh                       # config'ten framework'ü okur, doğru hook'u üretir
├── reports/                             # faz raporları buraya yazılır
├── ROADMAP.md / MEMORY.md / QA_REPORTS.md  # senin tarafından oluşturulur
└── .gitignore (graphify-out/, __pycache__/, tum_kodlar.txt eklenir)
```

---

## 🧠 Sistem Nasıl Çalışır

```text
Sen → kod yaz + ROADMAP/MEMORY/QA güncelle → git commit
                                                  │
                                  pre-commit ─────┤
                                                  ├─ testler (framework'e göre)
                                                  │
                                  post-commit ────┤
                                                  ├─ graphify update . (AST mimari harita)
                                                  └─ bundle.py
                                                       ├─ kodu paketle → tum_kodlar.txt
                                                       ├─ kritik dökümanlar → Drive
                                                       ├─ reports/ + graphify-out/ → Drive ayna
                                                       └─ NotebookLM'i Drive ile birebir eşitle
                                                  │
                                  NotebookLM web ─┘  ← "Yenile" butonu
```

| Parça | Ne yapar |
| --- | --- |
| **Claude / Antigravity** | Asıl işi yapar: kod yazar, faz raporu yazar, ROADMAP/MEMORY/QA günceller |
| **NotebookLM** | Projeyi okumuş danışman — soru sorarsın, cevap verir. Dosya yazmaz, faz yapmaz |
| **Graphify** | AST tabanlı mimari harita — refactor öncesi etki analizi |
| **bundle.py** | Drive ve NotebookLM'i kod + dökümanlarla birebir aynalar |
| **Git hooks** | Her commit'te otomatik tetikler |

---

## ⚙️ Config Şeması

`.claude/kod-fabrikasi.config.json` (init.sh tarafından üretilir):

```json
{
  "drive_folder_path": "/Users/.../Drive'ım/DEV_PROJELERI/<proje>",
  "notebook_id": "uuid-from-notebooklm",
  "python_bin": "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
  "graphify_bin": "/Library/Frameworks/Python.framework/Versions/3.13/bin/graphify",
  "framework": "flutter",
  "critical_docs": ["ROADMAP.md", "MEMORY.md", "QA_REPORTS.md", ...],
  "sync_dirs": ["reports", "graphify-out"],
  "phase_files": { "roadmap": "ROADMAP.md", ... }
}
```

Tam şablon: [`assets/kod-fabrikasi.config.example.json`](assets/kod-fabrikasi.config.example.json)

**Desteklenen framework'ler** (pre-commit test komutu seçimi):
- `flutter` → `flutter analyze` + `flutter test`
- `go` → `go test ./...`
- `php-laravel` → `php artisan test`
- `python` → `pytest`
- `node` → `npm test`
- `none` → test komutu yok

---

## 🛠️ Günlük Komutlar

```bash
make bundle              # Manuel: kod paketle + Drive + NotebookLM eşitle
make graphify-update     # Manuel: mimari haritayı güncelle
make end-phase           # Faz sonu: graphify + bundle birlikte
make setup-hooks         # Hook'ları (yeniden) kur
make check-config        # Config'i doğrula
```

Veya sadece `git commit` at — post-commit hook her şeyi otomatik yapar.

---

## 🚫 10 Kritik Tuzak (sistemi "iyileştireyim" derken düşme)

`bundle.py` ve `setup-hooks.sh` bu hatalardan geçerek olgunlaştı. Detay: [`references/tuzaklar.md`](references/tuzaklar.md)

1. NotebookLM kaynaklarını başlığa göre dict'leme (çiftler birikir)
2. Alt klasör dosyalarında başlık çakışması (`a/rapor.md` ≠ `b/rapor.md` → `__` ile düzleştir)
3. `python3` PATH varsayma (hook'lar farklı PATH ile çalışır)
4. Boş klasörde NotebookLM'i temizleme (güvenlik freni şart)
5. `__pycache__/` commit etme
6. Büyük HTML/JSON yükleme (NotebookLM boğulur)
7. `copytree(dirs_exist_ok=True)` (eski dosyalar birikir → `rmtree` + `copytree`)
8. `reports/` klasörünü `sync_dirs`'e koymama
9. Aynı içeriği hem `.md` hem `.txt` yazma (NotebookLM'de çift kaynak)
10. Runtime doğrulamayı atlayıp "yeşil" yazma

---

## 🆘 Sorun Giderme

| Sorun | Çözüm |
| --- | --- |
| `ModuleNotFoundError: notebooklm` | `python_bin` PATH'teki python3'e işaret ediyor ama paket başka python'a kurulu. `which python3` → config'i o yola sabitle. |
| NotebookLM'de çift kaynak | `make bundle` tekrar çalıştır — id bazında temizler. |
| `Drive klasöründe dosya yok` uyarısı | Güvenlik freni devreye girdi (iyi haber). Drive yolu doğru mu? Drive masaüstü çalışıyor mu? |
| Hook çalışmıyor | `make setup-hooks` tekrar çalıştır. `.git/hooks/post-commit` var mı kontrol et. |
| `init.sh: command not found` | Bash kullan: `bash ~/.claude/skills/kod-fabrikasi/scripts/init.sh` |

---

## 🔄 Güncelleme

```bash
cd ~/.claude/skills/kod-fabrikasi
git pull
```

Mevcut projelerin config'i değişmez; sadece skill içerikleri güncellenir.

---

## 📚 Kapsamlı Rehberler

- [`SKILL.md`](SKILL.md) — Claude'un okuduğu ana skill dosyası
- [`references/workflow.md`](references/workflow.md) — 6 adımlı faz akışı
- [`references/kurulum-rehberi.md`](references/kurulum-rehberi.md) — yeni proje kurulumu
- [`references/notebooklm-graphify.md`](references/notebooklm-graphify.md) — etkili kullanım
- [`references/faz-raporu-sablonu.md`](references/faz-raporu-sablonu.md) — rapor şablonu
- [`references/tuzaklar.md`](references/tuzaklar.md) — 10 kritik tuzak

---

## 📄 Lisans

MIT — bkz. [LICENSE](LICENSE)

---

## 🤝 Katkı

Bu skill kişisel iş akışımdan damıtıldı. Bug bildirimi / iyileştirme önerisi için **Issue** veya **PR** açabilirsiniz. Skill'i forklayıp kendi disiplininize uyarlayabilirsiniz.

**Yapı:** [Anthropic Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) spec'ine uygundur (frontmatter, progressive disclosure, references/scripts/assets klasörleri).
