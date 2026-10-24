# Contrato de dados — schema 1

Única ligação entre `coleta/` (produz) e `site/` (consome).
O site **nunca** acessa o TSE e **não recalcula** o que o TSE publica pronto.

Escopo deste projeto: **Presidente, 2º turno 2026** (pleito 3221, eleição 6258, cargo 1).

## Arquivos publicados

```
data/
├── latest.json                 manifesto (cache curto, ~10 s) — publicado POR ÚLTIMO
├── br/v00012.json              resultado imutável (cache longo)
├── uf/<uf>/v00012.json         27 UFs + zz (exterior)
└── historico/<abr>.json        série da evolução (cache curto)
```

`<abr>` = `br`, sigla da UF em minúsculo (`rs`, `sp`, …) ou `zz` (exterior).

## latest.json

```json
{
  "schema": 1,
  "tipo": "manifesto",
  "versao": 12,
  "publicado_em": "2026-10-25T18:42:10-03:00",
  "eleicao": { "pleito": "3221", "eleicao": "6258", "turno": 2, "cargo": 1, "cargo_nome": "Presidente", "ano": 2026 },
  "fonte": { "tipo": "oficial", "orgao": "TSE", "base": "https://resultados.tse.jus.br/oficial/ele2026/6258/" },
  "situacao": "em_andamento",
  "abrangencias": {
    "br": { "versao": 12, "arquivo": "br/v00012.json", "totalizado_tse": "2026-10-25T18:41:30-03:00", "pct_secoes": 87.41, "lider": "13" },
    "rs": { "versao": 9,  "arquivo": "uf/rs/v00009.json", "...": "..." }
  },
  "historico": { "br": "historico/br.json", "rs": "historico/rs.json" }
}
```

- `versao` do manifesto sobe a cada publicação. **Um número de versão nunca é reaproveitado**, nem depois de apagar os dados ou recomeçar: o site guarda cada versão como imutável. Cada abrangência tem sua própria versão (só sobe quando o TSE mudou aquela abrangência).
- `situacao`: `aguardando` (nada apurado) · `em_andamento` · `finalizada`.
- `fonte.tipo`: `oficial` ou `simulacao`. **O site mostra uma faixa "SIMULAÇÃO" sempre que não for `oficial`.**
- `lider`: número do candidato com mais votos, ou `null` se empate/zero. É `derivado` (vem de `derivados.lider`).
- Ordem dos candidatos: sempre pelo número, crescente. A cor segue essa ordem (1º = A verde-água `#0fa89a`, 2º = B violeta `#8e6cf0`) e nunca muda com quem lidera.

## Resultado (`br/vNNNNN.json`, `uf/<uf>/vNNNNN.json`)

```json
{
  "schema": 1,
  "tipo": "resultado",
  "versao": 12,
  "abrangencia": { "tipo": "br", "cd": "br", "nome": "Brasil" },
  "eleicao": { "...": "igual ao manifesto" },
  "fonte": {
    "tipo": "oficial",
    "url": "https://resultados.tse.jus.br/oficial/ele2026/6258/dados/br/br-c0001-e006258-u.json",
    "idg": "3535426",
    "gerado_tse": "2026-10-25T18:41:47-03:00",
    "totalizado_tse": "2026-10-25T18:41:30-03:00",
    "coletado_em": "2026-10-25T18:41:58-03:00",
    "sha256_bruto": "…"
  },
  "situacao": { "andamento": "em_andamento", "parcial": true, "totalizacao_final": false },
  "secoes":     { "total": 499248, "totalizadas": 436400, "pendentes": 62848, "pct_totalizadas": 87.41 },
  "eleitorado": { "total": 158745502, "apurado": 138760000, "comparecimento": 109500000, "abstencao": 29260000,
                  "pct_comparecimento": 78.91, "pct_abstencao": 21.09 },
  "votos":      { "total": 109500000, "validos": 104000000, "brancos": 2000000, "nulos": 3500000,
                  "pct_validos_sobre_total": 94.98, "pct_brancos_sobre_total": 1.83, "pct_nulos_sobre_total": 3.20 },
  "candidatos": [
    { "numero": "13", "nome": "LUIZ INÁCIO LULA DA SILVA", "nome_urna": "LULA", "partido": "PT",
      "votos": 53000000, "pct_validos": 50.96, "eleito": false, "situacao": "" }
  ],
  "derivados": {
    "_aviso": "calculado pelo INEMA a partir dos valores oficiais acima",
    "diferenca_votos": 2000000,
    "diferenca_pp_validos": 1.92,
    "pct_sobre_total": { "13": 48.40, "22": 46.58 },
    "lider": "13"
  }
}
```

### Regras de significado (verificadas no 1º turno, 29 arquivos, 24/10/2026)

| Campo | Origem TSE | Regra conferida |
|---|---|---|
| `secoes.total/totalizadas/pendentes` | `s.ts / s.st / s.snt` | `st + snt = ts` |
| `eleitorado.total` | `e.te` | — |
| `eleitorado.apurado` | `e.esa` | eleitorado das seções já apuradas |
| `comparecimento / abstencao` | `e.c / e.a` | `c + a = esa` (**não** `te`) |
| `pct_comparecimento / pct_abstencao` | `e.pcn / e.pan` | denominador = `esa` |
| `votos.total` | `v.tv` | `tv = e.c` |
| `votos.validos` | `v.vv` | `vv = Σ votos dos candidatos` |
| `votos.brancos` | `v.vb` | — |
| `votos.nulos` | `v.tvn` | `tvn = vn + vnt` (nulos + nulos técnicos); `vv + vb + tvn = tv` |
| `pct_*_sobre_total` | `v.pvvcn / v.pvbn / v.ptvnn` | denominador = `tv` |
| `candidatos[].votos` | `vap` | — |
| `candidatos[].pct_validos` | `pvapn` | denominador = `vv` |
| `br` | arquivo `br` | `br = Σ 27 UFs + zz` em todos os totais |

Percentuais vêm do valor oficial de alta precisão (`…n`, vírgula decimal) convertido para número, arredondado a 2 casas. **Nunca** recalculados.

Duas métricas que o site não pode confundir:
- **% dos votos válidos** (`pct_validos`): o número que decide a eleição.
- **% do total computado** (`derivados.pct_sobre_total` + brancos + nulos): usado só na barra 100%.

Horários: o TSE publica data e hora sem fuso; tratamos como horário de Brasília (`-03:00`). ⚠️ Premissa a confirmar na documentação.

## histórico (`historico/<abr>.json`)

```json
{ "schema": 1, "tipo": "historico", "abrangencia": "br",
  "pontos": [
    { "versao": 1, "totalizado_tse": "…", "pct_secoes": 0.52, "votos_total": 600000,
      "votos": { "13": 290000, "22": 280000 }, "pct_validos": { "13": 50.88, "22": 49.12 } }
  ] }
```

Um ponto por versão publicada daquela abrangência. Só cresce.

## Bloqueios (a coleta não publica a versão se falhar)

1. Alguma regra da tabela acima não fecha.
2. `secoes.totalizadas` ou `votos.total` diminuiu em relação à versão anterior.
3. `totalizado_tse` voltou no tempo.
4. Eleição, turno ou cargo diferente do esperado.
5. `br` deixa de bater com a soma das UFs **na totalização final**. Durante a apuração isso é só aviso no log: o TSE não publica BR e UFs ao mesmo tempo (no 1º turno, `idg`/`hg` do BR e do índice já diferem).

Falhou → mantém o último resultado válido publicado e registra o motivo no log.

## Compatibilidade

- Campo novo é aditivo e não muda o `schema`.
- Mudança que remove ou muda o significado de um campo → `schema: 2`. O site recusa schema que não conhece e mostra "dados em formato novo, atualize a página".
