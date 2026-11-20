---
name: kod-fabrikasi
description: AI destekli yazılım fabrikası (v3) — ana oturum orkestratör, alt ajan ekibi (kesifci, gelistirici, tester, reviewer, faz-arsivcisi + isteğe bağlı mimar, guvenlik-inceleyici, alan uzmanları), oturumlar arası faz hafızası (PROGRESS/DECISIONS/OPEN_QUESTIONS + SessionStart hook), graphify kod haritası, izin kuralları ve isteğe bağlı Drive/NotebookLM/Obsidian senkronu. KULLANICI faz başlatmak/bitirmek, "sıradaki faz", "nerede kalmıştık", alt ajan kurulumu, kod fabrikası kurulumu/migrasyonu, bundle, NotebookLM senkronu, graphify, git hook, roadmap/ADR/faz raporu güncelleme istediğinde MUTLAKA bu skill'i kullan. "FAZ_PROMPT", "faz raporu", "ADR", "açık soru", "kod fabrikası kur", "v2'den v3'e geçir", "selftest" gibi ifadelerde — açıkça "skill" demese bile — devreye gir.
allowed-tools: Read, Glob, Grep, Bash, Edit, Write, Agent, AskUserQuestion
---

# Kod Fabrikası (v3)

**Ne:** Ana Claude Code oturumu **orkestratördür**; işi böler, `.claude/agents/` altındaki uzman ajanlara brif verir, sonuçları birleştirir, kullanıcıya raporlar. Kodu yazan ajan kendi işini onaylamaz. Proje hafızası `.claude/` altındaki planlama belgelerinde durur ve her oturuma `SessionStart` hook'u ile yüklenir. Kod haritası graphify; Drive/NotebookLM/Obsidian isteğe bağlı.

**Akış:** bağlam → plan → **ONAY** → `gelistirici` (paralel, ≤3) → `tester` → `reviewer` → `faz-arsivcisi` → commit (yalnızca kullanıcı isterse).

Tek komut arayüzü: `python .claude/scripts/kf.py <komut>` (Windows/macOS/Linux; `make` ve bash gerekmez).

---

## ⚙️ İlk kontrol (skill her devreye girdiğinde)

```bash
python .claude/scripts/kf.py check 2>/dev/null || python ~/.claude/skills/kod-fabrikasi/scripts/kf.py check
```

| `YAPI` çıktısı | Ne yap |
| --- | --- |
| `v3` | Hazır. Kullanıcının isteğine göre faz akışına geç. `SESSION HK: yok` ise `repair`. |
| `v2` / `v1` / `v1-config-yok` | Kullanıcıya sor: "v3'e geçireyim mi? (dosyalar `git mv` ile taşınır, eski `bundle.py`/`Makefile` kaldırılır, ajanlar ve hook eklenir)". Onayla: `kf.py migrate --dry-run` göster → `kf.py migrate --remove-legacy` → `kf.py hooks` → `kf.py selftest`. |
| `yok` | Kurulu değil. Kullanıcıya sor: "Bu projeye Kod Fabrikası kurayım mı?" Onaylarsa [references/kurulum-rehberi.md](references/kurulum-rehberi.md): tek toplu `AskUserQuestion`, sonra `kf.py init ...` (etkileşimsiz). |

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
│   ├── kod-fabrikasi.config.json  # version:3 — TÜM proje-özel değerler
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

Config'i her zaman önce oku: `test_commands`, `live_write_commands` (ajanlar çalıştırmaz), `high_risk_areas`, `agents`, `phase_files`, `integrations.{graphify,drive,notebooklm,obsidian}.enabled`. Şema: [assets/kod-fabrikasi.config.example.json](assets/kod-fabrikasi.config.example.json). Belge rolleri: [references/hafiza.md](references/hafiza.md).

---

## 🧰 `kf.py` komutları

| Komut | Ne yapar |
| --- | --- |
| `check` / `status` | Kurulum durumu / faz hafızası çıktısı |
| `init --framework X --test-cmd ... --live-cmd ... --risk ... [--agents mimar,guvenlik-inceleyici] [--expert ad:Alan:yol] [--drive P] [--notebook ID] [--obsidian P]` | Etkileşimsiz kurulum (skill kopyasından) |
| `repair` / `migrate [--dry-run] [--remove-legacy]` | Eksikleri tamamla / v1-v2 → v3 |
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

---

## 🗣️ Sürüm ve güncelleme

GitHub: https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi — **v3.0** (ajan ekibi + faz hafızası + `kf.py`). Sürüm geçmişi ve v2 → v3 geçişi: [CHANGELOG.md](CHANGELOG.md).

```bash
git clone https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi.git ~/.claude/skills/kod-fabrikasi   # kurulum
cd ~/.claude/skills/kod-fabrikasi && git pull                                                                     # güncelleme
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py repair   # projedeki kf.py / hook kopyasını yeniler
```
