# Karar Kayıtları (ADR) — {{PROJECT_NAME}}

Tasarımı değiştiren her seçim bir ADR'dir: bağlam, karar, sonuç. Değişirse eskisi silinmez, "Geçersiz (ADR-NNN ile değişti)" olarak işaretlenir ve yeni kayıt eklenir. Yalnızca `faz-arsivcisi` yazar. Hook son ADR başlığını her oturuma yükler; başlık biçimi `## ADR-NNN: başlık` olmalı.

Kalıcı öğrenimler ve acı dersler buraya değil `.claude/context/MEMORY.md` dosyasına gider.

---

## ADR-001: Geliştirme Kod Fabrikası faz disipliniyle yürütülür

**Tarih:** {{DATE}}
**Durum:** Kabul edildi

**Bağlam.** Çok oturumlu, AI destekli geliştirmede bağlam kaybı ve onaysız değişiklik en büyük risk.

**Karar.** Her iş fazlara bölünür; akış bağlam → plan → kullanıcı onayı → `gelistirici` → `tester` → `reviewer` → `faz-arsivcisi` → commit. Kodu yazan ajan kendi işini onaylamaz. Planlama belgelerini yalnızca `faz-arsivcisi` günceller.

**Sonuç.** Her faz PROGRESS.md kaydı, faz raporu ve (gerekirse) ADR ile kapanır. Onaysız kod değişikliği yapılmaz.
