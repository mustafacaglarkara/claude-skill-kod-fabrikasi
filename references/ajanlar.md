# Ekip: Ajanlar, Brif Şablonu, Orkestratör Kuralları

Kaynak: iki gerçek projede haftalarca çalışan ekiplerden damıtıldı (bir API + web + panel + mesajlaşma ürünü; bir Rust + Astro ürünü). Kural bir şey ters gittiği için varsa nedeni tek satırda yazılıdır. Kuralları koru.

## Ekip

| Ajan | Model / effort | Yazar | Ne için | Ne zaman yükselt |
| --- | --- | --- | --- | --- |
| `kesifci` | sonnet / low, maxTurns 40 | ❌ | Çok dosyalı "nerede / kim çağırıyor" soruları; `dosya:satır`; brif hazırlığı | Cevap tasarım kararı gerektiriyorsa → `mimar` TASARIM |
| `gelistirici` | opus / medium | ✅ | Onaylı planın tek, bağımsız parçası; test ve lint | Başarısız → `mimar`; karar gerekiyor → kullanıcı |
| `tester` | sonnet / medium, maxTurns 60 | ❌ | Derleme, test, tip denetimi; kanıtlı rapor | — |
| `reviewer` | opus / high, maxTurns 60 | ❌ | Donmuş diff'in bağımsız incelemesi | Güvenlik alanı → + `guvenlik-inceleyici` |
| `faz-arsivcisi` | sonnet / low | yalnızca `.claude/*.md` | PROGRESS, ROADMAP, ADR, OPEN, MEMORY, QA, faz raporu | — |
| `mimar` (isteğe bağlı) | opus / xhigh | ✅ (onayla) | Yüksek risk, tasarım, kök neden, performans | En yüksek riskte kullanıcı Fable isterse ajan dosyasında `model: fable` |
| `guvenlik-inceleyici` (isteğe bağlı) | opus / high, maxTurns 60 | ❌ | Tehdit modeli, auth/token/yükleme/PII | — |
| `<alan>-uzmani` (isteğe bağlı, N tane) | sonnet / medium, maxTurns 40 | ❌ | Dış API / alan kuralları, hata kodları | — |

Projede gerekmeyen isteğe bağlı ajanı kurma (UI'sız projede UI uzmanı yok). `maxTurns` yalnızca salt okunur ajanlarda: sınırlı bir yazan ajan yarım iş bırakır.

**Ajans profili katmanı** (`profile: ajans`; şablonlar `assets/agents/ajans/`): `metin-yazari` (sonnet/medium, yazar: yalnızca `clients/<slug>/campaigns|content`), `marka-denetcisi` (sonnet/high, maxTurns 40, QA kapısı), `seo-teknisyeni`, `rakip-analisti`, `site-denetcisi` (sonnet/medium, maxTurns 60, Bash ile betik çalıştırır, dosya yazmaz; betikler `--out` ile yazar), `cloudflare-operatoru` (sonnet/medium, maxTurns 40; API yazma yalnızca `--yes` + kullanıcı onayı), isteğe bağlı `reklam-stratejisti` (sonnet/medium, maxTurns 40). Brife iki satır eklenir: `MÜŞTERİ: <slug>` ve `DOKUNMA: clients/<diğer>/**`. Akışlar ve kapı kuralları: [ajans.md](ajans.md).

Ajan dosyası = frontmatter (`name` = dosya adı, `description` katman + model + ne zaman + ne zaman yükselt, `tools`, `model`, `effort`, salt okunurlarda `maxTurns`, `color`) + rol, kaynak sırası, proje kuralları (config'ten doldurulur), yapma listesi, rapor şekli ve kelime sınırı + **Verimli çalış** bloğu. Şablonlar: `assets/agents/`. Ajan konuşmayı görmez; brif tek kaynağıdır.

## Brif şablonu (eksiksiz ver, kimse aramasın)

```text
MOD: BUILD | AUDIT | REVIEW | TEST | ARŞİV
HEDEF: <bir cümle>
FAZ/ADIM: Faz N.M — <başlık>
YAPILACAKLAR: 1. ... 2. ...   (her biri dosya:satır ile)
KAPSAM DIŞI: ...
KARARLAR (alınmış, tartışma): ADR-012 ..., kullanıcı dedi ki ...
DOĞRULANMIŞ GERÇEKLER: sürümler, komutlar, şema adları (tahmin değil)
KABUL KRİTERLERİ: - ... (test edilebilir)
TESTLER: <komutlar> ; şu test dosyaları: ...
DOKUNMA: <paralel ajanların dosyaları>, .claude/**/*.md, .env*
RAPOR ŞEKLİ: ajan dosyasındaki format, en fazla N kelime
```

Brif yazmadan önce `kesifci` ya da `graphify query` ile `dosya:satır` bul; ajan arama yapmasın.

## Orkestratör kuralları

- **Yeni iş → yeni ajan.** Bitmiş bir ajana ikinci görev verilince eski transkript her adımda yeniden okunur (ölçüldü: ikinci görevin token'larının %73'ü eski işti). Yalnızca aynı dosyalarda kısa düzeltme turu için, transkript küçükken devam ettir.
- **Büyük işi böl**: katman ya da klasör bazında, hiçbir ajan ~120 araç çağrısını geçmesin.
- **Aynı anda en fazla `max_parallel_editors` yazan ajan**, dosyaları çakışmayan alanlarda; salt okunurlar serbest. Paylaşılan dosyalarda (rota, çeviri, şema) her ajan kendi satırlarını düzenler ve düzenlemeden önce o aralığı yeniden okur.
- **İncelemeler**: her yüksek riskli değişiklik `reviewer` (donmuş diff) + gerekirse `guvenlik-inceleyici`; bulgular koda bakılarak teyit edilir (bir not bir zamanlar ilanın kendi videosunu sosyal bağlantı sanmıştı), teyitliler `dosya:satır` ile yeni ajana gider.
- **Başarısızlıkta kademe yükselt**; aynı brifi aynı ajana tekrar gönderme.
- **Test veritabanı**: testler dev veritabanına yazabilir; ayrı test DB olduğundan emin değilsen `tester` çalıştırmaz, raporlar. Paralel test koşan ajanlar aynı DB'yi bozmasın (tek test koşan ajan ya da kilit).
- **Şema değişikliği**: ajan SQL/migration verir, ana oturum kullanıcıya gösterir, onayla tek işlemde uygular; yıkıcı yeniden kurulum kullanıcı "evet" demeden asla.
- **Uygulamadaki kararlar uygulamadan geçer**: admin/moderasyon işlemleri test personel hesabıyla UI'dan; mevcut yöneticinin adına veritabanına yazmak yok.
- **Kullanıcının makinesi**: konteyner başlatmadan portları kontrol et; yalnızca gereken servisi aç; oluşturduğun test verisini temizle.
- **Ajan adlarını kullanıcıya rolüyle söyle** ("inceleyici şunu buldu"), iç kimlik değil.

## "Verimli çalış" bloğu (her ajan dosyasında, kelimesi kelimesine)

Neden: ~5.000 ajan adımı ölçüldü; token'ların yarısı arama ve okumaya gitti, aramaların %6'sı haritayı kullandı, okumaların %96'sı dosyayı bütün aldı. Ajan her adımda tüm transkriptini öder; maliyet ≈ transkript boyutu × adım.

```text
## Verimli çalış
(Her adımda tüm transkriptin yeniden okunur; maliyet ≈ transkript boyutu × adım sayısı.)
- Önce harita (`graphify query/explain`), sonra `Grep` ile dosya:satır; yalnızca o aralığı oku. Repo geneli arama yalnızca harita cevap vermiyorsa; tek klasöre daralt, önce `-l`/`-c`, sonra `| head -30`.
- 150 satırdan uzun dosyayı bütün okuma. Komut çıktısını kısa tut.
- Brifte verilen ve bu çalışmada okuduğun şey bilinir: yeniden kontrol etme. Az önce düzenlediğin dosyayı yeniden okuma. Sonucu bir sonraki adımını değiştirmeyecek kontrolü çalıştırma.
- Brifin istediğini, çevredeki kodun yaptığı gibi yap: ek seçenek, katman, refactor, döküman yok. Brif dışında yanlış gördüğünü raporuna yaz, dokunma.
- Testi orantılı tut: kabul kriteri ve gerçek risk başına bir test. Dokunduğun şeyi kullanan test dosyalarını bir kez çalıştır; düzeltmeden sonra yalnızca kırmızı olanı. Geçeni yeniden koşturma. Tam paketi `tester` koşar.
- Yeni testin değişiklik olmadan kırmızı olduğunu dosyanın GEÇİCİ KOPYASI ile kanıtla. `git stash`, `git checkout -- <dosya>`, `git reset` ASLA: aynı dosyalarda başka commit edilmemiş iş olabilir.
- Başka ajan başlatma. ~120 araç çağrısını geçersen temiz bir noktada dur; biteni ve kalanı raporla.
- Geçici dosyalar yalnızca kendi klasörüne: `$TMPDIR/<proje>-<ajan>/`. Commit atma. `.env` ve gizli dosya okuma; çıktıda sır görürsen maskele.
```

`kf.py selftest` bloğun varlığını ("Verimli") her ajanda denetler.

## Model ve effort

- Ana oturumun modelini skill **ayarlamaz** (`settings.json`'a `model`/`effortLevel` yazılmaz; kullanıcının varsayılanı değişmez). Kullanıcı isterse kendisi `/model` ile seçer; büyük/yüksek riskli üründe Fable, çoğu projede Opus yeterli.
- Ajan modelleri dosyada: salt okunur ve mekanik işler sonnet, yazma ve inceleme opus, en yüksek riskte `mimar` için kullanıcı isterse fable. Değiştirmek için ajan dosyasını düzenle; `kf.py repair --force-agents` şablondan geri yükler.
- Alt ajan prompt önbelleği ~5 dk; uzun ön planda bekleme tüm bağlamı yeniden gönderir. Küçük, taze, iyi briflenmiş ajan hem ucuz hem hızlı.
