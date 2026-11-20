# Kurulum Rehberi (v3) — Claude kurar, betik etkileşimsizdir

Kurulumu **Claude Code yürütür**: önce projeyi ucuza keşfeder, sonra kullanıcıya **tek toplu soru** sorar, cevaplarla `kf.py init` çalıştırır, `hooks` ve `selftest` ile doğrular. Betik hiçbir soru sormaz (Claude'un Bash'i etkileşimsizdir; `read` takılır).

## 0. Ön koşullar

| Araç | Gerekli | Kontrol / kurulum |
| --- | --- | --- |
| git | Evet | `git --version` · Windows: `winget install Git.Git` |
| Python 3.10+ | Evet | `python --version` (hook'lar için sistem Python'u yeter) |
| graphify (`graphifyy` paketi, çift y) | Önerilir | `uv tool install "graphifyy[sql]" --python 3.13` · `graphify --version`. Python 3.15'te uv ayrı 3.13 indirir; "minor version link" hatasında `uv python list --only-installed` ile tam yol ver. |
| notebooklm-py | Yalnızca NotebookLM etkinse | `python -m pip install "notebooklm-py[browser]"` · `playwright install chromium` · `notebooklm login`. **Hangi Python'a kurulduysa** config `python_bin` o olmalı. |
| Google Drive masaüstü | Yalnızca Drive etkinse | Klasör yolu erişilebilir mi (`G:\...`) |
| Obsidian | Yalnızca Obsidian etkinse | Kasa klasöründe `.obsidian/` var mı |

Skill kopyası: `git clone https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi.git ~/.claude/skills/kod-fabrikasi`.

## 1. Keşif (değişiklik yapmadan, ucuz)

`kf.py check` sonra:
- Manifestler (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pubspec.yaml`, `composer.json`, Dockerfile): framework ve sürüm.
- Çalışan komutlar: test, lint, build. **Testler veritabanını silebilir**: test ayarını oku, ayrı test DB var mı; emin değilsen çalıştırma, sor.
- Mevcut AI ayarları: `CLAUDE.md`, `.claude/settings*.json`, `.claude/agents`, hook'lar → **birleştirilir**, üzerine yazılmaz.
- Gizli/ticari dosyalar: `.env*`, `*.pem`, `*.key`, `*bilgi*.txt`, `*password*`, `*.db`, SQL dökümleri, müşteri verisi. İçeriğini yazdırma; `.gitignore`'da mı kontrol et (`git check-ignore -v`).
- Mevcut planlama belgeleri (ROADMAP, PROGRESS vb.): varsa korunur, `migrate` taşır.
- Canlıya / dış sisteme yazan komutlar (deploy, migrate reset, toplu silme, eBay/ödeme gönderimi).

## 2. Tek toplu soru (`AskUserQuestion`, öneri önce)

Kodun söyleyemediği şeyler; çok seçimli olabilir. **İlk soru her zaman departman sorusudur** (onay ve kurulumdan önce):

0. **Bu kurulumu hangi departmanlar için yapıyorsunuz?** (çoklu seçim) → `--department` (tekrarlanabilir)
   - `yazilim` — Yazılım geliştirme: çekirdek ekip, her kurulumda var (seçilmese de eklenir)
   - `ajans` — Dijital ajans: müşteri izolasyonu, reklam metni + marka denetimi, SEO/GA4, site denetimi, Cloudflare (hazır; `profile: ajans` olur)
   - `muhasebe` — Muhasebe / finans: fatura, tahsilat, nakit akışı, bütçe (**planlandı**, 3.2; seçim config'e yazılır, katman çıkınca `kf.py repair` ekler)
   - `depo` — Depo / stok yönetimi: stok, sipariş, sayım, ERP okuma (**planlandı**, 3.4; aynı şekilde)
   Seçime göre sonraki sorular daralır: `ajans` seçildiyse müşteri sorusu (soru 4 eki) sorulur; yalnızca `yazilim` ise sorulmaz. Planlanan departman seçildiyse kullanıcıya "şimdilik kayıt; katman gelince eklenecek" denir, kurulum durmaz.

1. **Test ve derleme komutları** doğru mu? (keşiften önerilenler) → `--test-cmd`, `--build-cmd`
2. **Canlıya yazan / onay isteyen komutlar** (keşiften adaylar + "yok") → `--live-cmd` (settings `ask` listesine girer, ajanlar çalıştırmaz)
3. **Yüksek riskli alanlar** (çoklu: auth/oturum, ödeme, kişisel veri, veritabanı/migration, altyapı/deploy, projeye özel) → `--risk`
4. **Ekip ve entegrasyonlar** (çoklu): `mimar`, `guvenlik-inceleyici`, alan uzmanı (ad + alan + klasör), Drive klasörü, NotebookLM notebook id, Obsidian kasa yolu → `--agents`, `--expert`, `--drive`, `--notebook`, `--obsidian`

Proje bir **dijital ajans çalışma alanıysa** (müşteri markaları, reklam metni, SEO raporu, site denetimi, Cloudflare yönetimi; keşifte `clients/`, `brand-guide`, GSC/GA4 izleri ya da kullanıcı ifadesi) soru 4'e ekle: "Ajans profili kurulsun mu? İlk müşteri(ler): slug, ad, domain [Cloudflare zone, GSC mülkü, GA4 property]; `reklam-stratejisti` isteniyor mu?" → `--profile ajans --client "slug:Ad:domain[:zone[:gsc[:ga4]]]" [--agency-agents reklam-stratejisti]`. Ajans için ek ön koşullar: `pip install certifi` (Windows TLS kökleri), Google verisi için `google-auth google-api-python-client google-analytics-data`, YouTube için `youtube-transcript-api`; kimlikler kurulumdan sonra `.credentials/env.example` → `.env` (insan doldurur; Claude okuyamaz). Ayrıntı: [ajans.md](ajans.md), [cloudflare.md](cloudflare.md).

5. **Plugin güçlendirmeleri** (init'ten SONRA; `kf.py plugins` çıktısındaki "yok" satırlarını tek `AskUserQuestion`, çoklu seçim, "hiçbiri" seçeneğiyle sor): "Bu ajanları güçlendiren Anthropic plugin'leri kurulsun mu?" Her seçenek: plugin adı + hangi ajana ne kattığı (tablodaki `why`). Kullanıcı seçerse **`kf.py plugins --install --only <seçilenler>`** çalıştır: betik `claude plugin install <id>@claude-plugins-official` ya da `<id>@anthropic-plugin-directory` ile kurar (`-y --json`, etkileşimsiz; resmi marketplace kayıtlı değilse ekler), kurulamayan için claude.ai → Ayarlar → Plugin'ler yolunu basar, ardından kurulu olan tüm ilgili plugin'leri `--apply` ile ajanlara işler. Zaten kurulu ama uygulanmamış olanlar seçim olmadan da `--apply` ile işlenir. Seçmezse varsayılan ajanlarla devam, bir daha sorma. Kapsam varsayılan `user` (takım projesinde `--scope project`). Ayrıntı: [plugins.md](plugins.md).

Dil (`--language tr|en`) ve commit kuralı ("commit/push yalnızca istenirse") varsayılan; kullanıcı aksini söylemediyse sorma. Ana oturum model/effort ayarı **sorulmaz, yazılmaz**.

## 3. Kurulum

```bash
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py init \
  --department yazilim --department ajans [--department muhasebe --department depo] \
  --framework node --test-cmd "npm test" --test-cmd "npm run lint" --build-cmd "npm run build" \
  --live-cmd "npm run deploy" --risk auth --risk payments \
  --agents mimar,guvenlik-inceleyici \
  --expert "odeme-uzmani:Ödeme sağlayıcı API:src/payments/:https://docs.ornek.test" \
  [--drive "G:\Drive'ım\DEV_PROJELERI\proje"] [--notebook <uuid>] [--obsidian "D:\obsidian_kasalar\proje"] \
  [--python "C:\...\python.exe"] [--graphify graphify] [--no-graphify]
```

`init` ne yapar: `.claude/{context,decisions,archives,references,agents,hooks,scripts}`; config (`version: 3`); eksik planlama belgeleri şablondan (`{{PROJECT_NAME}}`, tarih, komutlar doldurulur); ajan dosyaları (core + seçilen isteğe bağlı + alan uzmanları); `kf.py` ve `faz_hafiza.py` kopyası; `settings.json` **birleştirme** (deny `.env`/pem/key, ask push/reset/canlı komutlar, SessionStart hook); `.gitignore`, `.gitattributes` (LF), `.graphifyignore`, `.graphifyrc`; `CLAUDE.md`'ye işaretli "Alt ajanlar ve proje hafızası" bölümü (varsa güncellenir). Config varsa `init` durur (exit 2): `repair`, `migrate` ya da `--force`.

`--drive`, `--notebook`, `--obsidian` değerleri config'e değil **`.env.dev`**'e yazılır (`KF_DRIVE_FOLDER`, `KF_NOTEBOOKLM_ID`, `KF_OBSIDIAN_VAULT`); config'te yalnızca `enabled` niyeti kalır. `init` her zaman `.env.dev.example` (izlenir) ve yoksa `.env.dev` (git dışı, deny) oluşturur; kullanıcı sonradan değer eklerse `kf.py check` "etkin (.env.dev)" gösterir. Eski projede config'teki değerleri `kf.py repair` bir kez `.env.dev`'e taşır.

`--profile ajans` ek olarak: ajans ajanları (`assets/agents/ajans/`), `.claude/scripts/ajans/*.py`, `clients/<slug>/` (README, brand-guide, personas + alt klasörler), `shared/` (copywriting-frameworks, ad-policies), `.credentials/` (README + env.example; `.gitignore`'da), settings deny `.credentials/**` + `dns delete`, ask Cloudflare yazma + `wrangler deploy`, CLAUDE.md'ye ajans tablosu. Sonradan: `kf.py profile ajans`, `kf.py client add ...`.

Sonra:
```bash
git init -b main                              # repo değilse; Drive/Obsidian sürüm kontrolü değildir
python .claude/scripts/kf.py hooks            # pre-commit gizli bilgi taraması + post-commit end-phase
python .claude/scripts/kf.py selftest         # FAIL yoksa kurulum bitti
graphify update .                             # ilk harita (graphify etkinse)
python .claude/scripts/kf.py bundle --dry-run # ne paketlenecek (Drive/NotebookLM etkinse gerçek çalıştır)
```

İsteğe bağlı: `graphify install --project` (`/graphify` skill'i + PreToolUse hatırlatma hook'u ekler; `settings.json.graphify-bak` yedeğini kontrol edip sil). **`graphify hook install` KULLANMA**: post-commit'in tek sahibi `kf.py`'dir ve `end-phase` içinde `graphify update` zaten çalışır.

## 4. İlk commit öncesi gizli bilgi denetimi

`kf.py secret-scan` (izlenen tüm dosyalar) → temiz olmalı. Eşleşme çıkarsa dosyayı `.gitignore`'a al ya da değeri `.env`'e taşı; gerçek sır izlenen dosyadaysa commit etme, kullanıcıya söyle. Pre-commit aynı taramayı staged dosyalarda yapar; bilinçli atlama `KF_SKIP_SECRET=1` (önerilmez).

Commit ve remote/push: yalnızca kullanıcı isterse.

## 5. Teslim

Kullanıcıya söyle: ne kuruldu (ajan listesi rolüyle), `selftest` sonucu, `settings.json`'da nelerin değiştiği (deny/ask kuralları, hook; `ask` kuralı "her zaman izin ver" seçilse bile sorar), ajanların birkaç saniyede yüklendiği ("not found" görürse yeni oturum), git hook'larının kurulduğu, hiçbir şeyin commit edilmediği. İlk işi öner: Faz 0 keşif → PROGRESS/ROADMAP doldurma → ilk ADR.

## v1 / v2 → v3 geçişi

```bash
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py migrate --dry-run     # ne taşınacak
python ~/.claude/skills/kod-fabrikasi/scripts/kf.py migrate --remove-legacy
python .claude/scripts/kf.py hooks && python .claude/scripts/kf.py selftest
```

Taşınanlar (`git mv`): kök ya da `.claude/` altındaki ROADMAP/MEMORY/QA/KNOWN_BUGS/NOTEBOOKLM_SUMMARY/GRAPHIFY_NOTES/FAZ_PROMPT → v3 konumları; `reports/fazNN_x.md` → `.claude/archives/PHASE_NN_x.md`. Eski config yedeklenir (`.v2.bak`), v3 şemaya çevrilir (Drive/NotebookLM değerleri `integrations` altına; `framework`'ten `test_commands`). Kökteki Kod Fabrikası imzalı `bundle.py`/`Makefile`/`setup-hooks.sh` `--remove-legacy` ile kaldırılır. Eski post-commit kök `bundle.py`'yi çağırır: `kf.py hooks` yeniden yazar (varsa yabancı hook `.pre-kf.bak` olarak yedeklenir). Drive düzeni değişir (`kod/`, `belgeler/`, `claude__archives/`): eski kök dosyalar ilk `bundle`'da `stale_patterns` ile temizlenir; NotebookLM birebir aynalandığı için eski kaynaklar id bazında silinir.

## Kontrol listesi

- [ ] Keşif yapıldı; test DB ayrımı ve gizli dosyalar anlaşıldı
- [ ] Departman sorusu ilk soruldu (`--department`); planlananlar kullanıcıya "kayıt, katman bekliyor" diye söylendi
- [ ] Tek toplu soru soruldu, cevaplar `init` parametrelerine döküldü
- [ ] `kf.py init` çalıştı; `settings.json` birleştirildi (kullanıcının kuralları korundu)
- [ ] `kf.py hooks` kuruldu; `graphify hook install` kullanılmadı
- [ ] `kf.py selftest` FAIL vermiyor
- [ ] `kf.py plugins` soruldu; seçilenler kuruldu ve `plugins --apply` çalıştı (ya da "hiçbiri")
- [ ] `kf.py secret-scan` temiz; `.env`, db, döküm `git check-ignore` ile ignore'da
- [ ] Kullanıcıya teslim raporu verildi; commit atılmadı
