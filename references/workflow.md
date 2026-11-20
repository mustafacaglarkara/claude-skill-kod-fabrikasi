# Faz Bazlı Geliştirme — 9 Adımlı İş Akışı (v3)

Ana oturumun (orkestratör) **her fazda** uyguladığı yönerge. SKILL.md'deki özetin ayrıntısıdır. Ajan seçimi ve brif kuralları için [ajanlar.md](ajanlar.md); belge rolleri için [hafiza.md](hafiza.md).

## Tetikleyiciler

"Sıradaki fazı başlat", "Faz N'i başlat", "FAZ_PROMPT'u oku", "roadmap'teki ilk fazı yap", "nerede kalmıştık" (yalnızca durum; faz başlatmaz).

---

## Adım 0 — Fazı belirle

- `phase_files.roadmap` (`.claude/archives/ROADMAP.md`): "Faz Durumu Özeti" tablosunda ilk `[ ]` ya da 🟡 Aktif faz. Kullanıcı belirli bir faz söylediyse onu al.
- `OPEN_QUESTIONS.md` içinde bu fazı bloke eden `OPEN-NNN` varsa önce onu kullanıcıya sor; cevapsız bloklu faza başlama.
- Birden fazla aday varsa seçim sun (öneri önce).

## Adım 1 — Bağlam topla (ucuz)

Yereldeki belgeler esastır: `PROGRESS.md` (Sıradaki adım), `DECISIONS.md` (ilgili ADR'ler, `Grep`), `MEMORY.md` (acı dersler), `QA_REPORTS.md`, `KNOWN_BUGS.md`. Hook zaten özetini yükledi; dosyaları bütün okuma, ilgili bölümü `Grep` ile bul.

Kod konumları için **`kesifci`** (salt okunur, dosya:satır döner) ya da doğrudan `graphify query "<soru>"` / `graphify explain "<sembol>"`. Etki analizi gerekiyorsa `graphify-out/GRAPH_REPORT.md`. NotebookLM etkinse geniş/kesişen sorular için `notebooklm ask`. Çelişkide yerel dosyalar kazanır.

Alan sorusu (dış API, ödeme, vb.) varsa `<alan>-uzmani`.

## Adım 2 — Plan sun ve ONAY al ⚠️ zorunlu durak

Paket:
1. Sıralı, somut adımlar; her adımda **hangi ajan** (ya da "ana oturum kendisi").
2. Etkilenecek dosyalar `dosya:satır` ile; paralel parçaların dosya kümeleri **çakışmaz**.
3. Riskler ve geri alma planı; yıkıcı işlem varsa yedek adımı; yüksek riskli alana dokunuyorsa `reviewer` + `guvenlik-inceleyici` (+ gerekirse `mimar` TASARIM modu önce).
4. Kabul kriterleri (test edilebilir) ve koşulacak test komutları.
5. Kullanıcıdan istenen kararlar: tek toplu soru, öneri önce (`AskUserQuestion`).

Açık onay bekle ("onaylıyorum", "devam", "evet"). Belirsiz cevapta tekrar sor. Onay = yalnızca sunulan plan için; kapsam genişlerse yeniden sor.

## Adım 3 — Uygula

- Her parça için **yeni** `gelistirici`; aynı anda en fazla `agents.max_parallel_editors` (varsayılan 3) yazan ajan; salt okunur ajanlar yanında serbest.
- Brif: [ajanlar.md](ajanlar.md) şablonu, eksiksiz. Paralel ajanlara birbirinin dosyalarını bildir.
- Tam tanımlı küçük düzeltmeyi (bir alan, bir metin, bir rename) ana oturum kendisi yapabilir; testi kanıtlayarak.
- Yıkıcı işlem (şema, migration, toplu silme) ajanda değil: ajan SQL/komutu verir, ana oturum kullanıcıya gösterir, onayla uygular.
- Ajan raporunu oku; "brif dışı sorun" notlarını topla (sonraki fazlara ya da OPEN'a).

## Adım 4 — Test (`tester`, zorunlu)

- Brif: hangi komutlar (config `test_commands`), dar kapsam varsa hangi test dosyaları, PROGRESS'teki son "N test yeşil" değeri.
- ❌ KIRMIZI → başarısızlıkları `dosya:satır` ile **yeni** bir `gelistirici`'ye düzeltme brifi; sonra yalnızca kırmızı dosyalar için tekrar `tester`. Aynı gelistirici'ye ikinci kez verme; ikinci başarısızlıkta `mimar`.
- ⏸️ DOĞRULANAMADI (ortam yok) → raporda ve PROGRESS'te açıkça; "yeşil" yazılmaz.

## Adım 5 — İnceleme (`reviewer`, zorunlu)

- Donmuş diff ver: `git diff HEAD -- <dosyalar>` çıktısı ya da kesin dosya listesi. Ana oturumun yorumunu değil, kodu ver.
- Yüksek riskli alan (`high_risk_areas`) ya da auth/token/yükleme/PII → paralel `guvenlik-inceleyici`.
- Bulguları koda bakarak teyit et (bir inceleme notu yanlış olabilir); teyitlileri düzeltme turuna gönder (yeni `gelistirici`, `dosya:satır`); sonra ilgili testler tekrar.
- Karar ONAY değilse faz "Kısmen bitti".

## Adım 6 — Arşiv (`faz-arsivcisi`)

Brif: faz no/başlık, yapılanlar, değişen dosyalar (tek cümle/dosya), tester sonucu (sayılarla), reviewer kararı, alınan tasarım kararları (ADR adayı), kapanan/yeni OPEN ve QA/BUG numaraları, öğrenilen acı dersler (MEMORY adayı), sonraki faza notlar. Ajan şunları yazar: `PHASE_NN_<konu>.md` (şablon birebir), PROGRESS (Durum, Günlük, Sıradaki adım), ROADMAP durum işareti, DECISIONS, OPEN_QUESTIONS, MEMORY, QA_REPORTS/KNOWN_BUGS, (varsa) NOTEBOOKLM_SUMMARY. Raporunu kontrol et: "Bitti" kanıtsız yazılmış mı?

## Adım 7 — Kullanıcıya rapor

Kullanıcının dilinde, kısa: ne yapıldı (ajanları rolüyle an), ne geçti/geçmedi (çıktı alıntısıyla), ne test edilmedi, gereken kararlar (öneri önce), sıradaki adım, "commit atılmadı" ya da "commit için hazır". Ajan raporunu doğrulamadan aktarma.

## Adım 8 — Commit (yalnızca kullanıcı isterse)

- Adlı yollarla `git add <dosyalar>` (`-A` değil; `.env`, veri, döküm asla). Pre-commit gizli bilgi taraması çalışır.
- Mesaj projede tutarlı: `Faz N: <başlık>` ya da `feat: Faz N — <başlık>`.
- Post-commit: `kf.py end-phase` → graphify update → bundle (Drive/NotebookLM etkinse) → sync (Obsidian etkinse). Atlamak için `KF_SKIP=1 git commit ...`.
- Kullanıcıya hatırlat: NotebookLM etkinse web arayüzünde "Yenile". Push yalnızca kullanıcı isterse (settings `ask`).

---

## Kurallar (her fazda)

1. Önce onay, sonra kod. 2. Kodu yazan ajan kendi işini onaylamaz. 3. Her faz: tester yeşil + reviewer ONAY + faz-arsivcisi kaydı olmadan "bitti" değil. 4. Yıkıcı işlem = önce doğrulanmış yedek, kullanıcı onayı. 5. Doğru kaynak yerel belgeler; NotebookLM danışma katmanı. 6. Yeni iş → yeni ajan; başarısızlıkta kademe yükselt. 7. Çalıştıramadığını "yeşil" gösterme.

## Mikrofazlama (Faz X.Y)

Büyük faz 12 → 12.1, 12.2… Her alt faz ayrı onay, ayrı tester/reviewer turu; ayrı commit kullanıcı tercih ederse. Faz raporu alt faz büyükse ayrı (`PHASE_12_2_...`), küçükse ana rapora bölüm.

## Hata senaryoları

| Durum | Yap |
| --- | --- |
| Test kırmızı, kullanıcı "devam et" diyor | PROGRESS ve faz raporuna "Testler kırmızı: <neden>, fix Faz N+1" yaz; "Kısmen bitti". Yeşil gösterme. |
| Ajan "Agent type not found" | Hot reload birkaç saniye sürer; tekrar dene. Olmazsa kullanıcıya yeni oturum öner; acilse `general-purpose` ajanına "`.claude/agents/<ad>.md` dosyasını oku ve o role uy" brifi ver. |
| Ajan 120+ araç çağrısında yarım bıraktı | Raporundaki "kalan" listesini yeni bir ajana ver; aynı ajanı devam ettirme. |
| İki ajan aynı dosyayı değiştirdi | Planlama hatası: diff'i reviewer'a ver, çakışan parçayı tek gelistirici'ye yeniden yaptır; ajanlar.md "paylaşılan dosya" kuralını brife ekle. |
| post-commit hook çöktü | `python_bin` yanlış ya da notebooklm-py o Python'da yok (tuzaklar #3). `kf.py selftest`. Hook hiçbir zaman commit'i bozmaz. |
| Kullanıcı onaysız devam etmemi istiyor | "Onaysız ilerleyemem; plan üzerinde ne değiştirelim?" Bu kural esnemez. |
| NotebookLM/Drive erişilemez | Sorun değil; yerel `.claude/bundle-out/` kullanılır, faz tamamlanır. |
