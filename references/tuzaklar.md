# Kritik Tuzaklar — Bunlara SAKIN Düşme

Sistemin geçirdiği gerçek hatalardan damıtıldı. `kf.py`'yi "sadeleştireyim / iyileştireyim" derken bu hatalara **geri dönme**. Liste yalnızca büyür; tuzak silinmez.

## NotebookLM / paketleme (kf.py bundle)

### 1. Kaynakları başlığa göre dict'leme
`{s.title: s.id}` aynı başlıktan birden fazla kaynağı gizler → çiftler her çalıştırmada birikir. **Liste olarak dolaş, id bazında sil.** (`notebooklm_mirror`)

### 2. Alt klasör dosyalarında başlık çakışması
`add_file` başlığı dosya adından türetir; `a/rapor.md` ile `b/rapor.md` ikisi de "rapor.md" → biri diğerini ezer. **Göreli yolu `__` ile düzleştir**, staging klasöründen yükle. (`flat()`, `collect_sources`)

### 3. `python` PATH varsayma
Git hook'ları sınırlı PATH ile çalışır; `notebooklm-py` belirli bir Python'a kuruludur. **Config `python_bin` tam yol**; hook ve SessionStart komutu onu kullanır. Belirti: hook'ta `ModuleNotFoundError: notebooklm` → `kf.py selftest`.

### 4. Boş klasör = felaket (güvenlik freni)
Drive geçici erişilemezse "klasörde olmayan = sil" mantığı TÜM NotebookLM kaynaklarını siler. **`collect_sources` boş dönerse dokunma.** Freni KALDIRMA.

### 5. Büyük HTML / JSON yükleme
`graph.html` (~8 MB), `graph.json` NotebookLM'i boğar. İzinli uzantılar yalnızca `.md/.txt/.pdf`; `graphify-out`'tan yalnızca `.md` kopyalanır. Genişletme.

### 6. `copytree(dirs_exist_ok=True)`
Silinen/yeniden adlandırılan rapor hedefte kalır, birikir. **Önce `rmtree`, sonra `copytree`** (birebir ayna). `replace_dir`.

### 7. Aynı içeriği hem `.md` hem `.txt` yazma
NotebookLM ikisini ayrı kaynak sayar; çift atıf. Tek format.

### 8. Faz raporlarını `sync_dirs` dışında bırakma
Raporlar en değerli bağlamdır. `.claude/archives` `sync_dirs`'te kalır; raporlar başka yere yazılmaz.

### 9. `.gitignore`'u yok sayan paketleme (v2'de vardı)
v2 `bundle.py` `os.walk` + uzantı listesi (`.sql`, `.json`) ile dolaşırdı: `.env.json`, SQL dökümleri, veri dosyaları Drive'a ve Google'a gidebilirdi. **v3: paket yalnızca `git ls-files` çıktısından oluşur.** `os.walk`'a geri dönme. İzlenen veri dosyası istenmiyorsa `bundle.skip_prefixes`.

### 10. Düzleştirilen adın nokta ile başlaması
`.claude/archives/X.md` → `.claude__archives__X.md` olur; toplayıcı "gizli dosya" sanıp atlar, NotebookLM'e hiç gitmez. `flat()` baştaki noktayı kaldırır (`claude__archives__X.md`). Bu davranışı koru.

### 11. `__pycache__` ve `bundle-out` commit etme
`.gitignore`: `__pycache__/`, `graphify-out/`, `.claude/bundle-out/`, `.claude/settings.local.json`. `init` ekler.

## Ajanlar / orkestrasyon

### 12. Etkileşimli kurulum betiği
v2 `init.sh` `read -rp` ile soru sorardı. Claude'un Bash'i etkileşimsizdir: `read` boş döner ya da takılır; betik Claude tarafından hiç çalıştırılamaz. **Her bilgi parametreyle** (`kf.py init --...`); soruları `AskUserQuestion` toplu sorar.

### 13. İki post-commit sahibi
`graphify hook install` kendi post-commit'ini yazar; `kf.py hooks` da yazar. İkisi birden: harita iki kez üretilir ya da biri diğerini ezer. **Tek sahip `kf.py`**; `end-phase` içinde `graphify update` çağrılır. Yabancı hook varsa `kf.py hooks` onu `.pre-kf.bak` olarak yedekler ve uyarır.

### 14. Kodu yazan ajana kendi işini doğrulatma
`gelistirici`'ye "testleri de koş ve incele" demek bağımsızlığı yok eder. `tester` ve `reviewer` kod yazamaz (tools'ta Edit/Write yok); `selftest` bunu denetler. Bu ayrımı bozma.

### 15. Bitmiş ajana ikinci görev
Eski transkript her adımda yeniden okunur (ölçüm: ikinci görevin token'larının %73'ü eski iş). Yeni iş → yeni ajan. Yalnızca aynı dosyalarda kısa düzeltme turu için devam ettir.

### 16. Başarısız brifi aynı ajana tekrar göndermek
Aynı bağlam, aynı sonuç. Bir kademe yükselt (`gelistirici` → `mimar`), brife başarısızlığın kanıtını ekle.

### 17. Ajanlarda `git stash` / `git checkout --` / `git reset`
Paralel ajanlar aynı çalışma kopyasındadır; birinin stash'i diğerinin yarım işini yutar (yaşandı). Yeni testin kırmızı olduğunu kanıtlamak için dosyanın **geçici kopyası** kullanılır. `settings.json` bu komutları `ask`'a koyar.

### 18. Yazan ajanlara `maxTurns`
Sınıra çarpan `gelistirici` yarım iş bırakır ve rapor vermez. `maxTurns` yalnızca salt okunurlarda (40–80).

### 19. Planlama belgelerini herkesin yazması
Format dağılır, hook başlıkları bulamaz, ADR numaraları çakışır. **Yalnızca `faz-arsivcisi`** yazar; başlık adları (`## Durum`, `## Günlük`, `## Sıradaki adım`, `## ADR-NNN:`, `## OPEN-NNN:`) değişmez.

### 20. Ana oturumun modelini projeye yazmak
`settings.json` → `model`/`effortLevel` kullanıcının o projedeki varsayılan oturumunu değiştirir; kullanıcı fark etmez, maliyet sürpriz olur. Skill yazmaz; model yalnızca ajan dosyalarında.

### 21. İnceleme notunu doğrulamadan aktarmak
Bir reviewer notu ilanın kendi videosunu "sosyal bağlantı" sandı; bir "tutarlılık düzeltmesi" sahibin görünümünü bozdu. Bulguyu koda bakarak teyit et, sonra düzeltme turuna gönder.

## Süreç

### 22. Adım 2'yi atlayıp koda dalma
Kullanıcı onayı olmadan kod değişikliği YOK. "Onaysız devam et" denirse: "plan üzerinde ne değiştirelim?"

### 23. Runtime doğrulamayı atlayıp "yeşil" yazma
```markdown
# YANLIŞ
- Tüm testler yeşil ✅
# DOĞRU (çalıştırılamadıysa)
- `flutter test` çalıştırılamadı: <sebep>. Runtime doğrulama BEKLİYOR.
```
Dürüstlük > optimizm. PROGRESS "Bitti" yalnızca kanıtla.

### 24. Testlerin dev veritabanını silmesi
Test ayarı dev DB'ye bakıyorsa `flutter test`/`pytest` veriyi uçurur (yaşandı). Ayrı test DB'si doğrulanmadan `tester` koşmaz, raporlar.

### 25. Kök dizine yönetim dosyası / betik bırakma
README dışında AI yönetim `.md`'si ve `bundle.py`/`Makefile` kökte durmaz; `migrate --remove-legacy` temizler. `CLAUDE.md` 200 satırı aşarsa `.claude/rules/`.

## Bonus: 26. Mevcut kodu "iyileştireyim" diye yeniden yazma
`kf.py` bu tuzaklardan geçerek olgunlaştı. Refactor istiyorsan: 1) bu listeyi oku, 2) yapısal değişikliği gerekçeli sun ve ONAY al, 3) sonra `kf.py selftest` + deneme projesinde `init`/`migrate`/`bundle --dry-run` + (NotebookLM etkinse) `notebooklm source list` ile çift kaynak yok mu kontrol et.
