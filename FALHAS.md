# FALHAS — eleicoes2026

| data | o que quebrou | menor correção | prompt \| infra |
|---|---|---|---|
| 2026-10-24 | Marca d'água SIMULAÇÃO aparecia com dado oficial (CSS display:grid vencia o atributo hidden) | `[hidden]{display:none!important}` nas duas folhas; conferido nos dois modos | infra |
| 2026-10-24 | Um JSON corrompido do TSE derrubaria o ciclo inteiro do coletor | erro tratado por abrangência (trava só aquele estado) | infra |
| 2026-10-24 | Quadradinho do RS mostrou números da simulação antiga (88/99) | simulador começa cada rodada numa faixa de versões nova (rodada × 1000); contrato diz que versão nunca se repete | infra |
| 2026-10-24 | Cores dos candidatos não apareceram no navegador de teste (CSS antigo em cache) | servidor local manda no-cache + `?v=N` no CSS/JS | infra |
