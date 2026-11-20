# Yol Haritası — {{PROJECT_NAME}}

Fazlar ve her fazın ölçülebilir "bitti" ölçütü. Durum işaretleri PROGRESS.md ile uyumlu tutulur; "Bitti ölçütü" yalnızca kullanıcı onayıyla değişir.

## Faz Durumu Özeti

| Faz | Başlık | Durum | Öncelik |
| --- | --- | --- | --- |
| 0 | Keşif ve kurulum | 🟡 Aktif | P0 |
| 1 | <başlık> | [ ] | P0 |
| 2 | <başlık> | [ ] | P1 |

Öncelik: P0 = yayını bloke eder · P1 = beklenen · P2 = cila.

---

## Faz 0: Keşif ve kurulum

**Hedef.** Projenin yapısı, çalışan komutlar ve riskli alanlar anlaşılır; Kod Fabrikası kurulu ve `selftest` yeşil.

**Adımlar.**
1. Uygulamalar, framework sürümleri, çalışan test/derleme komutları doğrulanır.
2. Yüksek riskli alanlar ve canlıya yazan komutlar `kod-fabrikasi.config.json` içine işlenir.
3. İlk kod haritası (`graphify update .`) üretilir, en bağlı modüller `GRAPHIFY_NOTES.md` içine not edilir.

**Bitti ölçütü.** `kf.py selftest` FAIL vermiyor; PROGRESS.md "Durum" tablosu dolu; ilk ADR yazılmış.

---

## Faz 1: <başlık>

**Hedef.** ...

**Adımlar.**
1. ...

**Bitti ölçütü.** ... (ölçülebilir: "N test yeşil", "uç nokta X 200 döner", "ekran Y 320px'te yatay kaydırma yapmaz")

**Riskler / bağımlılıklar.** ...
