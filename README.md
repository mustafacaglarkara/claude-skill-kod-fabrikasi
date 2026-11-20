# Kod Fabrikası — Claude Code Skill (v3.1)

> **EN:** AI-powered software factory for Claude Code: the main session orchestrates a team of subagents (scout, developer, tester, reviewer, archivist + optional architect, security reviewer, domain experts), keeps project memory across sessions (PROGRESS / ADR / open questions + a SessionStart hook), maps the code with graphify, enforces permission rules, and optionally mirrors docs and code to Google Drive, NotebookLM and Obsidian. v3.1 adds a **digital agency profile**: per-client isolation, copywriter + brand/policy guardian QA gate, SEO technician (Search Console / GA4 / PageSpeed), competitor analyst (site + YouTube → NotebookLM), live-site auditor and a Cloudflare operator (plan → approve → apply). One Python CLI (`kf.py`), one per-project config, Windows/macOS/Linux. Documentation is in Turkish.

**TR:** Ana Claude Code oturumu **orkestratördür**: işi böler, `.claude/agents/` altındaki uzman ajanlara brif verir, sonuçları birleştirir. Kodu yazan ajan kendi işini onaylamaz. Proje hafızası `.claude/` altındaki belgelerde durur ve her oturuma otomatik yüklenir. Kod haritası graphify; Drive / NotebookLM / Obsidian isteğe bağlı. Tek komut arayüzü `kf.py`; `make` ve bash gerekmez.

**v3.1:** `yazilim` profili (v3.0 ile aynı) + **`ajans` profili** (dijital ajans katmanı). v2'den geçiş: `kf.py migrate`; ajans katmanı: `kf.py profile ajans` (bkz. [CHANGELOG.md](CHANGELOG.md)).

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

## 🏢 Dijital ajans profili (v3.1)

```bash
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py init --framework node --test-cmd "npm test" \
  --profile ajans --client "musteri-a:Müşteri A:musteri-a.com" --agency-agents reklam-stratejisti
# ya da mevcut v3 projede:  python .claude/scripts/kf.py profile ajans --client "musteri-a:Müşteri A:musteri-a.com"
python .claude/scripts/kf.py client add --slug musteri-b --name "Müşteri B" --domain musteri-b.com --ga4 123456
cp .credentials/env.example .credentials/.env   # Cloudflare token, PageSpeed/YouTube key; service-account.json (GSC/GA4) — Claude okuyamaz
python .claude/scripts/kf.py selftest
```

| Ajan | Yazar | Görev | Kapı |
| --- | --- | --- | --- |
| `metin-yazari` | yalnızca `clients/<slug>/campaigns|content` | reklam, sosyal, e-posta, blog, video senaryosu | → `marka-denetcisi` |
| `marka-denetcisi` | ❌ | ton, yasaklı kelime, Meta/Google/TikTok politikası, iddia, kanca, müşteriler arası sızıntı | ONAY olmadan teslim yok |
| `seo-teknisyeni` | ❌ | GSC / GA4 / PageSpeed → öncelikli aksiyon listesi | — |
| `rakip-analisti` | ❌ | rakip hiyerarşi / schema / içerik boşluğu, YouTube transkript → NotebookLM | — |
| `site-denetcisi` | ❌ | yaptığımız siteyi teslim öncesi / yayın sonrası / periyodik test | "yayına hazır" yalnızca raporla |
| `cloudflare-operatoru` | API (`--yes`) | zone sağlığı, purge, 301, DNS, SSL/WAF, dev-mode, under-attack, Pages durumu | PLAN → onay → `--yes` |
| `reklam-stratejisti` (isteğe bağlı) | ❌ | kanal / bütçe / huni / UTM / test planı | — |

**Plugin güçlendirmeleri (isteğe bağlı):** `kf.py plugins` profil ve framework'e göre Anthropic plugin'lerini önerir (`typescript-lsp`, `security-guidance`, `pr-review-toolkit`, `engineering`; ajansta `searchfit-seo`, `marketing`, `cloudflare`...). Kurulum sırasında bir kez sorulur; kurulanlar `kf.py plugins --apply` ile ilgili ajana "Güçlendirmeler" bloğu + `Skill` aracı olarak işlenir, `--remove` geri alır. Kurulmazsa varsayılan ajanlar aynen çalışır. Katalog ve değerlendirme: [references/plugins.md](references/plugins.md). Gelecek planı (finans katmanı vb.): [references/yol-haritasi.md](references/yol-haritasi.md).

Müşteriler `clients/<slug>/` altında izole (brand-guide, personas, campaigns, seo/reports, audits, research, youtube-research, infra). Betikler `.claude/scripts/ajans/`: `cloudflare_ops.py` · `site_audit.py` · `pagespeed_check.py` · `gsc_query.py` · `ga4_query.py` · `youtube_fetch.py` (stdlib; `--client <slug> --out dosya`; kimlikler `.credentials/.env`'den, asla yazdırılmaz). Cloudflare yazma komutları `--yes` olmadan yalnızca PLAN basar, settings.json `ask` ile ikinci kez sorulur, `dns delete` Claude için yasak, zone silme yok. Akışlar: [references/ajans.md](references/ajans.md) · Cloudflare: [references/cloudflare.md](references/cloudflare.md).

---

## 🏗️ Yapı

```text
~/.claude/skills/kod-fabrikasi/
├── SKILL.md                      # Claude'un okuduğu ana dosya
├── references/                   # workflow · ajanlar · hafiza · kurulum-rehberi · faz-raporu-sablonu · notebooklm-graphify · tuzaklar
├── scripts/
│   ├── kf.py                     # CLI: check init repair migrate profile client plugins hooks secret-scan graphify bundle sync end-phase selftest status
│   ├── faz_hafiza.py             # SessionStart hook
│   └── ajans/                    # cloudflare_ops site_audit pagespeed_check gsc_query ga4_query youtube_fetch (_ortak)
└── assets/
    ├── kod-fabrikasi.config.example.json
    ├── settings.example.json     # deny/ask kuralları + hook (birleştirilir)
    ├── agents/                   # 8 ajan şablonu + ajans/ 7 ajans ajanı ({{PROJECT_NAME}} vb. doldurulur)
    └── templates/                # ROADMAP PROGRESS DECISIONS OPEN_QUESTIONS FAZ_PROMPT MEMORY QA_REPORTS KNOWN_BUGS
                                  # NOTEBOOKLM_SUMMARY GRAPHIFY_NOTES PHASE_TEMPLATE CLAUDE_SECTION graphifyignore graphifyrc
                                  # ajans/: README brand-guide personas copywriting-frameworks ad-policies credentials-README env.example CLAUDE_SECTION_AJANS
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

git · Python 3.10+ · (önerilir) graphify: `uv tool install "graphifyy[sql]" --python 3.13` · (NotebookLM etkinse) `pip install "notebooklm-py[browser]"`, `playwright install chromium`, `notebooklm login`; hangi Python'a kurulduysa config `python_bin` o olmalı. Ajans profili: `pip install certifi` (Windows TLS kökleri), GSC/GA4 için `google-auth google-api-python-client google-analytics-data`, YouTube transkripti için `youtube-transcript-api`; Cloudflare/PageSpeed/site denetimi stdlib ile çalışır.

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
| `CERTIFICATE_VERIFY_FAILED` (site_audit / pagespeed) | Windows OpenSSL deposunda kök eksik: `pip install certifi` (betikler otomatik kullanır). |
| `CLOUDFLARE_API_TOKEN tanimli degil` | `.credentials/env.example` → `.env`; token izinleri [references/cloudflare.md](references/cloudflare.md). |
| Cloudflare purge komutu sorulmadan çalıştı | `/permissions` ile `Bash(*cloudflare_ops.py purge*)` kuralı geçerli mi; sürüm ortada `*` desteklemiyorsa tam yol önekiyle yaz. |

---

## 📚 Rehberler

[SKILL.md](SKILL.md) · [references/workflow.md](references/workflow.md) · [references/ajanlar.md](references/ajanlar.md) · [references/hafiza.md](references/hafiza.md) · [references/kurulum-rehberi.md](references/kurulum-rehberi.md) · [references/faz-raporu-sablonu.md](references/faz-raporu-sablonu.md) · [references/notebooklm-graphify.md](references/notebooklm-graphify.md) · [references/tuzaklar.md](references/tuzaklar.md) · [references/ajans.md](references/ajans.md) · [references/cloudflare.md](references/cloudflare.md) · [references/plugins.md](references/plugins.md) · [references/yol-haritasi.md](references/yol-haritasi.md)

## 📄 Lisans ve katkı

MIT — [LICENSE](LICENSE). Katkı kuralları: [CONTRIBUTING.md](CONTRIBUTING.md). Yapı [Anthropic Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) spec'ine uygundur.
