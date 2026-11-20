# Faz Raporu Şablonu ve Brif

Faz raporunu **`faz-arsivcisi`** yazar; ana oturum ona kanıtları brifler. Dosya: `.claude/archives/PHASE_NN_<konu>.md` (NN iki haneli: `PHASE_07_...`; alt faz `PHASE_12_3_...`; konu snake_case, Türkçe karakter yok). Projedeki `.claude/archives/PHASE_TEMPLATE.md` esastır (projeye özel bölüm eklenmiş olabilir); yoksa skill şablonu `assets/templates/PHASE_TEMPLATE.md`.

`.claude/archives/` config `bundle.sync_dirs` içinde olduğundan raporlar Drive/NotebookLM'e otomatik gider (etkinse).

## faz-arsivcisi'ne brif (örnek)

```text
MOD: ARŞİV
FAZ: 14.2 — Form UX polish
YAPILANLAR: DatePickerField theme hizalandı; currency formatter intl ile; kategori boşsa "Diğer"; autovalidate onUserInteraction.
DEĞİŞEN DOSYALAR: lib/widgets/date_picker_field.dart (colorScheme) · lib/utils/currency.dart (intl formatter) · lib/screens/add_expense.dart (autovalidate) · lib/main.dart (defaultLocale)
TESTER: ✅ flutter test 47/47; flutter analyze 0 error 2 info; manuel iOS sim + Android emu
REVIEWER: ONAY (1 düşük bulgu düzeltildi: null kategori)
KARARLAR: intl ^0.19 seçildi, manuel NumberFormat reddedildi (lokal desteği) → ADR aday
AÇIK/KAPANAN: QA-104 kapandı; OPEN yok
ACI DERS (MEMORY): Intl.defaultLocale set edilmeden currency formatter güvenilmez
SONRAKİ FAZA: Faz 14.3 submit async pattern; autovalidate değişikliği Quick Add'de manuel test ister
COMMIT: henüz yok
```

## Şablon

Bkz. `assets/templates/PHASE_TEMPLATE.md`. Bölümler: başlık ve meta (Tarih, Durum, Faz hedefi, Commit) · Yapılanlar · **Ajanlar ve sonuçları** (tablo) · Alınan Kararlar (→ ADR-NNN) · Karşılaşılan Sorunlar ve Çözümler · Test Sonuçları · Değişen Dosyalar · Belge Güncellemeleri · Sonraki Faza Notlar.

## Kurallar

1. Şablonun tüm bölümleri bulunur; bilgi yoksa "Yok" / "Uygulanamaz". Atlanmaz.
2. "Tüm testler yeşil" yalnızca tester raporunda sayı varsa; yoksa "runtime doğrulama bekliyor: <sebep>".
3. Durum: ✅ yalnızca tester yeşil **ve** reviewer ONAY; aksi ⚠️ Kısmi (neden).
4. MEMORY'ye giden öğrenim raporda da görünür (iz sürülebilirlik).
5. Rapor commit'ten önce yazılır, commit ile gider. Faz raporu olmayan faz kapanmış sayılmaz.
