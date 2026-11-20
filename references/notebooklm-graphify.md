# Graphify ve NotebookLM'i Etkili Kullanma

| Parça | Ne yapar | Yazar mı | Zorunlu mu |
| --- | --- | --- | --- |
| **Graphify** | **Yapı**: AST tabanlı harita; "X, Y'yi çağırıyor". Yerelde tree-sitter, LLM ve ağ yok. | `graphify-out/` | Önerilir (`integrations.graphify`) |
| **NotebookLM** | **Anlam**: projeyi okumuş danışman; soru sorarsın, cevap verir. | ❌ Asla | İsteğe bağlı (`integrations.notebooklm`) |
| **kf.py bundle** | git'in izlediği kod + belgeleri paketler, Drive'a (ya da `.claude/bundle-out/`) yazar, NotebookLM'i birebir aynalar | Drive / bundle-out | — |
| **Ajanlar / ana oturum** | Asıl işi yapar | ✅ | — |

Kullanıcı işi **sana** söyler; NotebookLM iş yapmaz.

## Graphify

```bash
graphify update .                       # harita (saniyeler); post-commit end-phase bunu zaten çağırır
graphify query "fiyat nasıl hesaplanıyor?"
graphify explain "OrderService"
graphify path "Checkout" "PaymentGateway"
graphify export callflow-html           # çağrı zincirleri
graphify install --project              # /graphify skill'i + PreToolUse hatırlatma (isteğe bağlı)
```

Çıktılar: `graph.html` (etkileşimli; "buraya dokunsam nereler kırılır"), `GRAPH_REPORT.md` (metin özeti; paketle NotebookLM'e gider), `graph.json`. `.graphifyignore` taramayı daraltır (veri, görsel, lock, eski migrasyon); `.graphifyrc` `viz_node_limit`, `query_budget`.

**Ajanlar için kural:** "Verimli çalış" bloğu `graphify query/explain`'i repo geneli `Grep`'ten önce koyar. Harita yoksa (`graphify-out/` yok) doğrudan `Grep`.

Ne zaman: refactor öncesi etki analizi, coupling sıcak noktaları, ölü kod, onboarding. Yorumlar `.claude/context/GRAPHIFY_NOTES.md`'ye (faz-arsivcisi).

`graphify hook install` KULLANMA (post-commit çakışması, tuzaklar #13). `graphify claude uninstall` PreToolUse hatırlatmasını kaldırır.

## NotebookLM (etkinse)

```bash
notebooklm source list --notebook <ID>                  # kaynaklar; başlıklar BENZERSİZ olmalı
notebooklm ask "ROADMAP'e göre sıradaki faz hangi dosyalara dokunur?"
notebooklm ask "Auth akışı nasıl?" -s <kaynak_id_kod> -s <kaynak_id_roadmap>   # hedefli
notebooklm ask "Refactor önerin?" --save-as-note
notebooklm generate audio "Faz durumu özeti" | mind-map | report --format briefing-doc
```

Web: her senkron sonrası **"Yenile (Refresh)"**; yoksa eski koda göre cevap verir.

Paket düzeni (`kf.py bundle`): `kod/tum_kodlar.txt` (izlenen kaynak dosyaların birleşimi, klasör listesiyle), `belgeler/<yol__ad>.md` (planlama belgeleri, README, CLAUDE.md, docs/*.md, GRAPH_REPORT.md), `claude__archives/` (faz raporları), `graphify-out/` yalnızca `.md`. NotebookLM'e yalnızca `.md/.txt/.pdf` ve 50 MB altı gider; başlık = düzleştirilmiş yol.

Tipik sorular: "sıradaki faz ne" · "Faz 4F için adım adım plan ve dokunulacak dosyalar" · "/urunler akışı hangi controller'lardan geçer" · "QA_REPORTS'taki çözülmemiş sorunlar".

Sınır: NotebookLM son commit'ten geride olabilir; çelişkide yerel belgeler esas. Kodun ve iş kurallarının Google'a yüklenmesi kullanıcının/şirketin kararıdır: etkinleştirmeden önce sor.

## İkisi birlikte

1. `GRAPH_REPORT.md` / `graph.html`'de aşırı bağlı düğüm → 2. `kesifci` ya da NotebookLM'e "bu modül ne işe yarıyor, nasıl sadeleşir?" → 3. `mimar` TASARIM modu ile plan → 4. onay → `gelistirici`.

## Kritik alışkanlık

Belgeler **commit'ten önce** güncellenir (faz-arsivcisi): kod yaz → tester → reviewer → **faz-arsivcisi** → commit → post-commit (graphify + bundle + sync) → NotebookLM "Yenile". Belge güncellenmeden commit atılırsa NotebookLM yalnızca kodu görür, bağlamı görmez.
