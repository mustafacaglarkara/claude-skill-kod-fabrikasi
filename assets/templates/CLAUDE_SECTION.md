## Alt ajanlar ve proje hafızası (Kod Fabrikası v3)

Ana oturum orkestratördür: işi böler, alt ajanı kendisi seçer (`.claude/agents/`), sonuçları birleştirir, kullanıcıya raporlar. Kullanıcının ajan adı söylemesi gerekmez. Ajanlar konuşmayı görmez; brif tek kaynaklarıdır.

| Durum | Ajan |
| --- | --- |
| "X nerede, Y'yi kim çağırıyor" (çok dosyalı, salt okunur soru) | `kesifci` (dosya:satır verir; brif hazırlarken kullan) |
| Onaylanmış planın dosyaları çakışmayan bağımsız parçası | `gelistirici` (paralel, aynı anda en fazla {{MAX_PARALLEL}}) |
| Kod değişti → derleme / test / tip denetimi | `tester` (zorunlu; kodu düzeltmez) |
| Adım/faz bitmeden, commit'ten önce bağımsız inceleme | `reviewer` (zorunlu; salt okunur; donmuş diff alır) |
| PROGRESS / DECISIONS / OPEN_QUESTIONS / ROADMAP / MEMORY / QA / faz raporu | `faz-arsivcisi` (planlama belgelerine yalnızca o yazar) |
{{OPTIONAL_ROWS}}
{{EXPERT_ROWS}}

**Faz akışı:** bağlam → plan → **kullanıcı onayı** → `gelistirici` → `tester` → `reviewer` → `faz-arsivcisi` → commit (yalnızca kullanıcı isterse).

Kurallar:
- Küçük işler (birkaç dosya okuma, tek düzenleme) ajansız yapılır. Kodu yazan ajan kendi işini onaylamaz.
- Brif eksiksiz olur: mod, hedef, `dosya:satır`, kapsam dışı, alınan kararlar, kabul kriterleri, koşulacak testler, paralel ajanların dokunduğu dosyalar, cevap şekli. Yeni iş → yeni ajan; aynı ajana ikinci görev verilmez.
- Başarısızlıkta aynı brif aynı ajana tekrar gönderilmez; bir kademe yükseltilir (`gelistirici` → `mimar`).
- Yüksek riskli alanlar: {{HIGH_RISK_AREAS}}. Bunlara dokunan değişiklik `reviewer` (+ varsa `guvenlik-inceleyici`) onayı olmadan bitmez.
- Ajan raporu doğrulanmadan kullanıcıya aktarılmaz; bir inceleme notu koda bakılarak teyit edilir.
- Commit, push ve canlıya yazan komutlar yalnızca kullanıcı isterse. `.env` okunmaz; sır gerekirse kullanıcıya ne ekleyeceği söylenir.
- `SessionStart` hook'u (`.claude/hooks/faz_hafiza.py`) PROGRESS durumunu, sıradaki adımı, açık soruları ve son commit'leri her oturuma yükler.
- Komutlar: `python .claude/scripts/kf.py <check|status|bundle|graphify|end-phase|selftest>`. `graphify query "<soru>"` kod haritası için `Grep`'ten önce gelir.
{{PROFILE_SECTION}}
