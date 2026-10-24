# Municípios — apuração cidade por cidade (sistema à parte)

Mapa de cada estado com os municípios desenhados. A cidade começa **cinza** e fica **vermelha ou
azul** (cor de quem lidera) conforme o TSE apura; quanto mais forte a cor, mais seções apuradas.
Ao lado, a lista das 10 cidades: **maiores**, **mais apuradas** ou **100% apuradas**. Busca por nome,
zoom e o quadro completo da cidade escolhida.

É um sistema **separado** do painel oficial: coletor, serviço, pasta de saída, site e Worker do
Cloudflare próprios. Do painel oficial só reaproveita o leitor do formato do TSE e as regras de
conferência (`coleta/nucleo.py`, só leitura). Se este sistema parar, o painel não percebe.

## O processo, do início ao fim

🧠 sessão com o Nei · ⚙️ script/serviço

1. 🧠 **Desenho dos municípios** (uma vez): `python3 municipios/gerar_malhas.py` baixa a malha do
   IBGE (API de malhas v3, qualidade mínima) para `saida/geo/ibge/` e gera
   `municipios/site/assets/malha/<uf>.json` (27 arquivos, ~1,9 MB no total, MG = 268 KB).
   Liga ao TSE pelo código IBGE (`cdi`) da lista oficial `mun-e006258-cm.json`.
2. ⚙️ **Coletor** (`eleicoes-municipios`, volta sozinho): a cada 15 s pede os 27 índices
   `dados/<uf>/<uf>-e006258-ab.json` com ETag. Cidade com 0 seções não é baixada (fica cinza).
3. ⚙️ **Fila**: cidade que mudou vira pendente; baixa até 300 por ciclo, 8 conexões, primeiro quem
   espera há mais tempo (empate: a maior). Arquivo velho do CDN = espera e tenta de novo.
4. ⚙️ **Confere** cada cidade com as regras do contrato (`nucleo.conferir`). Problema = só aquela
   cidade trava com o último valor bom. Liberar: `touch saida/municipios/aceitar/<código TSE>`.
5. ⚙️ **Publica** em `saida/municipios/data/`: um arquivo por estado com todas as cidades
   (`uf/<uf>/vNNNNN.json`, guarda as 6 últimas) e `latest.json` por último.
6. ⚙️ **Site local** (`eleicoes-municipios-web`): http://localhost:8471/ — lê o manifesto a cada
   15 s e baixa só o estado aberto.
7. 🧠 **Acompanhar**: `cat saida/municipios/status.json` (pendentes, bloqueios, erros) e
   `journalctl --user -u eleicoes-municipios -f`.
8. ⚙️ **Publicar** (no ar desde 24/10/2026): serviço `eleicoes-municipios-publicar` roda
   `municipios/publicar_mun.py --laco 20` e envia ao Worker `eleicoes2026-municipios`
   (https://municipios.inema.club). Conferir sem enviar: `python3 municipios/publicar_mun.py --montar`.
   Só publica manifesto oficial do 2º turno; as pastas de teste (`data-1t`, `data-sim`) nunca vão.
9. 🧠 **Botão no painel** (aplicado em 24/10/2026): `municipios/painel-botao.patch` pôs o
   item "Municípios" no menu (Central e Clássica) e o botão "Ver os municípios de <estado>" no card
   do estado; o link leva ao mesmo estado e, na simulação, à simulação. Prévia: porta 8474.
   Já está em `site/`; o arquivo fica como registro da mudança.
10. ⚙️ **Simulação no navegador** (`?sim=1`, botão "Simulação" no menu): apuração inventada de 90 s
   que recomeça sozinha, nomes fictícios, sem servidor. Dados finais por cidade em
   `site/assets/sim/<uf>.json`, gerados por `python3 municipios/gerar_sim.py saida/municipios-1t/data`.

## Testes

```bash
# 1º turno real, 5.571 cidades (~2,5 min). Soma das cidades = resultado oficial nos 27 estados.
python3 municipios/coletor_mun.py --saida saida/municipios-1t --eleicao 6257 --turno 1 --n-cand 0 \
  --uma-vez --max-por-ciclo 600     # repetir até status.json mostrar pendentes 0
# ver: http://localhost:8471/?dados=data-1t

# Simulação acelerada (TSE falso, nomes fictícios, 20 min): cidades saem do cinza e ganham cor
municipios/simulacao.sh            # ou: municipios/simulacao.sh 40   |   municipios/simulacao.sh parar
# ver: http://localhost:8471/?dados=data-sim
```

`?dados=` só aceita pastas locais (`data-1t`, `data-sim`); a publicação nunca leva essas pastas.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `gerar_malhas.py` | IBGE → desenho SVG por estado, confere códigos IBGE × TSE |
| `coletor_mun.py` | coleta, fila, conferência e publicação por estado |
| `simular_tse.py` | TSE falso a partir do 1º turno (só teste) |
| `simulacao.sh` | liga/desliga a simulação local |
| `gerar_sim.py` | resultados finais fictícios por cidade para o `?sim=1` |
| `painel-botao.patch` | registro da mudança que pôs o menu e o botão "Municípios" no painel oficial |
| `publicar_mun.py` | monta e envia ao Worker separado |
| `site/` | `index.html`, `mun.js`, `mun.css`, `menu.css` (cópia do painel), `assets/malha/` |

## Limites conhecidos

- **Boa Esperança do Norte (MT)** está no TSE mas não tem desenho no IBGE (município novo): entra
  na lista e na busca pelo nome do TSE, mas não aparece no mapa.
- **Índice do 2º turno ainda preliminar** (gerado pelo TSE em 09/10): o eleitorado por cidade antes
  da apuração vem incompleto (ex.: capital de SP 2,68 mi, contra 9,1 mi no 1º turno). Quando a
  cidade começa a apurar, os números passam a vir do arquivo dela, que é o oficial.
- A ordem "Maiores" usa o eleitorado do índice; até o TSE atualizá-lo, pode sair diferente do real.
- Sem gesto de pinça no celular: zoom pelos botões + e −.
