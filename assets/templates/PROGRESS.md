# İlerleme — {{PROJECT_NAME}}

Her oturum başında okunur (SessionStart hook'u otomatik yükler), her adım/faz sonunda `faz-arsivcisi` günceller. Tarih formatı YYYY-MM-DD. Başlık adlarını DEĞİŞTİRME: hook `## Durum`, `## Günlük`, `## Sıradaki adım` başlıklarını okur.

## Durum

| Faz | Durum | Başlangıç | Bitiş | Not |
| --- | --- | --- | --- | --- |
| 0 Keşif ve kurulum | Devam ediyor | {{DATE}} | | Kod Fabrikası v3 kuruldu |

Durum değerleri: Başlamadı · Devam ediyor · Kısmen bitti (neden) · Bitti (kanıt: "N test yeşil, reviewer ONAY").

## Günlük

- {{DATE}} Kod Fabrikası v3 kuruldu: ajanlar, faz hafızası hook'u, izin kuralları, planlama belgeleri.

## Sıradaki adım

1. Faz 0 keşfini tamamla: test komutlarını çalıştırıp doğrula, riskli alanları config'e işle.
2. İlk kod haritasını üret ve ilk ADR'yi yaz.
