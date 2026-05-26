# Changelog

Bu skill'in sürüm geçmişi. Önemli değişiklikler en üstte.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) Türkçe uyarlaması.
Versioning: [SemVer](https://semver.org/) — `MAJOR.MINOR.PATCH`.

---

## [2.0.0] — 2026-05-26

**Tema:** Proje kök dizini temizliği. AI yönetim `.md` dosyaları artık `.claude/` altında konuya göre gruplanıyor.

### Eklendi (Added)

- **Klasör konvansiyonu** — `.claude/{context,decisions,archives,references}/` alt klasörleri:
  - `context/` → MEMORY.md, GRAPHIFY_NOTES.md (kalıcı bağlam)
  - `decisions/` → FAZ_PROMPT.md (aktif faz/iş akışı kuralları)
  - `archives/` → ROADMAP.md, NOTEBOOKLM_SUMMARY.md, PHASE_TEMPLATE.md, PHASE_NN_*.md (kronolojik kayıt)
  - `references/` → KNOWN_BUGS.md, QA_REPORTS.md (sürekli güncellenen kataloglar)
- **`PHASE_NN_<konu>.md` rapor formatı** — eski `reports/fazNN_*.md` yerine. `.claude/archives/PHASE_TEMPLATE.md` şablonu birebir uygulanır.
- **bundle.py auto-discovery** — `critical_docs` boş bırakılırsa `.claude/` alt klasörlerini otomatik tarar; backward compat (root'taki eski dosyaları da görür).
- **Config `phase_files`** alanında varsayılan v2 path'leri.

### Değişti (Changed)

- **SKILL.md** — yeni klasör konvansiyonu bölümü; "İlk Kontrol" adımı v1/v2 ayrımı yapar; tuzak listesi #8 ve #9 güncellendi (root'a yönetim dosyası bırakma, `reports/` yerine `archives/`).
- **`references/workflow.md`** — Adım 4 ve Adım 5 yeni path'lere işaret eder.
- **`assets/kod-fabrikasi.config.example.json`** — `phase_files` v2 path'leri; `critical_docs` boş array (auto-discover).
- **`sync_dirs` varsayılan** — eski `["reports", "graphify-out"]` yerine `[".claude/archives", "graphify-out"]`.

### Kaldırıldı (Removed)

- Eski `reports/` klasör konvansiyonu (yine de bundle.py auto-discover ile bulur eğer kalmışsa).

### Migration Rehberi (v1 → v2)

Eski projelerde manuel taşıma (otomatik `init.sh --migrate-v2` v2.1'de gelecek):

```bash
cd <proje-root>
mkdir -p .claude/{context,decisions,archives,references}

git mv MEMORY.md .claude/context/
git mv GRAPHIFY_NOTES.md .claude/context/
git mv FAZ_PROMPT.md .claude/decisions/
git mv ROADMAP.md .claude/archives/
git mv NOTEBOOKLM_SUMMARY.md .claude/archives/
git mv KNOWN_BUGS.md .claude/references/
git mv QA_REPORTS.md .claude/references/

# Eski faz raporlarını taşı + adlandır
git mv reports/fazNN_konu.md .claude/archives/PHASE_NN_konu.md

# Config'i güncelle
$EDITOR .claude/kod-fabrikasi.config.json  # phase_files path'lerini v2'ye çevir
```

Commit mesajı önerisi: `chore: kod-fabrikasi v2 — root cleanup, .claude/ alt klasör konvansiyonu`

---

## [1.0.0] — 2026-05-25

**Tema:** İlk yayın — projeye özgü `OtoLog/.claude/skills/kod-fabrikasi/`'den proje-bağımsız, config-driven hale getirildi.

### Eklendi

- `SKILL.md` — Anthropic Agent Skills spec uyumlu frontmatter + 6 adımlık faz akışı.
- `references/` (5 dosya): workflow, kurulum-rehberi, notebooklm-graphify, faz-raporu-sablonu, tuzaklar.
- `scripts/init.sh` — interaktif 4-soru kurulum, config-driven `bundle.py`/`Makefile`/`setup-hooks.sh` template'leri.
- `scripts/bundle.py` — config-driven; Drive + NotebookLM ayna senkronu.
- `scripts/setup-hooks.sh` — framework-aware (flutter/go/php-laravel/python/node/none).
- `assets/kod-fabrikasi.config.example.json` — örnek konfigürasyon.
- README.md, LICENSE (MIT), .gitignore.

### Yapısı

- Her proje kendi `.claude/kod-fabrikasi.config.json`'unu tutar.
- v1'de proje yönetim dosyaları root'tadır (ROADMAP.md, MEMORY.md, …) — v2'de bu değişti.
