# Análise do PROMPT MESTRE — INEMA Eleições Live 2026

Data: 24/10/2026 (madrugada). Segundo turno: **domingo 25/10/2026**. Faltam ~1,5 dia.
Fonte analisada: `PROMPT_MESTRE_INEMA_ELEICOES_LIVE.md` (clipboard).
Destino decidido pelo Nei: **`eleicoes.inema.club`** (não mais `aventuras.inema.club/eleicoes/`).

Legenda: ✅ verificado agora · ⚠️ hipótese · ❗ decisão necessária

---

## 1. Veredito curto

O prompt é bom como plano de produto de longo prazo, mas **não cabe no prazo**. Ele pede 12 documentos de planejamento antes da primeira linha de código, e a eleição é amanhã. Recomendação: cortar para um MVP de 1 dia (seção 6) e deixar o resto do prompt como roadmap para 2028.

A boa notícia: os dados do TSE de 2026 estão no ar, com os códigos e candidatos do 2º turno já publicados, e o 1º turno completo serve de base de teste.

---

## 2. O que foi verificado no TSE (24/10/2026)

| Item | Resultado |
|---|---|
| ✅ Config geral | `https://resultados.tse.jus.br/oficial/comum/config/ele-c.json` (200) |
| ✅ Pleito 2º turno | `3221`, data 25/10/2026, ciclo `ele2026` |
| ✅ Presidente 2º turno | eleição **6258**, abrangência `br`, cargo `1` |
| ✅ Governador 2º turno | eleição **6260**, cargo `3`, **só 6 UFs**: AC, AM, DF, ES, RN, TO |
| ✅ 1º turno (para teste) | federal **6257** (totalizado 100%, dados finais) |
| ✅ Arquivo de resultado | `oficial/ele2026/6258/dados/<uf>/<uf>-c0001-e006258-u.json` (~9 KB) |
| ✅ Índice de abrangências | `oficial/ele2026/6258/dados/br/br-e006258-ab.json` (~27 KB, 29 abrangências: BR + 27 UFs + exterior) com seções, eleitorado e hora de cada UF |
| ✅ Municípios (config) | `oficial/ele2026/6258/config/mun-e006258-cm.json` (~530 KB) |
| ✅ Candidatos no arquivo | FLAVIO NANTES BOLSONARO (22) e LUIZ INÁCIO LULA DA SILVA (13), zerados |
| ✅ Cache do TSE | `Cache-Control: max-age` entre 6 e 58 s, com `ETag` e `Last-Modified` |
| ❗ Mudança de formato | O caminho de 2022 (`dados-simplificados/...-r.json`) **dá 404** em 2026. Agora é `dados/...-u.json`, com estrutura nova (`carg → agr → par → cand`, blocos `s` seções, `e` eleitorado, `v` votos). Código feito para 2022 não serve. |
| ⚠️ EA14/EA15/EA20 | Não conferi os nomes oficiais dos leiautes; a documentação técnica do TSE precisa ser lida para mapear os campos. |

Campos úteis já vistos no `-u.json`: `dg/hg` (data/hora de geração), `dt/ht` (hora da totalização), `s.st/s.pst` (seções totalizadas), `e.te` (eleitorado), `v.tv` (total), `v.vv` (válidos), `v.vb` (brancos), nulos, e por candidato `vap` (votos) e `pvap` (% válidos). Os números vêm como **texto com vírgula** (`"47,03"`) e há versão numérica (`pvapn`). Usar sempre o valor bruto e o oficial; nunca recalcular por cima.

### Sobre 15 segundos

- O próprio CDN do TSE usa `max-age` de até ~60 s. Consultar a cada 15 s é razoável **se** for só o índice `ab.json` (27 KB) e um pedido condicional (`If-None-Match`/ETag), baixando os `-u.json` apenas das UFs cuja hora mudou.
- 28 arquivos × 9 KB a cada 15 s ≈ 17 KB/s. Carga desprezível para o TSE.
- A latência real até o visitante fica em ~15–60 s (cache do TSE + coleta + cache do nosso site). Não prometer 15 s.

---

## 3. Problemas no prompt original

1. **Prazo.** 7 fases e 12 documentos não cabem em 1,5 dia. O caminho crítico é: coletor → JSON → página → publicação → teste com o 1º turno.
2. **"27 painéis estaduais" de governador não existe.** Só 6 UFs têm 2º turno para governador. Os 27 painéis fazem sentido para **presidente por UF**.
3. **Hospedagem estática:** o domínio original planejado servia um site dinâmico (com login). Cada acesso de 15 em 15 s passaria pelo código do site e esbarraria em limites de requisições. ✅ Por isso o painel ficou num subdomínio próprio, servido como arquivos estáticos.
4. **Mapas municipais e IA no MVP.** O próprio prompt já os tira do MVP; manter assim.
5. **VPS nova.** Para amanhã, montar e endurecer uma VPS é risco extra. O coletor pode rodar nesta máquina (é leve) com uma segunda máquina de reserva. ⚠️ Depende de a rede daqui ficar estável no domingo.
6. **SQLite vs PostgreSQL.** SQLite basta com folga (alguns milhares de snapshots). Ou só arquivos JSON versionados em disco.

---

## 4. Arquitetura recomendada para `eleicoes.inema.club`

```
TSE (resultados.tse.jus.br)
   │  a cada 15 s: ab.json com ETag → só os -u.json que mudaram
   ▼
Coletor + consolidador (1 script, nesta máquina, systemd)
   │  guarda bruto + hash · valida · gera JSON compacto versionado
   ▼
Cloudflare R2 (bucket público com domínio eleicoes.inema.club/data/*)
   │  v00125.json imutáveis (cache longo) · latest.json (cache 10 s)
   ▼
Cloudflare Pages (HTML/CSS/JS estático, publicado UMA vez)
   ▼
Visitante: lê latest.json a cada 15 s, baixa só o que mudou
```

Por que essa divisão:

- **Pages** para o site: requisições estáticas ilimitadas e grátis. Mas o Free tem limite de ~500 publicações por mês, então **não dá para publicar dados pelo Pages** a cada 15 s.
- **R2** para os dados: upload a qualquer frequência. Com cache do Cloudflare na frente, quase nada chega ao R2. Leituras do R2 no Free: 10 milhões por mês.
- Arquivos versionados com cache longo e `latest.json` publicado por último, como o prompt pede. Correto.

Carga estimada (só `latest.json`, ~1 KB):

| Visitantes simultâneos | Pedidos/s na borda | Situação |
|---|---|---|
| 10 mil | ~670 | tranquilo |
| 100 mil | ~6.700 | tranquilo (cache) |
| 500 mil | ~33.000 | ⚠️ Cloudflare aguenta cache hit; testar antes |

---

## 4.1 Separação: dados × apresentação (decisão do Nei, 24/10/2026)

Duas partes independentes, ligadas **só pelos arquivos JSON publicados** (o contrato).

| | **Parte 1 — Dados** (coleta + processamento) | **Parte 2 — Apresentação** |
|---|---|---|
| Faz | lê TSE, guarda bruto, valida, consolida, publica JSON | lê os JSON e desenha os painéis |
| Roda em | máquina/VPS (systemd) | navegador do visitante (site estático) |
| Sabe do TSE? | sim, é a única que sabe | **não** — nunca acessa o TSE |
| Sabe de tela? | não | sim |
| Pasta | `coleta/` | `site/` |
| Publica em | `eleicoes.inema.club/data/` (R2) | `eleicoes.inema.club/` (Pages) |
| Testa com | 1º turno 6257 (dados reais finais) | arquivos de exemplo em `site/fixtures/` |

O que o contrato define (arquivo `contrato/` com esquema + exemplos):

- `data/latest.json` — manifesto: versão atual de cada abrangência, hora oficial, hora da coleta, estado (`parcial`/`final`).
- `data/br/vNNNNN.json` e `data/uf/<uf>/vNNNNN.json` — resultado já consolidado: seções, eleitorado, comparecimento, abstenção, brancos, nulos, válidos, candidatos (votos + % válidos), tudo com o valor oficial e a origem.
- `data/historico/<abr>.json` — série da evolução (uma linha por versão).
- Campo `schema: 1` em todos. Mudança que quebra = `schema: 2`, e a apresentação recusa versão que não conhece.

Regras:

1. A apresentação **não calcula** nada que o TSE publica pronto; só formata. Derivados (diferença entre candidatos, por exemplo) vêm marcados como `derivado` no próprio JSON.
2. A Parte 1 pode cair, trocar de máquina ou ser reescrita sem mexer no site, desde que mantenha o contrato.
3. A Parte 2 pode ganhar mapa, modo TV etc. sem mexer na coleta.
4. Em 2028, só a Parte 1 muda (novos códigos/formato do TSE).

Ordem de trabalho: **contrato primeiro** (esquema + 3 exemplos tirados do 1º turno). Depois as duas partes andam em paralelo.

---

## 5. O que precisa de autorização sua (regra de API)

- ✅ **Cloudflare:** autorizado em 24/10/2026. Publicação em `eleicoes.inema.club` como arquivos estáticos (ver `README.md`).
- O acesso ao TSE é leitura pública de arquivos, sem chave. Já usei hoje para esta verificação.

---

## 6. MVP proposto para domingo (ordem do caminho crítico)

1. **Coletor** (Python, sem dependências): lê `ab.json` com ETag, baixa os `-u.json` de BR + 27 UFs (presidente) + 6 UFs (governador), salva bruto com hash e hora.
   Pronto quando: rodando contra o 1º turno (6257), gera 28 arquivos e não baixa nada repetido quando nada muda.
2. **Consolidador**: extrai seções, eleitorado, comparecimento, abstenção, brancos, nulos, válidos e votos/% por candidato, **só valores oficiais**. Checagens que bloqueiam a publicação: soma dos candidatos = válidos; válidos + brancos + nulos = total; seções nunca diminuem; hora nunca volta.
   Pronto quando: os números do 1º turno batem 100% com o arquivo oficial.
3. **Publicador**: grava `vNNNNN.json` → confere que o arquivo responde → publica `latest.json`. Mantém o último válido se algo falhar.
4. **Página única**: placar Brasil, barra 100% (votos computados com brancos e nulos), % de válidos em separado, seções totalizadas, grade das 27 UFs (mapa em cartograma de quadradinhos, sem geometria), clique abre a UF, gráfico simples da evolução. Visual INEMA (`inema-design/DESIGN.md`) com **duas cores neutras para os candidatos**, nenhuma em amarelo da marca.
5. **Ensaio geral**: "replay" com snapshots falsos derivados do 1º turno (0% → 100%) para testar atualização e tela.
6. **Domingo**: coletor ligado às 16h30, apuração começa ~17h (horário de Brasília), monitorar o log e ter uma pessoa olhando.

Fica para depois: mapa municipal, histórico com replay público, modo TV, compartilhamento por cidade, narração, VPS dedicada, os 12 documentos.

---

## 7. Decisões que preciso de você

- ❗ Autoriza o uso da API do Cloudflare (R2 + Pages + DNS de `eleicoes.inema.club`)?
- ❗ Coletor nesta máquina (mais rápido) ou numa VPS (mais seguro, mais trabalho)?
- ❗ Incluir governador das 6 UFs no MVP ou só presidente?
- ❗ Repositório: `inematds/eleicoes2026` (nome da pasta, autor inematds)?
- ❗ Separação: um repo com pastas `contrato/`, `coleta/`, `site/` (mais simples) ou dois repos?
