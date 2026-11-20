# Kod Fabrikası — Claude Code Skill (v3.0)

> **EN:** AI-powered software factory for Claude Code: the main session orchestrates a team of subagents (scout, developer, tester, reviewer, archivist + optional architect, security reviewer, domain experts), keeps project memory across sessions (PROGRESS / ADR / open questions + a SessionStart hook), maps the code with graphify, enforces permission rules, and optionally mirrors docs and code to Google Drive, NotebookLM and Obsidian. One Python CLI (`kf.py`), one per-project config, Windows/macOS/Linux. Documentation is in Turkish.

**TR:** Ana Claude Code oturumu **orkestratördür**: işi böler, `.claude/agents/` altındaki uzman ajanlara brif verir, sonuçları birleştirir. Kodu yazan ajan kendi işini onaylamaz. Proje hafızası `.claude/` altındaki belgelerde durur ve her oturuma otomatik yüklenir. Kod haritası graphify; Drive / NotebookLM / Obsidian isteğe bağlı. Tek komut arayüzü `kf.py`; `make` ve bash gerekmez.

**v3.0:** ajan ekibi + faz hafızası + `kf.py`. v2'den geçiş: `kf.py migrate` (bkz. [CHANGELOG.md](CHANGELOG.md)).

---

## ⚡ Hızlı başlangıç

```bash
# 1. Skill'i bir kez kur
git clone https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi.git ~/.claude/skills/kod-fabrikasi

# 2. Projede Claude Code'a yaz:
#    "Bu projeye kod fabrikası kur."
#    Claude projeyi keşfeder, tek toplu soru sorar (test komutları, canlıya yazan komutlar,
#    riskli alanlar, ekip/entegrasyonlar) ve kf.py init ... ile kurar; hooks + selftest çalıştırır.

# 3. Faz başlat:
#    "Sıradaki fazı başlat."
```

Akış: bağlam → plan → **onay** → `gelistirici` (paralel ≤3) → `tester` → `reviewer` → `faz-arsivcisi` → commit (yalnızca siz isterseniz). Post-commit: graphify + bundle + sync.

Elle kurulum örneği:

```bash
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py init --framework node \
  --test-cmd "npm test" --live-cmd "npm run deploy" --risk auth \
  --agents mimar,guvenlik-inceleyici --expert "odeme-uzmani:Ödeme API:src/payments/"
python .claude/scripts/kf.py hooks && python .claude/scripts/kf.py selftest
```

---

## 👥 Ekip

| Ajan | Model | Yazar | Görev |
| --- | --- | --- | --- |
| `kesifci` | sonnet | ❌ | "X nerede, Y'yi kim çağırıyor" → dosya:satır |
| `gelistirici` | opus | ✅ | Onaylı planın bağımsız parçası |
| `tester` | sonnet | ❌ | Derleme / test / tip denetimi, kanıtlı rapor |
| `reviewer` | opus | ❌ | Donmuş diff'in bağımsız incelemesi |
| `faz-arsivcisi` | sonnet | yalnızca `.claude/*.md` | PROGRESS, ROADMAP, ADR, açık sorular, faz raporu |
| `mimar` (isteğe bağlı) | opus xhigh | ✅ | Yüksek risk, tasarım, kök neden |
| `guvenlik-inceleyici` (isteğe bağlı) | opus | ❌ | Auth / token / yükleme / PII |
| `<alan>-uzmani` (isteğe bağlı) | sonnet | ❌ | Dış API / alan kuralları |

Her ajan dosyasında ortak **"Verimli çalış"** bloğu (harita önce, aralık okuma, orantılı test, stash yasağı, ~120 çağrı sınırı). Ayrıntı: [references/ajanlar.md](references/ajanlar.md).

---

## 🏗️ Yapı

```text
~/.claude/skills/kod-fabrikasi/
├── SKILL.md                      # Claude'un okuduğu ana dosya
├── references/                   # workflow · ajanlar · hafiza · kurulum-rehberi · faz-raporu-sablonu · notebooklm-graphify · tuzaklar
├── scripts/
│   ├── kf.py                     # CLI: check init repair migrate hooks secret-scan graphify bundle sync end-phase selftest status
│   └── faz_hafiza.py             # SessionStart hook
└── assets/
    ├── kod-fabrikasi.config.example.json
    ├── settings.example.json     # deny/ask kuralları + hook (birleştirilir)
    ├── agents/                   # 8 ajan şablonu ({{PROJECT_NAME}} vb. doldurulur)
    └── templates/                # ROADMAP PROGRESS DECISIONS OPEN_QUESTIONS FAZ_PROMPT MEMORY QA_REPORTS KNOWN_BUGS
                                  # NOTEBOOKLM_SUMMARY GRAPHIFY_NOTES PHASE_TEMPLATE CLAUDE_SECTION graphifyignore graphifyrc
```

Projede oluşan yapı:

```text
<proje>/
├── CLAUDE.md                     # "Alt ajanlar ve proje hafızası" bölümü (işaretli, güncellenebilir)
├── .claude/
│   ├── kod-fabrikasi.config.json # version 3; test/canlı komutlar, riskli alanlar, ajanlar, entegrasyonlar
│   ├── settings.json             # deny .env/pem/key · ask push/reset/canlı komutlar · SessionStart hook
│   ├── agents/  hooks/faz_hafiza.py  scripts/kf.py
│   ├── archives/   ROADMAP PROGRESS PHASE_TEMPLATE PHASE_NN_* NOTEBOOKLM_SUMMARY
│   ├── decisions/  DECISIONS (ADR) OPEN_QUESTIONS FAZ_PROMPT
│   ├── context/    MEMORY GRAPHIFY_NOTES
│   ├── references/ QA_REPORTS KNOWN_BUGS
│   └── bundle-out/               # Drive kapalıysa paket (gitignore)
└── .graphifyignore .graphifyrc .gitattributes
```

---

## 🔐 Güvenlik ilkeleri

- Paket (`kf.py bundle`) **yalnızca `git ls-files`** dosyalarından oluşur; `.env`, veritabanı, döküm git dışında olduğu için hiç girmez.
- Pre-commit hook staged dosyalarda gizli bilgi tarar (ad kalıpları + `.env` değerleri); eşleşmede commit durur.
- `settings.json`: `.env`/pem/key okunamaz; `git push`, `reset --hard`, `stash`, canlıya yazan komutlar her seferinde sorar.
- Ajanlar commit/push/deploy yapmaz; `tester` ve `reviewer` kod yazamaz; planlama belgelerini yalnızca `faz-arsivcisi` günceller.
- NotebookLM aynalamada güvenlik freni: paket klasörü boşsa hiçbir kaynak silinmez.

---

## 🛠️ Komutlar

```bash
python .claude/scripts/kf.py check        # kurulum durumu
python .claude/scripts/kf.py status       # faz hafızası (hook çıktısı)
python .claude/scripts/kf.py selftest     # PASS/FAIL/WARN
python .claude/scripts/kf.py bundle       # paket + Drive + NotebookLM (etkinse); --dry-run
python .claude/scripts/kf.py graphify     # harita
python .claude/scripts/kf.py end-phase    # graphify + bundle + sync (post-commit bunu çağırır)
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py migrate --dry-run   # v1/v2 → v3
```

`KF_SKIP=1 git commit ...` post-commit otomasyonunu bir kez atlar.

---

## 📦 Ön gereksinimler

git · Python 3.10+ · (önerilir) graphify: `uv tool install "graphifyy[sql]" --python 3.13` · (NotebookLM etkinse) `pip install "notebooklm-py[browser]"`, `playwright install chromium`, `notebooklm login`; hangi Python'a kurulduysa config `python_bin` o olmalı.

---

## 🆘 Sorun giderme

| Sorun | Çözüm |
| --- | --- |
| `Agent type 'x' not found` | Ajanlar birkaç saniyede yüklenir (hot reload); olmazsa yeni oturum. |
| Hook bağlama hiçbir şey eklemiyor | PROGRESS başlıkları `## Durum` / `## Günlük` / `## Sıradaki adım` değil; hook'u uyarla. `kf.py status` ile dene. |
| `ModuleNotFoundError: notebooklm` | `python_bin` yanlış Python'a işaret ediyor. `kf.py selftest`. |
| post-commit iki kez graphify çalıştırıyor | `graphify hook install` kurulmuş; `kf.py hooks` tek sahip olmalı. |
| `graphify: command not found` | `uv tool update-shell`, terminali yeniden aç; ya da config `graphify_bin` tam yol. |
| `init` "config zaten var" (exit 2) | `repair` (eksikler), `migrate` (v1/v2), `init --force`. |
| Drive klasörü yok uyarısı | Paket `.claude/bundle-out/` altına yazıldı; Drive masaüstü çalışıyor mu? |

---

## 📚 Rehberler

[SKILL.md](SKILL.md) · [references/workflow.md](references/workflow.md) · [references/ajanlar.md](references/ajanlar.md) · [references/hafiza.md](references/hafiza.md) · [references/kurulum-rehberi.md](references/kurulum-rehberi.md) · [references/faz-raporu-sablonu.md](references/faz-raporu-sablonu.md) · [references/notebooklm-graphify.md](references/notebooklm-graphify.md) · [references/tuzaklar.md](references/tuzaklar.md)

## 📄 Lisans ve katkı

MIT — [LICENSE](LICENSE). Katkı kuralları: [CONTRIBUTING.md](CONTRIBUTING.md). Yapı [Anthropic Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) spec'ine uygundur.
