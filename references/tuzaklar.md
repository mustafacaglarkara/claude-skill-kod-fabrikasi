# 10 Kritik Tuzak — Bunlara SAKIN Düşme

Bu liste, sistemin geçirdiği hatalardan damıtıldı. `bundle.py` veya `setup-hooks.sh`'yi "sadeleştireyim / iyileştireyim" derken bu hatalara **geri dönme**.

---

## 1. NotebookLM kaynaklarını başlığa göre dict'leme

```python
# YANLIŞ — aynı başlıktan birden fazla kaynak GİZLENİR
title_to_id = {s.title: s.id for s in sources}

# DOĞRU — kaynakları LİSTE olarak dolaş, id bazında sil
for s in sources:
    if s.title not in desired_titles:
        await client.sources.delete(notebook_id, s.id)
```

**Neden:** NotebookLM aynı başlıktan birden fazla kaynak tutabilir (race condition, yarım kalan yükleme). Dict yaparsan ikinciyi kaybedersin → çiftler her çalıştırmada birikir.

**Mevcut bundle.py'de:** `sync_to_notebooklm_async()` doğru çalışıyor (`old_sources` listesi olarak dolaşıyor).

---

## 2. Alt klasör dosyalarında başlık çakışması

```python
# YANLIŞ — add_file başlığı dosya adından türetir
client.sources.add_file(notebook_id, "a/rapor.md")   # title: "rapor.md"
client.sources.add_file(notebook_id, "b/rapor.md")   # title: "rapor.md" ← çakıştı!

# DOĞRU — göreli yolu '__' ile düzleştir
title = rel_path.replace(os.sep, '__')   # "a__rapor.md"
# Sonra geçici staging dir'e bu adla kopyalayıp yükle
```

**Neden:** NotebookLM kaynak başlığı dosya adından otomatik türer. Alt klasörde aynı isimli dosyalar → ikincisi birincisini ezer.

**Mevcut bundle.py'de:** `collect_drive_sources()` ve `upload_as_source()` bunu yapıyor.

---

## 3. `python3` PATH varsayma

```bash
# YANLIŞ — git hook sınırlı PATH ile çalışır
python3 bundle.py   # ModuleNotFoundError: notebooklm

# DOĞRU — TAM YOL kullan (config'ten oku)
PYTHON_BIN=$(python3 -c "import json; print(json.load(open('.claude/kod-fabrikasi.config.json'))['python_bin'])")
$PYTHON_BIN bundle.py
```

**Neden:** `notebooklm-py` belirli bir Python interpreter'a kuruludur. Git hook'ları (ve cron, systemd) genelde sınırlı PATH ile çalışır → `python3` farklı bir Python'a denk gelir → `from notebooklm import ...` patlayarak tüm bundle'ı çökerir.

**Mevcut setup-hooks.sh'da:** `PYTHON_BIN` tam yola sabitlenmiş; config-driven versiyonda da öyle olacak.

---

## 4. Boş klasör = felaket (güvenlik freni)

```python
# YANLIŞ — boş listeyle çağırırsan TÜM NotebookLM kaynaklarını siler
drive_sources = collect_drive_sources()   # bir hatayla boş döndü
for s in old_sources:
    if s.title not in {t for t, _ in drive_sources}:   # set boş!
        delete(s.id)   # HEPSİ silinir

# DOĞRU — boş ise hiçbir şeye dokunma
if not drive_sources:
    print("⚠️ Drive klasörü boş — güvenlik için NotebookLM'e dokunulmuyor.")
    return
```

**Neden:** Drive masaüstü uygulaması geçici olarak klasörü erişilemez yapabilir; Drive yolu yanlış yazılmış olabilir. "Klasörde olmayan = sil" mantığı boş klasörde tüm NotebookLM kaynaklarını yok eder.

**Mevcut bundle.py'de:** Güvenlik freni var (`sync_to_notebooklm_async` başında). **KALDIRMA.**

---

## 5. `__pycache__` commit etme

`bundle.py` import edilince `__pycache__/` oluşur. `.gitignore`'a ekle:

```gitignore
__pycache__/
graphify-out/
.claude/settings.local.json
```

`init.sh` bunları otomatik ekler.

---

## 6. Büyük HTML / JSON yükleme

```python
# YANLIŞ — graph.html (~8 MB) NotebookLM'i boğar / hata verir
NOTEBOOKLM_ALLOWED_EXTENSIONS = {'.md', '.txt', '.pdf', '.html', '.json'}   # !

# DOĞRU — sadece metin tabanlı, NotebookLM dostu uzantılar
NOTEBOOKLM_ALLOWED_EXTENSIONS = {'.md', '.txt', '.pdf'}
```

**Neden:** NotebookLM web UI büyük HTML/JSON dosyalarında kasar veya kelime limitini aşar. Graphify'ın `graph.html` (~8 MB), `graph.json`, `manifest.json` çıktıları bu kategoridedir.

**Çıkış yolu:** Graphify'ın `GRAPH_REPORT.md` çıktısı (kısa metin özeti) zaten NotebookLM'e gider — yapısal bilgi için yeterli.

---

## 7. `copytree(dirs_exist_ok=True)` ile eski dosyalar birikir

```python
# YANLIŞ — hedefte eski dosyalar kalır, birikir
shutil.copytree(src, dest, dirs_exist_ok=True)

# DOĞRU — önce sil, sonra kopyala (birebir ayna)
shutil.rmtree(dest, ignore_errors=True)
shutil.copytree(src, dest)
```

**Neden:** Faz raporu silindiyse veya yeniden adlandırıldıysa, `dirs_exist_ok=True` eski dosyayı bırakır. Drive'da artık dosyalar birikir → NotebookLM'de eski içerik görünür.

**Mevcut bundle.py'de:** `SYNC_DIRS` döngüsü `rmtree` + `copytree` ile çalışıyor.

---

## 8. `reports/` klasörünü `sync_dirs`'e koymama

```json
// YANLIŞ — faz raporları NotebookLM'e hiç gitmez
"sync_dirs": ["graphify-out"]

// DOĞRU — reports da dahil
"sync_dirs": ["reports", "graphify-out"]
```

**Neden:** Faz raporları (`reports/fazNN_*.md`) en değerli bağlamdır — sonraki fazlar bunları okur. `sync_dirs`'e dahil değilse NotebookLM görmez, soru sorulduğunda "bilmiyorum" der.

---

## 9. Aynı içeriği hem `.md` hem `.txt` olarak yazma

```python
# YANLIŞ — NotebookLM'de aynı içerik çift kaynak olarak görünür
write_to_drive("tum_kodlar.md", content)
write_to_drive("tum_kodlar.txt", content)   # !!

# DOĞRU — tek format seç (genelde .txt — NotebookLM .md'yi markdown render eder, kodda render istemiyoruz)
write_to_drive("tum_kodlar.txt", content)
```

**Neden:** NotebookLM iki kaynağı ayrı sayar; sorularda çift atıf çıkar, kaynak listesi şişer.

---

## 10. Runtime doğrulamayı atlayıp "yeşil" yazma

```markdown
# YANLIŞ
## Test Sonuçları
- Tüm testler yeşil ✅

# DOĞRU (eğer test çalıştırılamadıysa)
## Test Sonuçları
- `flutter test` çalıştırılamadı: bağımlılıklar kuruluma uygun değil.
- Runtime doğrulama BEKLİYOR — sonraki sessionda test çalıştırılmalı.
```

**Neden:** "Yeşil" yazıp commit atarsan sonraki AI veya kullanıcı sisteme güvenir. Sonra bug çıkarsa kaynağı bulmak zor olur. **Dürüstlük > optimizm.**

---

## Bonus: 11. Mevcut kodu "iyileştireyim" diye yeniden yazma

`bundle.py` ve `setup-hooks.sh` bu 10 tuzaktan geçerek olgunlaştı. Refactor etmek istersen:

1. **Önce bu listeyi oku.**
2. **Yapısal değişiklik öneriyorsan kullanıcıya gerekçeli sun, ONAY al** (FAZ_PROMPT Adım 2 zaten bunu söylüyor).
3. **Değişiklikten sonra hızlı duman testi:** `make bundle` çalıştır + `notebooklm source list` ile çift kaynak yok mu kontrol et.

Geçmişte ne kazandık, ne kaybetmemeli — bunu bilen tek belge bu dosya.
