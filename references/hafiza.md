# Proje Hafızası: Belgeler ve SessionStart Hook'u

Hafıza `.claude/` altında, git'in izlediği düz Markdown'dur. Yalnızca `faz-arsivcisi` yazar (format tutarlı kalır). Konumlar config `phase_files` ile değişebilir; hook ve `kf.py` oradan okur.

## Dosyalar ve rolleri (karışmasın)

| Dosya | Rol | Ne DEĞİL |
| --- | --- | --- |
| `archives/ROADMAP.md` | Fazlar, öncelik (P0/P1/P2), ölçülebilir **bitti ölçütü** | İlerleme günlüğü değil; bitti ölçütü kullanıcı onayı olmadan değişmez |
| `archives/PROGRESS.md` | `## Durum` tablosu, `## Günlük` (`- YYYY-MM-DD ...`), `## Sıradaki adım` | Karar kaydı değil |
| `decisions/DECISIONS.md` | ADR: `## ADR-NNN: başlık` · Tarih · Durum · Bağlam · Karar · Sonuç. Eski karar silinmez, "Geçersiz (ADR-MMM ile değişti)" | Öğrenim/tuzak listesi değil (o MEMORY) |
| `decisions/OPEN_QUESTIONS.md` | `## OPEN-NNN: soru` · Bloke ettiği faz · Neden · Seçenekler. Cevaplanınca silinir → ADR'ye taşınır, "Kapananlar" satırına numarası | Bug listesi değil (o KNOWN_BUGS) |
| `decisions/FAZ_PROMPT.md` | Projeye özel faz ekleri (test komutları, canlı komutlar, riskli alanlar) | Akışın kendisi değil (o skill'de) |
| `context/MEMORY.md` | Acı dersler, kalıcı kalıplar: "X'i Y olmadan yapma çünkü Z oldu" | Karar değil |
| `context/GRAPHIFY_NOTES.md` | Haritadan çıkan insan/AI yorumları: en bağlı modüller, refactor adayları | Otomatik rapor değil (o `graphify-out/GRAPH_REPORT.md`) |
| `references/QA_REPORTS.md` | `QA-NNN` kalite bulguları, son test paketi durumu | — |
| `references/KNOWN_BUGS.md` | `BUG-NNN` yeniden üretilebilen hatalar, geçici çözüm, planlanan faz | — |
| `archives/PHASE_NN_<konu>.md` | Faz raporu (şablon `PHASE_TEMPLATE.md` birebir) | — |
| `archives/NOTEBOOKLM_SUMMARY.md` | ~30 satır güncel özet (NotebookLM için) | — |

Başlık adlarını değiştirme: hook `## Durum`, `## Günlük`, `## Sıradaki adım`, `## OPEN-NNN:`, `## ADR-NNN:` kalıplarını okur. Mevcut projede başlıklar farklıysa `.claude/hooks/faz_hafiza.py` içindeki `bolum(...)` çağrılarını uyarla, belgeleri yeniden adlandırma.

## SessionStart hook'u (`.claude/hooks/faz_hafiza.py`)

- `settings.json` → `hooks.SessionStart`, matcher `startup|resume|clear|compact`: yeni oturum, `/resume`, `/clear` ve bağlam sıkıştırması sonrası çalışır. stdout Claude'un bağlamına girer.
- Çıktı: Durum tablosu (≤20 satır), son günlük tarihi ve son 3 madde, Sıradaki adım (≤15), açık soru başlıkları (≤10), son ADR ve toplam, son 5 commit ve commit edilmemiş dosya sayısı, bir satır kural hatırlatması. PROGRESS yoksa ROADMAP'ten aktif maddeler.
- Her zaman exit 0; hata olsa bile oturumu bozmaz. `.env` okumaz. Komut `python_bin` tam yolu ile yazılır (hook PATH'i sınırlı).
- Test: `python .claude/scripts/kf.py status` (aynı çıktı) ya da `CLAUDE_PROJECT_DIR=$(pwd) python .claude/hooks/faz_hafiza.py; echo $?`.
- Çıktı uzuyorsa PROGRESS "Günlük" bölümünü kısaltmayın; hook zaten yalnızca son gün maddelerini alır. Durum tablosunu 20 satır altında tutun (eski fazları tek satırda özetleyin).

## Kullanıcı "nerede kalmıştık?" dediğinde

Hook çıktısı yeterliyse ona göre özetle; değilse `faz-arsivcisi`'ne "yalnızca oku ve özetle: aktif faz, sıradaki adım, bloke eden OPEN'lar, son 3 ADR" brifi ver. Faz başlatma değildir; onay istemez.

## Obsidian ile düzenleme (isteğe bağlı)

`kf.py sync` kasada `Proje` adıyla `.claude/` klasörüne junction/symlink kurar; kasada düzenlenen belge doğrudan projeye yazılır ve git görür. Obsidian nokta ile başlayan klasörleri göstermediği için ad `Proje`. Kasa düzenlemeleri de "faz-arsivcisi yazar" kuralının dışındadır: kullanıcı elle yazıyorsa format başlıklarını korusun.
