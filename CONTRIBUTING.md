# Katkıda Bulunma

Bu skill kişisel iş akışından çıktı; fork, issue, PR açık.

## Hızlı yönlendirme

| Ne istiyorsun? | Nereye |
| --- | --- |
| Skill'i kullanmak | [README.md](README.md) |
| Sürüm geçmişi / geçiş | [CHANGELOG.md](CHANGELOG.md) |
| Bug bildirmek | GitHub Issue: `kf.py selftest` çıktısı + repro + işletim sistemi |
| Özellik önerisi | GitHub Issue ("enhancement"): kullanım senaryosu |
| Kod katkısı | PR; aşağıdaki sözleşme |

## Geliştirme kurulumu ve test

```bash
git clone https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi.git ~/.claude/skills/kod-fabrikasi
# Boş deneme projesinde uçtan uca:
mkdir /tmp/kf-test && cd /tmp/kf-test && git init -b main
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py init --framework none --test-cmd "echo ok" --live-cmd "echo deploy" --agents mimar,guvenlik-inceleyici --expert "x-uzmani:X API:src/"
python .claude/scripts/kf.py hooks && python .claude/scripts/kf.py selftest     # FAIL: 0 olmalı
# Ajans profili (ayrı deneme projesinde):
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py init --framework node --test-cmd "echo ok" --profile ajans --client "demo:Demo:demo.example.com" --agency-agents reklam-stratejisti
python .claude/scripts/kf.py client add --slug b --name "B" --domain b.com && python .claude/scripts/kf.py selftest   # FAIL: 0
echo "A=1" > a.txt && git add -A && git commit -m t                               # pre-commit + post-commit çalışır
python .claude/scripts/kf.py bundle --dry-run
# v2 fixture ile migrate --dry-run / migrate --remove-legacy da dene
```

Önce [references/tuzaklar.md](references/tuzaklar.md): 26 tuzak. PR hiçbirini tetiklememeli.

## PR sözleşmesi

- **Yapı:** referanslar `references/`, betikler `scripts/` (`kf.py`, `faz_hafiza.py` ve ajans profili için `scripts/ajans/*.py`; yeni bash/Makefile ekleme), şablonlar `assets/agents/` (+ `assets/agents/ajans/`) ve `assets/templates/` (+ `assets/templates/ajans/`), örnekler `assets/`. Kökte README/LICENSE/CHANGELOG/CONTRIBUTING/SKILL dışında dosya yok.
- **Ajans betikleri:** yalnızca stdlib (Google/YouTube kütüphaneleri tembel import + açık kurulum mesajı); kimlikler `_ortak.need()` ile `.credentials/.env`'den, hiçbir çıktıya yazılmaz (`mask()`); her yazma komutu `write_guard()` (PLAN → `--yes`) + `audit()`; TLS doğrulaması kapatılmaz; `--client`, `--json`, `--out` ortak parametreler. Test: `python scripts/ajans/site_audit.py https://www.python.org --crawl 3 --links`, token'sız `cloudflare_ops.py zones` açık hata vermeli.
- **Etkileşimsizlik:** betikler soru sormaz (`input()`/`read` yok); her bilgi parametre ya da config.
- **Platform:** Windows + macOS + Linux. Dosya yazarken `newline="\n"`, yollar `pathlib`, hook komutlarında tam `python_bin`.
- **Güvenlik:** paket yalnızca `git ls-files`; `.env` okunmaz; NotebookLM güvenlik freni ve id bazlı silme değişmez.
- **Ajan dosyaları:** `name` = dosya adı; `description` katman + model + ne zaman + "PROAKTİF" (`selftest` kontrol eder); salt okunurlarda Edit/Write yok ve `maxTurns` var; "Verimli çalış" bloğu kelimesi kelimesine.
- **Plugin kataloğu (`PLUGIN_CATALOG`):** yalnızca Anthropic marketplace'i ya da claude.ai kataloğunda yayımlanan plugin'ler; her girdi `id`, `market`, `profile`, `why` ve ajan → (skill, ne zaman) eşlemesi taşır. Ajan başlatan skill'ler `orchestrator`'a, yalnızca kurulması yeten plugin'ler `env`'e; dış sisteme yazabilen MCP'ler `settings_ask`'a. Skill adını plugin içeriğinden doğrula (`claude plugin details <ad>`), tahmin etme. Çekirdek ajan şablonlarına plugin bağımlılığı yazılmaz; blok yalnızca `--apply` ile işaretli alanda.
- **SKILL.md:** < 200 satır; "İlk kontrol" bloğu ve "ASLA YAPMA" listesi korunur; yeni tuzak öğrenildikçe eklenir, silinmez.
- **Geriye uyumluluk:** v2 projeler `migrate` ile geçer; breaking change → MAJOR + CHANGELOG'da geçiş rehberi.
- **Commit:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`), tek satır özet.

## Felsefe

1. Önce onay, sonra kod. 2. Kodu yazan kendi işini onaylamaz. 3. Tuzaklar silinmez, eklenir. 4. Config-driven; hardcoded yol yok. 5. Türkçe öncelikli; İngilizce için `references/en/` paralel dizin.
