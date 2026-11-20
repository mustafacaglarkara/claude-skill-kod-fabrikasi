# Changelog

Bu skill'in sürüm geçmişi. Önemli değişiklikler en üstte.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) Türkçe uyarlaması. Versioning: [SemVer](https://semver.org/).

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
