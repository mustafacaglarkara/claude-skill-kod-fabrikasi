---
name: kod-fabrikasi
description: AI destekli yazılım fabrikası (v3.1) — ana oturum orkestratör, alt ajan ekibi (kesifci, gelistirici, tester, reviewer, faz-arsivcisi + isteğe bağlı mimar, guvenlik-inceleyici, alan uzmanları), oturumlar arası faz hafızası (PROGRESS/DECISIONS/OPEN_QUESTIONS + SessionStart hook), graphify kod haritası, izin kuralları, isteğe bağlı Drive/NotebookLM/Obsidian senkronu ve DİJİTAL AJANS profili (metin-yazari, marka-denetcisi, seo-teknisyeni, rakip-analisti, site-denetcisi, cloudflare-operatoru; müşteri izolasyonu; GSC/GA4/PageSpeed/Cloudflare/YouTube API betikleri). KULLANICI faz başlatmak/bitirmek, "sıradaki faz", "nerede kalmıştık", alt ajan kurulumu, kod fabrikası kurulumu/migrasyonu, bundle, NotebookLM senkronu, graphify, git hook, roadmap/ADR/faz raporu güncelleme; ajans tarafında "dijital ajans kur", "müşteri ekle", "reklam metni yaz", "marka denetimi", "SEO raporu", "trafik neden düştü", "rakip analizi", "siteyi kontrol et / teslim öncesi denetim", "cache temizle", "yönlendirme ekle", "Cloudflare", "YouTube rakip araştırması" istediğinde MUTLAKA bu skill'i kullan. "FAZ_PROMPT", "faz raporu", "ADR", "açık soru", "kod fabrikası kur", "v2'den v3'e geçir", "selftest" gibi ifadelerde — açıkça "skill" demese bile — devreye gir.
allowed-tools: Read, Glob, Grep, Bash, Edit, Write, Agent, AskUserQuestion
---

# Kod Fabrikası (v3)

**Ne:** Ana Claude Code oturumu **orkestratördür**; işi böler, `.claude/agents/` altındaki uzman ajanlara brif verir, sonuçları birleştirir, kullanıcıya raporlar. Kodu yazan ajan kendi işini onaylamaz. Proje hafızası `.claude/` altındaki planlama belgelerinde durur ve her oturuma `SessionStart` hook'u ile yüklenir. Kod haritası graphify; Drive/NotebookLM/Obsidian isteğe bağlı.

**Akış:** bağlam → plan → **ONAY** → `gelistirici` (paralel, ≤3) → `tester` → `reviewer` → `faz-arsivcisi` → commit (yalnızca kullanıcı isterse).

Tek komut arayüzü: `python .claude/scripts/kf.py <komut>` (Windows/macOS/Linux; `make` ve bash gerekmez). İki profil: `yazilim` (varsayılan) ve `ajans` (çekirdek + dijital ajans katmanı; bkz. [🏢 Dijital ajans](#-dijital-ajans-profili)).

---

## ⚙️ İlk kontrol (skill her devreye girdiğinde)

```bash
python .claude/scripts/kf.py check 2>/dev/null || python ~/.claude/skills/kod-fabrikasi/scripts/kf.py check
```

| `YAPI` çıktısı | Ne yap |
| --- | --- |
| `v3` | Hazır. Kullanıcının isteğine göre faz akışına geç. `SESSION HK: yok` ise `repair`. |
| `v2` / `v1` / `v1-config-yok` | Kullanıcıya sor: "v3'e geçireyim mi? (dosyalar `git mv` ile taşınır, eski `bundle.py`/`Makefile` kaldırılır, ajanlar ve hook eklenir)". Onayla: `kf.py migrate --dry-run` göster → `kf.py migrate --remove-legacy` → `kf.py hooks` → `kf.py selftest`. |
| `yok` | Kurulu değil. Kullanıcıya sor: "Bu projeye Kod Fabrikası kurayım mı?" Onaylarsa [references/kurulum-rehberi.md](references/kurulum-rehberi.md): **ilk soru departman** ("hangi departmanlar için? yazılım / dijital ajans / muhasebe (planlandı) / depo (planlandı)", çoklu seçim → `--department`), sonra tek toplu `AskUserQuestion`, sonra `kf.py init ...` (etkileşimsiz), sonra plugin sorusu. |
| `PROFIL: yazilim` + ajans isteği | Kullanıcı ajans işi istiyor (müşteri, reklam metni, SEO raporu, site denetimi, Cloudflare): "Ajans katmanını ekleyeyim mi?" → `kf.py profile ajans [--client slug:Ad:domain]` → `repair` → `selftest`. |
| `PLUGIN: kurulu-bekleyen N` | Kurulu Anthropic plugin'i var ama ajanlara işlenmemiş: "Güçlendirme olarak uygulayayım mı?" → `kf.py plugins --apply`. `onerilen-eksik` için kurulumda bir kez `AskUserQuestion` (çoklu seçim + "hiçbiri"): kabul → `kf.py plugins --install --only a,b` (kurar + uygular); ret → varsayılan ajanlar, bir daha sorma. Bkz. [references/plugins.md](references/plugins.md). |

`SKILL DIR: bulunamadi` ise `init/migrate/repair` için skill kopyasının yolunu kullan: `python ~/.claude/skills/kod-fabrikasi/scripts/kf.py ...`.

---

## 👥 Ekip ve yönlendirme

| Durum | Ajan | Yazar mı |
| --- | --- | --- |
| "X nerede, Y'yi kim çağırıyor" | `kesifci` (sonnet) | ❌ |
| Onaylanmış planın bağımsız parçası | `gelistirici` (opus) | ✅ |
| Kod değişti → test/derleme | `tester` (sonnet) | ❌ |
| Faz bitmeden / commit'ten önce inceleme | `reviewer` (opus) | ❌ |
| PROGRESS / DECISIONS / OPEN_QUESTIONS / ROADMAP / MEMORY / QA / faz raporu | `faz-arsivcisi` (sonnet) | yalnızca `.claude/*.md` |
| Yüksek risk, tasarım, kök neden, `gelistirici` başarısız | `mimar` (opus xhigh, isteğe bağlı) | ✅ |
| Auth / token / yükleme / PII dokunan değişiklik | `guvenlik-inceleyici` (opus, isteğe bağlı) | ❌ |
| Dış API / alan sorusu | `<alan>-uzmani` (sonnet, isteğe bağlı) | ❌ |

Orkestratör kuralları, brif şablonu ve "Verimli çalış" bloğu: [references/ajanlar.md](references/ajanlar.md). Küçük işler (birkaç dosya okuma, tek düzenleme) ajansız yapılır.

---

## 🏢 Dijital ajans profili

`init --profile ajans` / `profile ajans`: çekirdek ekip kalır, şu katman eklenir. Müşteriler `clients/<slug>/` altında **izole** (brifte `MÜŞTERİ: <slug>` + `DOKUNMA: clients/<diğer>/**`); kimlikler `.credentials/.env` (Claude okuyamaz, betikler okur); araçlar `python .claude/scripts/ajans/<betik>.py --client <slug> [--out dosya]`.

| Durum | Ajan | Yazar mı | Kapı |
| --- | --- | --- | --- |
| Reklam / sosyal / e-posta / blog / video metni (onaylı brif) | `metin-yazari` (sonnet) | yalnızca `clients/<slug>/campaigns|content` | → `marka-denetcisi` |
| Her metin tesliminden önce ton + yasaklı kelime + politika + iddia + sızıntı | `marka-denetcisi` (sonnet high) | ❌ | ONAY olmadan teslim YOK |
| GSC / GA4 / PageSpeed verisi, "trafik neden düştü", aylık SEO raporu | `seo-teknisyeni` (sonnet) | ❌ (betik `--out`) | — |
| Rakip hiyerarşi / schema / içerik boşluğu; YouTube transkript → NotebookLM | `rakip-analisti` (sonnet) | ❌ | — |
| Yaptığımız siteyi test et: teslim öncesi / yayın sonrası / periyodik | `site-denetcisi` (sonnet) | ❌ | "yayına hazır" yalnızca raporla |
| Cache purge, 301, DNS, SSL/WAF ayarı, trafik, saldırı | `cloudflare-operatoru` (sonnet) | dosya ❌ / API `--yes` | PLAN → kullanıcı onayı → `--yes` (`ask`) |
| Kampanya planı, bütçe, kanal, UTM, test planı (isteğe bağlı) | `reklam-stratejisti` (sonnet) | ❌ | — |
| Landing page / tema / GTM kodu | çekirdek `gelistirici` → `tester` → `site-denetcisi` | ✅ | — |

Betikler (stdlib; Google için `pip install google-auth google-api-python-client google-analytics-data`, YouTube için `youtube-transcript-api`, Windows TLS için `certifi`): `cloudflare_ops.py` (check · dns · ssl · analytics · security-events · firewall · redirect · purge · setting · dev-mode · under-attack · pages) · `site_audit.py` (teknik SEO + güvenlik başlıkları + kırık link + robots/sitemap/404; `--competitor`) · `pagespeed_check.py` (CWV lab + CrUX) · `gsc_query.py` (summary · drops · ctr-gap · pages · queries · inspect) · `ga4_query.py` (summary · channels · pages · landing · conversions) · `youtube_fetch.py` (transkript + yorum + arama/kanal).

Akışlar (kreatif, SEO raporu, site denetimi, rakip, YouTube/NotebookLM, Cloudflare): [references/ajans.md](references/ajans.md). Cloudflare token izinleri, komut matrisi, `check` yorumu, senaryolar: [references/cloudflare.md](references/cloudflare.md).

---

## 📋 Faz akışı (9 adım, özet)

```text
0. Faz seç        → ROADMAP.md'de ilk [ ] / 🟡 faz (ya da kullanıcının dediği)
1. Bağlam         → PROGRESS, DECISIONS (ilgili ADR), OPEN_QUESTIONS (bloke eden?), MEMORY,
                    QA_REPORTS, KNOWN_BUGS; gerekirse kesifci + graphify query (+ notebooklm ask)
2. Plan + ONAY    → adımlar, dosya:satır, riskler, geri alma, kabul kriterleri, ajan dağılımı.
                    ⚠️ Kullanıcı onayı olmadan koda dokunma.
3. Uygula         → gelistirici(ler): çakışmayan dosya kümeleri, aynı anda ≤ max_parallel_editors.
                    Küçük, tam tanımlı düzeltmeyi ana oturum kendisi yapabilir.
4. Test           → tester (zorunlu). Kırmızı → düzeltme turu yeni gelistirici'ye (dosya:satır ile).
5. İnceleme       → reviewer (zorunlu; donmuş diff). Yüksek risk → + guvenlik-inceleyici.
                    Bulgu koda bakılarak teyit edilir, sonra düzeltme turu.
6. Arşiv          → faz-arsivcisi: PROGRESS, ROADMAP, DECISIONS (ADR), OPEN_QUESTIONS, MEMORY,
                    QA, PHASE_NN_<konu>.md (şablon birebir).
7. Rapor          → kullanıcıya kısa: ne yapıldı, ne geçti/geçmedi (çıktıyla), test edilmeyen,
                    gereken kararlar (öneriyle), sıradaki adım. Ajanları rolüyle an.
8. Commit         → yalnızca kullanıcı isterse: "Faz N: <başlık>". post-commit → graphify + bundle + sync.
```

Ayrıntı ve hata senaryoları: [references/workflow.md](references/workflow.md).

---

## 🗂️ Proje yapısı ve config

```text
<proje>/
├── CLAUDE.md                      # "Alt ajanlar ve proje hafızası" bölümü (kf.py ekler/günceller)
├── .claude/
│   ├── kod-fabrikasi.config.json  # version:3 — proje-özel ayarlar (makineye özel değerler ve sırlar DEĞİL)
├── .env.dev                       # git dışı, Claude okuyamaz: KF_DRIVE_FOLDER, KF_NOTEBOOKLM_ID, KF_OBSIDIAN_VAULT, KF_PYTHON_BIN + ajans API anahtarları (şablon: .env.dev.example)
│   ├── settings.json              # deny: .env/pem/key · ask: push/reset/canlı komutlar · SessionStart hook
│   ├── agents/*.md                # ekip
│   ├── hooks/faz_hafiza.py        # SessionStart: PROGRESS/OPEN/ADR/git → bağlam
│   ├── scripts/kf.py              # CLI
│   ├── archives/   ROADMAP.md PROGRESS.md PHASE_TEMPLATE.md PHASE_NN_*.md NOTEBOOKLM_SUMMARY.md
│   ├── decisions/  DECISIONS.md (ADR) OPEN_QUESTIONS.md FAZ_PROMPT.md
│   ├── context/    MEMORY.md (acı dersler) GRAPHIFY_NOTES.md
│   ├── references/ QA_REPORTS.md KNOWN_BUGS.md
│   └── bundle-out/                # Drive kapalıysa paket çıktısı (gitignore)
└── .graphifyignore, .graphifyrc, .gitattributes
```

Config'i her zaman önce oku: `test_commands`, `live_write_commands` (ajanlar çalıştırmaz), `high_risk_areas`, `agents`, `phase_files`, `integrations.{graphify,drive,notebooklm,obsidian}.enabled`. Drive klasörü, NotebookLM id, Obsidian kasası ve API anahtarları **`.env.dev`'dedir** (git dışı; `kf.py` okur ve config'in üstüne yazar; sen okuyamazsın, değerini kullanıcıya sor ya da `kf.py check` ile "etkin/kapalı" durumuna bak). Şema: [assets/kod-fabrikasi.config.example.json](assets/kod-fabrikasi.config.example.json). Belge rolleri: [references/hafiza.md](references/hafiza.md).

---

## 🧰 `kf.py` komutları

| Komut | Ne yapar |
| --- | --- |
| `check` / `status` | Kurulum durumu / faz hafızası çıktısı |
| `init --department yazilim[,ajans,muhasebe,depo] --framework X --test-cmd ... --live-cmd ... --risk ... [--agents mimar,guvenlik-inceleyici] [--expert ad:Alan:yol] [--drive P] [--notebook ID] [--obsidian P] [--client slug:Ad:domain --agency-agents reklam-stratejisti]` | Etkileşimsiz kurulum (skill kopyasından); `ajans` departmanı ajans profilini açar, planlanan departmanlar config'e yazılır |
| `repair` / `migrate [--dry-run] [--remove-legacy]` | Eksikleri tamamla / v1-v2 → v3 |
| `profile ajans|yazilim [--client ...]` · `client list|add --slug --name --domain [--zone] [--gsc] [--ga4] [--url]|remove --slug` | Mevcut projeye ajans katmanı / müşteri yönetimi (klasör + config + CLAUDE.md) |
| `plugins` · `plugins --install [--only a,b] [--scope user|project]` · `plugins --apply` · `plugins --remove` | Önerilen Anthropic plugin'leri (profil + framework'e göre) listele; seçilenleri `claude plugin install` ile kur ve ajan dosyalarına "Güçlendirmeler" bloğu + `Skill` aracı olarak işle / geri al |
| `hooks` | pre-commit (gizli bilgi taraması) + post-commit (end-phase). `graphify hook install` KULLANMA. |
| `secret-scan [--staged]` · `graphify` · `bundle [--dry-run]` · `sync` · `end-phase` | Tekil adımlar |
| `selftest` | PASS/FAIL/WARN; FAIL varsa exit 1. Kurulum "bitti" demeden önce yeşil olmalı. |

---

## 🚫 ASLA YAPMA (özet; ayrıntı [references/tuzaklar.md](references/tuzaklar.md))

1. Onaysız kod değişikliği (Adım 2 atlanmaz). Kullanıcı "onaysız devam et" dese bile: "plan üzerinde ne değiştirelim?" diye sor.
2. Kodu yazan ajana kendi işini doğrulatma; aynı ajana ikinci görev verme; başarısız brifi aynı ajana tekrar gönderme (bir kademe yükselt).
3. Planlama belgelerini `faz-arsivcisi` dışında güncelleme; "Bitti" yazmak için kanıt istemeden geçme.
4. Commit, push, deploy, canlıya yazan komut: yalnızca kullanıcı isterse. `git stash/checkout --/reset` ajanlarda yasak.
5. `.env` ve gizli dosya okuma; sırrı koda/teste/dokümana/Drive'a yazma. Paket yalnızca `git ls-files`'tan oluşur, bunu değiştirme.
6. NotebookLM kaynaklarını başlığa göre dict'leme; boş klasörde NotebookLM'i temizleme (güvenlik freni); `copytree(dirs_exist_ok=True)`; büyük HTML/JSON yükleme; başlıkları `__` ile düzleştirmeden yükleme.
7. `python` PATH varsayma: hook'lar `python_bin` tam yolunu kullanır.
8. `init.sh` gibi etkileşimli (`read`) betik: Claude'un Bash'i etkileşimsizdir; her bilgi parametreyle gelir.
9. İki post-commit sahibi (`graphify hook install` + kf.py): tek sahip kf.py.
10. Kök dizine yönetim `.md` dosyası ya da betik bırakma; `CLAUDE.md` 200 satırı aşırsa `.claude/rules/` kullan.
11. Ana oturumun `model`/`effortLevel` ayarını projeye yazma (kullanıcının varsayılanı değişir); yalnızca ajan dosyalarında model belirt.
12. Ajan raporunu doğrulamadan kullanıcıya aktarma; "Agent type not found" görünce ajanı yeniden yaratma (hot reload birkaç saniye; olmazsa yeni oturum).
13. (Ajans) Brifte müşteri slug'ı olmadan ajan çalıştırma; iki müşteriyi tek brife koyma; `marka-denetcisi` ONAY'ı olmadan metin teslim etme; `site-denetcisi` raporu olmadan "yayına hazır" deme.
14. (Ajans) `cloudflare_ops.py` yazma komutunu PLAN göstermeden `--yes` ile çalıştırma; `purge-all` ve `dns delete`'i kullanıcı açıkça istemeden önerme; `.credentials/` okuma, token'ı çıktıya/dokümana yazma; müşteri verisini proje NotebookLM'ine yükleme (müşteri başına notebook).

---

## 📚 Derin referanslar (konuya göre oku, başta hepsini değil)

| Dosya | Ne zaman |
| --- | --- |
| [references/workflow.md](references/workflow.md) | Faz başlatırken, plan sunarken, hata senaryolarında |
| [references/ajanlar.md](references/ajanlar.md) | Brif yazarken, ajan seçerken, paralellik ve kademe kararlarında |
| [references/hafiza.md](references/hafiza.md) | PROGRESS/ADR/OPEN/MEMORY rollerini ayırırken, hook davranışında |
| [references/kurulum-rehberi.md](references/kurulum-rehberi.md) | Yeni kurulum, soru seti, `init` parametreleri, migrate |
| [references/faz-raporu-sablonu.md](references/faz-raporu-sablonu.md) | `faz-arsivcisi`'ne faz raporu brifi verirken |
| [references/notebooklm-graphify.md](references/notebooklm-graphify.md) | `graphify query`, `notebooklm ask`, etki analizi |
| [references/tuzaklar.md](references/tuzaklar.md) | `kf.py`'ye dokunurken, "iyileştireyim" derken |
| [references/ajans.md](references/ajans.md) | Ajans profili: kreatif / SEO / site denetimi / rakip / YouTube akışları, brif şablonu, müşteri klasörü |
| [references/cloudflare.md](references/cloudflare.md) | Cloudflare token izinleri, komut matrisi (ask/deny), `check` yorumu, senaryolar, hata kodları |
| [references/plugins.md](references/plugins.md) | Plugin kataloğu (hangi ajan hangi skill'i ne zaman), kurulum sorusu, `--apply` mekanizması, token/çakışma uyarıları |
| [references/yol-haritasi.md](references/yol-haritasi.md) | Skill'in gelecek planı: finans katmanı (3.2), `finans` profili (3.3), plugin ölçümü, diğer fikirler |

---

## 🗣️ Sürüm ve güncelleme

GitHub: https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi — **v3.1** (ajan ekibi + faz hafızası + `kf.py` + dijital ajans profili). Sürüm geçmişi ve v2 → v3 geçişi: [CHANGELOG.md](CHANGELOG.md).

```bash
git clone https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi.git ~/.claude/skills/kod-fabrikasi   # kurulum
cd ~/.claude/skills/kod-fabrikasi && git pull                                                                     # güncelleme
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py repair   # projedeki kf.py / hook kopyasını yeniler
```
