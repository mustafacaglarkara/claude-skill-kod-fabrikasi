# Plugin Güçlendirmeleri — Anthropic plugin'lerini ajanlara bağlama

Kod Fabrikası plugin'siz tam çalışır. Kurulu Anthropic plugin'leri varsa `kf.py plugins --apply` ilgili ajan dosyalarına işaretli bir **"Güçlendirmeler"** bloğu yazar ve ajana `Skill` aracını verir; ajan brif gerektirdiğinde `/plugin:skill` çağırır, yoksa normal devam eder. Blok kaldırılınca (`--remove`) ajan varsayılan hâline döner. Çekirdek dosyalar değişmez.

## Nasıl çalışır (doğrulanmış)

- Alt ajan (`.claude/agents/*.md`) `tools:` listesinde `Skill` varsa proje, kullanıcı ve plugin skill'lerini `/<plugin>:<skill>` adıyla çağırabilir. `skills:` frontmatter'ı ise skill'i her çalıştırmada **ön yükler** (token maliyeti); biz çağrı üzerine yükleme kullanırız. (Kaynak: code.claude.com/docs/en/sub-agents, skills.)
- Ajan başlatan skill'ler (`pr-review-toolkit`, `claude-security`, `feature-dev`, `searchfit-seo:competitor-analyzer`) alt ajandan çağrılmaz ("Başka ajan başlatma" kuralı); bunlar `FAZ_PROMPT.md`'ye **ana oturum** bloğu olarak yazılır.
- Ortam plugin'leri (LSP, `security-guidance` hook'ları) skill çağrısı gerektirmez; kurulu olması yeter.
- Tespit: `claude plugin list --json` (resmi marketplace `name@claude-plugins-official`, claude.ai senkronu `name@synced`); yoksa `~/.claude/plugins/installed_plugins.json` + `synced/`. Senkron plugin'ler claude.ai hesabına bağlıdır; makineye kurulmaz, başka makinede görünmeyebilir. Proje `settings.json` `enabledPlugins` ile "öneri" yazılabilir ama kurulumu yapmaz; takım arkadaşı `claude plugin install ... --scope project` çalıştırır.

## Katalog (`kf.py plugins` çıktısıyla aynı; profil ve framework'e göre süzülür)

| Plugin | Kaynak | Profil | Hedef | Ne zaman |
| --- | --- | --- | --- | --- |
| `typescript-lsp` `pyright-lsp` `gopls-lsp` `php-lsp` `rust-analyzer-lsp` `csharp-lsp` | resmi | her ikisi (framework'e göre tek) | ortam | kesifci/gelistirici/tester'ın arama yerine tanım/referans kullanması |
| `security-guidance` | resmi | her ikisi | ortam (hook) | her düzenlemede kalıp uyarısı, Stop'ta diff incelemesi |
| `pr-review-toolkit` | resmi | her ikisi | ana oturum | Adım 5: `reviewer` ile paralel ikinci göz |
| `claude-security` | resmi | her ikisi | ana oturum | yüksek riskli fazda `guvenlik-inceleyici`'den önce derin tarama |
| `feature-dev` | resmi | her ikisi | ana oturum | büyük özellikte Adım 1-2 alternatifi; plan yine ONAY'a gelir |
| `frontend-design` | resmi | her ikisi | `gelistirici` | UI / landing page kodundan önce |
| `claude-md-management` | resmi | her ikisi | ana oturum | CLAUDE.md 200 satırı aşınca (işaretli bölüme dokunmaz) |
| `engineering` | claude.ai (Anthropic) | her ikisi | `mimar`, `tester`, ana oturum | architecture / system-design / debug · testing-strategy · deploy-checklist |
| `coding-skills` | claude.ai dizini | her ikisi | `gelistirici`, `reviewer` | eşzamanlılık, idempotency, zaman dilimi dokunan iş |
| `backend-design` | claude.ai dizini | her ikisi | `mimar` | API / servis / veri modeli |
| `searchfit-seo` | claude.ai (Anthropic kataloğu; geliştirici SearchFit) | ajans | `seo-teknisyeni`, `site-denetcisi`, `rakip-analisti`, `metin-yazari`, ana oturum | technical-seo, on-page, schema, internal-linking, keyword-clustering · seo-audit, broken-links · content-strategy/brief, ai-visibility · competitor-analyzer ajanı |
| `marketing` | claude.ai (Anthropic) | ajans | `metin-yazari`, `marka-denetcisi`, `reklam-stratejisti`, `seo-teknisyeni` | content-creation, draft-content, email-sequence · brand-review · campaign-plan, competitive-brief, performance-report |
| `cloudflare` | claude.ai dizini (Cloudflare) | ajans | `cloudflare-operatoru`, `gelistirici` | cloudflare, web-perf, wrangler · frameworks-on-cloudflare, workers-best-practices. **MCP sunucusu yazma yapabilir** → settings `ask` eklenir; yazma yalnızca `cloudflare_ops.py --yes` |
| `website-design` | claude.ai dizini (UXKIN) | ajans | `gelistirici` | landing page tasarım yönü / DESIGN.md |

Yerleşik (`/code-review`, `/security-review`, `/simplify`) her kurulumda vardır, katalogda yer almaz; ana oturum Adım 5'te `reviewer`'a ek olarak kullanabilir.

## Kurulum akışı (Claude kurulumda sorar)

1. `kf.py plugins` → öneri tablosu (profil + framework'e göre). Kullanıcıya tek soru (`AskUserQuestion`, çoklu seçim): "Şu plugin'ler kurulsun mu? (hiçbiri = varsayılan ajanlarla devam)". Her seçenekte hangi ajana ne kattığı yazılır.
2. Kabul → `kf.py plugins --install --only <seçilenler> [--scope user|project|local]`: betik `claude plugin install <id>@claude-plugins-official` (resmi) ya da `<id>@anthropic-plugin-directory` (claude.ai Dizini; Claude Code'da yerleşik marketplace) komutunu `-y --json` ile etkileşimsiz çalıştırır; resmi marketplace kayıtlı değilse ekler; kurulamayanı raporlar ve claude.ai → Ayarlar → Plugin'ler yolunu söyler; sonunda kurulu olan tüm ilgili plugin'leri `--apply` ile işler.
3. `--apply` → ajan blokları + `Skill` aracı + `FAZ_PROMPT.md` ana oturum bloğu + (cloudflare) settings ask. `kf.py selftest` uygulanan plugin'in hâlâ kurulu olduğunu kontrol eder (WARN).
4. Yeni oturum ya da birkaç saniye bekleme (ajan dosyaları yeniden yüklenir). Ret → bir daha sorulmaz; `kf.py plugins` her zaman elle çalıştırılabilir.

## Etkili olur mu? (değerlendirme)

**Evet, seçici kullanılırsa.** Kazanç en çok şu üçünde: `searchfit-seo` (ajan şablonumuzda olmayan ayrıntılı SEO kontrol listeleri ve şema üretimi), `engineering:testing-strategy` / `debug` (tester ve mimar için yöntem), `pr-review-toolkit` (reviewer'ın kaçırabileceği sessiz hata/test kalitesi için bağımsız ikinci göz). LSP plugin'leri arama maliyetini düşürdüğü için her projede önerilir.

Dikkat edilecekler (tasarım bunlara göre):
- **Token**: skill çağrısı o ajanın transkriptine binlerce token ekler; bu yüzden ön yükleme değil, "brif gerektirdiğinde" çağrı. Rapor formatı ve kelime sınırı değişmez.
- **Çakışan talimat**: plugin skill'i "şu dosyayı yaz" diyebilir; blok metni açıkça "bu dosyadaki kurallar üstündür" der. Salt okunur ajan salt okunur kalır; selftest denetler.
- **Çift tarama**: `searchfit-seo:seo-audit` ile `site_audit.py` aynı siteyi tarar; blok "ek kontrol listesi olarak, tekrar tarama" der. Kota (PageSpeed) için de aynı kural.
- **Taşınabilirlik**: plugin yoksa blok zararsızdır (skill bulunamazsa ajan devam eder); yine de `--remove` ile temiz hâle dönülebilir. Senkron plugin'ler hesaba bağlı; takım kullanımında resmi marketplace olanları tercih edin.
- **MCP yazma riski**: `cloudflare` ve `marketing` (ahrefs, hubspot vb.) MCP sunucuları dış sisteme yazabilir; Cloudflare için `ask` kuralı eklenir, diğerleri bağlantı yetkisi gerektirdiği için varsayılan kapalıdır. Yazma kapısı değişmez: Cloudflare'de yalnızca `cloudflare_ops.py --yes`.
- **Sürüm**: plugin güncellemesi ajan davranışını sessizce değiştirebilir; `QA_REPORTS`'a "plugin'li/plugin'siz" karşılaştırma notu düşülür (yol haritası).
- **Üçüncü taraf**: `searchfit-seo`, `website-design`, `cloudflare`, `coding-skills`, `backend-design` Anthropic kataloğunda yayımlanır ama başka geliştiricilerindir; `claude plugin details <ad>` ile içeriğe ve token maliyetine bakın.
