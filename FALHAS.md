# FALHAS — eleicoes2026

| data | o que quebrou | menor correção | prompt \| infra |
|---|---|---|---|
| 2026-10-25 | Municípios: ~468 cidades presas em "aguardando" com o TSE já fechado — CDN entregava a cópia vazia (sem hora) e o coletor aceitava como resolvida | arquivo sem hora quando o índice já tem hora = cópia velha (espera); estado das cidades limpo e coletor reiniciado | infra |
| 2026-10-25 | Hora de atualização de AC (−2 h) e AM/RR/RO/MT/MS (−1 h) aparecia no fuso local do estado, não em Brasília | `_iso(d, h, abr)` soma o atraso do fuso (tabela `FUSO_ATRAS`) | infra |
| 2026-10-25 | Noite do 2º turno: total Brasil (e Exterior) não publicava — índice do TSE traz br/zz com hora local do exterior (26/10 09:05), arquivo parecia "mais velho que o índice" para sempre | hora do índice no futuro (>10 min) é ignorada; estado br/zz limpo e coletor reiniciado aqui e na VPS4 | infra |
| 2026-10-25 | Reserva na VPS: nginx devolvia 403 em data/*.json (mkstemp grava 600; só funcionava aqui porque quem publica é o mesmo usuário) | `os.chmod(tmp, 0o644)` no `_grava_atomico` | infra |
| 2026-10-25 | Espera "até 17:00" dispararia às 14h na VPS (fuso UTC) | horário com fuso explícito (`-0300`) no `espera_ate.sh` | infra |
| 2026-10-24 | Municípios (revisão): eleitorado do índice preliminar sobrescrevia o da cidade já apurada → 27 estados republicados a cada 15 s com número errado | índice só preenche eleitorado/seções enquanto a cidade não tem arquivo | infra |
| 2026-10-24 | Municípios (revisão): índice atualizado depois do arquivo faria baixar a mesma cidade para sempre | mesmo arquivo + hora publicada ≥ hora do índice = resolvido; teto de 8 tentativas | infra |
| 2026-10-24 | Municípios: com a fila ordenada só pelo tamanho, cidade pequena nunca seria baixada enquanto as grandes mudassem (simulação: fila só crescia) | fila por tempo de espera, tamanho só desempata | infra |
| 2026-10-24 | Municípios: ao reiniciar, o coletor esquecia as cidades na fila (índice voltava 304) e dava "0 pendentes" falso | não reaproveitar ETag dos índices na partida (relê os 27) | infra |
| 2026-10-24 | Municípios: coletor caía na partida se a lista de municípios do TSE não viesse | tenta de novo a cada 15 s em vez de sair | infra |
| 2026-10-24 | Marca d'água SIMULAÇÃO aparecia com dado oficial (CSS display:grid vencia o atributo hidden) | `[hidden]{display:none!important}` nas duas folhas; conferido nos dois modos | infra |
| 2026-10-24 | Um JSON corrompido do TSE derrubaria o ciclo inteiro do coletor | erro tratado por abrangência (trava só aquele estado) | infra |
| 2026-10-24 | Quadradinho do RS mostrou números da simulação antiga (88/99) | simulador começa cada rodada numa faixa de versões nova (rodada × 1000); contrato diz que versão nunca se repete | infra |
| 2026-10-24 | Cores dos candidatos não apareceram no navegador de teste (CSS antigo em cache) | servidor local manda no-cache + `?v=N` no CSS/JS | infra |
