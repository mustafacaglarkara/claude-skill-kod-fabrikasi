# Katkıda Bulunma

Bu skill kişisel iş akışından çıktı; başkalarının kullanımı/iyileştirmesi memnuniyetle karşılanır. Fork, issue, PR — hepsi açık.

---

## Hızlı Yönlendirme

| Ne istiyorsun? | Nereye |
| --- | --- |
| Skill'i kullanmak | [README.md](README.md) → Hızlı Başlangıç |
| Sürüm geçmişini görmek | [CHANGELOG.md](CHANGELOG.md) |
| Bug bildirmek | GitHub Issue aç — repro + log + workaround belirt |
| Yeni özellik önerisi | GitHub Issue aç ("enhancement" etiketi) — kullanım senaryosunu yaz |
| Kod katkısı | PR aç — aşağıdaki konvansiyonlara uy |

---

## Geliştirme Kurulumu

```bash
# Skill'i kendi makinene yereldeki ile bağla (test için)
git clone https://github.com/mustafacaglarkara/claude-skill-kod-fabrikasi.git ~/.claude/skills/kod-fabrikasi
cd ~/.claude/skills/kod-fabrikasi

# Bir test projesinde init.sh çalıştır
cd /tmp && mkdir test-proje && cd test-proje
git init
bash ~/.claude/skills/kod-fabrikasi/scripts/init.sh
```

İlk olarak [references/tuzaklar.md](references/tuzaklar.md)'yi oku — 10 kritik tuzak. Hiçbirini tetiklemediğinden emin ol.

---

## Pull Request Sözleşmesi

### Klasör konvansiyonu (v2.0)

- Skill içindeki referans dosyalar `references/` altında, scripts `scripts/` altında, örnek dosyalar `assets/` altında.
- Yeni özellik için yeni klasör eklemeden önce mevcut yapıya sığıp sığmadığını düşün.
- **Kök dizine yeni `.md` ekleme** — README/LICENSE/CHANGELOG/CONTRIBUTING dışında yenisi root'ta olmamalı.

### Skill yapı kuralı

- `SKILL.md` frontmatter formatı: `name`, `description` (pushy + trigger keyword'lerle dolu), `allowed-tools`. Anthropic Agent Skills spec'ine uyumlu.
- "İlk Kontrol" bloğu skill her devreye girdiğinde çalışmalı — proje durumunu kontrol eder.
- "ASLA YAPMA" tuzak listesi: yeni tuzak öğrenildikçe ekle, hiç sileme.

### Backward compatibility

- v1 (root-bazlı) yapıyı destekleyen kod düşürülmeden tutulmalı. Bir kullanıcının eski projesi en az 1 minor version daha çalışmalı.
- Breaking change → MAJOR version artışı + CHANGELOG'da net migration rehberi.

### Test (skill içi)

- Skill'in kendisinin pubspec/test'i yok (saf .md + script). Test = manuel:
  1. Boş bir test projesinde `init.sh` çalıştır → klasörler oluşmalı, config doğru üretilmeli
  2. `make setup-hooks` → hook'lar kurulmalı
  3. Sahte bir kayıt commit at → post-commit graphify + bundle çalışmalı
  4. NotebookLM web'de kaynakların güncellendiğini gör

### Commit mesajı

- Conventional Commits önerilir: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`.
- Bir satır özet (50 karakter altı tercih edilir).
- Önemli değişiklik varsa boş satır + paragraf açıklama.

---

## Proje Felsefesi

1. **Önce onay, sonra kod** — Skill kullanıcının iş akışını dikte etmez, onaylanan plana göre çalışır. PR'lar da kullanıcı geri bildirimine uyumlu olmalı.
2. **Tuzaklar SİLİNMEZ** — Geçmiş hatalardan damıtılan `references/tuzaklar.md` zamanla zenginleşir, küçülmez. Yeni öğrenilen tuzak varsa **ekle**.
3. **Config-driven** — Yeni özellik eklerken: hardcoded path/değer mi yoksa config alanı mı? Config'te tutulabiliyorsa orada tut.
4. **Türkçe öncelikli** — Skill içeriği Türkçe (kullanıcı tabanı Türk). İngilizce'ye genişletmek istersen `references/en/` gibi paralel dizin aç, ana içeriği değiştirme.

---

## Soru/Destek

- GitHub Issue ile temasa geç.
- Hızlı sohbet için PR'ın "Discussion" bölümünü kullan.

Teşekkürler — her katkı değerli. 🛠️
