# Faz Çalışma Promptu — {{PROJECT_NAME}}

Tetikleyici: "FAZ_PROMPT'u oku ve sıradaki fazı başlat." / "Faz N'i başlat." / "Sıradaki faz."

Akışın tamamı `kod-fabrikasi` skill'indedir (`references/workflow.md`). Bu dosya yalnızca projeye özel ekleri taşır:

## Projeye özel kurallar

- Framework: {{FRAMEWORK}}
- Test komutları:
{{TEST_COMMANDS}}
- Canlıya yazan / onay isteyen komutlar (ajanlar çalıştırmaz):
{{LIVE_WRITE_COMMANDS}}
- Yüksek riskli alanlar (reviewer + guvenlik-inceleyici zorunlu): {{HIGH_RISK_AREAS}}

## Faz başlatma kontrol listesi

1. `.claude/archives/ROADMAP.md` → ilk `[ ]` / 🟡 faz.
2. Bağlam: PROGRESS, DECISIONS (ilgili ADR), OPEN_QUESTIONS (bloke eden var mı?), MEMORY, QA_REPORTS, KNOWN_BUGS; gerekirse `kesifci` ve `graphify query`.
3. Plan sun: adımlar, `dosya:satır`, riskler, geri alma, kabul kriterleri, hangi ajan hangi parçayı alır.
4. **Onay bekle.** Onaysız koda dokunma.
