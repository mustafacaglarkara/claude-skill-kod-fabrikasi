# Faz Raporu Şablonu

Her faz kapanışında `reports/fazNN_<kisa_isim>.md` dosyası **birebir bu şablon kullanılarak** yazılır.

- **NN**: iki haneli faz numarası (`faz01`, `faz12`, `faz14_2`).
- **`<kisa_isim>`**: snake_case, Türkçe karakter kullanma. Örn: `faz14_2_form_ux_polish.md`.

`reports/` klasörü `bundle.py` tarafından `sync_dirs`'e dahil edildiği için faz raporları otomatik olarak NotebookLM'e yüklenir.

---

## Şablon (kopyala-yapıştır)

```markdown
# Faz NN Raporu — <Faz Başlığı>

- **Tarih:** YYYY-MM-DD
- **Durum:** ✅ Tamamlandı  /  ⚠️ Kısmi tamamlandı  /  ❌ İptal
- **Faz hedefi:** <ROADMAP'teki hedefin bir cümlelik özeti>
- **Bağlı PR / Commit:** <commit hash veya PR numarası>

## Yapılanlar

- <atılan somut adımlar — bullet listesi>
- <her bullet bir değişikliği temsil etsin>

## Alınan Kararlar

- <neden bu yol seçildi>
- <reddedilen alternatifler ve sebepleri>
- <varsa: gelecekteki fazlara aktarılan açık sorular>

## Karşılaşılan Sorunlar ve Çözümler

- <sorun açıklaması> → <çözüm veya geçici çözüm>
- <bilinmeyen bir davranış keşfedildiyse buraya yaz; MEMORY.md'ye de eklenmeli>

## Test Sonuçları

- <çalıştırılan testler — komut + sonuç>
- <başarısız varsa açıkça belirt; "Tüm testler yeşil" yazmadan önce gerçekten yeşil olduğundan emin ol>
- <runtime doğrulama yapılamadıysa "runtime doğrulama bekliyor: <sebep>" yaz>

## Değişen Dosyalar

- `path/to/file.dart` — <yapılan değişikliğin tek cümlelik özeti>
- `path/to/another.py` — <...>

## ROADMAP / MEMORY / QA Güncellemeleri

- **ROADMAP.md:** Faz NN [x] işaretlendi; sıradaki faz <NN+1> 🟡 Aktif yapıldı.
- **MEMORY.md:** <eklenen kalıcı öğrenim varsa>
- **QA_REPORTS.md:** <çözülen QA item ID'leri, yeni eklenenler>

## Sonraki Faza Notlar

- <bir sonraki fazı yapacak kişi/AI için uyarılar>
- <açık işler, ertelenen iyileştirmeler>
- <bu fazda dokunulmayan ama dikkat edilmesi gereken alanlar>
```

---

## Dolulu örnek

```markdown
# Faz 14.2 Raporu — Form UX Polish (date field, currency, kategori, autovalidate)

- **Tarih:** 2026-05-26
- **Durum:** ✅ Tamamlandı
- **Faz hedefi:** Eklenti formlarındaki UX pürüzlerini gidermek (tarih seçici hizalama, para birimi formatı, autovalidate timing).
- **Bağlı PR / Commit:** 85074e7

## Yapılanlar

- DatePickerField widget'ı theme'le hizalandı (Material 3 colorScheme).
- Currency formatter intl paketi ile lokal tabanlı yazıldı.
- Kategori dropdown'da boş kategori "Diğer" olarak normalize edildi.
- AutoValidate mode `onUserInteraction` yapıldı (önce: `always`).

## Alınan Kararlar

- intl paketini Dart 3 ile uyumlu son sürüme aldık (^0.19.0); alternatif olarak NumberFormat manuel implementasyon değerlendirildi ama lokal desteği için intl tercih edildi.
- AutoValidate'i tamamen kapatmadık — form submit'te yine validate çalışıyor.

## Karşılaşılan Sorunlar ve Çözümler

- intl paketi global locale set edilmemişti → currency formatter İngilizce dönüyordu.
  Çözüm: `main.dart`'ta `Intl.defaultLocale = 'tr_TR'` set edildi.

## Test Sonuçları

- `flutter test` → 47 / 47 yeşil.
- `flutter analyze` → 0 error, 2 info (kabul edilebilir).
- Manuel test: iOS sim + Android emu, formlar test edildi.

## Değişen Dosyalar

- `lib/widgets/date_picker_field.dart` — colorScheme align.
- `lib/utils/currency.dart` — intl-based formatter.
- `lib/screens/add_expense.dart` — autovalidate mode değişti.
- `main.dart` — defaultLocale set.

## ROADMAP / MEMORY / QA Güncellemeleri

- **ROADMAP.md:** Faz 14.2 [x] işaretlendi; Faz 14.3 🟡 Aktif yapıldı.
- **MEMORY.md:** "intl Intl.defaultLocale set etmeden currency formatter güvenilmez" notu eklendi.
- **QA_REPORTS.md:** QA-104 (currency yanlış formatı) kapandı.

## Sonraki Faza Notlar

- Faz 14.3'te loading button state için `submit` async pattern'i tekrar ele alınacak.
- AutoValidate mode değişikliği başka formları etkileyebilir — Quick Add ekranında manuel test gerekli.
```

---

## Kurallar

1. **Şablonun tüm bölümleri var olsun** — bilgi yoksa "Yok" veya "Uygulanamaz" yaz, atlama.
2. **"Tüm testler yeşil"** demeden önce **gerçekten** yeşil olduğunu doğrula. Yoksa "runtime doğrulama bekliyor" yaz.
3. **MEMORY.md'ye eklenen öğrenimler raporda da görünsün** — iz sürülebilirlik için.
4. **Faz raporu = sonuç dosyası**; commit'ten önce yazılır, commit ile birlikte gider.
