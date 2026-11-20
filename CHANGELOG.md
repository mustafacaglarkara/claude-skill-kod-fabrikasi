# Changelog

Bu skill'in sürüm geçmişi. Önemli değişiklikler en üstte.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) Türkçe uyarlaması. Versioning: [SemVer](https://semver.org/).

---

## [3.1.0] — 2026-11-20

**Tema:** **Dijital ajans profili** — aynı skill, iki profil. `yazilim` (varsayılan) değişmedi; `ajans` profili çekirdek ekibin üstüne müşteri izolasyonu, kreatif QA kapısı, SEO/analitik/Cloudflare/YouTube API araçları ve site denetimi ekler. Kaynak: dijital ajans orkestrasyon raporu + yapılandırma belgesi (Claude Code + NotebookLM + GSC/GA4 + Cloudflare).

### Eklendi

- **`--profile ajans`** (`init`) ve **`kf.py profile ajans`** (mevcut v3 projeye katman ekler); **`kf.py client list|add|remove`** (müşteri klasörü şablondan + config `agency.clients[]` + CLAUDE.md bölümü). Config: `profile`, `agency{clients_dir, shared_dir, credentials_dir, agents, optional_agents, clients[]}`, `skill_dir` (proje kopyasındaki `kf.py` şablonları bulsun diye).
- **Ajans ajanları** (`assets/agents/ajans/`): `metin-yazari` (yazar; yalnızca müşteri `campaigns|content`), `marka-denetcisi` (salt okunur QA kapısı: ton, yasaklı kelime, Meta/Google/TikTok politikası, iddia, kanca, çapraz sızıntı), `seo-teknisyeni`, `rakip-analisti`, `site-denetcisi`, `cloudflare-operatoru` (hepsi dosya yazmaz), isteğe bağlı `reklam-stratejisti`. Rapor'daki `web-developer` çekirdek `gelistirici`'ye, `account-archivist` `faz-arsivcisi`'ne eşlendi.
- **Betikler** (`scripts/ajans/`, projeye `.claude/scripts/ajans/` olarak kopyalanır; stdlib; kimlikler `.credentials/.env`'den, asla yazdırılmaz; `--client <slug>`, `--json`, `--out`):
  - `cloudflare_ops.py`: okuma `zones check settings dns list ssl analytics security-events firewall list redirect list pagerules pages`; yazma `purge purge-all redirect add/remove dns add/update setting set dev-mode under-attack firewall add/remove` — `--yes` yoksa yalnızca PLAN; her yazma `clients/<slug>/infra/cloudflare-log.md`'ye kaydedilir; `dns delete` Claude için DENY; zone silme yok. `check` 25 satırlık sağlık özeti (SSL modu, HTTPS, TLS, HSTS, DNSSEC, dev mode, cache, Brotli/HTTP3, security level, bot, WAF/redirect sayısı, apex proxy, Rocket Loader).
  - `site_audit.py`: teknik SEO (title/description/H1/canonical/robots/JSON-LD/OG/hreflang/alt/viewport/lang), site düzeyi (http→https, www, robots.txt + Sitemap, sitemap.xml, 404), güvenlik başlıkları (6), Cloudflare tespiti, `--crawl N`, `--links` kırık bağlantı, `--competitor` hiyerarşi.
  - `pagespeed_check.py` (PSI v5: skorlar, lab CWV, CrUX p75, fırsatlar), `gsc_query.py` (summary/drops/ctr-gap/pages/queries/inspect), `ga4_query.py` (summary/channels/pages/landing/conversions), `youtube_fetch.py` (transkript + yorum + arama/kanal → NotebookLM kaynağı).
- **Şablonlar** (`assets/templates/ajans/`): müşteri `README.md`, `brand-guide.md`, `personas.md`; ortak `shared/copywriting-frameworks.md`, `shared/ad-policies.md`; `.credentials/README.md` + `env.example`; `CLAUDE_SECTION_AJANS.md` (CLAUDE.md'ye ajans yönlendirme tablosu + müşteri listesi).
- **settings.json** (ajans): deny `.credentials/**`, `**/service-account*.json`, `cloudflare_ops.py dns delete`; ask tüm Cloudflare yazma komutları + `wrangler deploy`. `.gitignore`: `.credentials/` (README/env.example hariç), `*service-account*.json`.
- **SessionStart hook**: ajans profilinde müşteri listesi + son denetim/kampanya/rapor dosyası.
- **selftest** (+~15 kontrol): ajans ajanları salt okunurluk, betikler, `.credentials` ignore + git'te sır yok, deny/ask kuralları, müşteri klasörleri, certifi/.env/service-account uyarıları.
- Referanslar: `references/ajans.md` (akışlar A-F, brif şablonu, izolasyon, faz hafızası ilişkisi), `references/cloudflare.md` (token izin tablosu, komut matrisi, `check` yorumu, senaryolar, sınırlar, hata kodları). `tuzaklar.md` 26 → 31.
- **Plugin güçlendirmeleri** (`kf.py plugins [--apply|--remove|--only]`): Anthropic marketplace / claude.ai kataloğundaki 16 plugin için katalog (profil + framework'e göre süzülür; LSP'ler, `security-guidance`, `pr-review-toolkit`, `claude-security`, `feature-dev`, `frontend-design`, `claude-md-management`, `engineering`, `coding-skills`, `backend-design`; ajansta `searchfit-seo`, `marketing`, `cloudflare`, `website-design`). Tespit `claude plugin list --json` (yedek: `installed_plugins.json` + `synced/`). `--apply`: ilgili ajan dosyalarına işaretli "Güçlendirmeler" bloğu (hangi `/plugin:skill` ne zaman) + `Skill` aracı; ajan başlatan skill'ler `FAZ_PROMPT.md`'ye ana oturum bloğu; `cloudflare` MCP için settings `ask`. `check` PLUGIN satırı, `selftest` uygulanan plugin'in kurulu kaldığını denetler. Kurulum rehberine 5. soru ("kurulsun mu?"; hayır = varsayılan ajanlar). `references/plugins.md` (katalog, mekanizma, etkinlik değerlendirmesi).
- `references/yol-haritasi.md`: finans katmanı (3.2, ajans/şirket finans operasyonu), `finans` profili (3.3, finansal yazılım), piyasa analizi (ayrı skill), plugin ölçümü ve diğer fikirler.
- `kf.py plugins --install [--only a,b] [--scope]`: kurulumda kullanıcı "kurulsun mu?" sorusuna evet derse seçilen plugin'ler `claude plugin install <id>@claude-plugins-official|anthropic-plugin-directory` ile etkileşimsiz kurulur ve ardından `--apply` çalışır; kurulamayan için claude.ai yolu gösterilir.

### Değişti

- `skill_dir()` arama sırası: skill kopyası > `KF_SKILL_DIR` > config `skill_dir` > `~/.claude/skills/kod-fabrikasi` (skill başka klasördeyse `client add`/`repair` yine şablon bulur).
- `print_next_steps` Python yolunu tırnaklar; `ensure_lines` LF yazar (Windows'ta `.gitignore` CRLF uyarısı).
- SKILL.md: ajans bölümü, tetikleyiciler, ASLA YAPMA #13-14.

### Geçiş

v3.0 projeler dokunmadan çalışır (`profile` yok = `yazilim`). Ajans katmanı: `python ~/.claude/skills/kod-fabrikasi/scripts/kf.py profile ajans --client "slug:Ad:domain"` → `.credentials/env.example` doldur → `kf.py selftest`.

---

## [3.0.0] — 2026-11-20

**Tema:** Tek oturumdan **ajan ekibine**; oturumlar arası **faz hafızası**; `make`/bash yerine tek **Python CLI**; Drive/NotebookLM **isteğe bağlı**. Kaynaklar: çok uygulamalı bir üründe haftalarca çalışan ajan ekibi oyun kitabı ve OtoSesli (Rust + Astro) orkestrasyon kurulumu.

### Eklendi

- **Ajan ekibi** (`assets/agents/`, `init` projeye kopyalar): çekirdek `kesifci`, `gelistirici`, `tester`, `reviewer`, `faz-arsivcisi`; isteğe bağlı `mimar`, `guvenlik-inceleyici`, `<alan>-uzmani` (N tane, config `agents.domain_experts`). Frontmatter `model`/`effort`/`maxTurns`/`color` resmi dokümandan doğrulandı. Her ajanda ortak **"Verimli çalış"** bloğu. `tester`/`reviewer` kod yazamaz; planlama belgelerini yalnızca `faz-arsivcisi` yazar (faz raporu dahil).
- **Faz hafızası**: `PROGRESS.md`, `DECISIONS.md` (ADR), `OPEN_QUESTIONS.md` eklendi (v2 dosyaları korunur). `scripts/faz_hafiza.py` SessionStart hook'u (`startup|resume|clear|compact`) durumu, sıradaki adımı, açık soruları, son ADR'yi ve git durumunu her oturuma yükler.
- **`scripts/kf.py`** tek giriş noktası: `check init repair migrate hooks secret-scan graphify bundle sync end-phase selftest status`. Windows/macOS/Linux; etkileşimsiz (`init` tüm bilgileri parametreyle alır).
- **`settings.json` birleştirme**: deny `.env`/pem/key; ask `git push`, `reset --hard`, `checkout --`, `stash`, `clean`, `rm -rf` ve config `live_write_commands`; SessionStart hook. Mevcut kurallar korunur.
- **`CLAUDE.md` bölümü** (işaretli; `repair` günceller): ajan yönlendirme tablosu, faz akışı, kurallar.
- **Pre-commit gizli bilgi taraması** (dosya adı kalıpları + `.env` değerlerinin izlenen içerikte aranması; değer yazdırılmaz). Tam test paketi pre-commit'ten kaldırıldı (tester ajanı koşar).
- **Obsidian senkronu** (`kf.py sync`): kasada `Proje` junction → `.claude/`, `Belgeler/`, `Kod Haritası/` (graphify export).
- `selftest`: 50+ kontrol (config, belgeler, ajan frontmatter ve salt-okunurluk, settings, hook çalışması, gitignore, git hook'ları, CLAUDE.md uzunluğu, entegrasyonlar, gizli bilgi).
- `.gitattributes` (LF), `.graphifyignore`, `.graphifyrc` şablonları. Config `version: 3`, `test_commands`, `live_write_commands`, `high_risk_areas`, `integrations.*.enabled`.
- Referanslar: `ajanlar.md`, `hafiza.md` (yeni); `tuzaklar.md` 11 → 26 tuzak.

### Değişti

- **Faz akışı 6 → 9 adım**: uygula → **tester** → **reviewer** → **faz-arsivcisi** ayrı adımlar; commit yalnızca kullanıcı isterse.
- **Paketleme güvenliği**: `bundle` artık `os.walk` yerine **`git ls-files`** kullanır; `.env`, döküm, veritabanı dosyaları git dışında olduğu için pakete hiç girmez. Düzleştirilen adlar baştaki noktayı kaldırır (`claude__archives__X.md`), yoksa NotebookLM toplayıcısı atlıyordu.
- Drive düzeni: `kod/tum_kodlar.txt`, `belgeler/`, `claude__archives/`, `graphify-out/` (yalnızca `.md`). Drive kapalı/erişilemezse `.claude/bundle-out/`.
- NotebookLM ve Drive **isteğe bağlı**; çekirdek (git + ajanlar + hafıza + graphify) onlarsız çalışır. NotebookLM aynalama mantığı (id bazlı silme, güvenlik freni, `__` düzleştirme) **değişmedi**.
- Post-commit'in tek sahibi `kf.py` (`end-phase`); `graphify hook install` kullanılmaz.
- Betikler kökten `.claude/scripts/` ve `.claude/hooks/` altına; `init.sh`, `setup-hooks.sh`, `Makefile`, `bundle.py` kaldırıldı (`migrate --remove-legacy` projelerden de kaldırır).
- Varsayılan yollar Windows'u da kapsar; `python_bin` varsayılanı `sys.executable`.
- Ana oturum `model`/`effortLevel` **yazılmaz** (kullanıcının varsayılanı değişmez).

### Kaldırıldı

- `scripts/init.sh` (etkileşimli `read`: Claude çalıştıramıyordu), `scripts/setup-hooks.sh`, `scripts/Makefile`, `scripts/bundle.py` (mantığı `kf.py bundle` içinde).
- SKILL.md'de var olmayan `--migrate-v2` referansı (yerine çalışan `kf.py migrate`).

### Geçiş (v1 / v2 → v3)

```bash
cd <proje>
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py migrate --dry-run
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py migrate --remove-legacy
python .claude/scripts/kf.py hooks
python .claude/scripts/kf.py selftest
```

`migrate`: belgeleri `git mv` ile v3 konumlarına taşır (`reports/fazNN_x.md` → `.claude/archives/PHASE_NN_x.md`), eski config'i `.v2.bak` olarak yedekleyip v3 şemaya çevirir (Drive/NotebookLM → `integrations`, `framework` → `test_commands`), eksik belge/ajan/hook/settings/CLAUDE.md bölümünü ekler. Eski Drive kök dosyaları (`tum_kodlar.txt`, `ROADMAP.md`, `CLAUDE_*.md`…) ilk `bundle`'da `stale_patterns` ile temizlenir. Commit önerisi: `chore: kod-fabrikasi v3 — ajan ekibi, faz hafızası, kf.py`.

---

## [2.0.0] — 2026-05-26

**Tema:** Proje kök dizini temizliği; AI yönetim `.md` dosyaları `.claude/{context,decisions,archives,references}/` altında.

### Eklendi
- Klasör konvansiyonu; `PHASE_NN_<konu>.md` rapor formatı; bundle.py auto-discovery (belgelendi, kodda tamamlanmadı — v3'te kapatıldı); config `phase_files` v2 yolları.

### Değişti
- SKILL.md, workflow.md, config örneği, `sync_dirs` varsayılanı `[".claude/archives", "graphify-out"]`.

### Kaldırıldı
- `reports/` konvansiyonu.

---

## [1.0.0] — 2026-05-25

İlk yayın: `OtoLog/.claude/skills/kod-fabrikasi/`'den proje-bağımsız, config-driven skill. SKILL.md, 5 referans, `init.sh`, `bundle.py`, `setup-hooks.sh`, config örneği, MIT lisans.
