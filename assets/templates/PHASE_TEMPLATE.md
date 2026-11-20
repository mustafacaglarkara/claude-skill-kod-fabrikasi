# Faz Raporu Şablonu

Her faz kapanışında `faz-arsivcisi` bu şablonu birebir uygulayarak `.claude/archives/PHASE_NN_<konu>.md` yazar. NN iki haneli (`PHASE_07_...`), alt faz `PHASE_12_3_...`; konu snake_case, Türkçe karakter yok. Tüm bölümler bulunur; bilgi yoksa "Yok" ya da "Uygulanamaz" yazılır.

---

# Faz NN Raporu — <Faz Başlığı>

- **Tarih:** YYYY-MM-DD
- **Durum:** ✅ Tamamlandı / ⚠️ Kısmi tamamlandı (neden) / ❌ İptal
- **Faz hedefi:** <ROADMAP'teki hedefin bir cümlelik özeti>
- **Commit:** <hash> (kullanıcı commit atmadıysa "henüz commit yok")

## Yapılanlar

- <somut adım; her madde bir değişiklik>

## Ajanlar ve sonuçları

| Ajan | Görev | Sonuç |
| --- | --- | --- |
| gelistirici (×N) | <parçalar> | <değişen dosya sayısı> |
| tester | <komutlar> | ✅ N/N yeşil / ❌ ... |
| reviewer | <diff> | ONAY / DÜZELTME GEREKLİ (düzeltildi mi?) |
| guvenlik-inceleyici | <varsa> | ... |

## Alınan Kararlar

- <karar → ADR-NNN> ; reddedilen alternatifler ve nedeni

## Karşılaşılan Sorunlar ve Çözümler

- <sorun> → <çözüm veya geçici çözüm>; MEMORY.md'ye eklendi mi?

## Test Sonuçları

- <komut> → <sayı ile sonuç>. "Tüm testler yeşil" yazmadan önce gerçekten yeşil olduğundan emin ol; çalıştırılamadıysa "runtime doğrulama bekliyor: <sebep>".

## Değişen Dosyalar

- `path/to/file` — <tek cümle>

## Belge Güncellemeleri

- **ROADMAP.md:** Faz NN [x]; sıradaki faz 🟡 Aktif.
- **PROGRESS.md:** Durum satırı, günlük maddesi, sıradaki adım.
- **DECISIONS.md:** ADR-NNN eklendi / yok.
- **OPEN_QUESTIONS.md:** OPEN-NNN kapandı / eklendi / yok.
- **MEMORY.md / QA_REPORTS.md / KNOWN_BUGS.md:** <özet>

## Sonraki Faza Notlar

- <uyarılar, ertelenen işler, dokunulmayan ama izlenmesi gereken alanlar>
