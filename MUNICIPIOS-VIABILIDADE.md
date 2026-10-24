# Mapa por município — viabilidade

Conferido no TSE em 24/10/2026, de madrugada (só leitura, arquivos públicos de `resultados.tse.jus.br`).
**Decisão:** fazer como **sistema à parte**, aberto por um botão **Municípios** no painel.
**Atualização 24/10, manhã:** o Nei pediu para fazer já, no mesmo repo e com deploy separado.
Feito em `municipios/` (ver `municipios/README.md`): rodando localmente (porta 8471) para validação.
A publicação no Cloudflare e o botão no painel ficam para depois da validação.

## Resumo

**É viável.** O TSE publica o resultado de cada cidade em 2026 e um índice por estado que diz quais
cidades mudaram. O 1º turno (eleição 6257), já 100% apurado, serve de base de teste com dados reais.
O que falta é o desenho dos municípios (malha do IBGE), que não temos hoje.

## O que existe no TSE (testado)

| Arquivo | Caminho (base `oficial/ele2026/<eleição>/`) | Resultado |
|---|---|---|
| Lista de municípios | `config/mun-e006258-cm.json` | 200, ~530 KB. 28 grupos (27 UFs + exterior `zz`), **5.757 locais**, cada um com código TSE (`cd`), **código IBGE (`cdi`)**, nome e zonas |
| Índice por estado | `dados/<uf>/<uf>-e006258-ab.json` | 200. SP: 646 itens (645 cidades + o estado), ~480 KB, **~9 KB com gzip**. Por cidade: hora da totalização (`dt/ht`), seções totalizadas (`s.st`, `s.pst`), eleitorado (`e`). **Não traz votos** |
| Resultado da cidade | `dados/<uf>/<uf><cod>-c0001-e006258-u.json` | 200, ~3 KB no 2º turno (9 KB no 1º). Mesmo formato do arquivo do estado: votos por candidato (`vap`, `pvap`), brancos, nulos, abstenção, seções |
| 1º turno por cidade | mesmo caminho com `e006257` | 200. Ex.: São Paulo capital, 100% apurado, Lula 46,58% e Flávio 42,13% dos válidos |
| Formatos de 2022 (`-v.json`, `-f.json`) | — | 404. Não existem mais |

O cache do TSE é igual ao que o coletor já usa: `max-age` de 7 a 60 s, `ETag` e `Last-Modified`.
Ou seja, dá para pedir só o que mudou.

Maiores estados: MG 853 cidades, SP 645, RS 497, BA 417. DF é 1. O exterior (`zz`, ~187 locais) não entra no mapa.

## Como funcionaria

1. **Coletor próprio** (serviço separado, ex.: `eleicoes-municipios`), sem tocar no coletor oficial.
   A cada 15–30 s, pede os 27 índices por estado (com ETag, ~9 KB cada com gzip). Baixa o `-u.json`
   **só das cidades cuja hora mudou**.
2. **Carga no TSE:** a noite toda dá ~5.570 arquivos × ~3 KB ≈ 17 MB, mais os índices. Fica no mesmo
   nível do que já fazemos, só que espalhado.
3. **Saída agregada por estado:** um arquivo por UF com todas as cidades (código IBGE, % apurado,
   votos e % de cada candidato). São 27 arquivos, não 5.570. Isso mantém a publicação no Cloudflare
   rápida (hoje 59 arquivos levam ~20 s) e longe do limite de arquivos.
4. **Mapa:** malha municipal do IBGE simplificada, **um arquivo por estado**, que não muda. É baixado
   uma vez e fica em cache. O código IBGE (`cdi`) do TSE liga a cidade ao desenho sem tabela extra.
   - Cinza = 0% apurado. Vermelho ou azul = quem lidera, com a cor mais forte conforme o % apurado
     ou a margem (a decidir), seguindo as cores dos candidatos do painel.
5. **Lista ao lado:** as 10 maiores cidades por eleitorado, com troca para "mais apuradas" ou "já 100%".
6. **Ligação com o painel:** só um botão **Municípios** no menu, levando para `/municipios/`
   (ou um subdomínio). Se o sistema de municípios cair, o painel oficial não é afetado.

## Riscos e pontos a decidir

- **Malha do IBGE:** o jeito oficial é a API de malhas do IBGE (`servicodados.ibge.gov.br`).
  **Pela regra do projeto, usar qualquer API precisa da autorização do Nei.** Alternativa: arquivos
  GeoJSON prontos de repositórios públicos no GitHub, que precisam ser conferidos antes de usar.
- **Tamanho no celular:** em MG e SP as cidades ficam minúsculas. Precisa de zoom e toque, e de
  teste em tela pequena.
- **Conferência dos números:** regra nova "soma das cidades = estado", só como **aviso** durante a
  apuração (igual a Brasil × UFs). A fonte da verdade continua sendo o arquivo oficial do estado.
- **Simulação pública:** precisa de dados fictícios por cidade (regra: nomes fictícios na simulação pública).
- **Peso da página:** carregar só o estado escolhido, nunca o Brasil inteiro de uma vez.

## Esforço estimado

| Parte | Esforço |
|---|---|
| Coletor de municípios + arquivo agregado por UF | ~0,5 dia |
| Preparar malhas (simplificar, um arquivo por UF) | ~0,5 dia |
| Página do mapa + lista de 10 + cores | ~1 dia |
| Testes com o 1º turno, celular, simulação fictícia | ~0,5 dia |
| **Total** | **~2–3 dias** |

## Impacto

- **Fazer:** dá o que o painel ainda não tem (ver a própria cidade) e o efeito visual mais
  compartilhável. Continua útil depois da eleição. Custa ~2–3 dias e um serviço a mais para vigiar.
- **Não fazer:** nada muda no painel atual. Quem quiser ver a própria cidade vai para outro site (G1, app do TSE).
- **Fazer depois da eleição:** com os dados finais do 2º turno e do 1º turno, vira um mapa de
  consulta. Sem a pressão do ao vivo, e sem risco para o domingo.
