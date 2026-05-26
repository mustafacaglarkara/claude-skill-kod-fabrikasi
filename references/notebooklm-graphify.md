# NotebookLM ve Graphify'ı Etkili Kullanma

## Mental model — kim ne yapar

| Parça | Ne yapar | Dosya yazar mı? |
|---|---|---|
| **Graphify** | **Yapı**: "X, Y'yi çağırıyor" — AST tabanlı bağımlılık haritası | Sadece `graphify-out/`'a HTML/JSON üretir |
| **NotebookLM** | **Anlam**: "X neden var, ne yapıyor" — projeyi okumuş danışman | ❌ Asla |
| **bundle.py** | İkisinin çıktısını + kodu + dökümanları Drive'a yazıp NotebookLM'i senkronlar | ✅ Drive'a |
| **Claude / Antigravity** | Asıl işi yapar: kod yazar, raporu yazar, ROADMAP günceller | ✅ |

**Önemli kural:** Kullanıcı sana iş söyler — NotebookLM'e değil. NotebookLM cevap verir, iş yapmaz.

---

## NotebookLM ile etkili sorgu

### Terminal

```bash
# Genel soru
notebooklm ask "ROADMAP'e göre sıradaki faz hangi dosyalara dokunmamı gerektirir?"

# Sadece belirli kaynağa hedefle (büyük tum_kodlar.txt tek başına dağıtabilir)
notebooklm source list --notebook <NOTEBOOK_ID>   # id'leri öğren
notebooklm ask "Auth akışı nasıl?" -s <source_id_kod> -s <source_id_roadmap>

# Önemli cevabı not olarak sakla
notebooklm ask "Refactor önerin?" --save-as-note

# Üret
notebooklm generate audio "Faz durumu özeti"        # podcast brifingi
notebooklm generate mind-map                         # kavram haritası
notebooklm generate report --format briefing-doc    # onboarding dökümanı
```

### Web (notebooklm.google.com)

- Sohbet kutusu — kaynaklara atıf vererek cevap verir `[1][2]`.
- **"Yenile (Refresh)"** butonu — her commit sonrası bas, yoksa eski koda göre cevap alırsın.
- "Audio Overview" butonu — proje brifingi podcast.

### Tipik soru kalıpları

| İhtiyaç | Örnek soru |
|---|---|
| Neredeyiz / ne sırada | `"sıradaki faz ne olacak"` |
| Faz planı fikri | `"Faz 4F için adım adım çözüm planı ve dokunulacak dosyalar?"` |
| Kod anlama | `"/urunler listeleme akışı hangi controller ve view'lardan geçiyor?"` |
| Faz sonrası kontrol | `"faz4f raporuna göre hangi testler geçti?"` |
| Bilinen sorunlar | `"QA_REPORTS'taki çözülmemiş sorunlar neler?"` |

---

## Graphify ile etki analizi

```bash
# Mimari haritayı güncelle (AST tabanlı, LLM yok)
make graphify-update
# veya: graphify update .

# Callflow diyagramları (çağrı zincirleri)
graphify export callflow-html
```

### Çıktılar (`graphify-out/`)

| Dosya | Ne için |
|---|---|
| `graph.html` | İnteraktif bağımlılık grafiği — tarayıcıda aç, modüllere zoom, düğümlere tıkla. **Refactor öncesi "buraya dokunsam nereler kırılır?" sorusunun görsel cevabı.** |
| `GRAPH_REPORT.md` | Metin özeti: en bağlantılı/kırılgan modüller, metrikler. Bu rapor NotebookLM'e de gider. |
| `callflow-html/` | Bir isteğin/akışın çağrı zincirini izlemek için |

### `.graphifyignore`

Taranmayacak yerleri kontrol eder. Tipik:
```
node_modules/
vendor/
public/
.dart_tool/
build/
storage/
```

### Ne zaman Graphify'a bak

- Refactor öncesi etki analizi
- Coupling sıcak noktalarını bulma
- Ölü kod tespiti
- Yeni gelen geliştiriciye onboarding

---

## İkisini birlikte — asıl güç burada

**Graphify** (yapı) + **NotebookLM** (anlam) = tam resim.

### Tipik akış

```
1. graph.html'de karmaşık/aşırı bağlı bir düğüm görürsün
                    ↓
2. NotebookLM'e sor: "GRAPH_REPORT'a göre en bağlı modül şu;
                      bu modül ne işe yarıyor ve nasıl sadeleştirebilirim?"
                    ↓
3. NotebookLM yapısal + planlama bağlamını birleştirip cevap verir
                    ↓
4. Sen bunu Claude'a aktarır, refactor planı için kullanırsın
```

### Refactor planı kalıbı

NotebookLM'e ROADMAP + GRAPH_REPORT kaynaklarıyla:
> "Şu fazı yaparken hangi dosyalar etkilenir? Hangi bağımlılıklar kırılır?"

→ Yapısal + planlama bağlamını birleştirir → güvenli plan.

---

## Kritik alışkanlık: Dökümanları commit'ten ÖNCE güncelle

NotebookLM'in en iyi cevap verdiği kaynaklar **kod değil, bağlam**:
- `ROADMAP.md`, `MEMORY.md`, `QA_REPORTS.md`

Sıralama:
```
1. Kod yaz
2. ROADMAP / MEMORY / QA güncelle    ← BUNU UNUTMA
3. git commit
4. post-commit otomatik: graphify + bundle → NotebookLM güncel
5. NotebookLM web'de "Yenile"
6. Sonraki fazı NotebookLM'e sor → iyi cevap alırsın
```

Adım 2'yi atlarsan NotebookLM sadece kodu görür, **bağlamı görmez** — cevaplar yüzeyselleşir.
