# INEMA Eleições 2026 — apuração ao vivo

[![Apuração ao vivo](guia/assets/banner.jpg)](https://inematds.github.io/eleicoes2026/guia/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## O que é

O INEMA Eleições 2026 é um painel aberto para acompanhar a apuração do 2º turno para Presidente com os dados oficiais do TSE (Tribunal Superior Eleitoral). Serve para quem quer ver o resultado do Brasil e de cada estado num mapa, sem números inventados. Um coletor busca os arquivos públicos do TSE a cada 15 segundos, confere as contas e publica arquivos prontos; o site só lê esses arquivos. Para acompanhar, basta abrir eleicoes.inema.club; para rodar o seu, você só precisa de Python 3.

- **Painel no ar:** https://eleicoes.inema.club · simulação acelerada: botão **Simulação** no menu (ou `?sim=1`)
- **📖 Guia de uso** (landing + passo a passo): **https://inematds.github.io/eleicoes2026/guia/**

Painel independente, sem vínculo com o TSE.

Duas partes separadas, ligadas só pelos arquivos JSON do contrato:

| Parte | Pasta | Faz |
|---|---|---|
| 1. Dados | `coleta/` | lê o TSE, guarda o bruto, confere, consolida e publica JSON versionado |
| Contrato | `contrato/README.md` | formato dos JSON (schema 1), regras de cada número, bloqueios |
| 2. Apresentação | `site/` | `index.html` (Central, padrão) e `classica.html`; nunca acessa o TSE |
| 3. Municípios (à parte) | `municipios/` | coletor, mapa e site próprios, cidade por cidade; não toca no painel — ver `municipios/README.md` |

Análise inicial e decisões: `ANALISE.md`. Falhas corrigidas: `FALHAS.md`.

## O processo, do início ao fim

🧠 sessão com o Nei · ⚙️ script/serviço · 🤖 `claude -p`

1. ⚙️ **Coletor ligado** (serviço permanente, volta sozinho):
   `systemctl --user status eleicoes-coletor` — a cada 15 s pede ao TSE o índice
   `oficial/ele2026/6258/dados/br/br-e006258-ab.json` (com ETag; sem novidade = 304).
   Antes da abertura (TSE só divulga às 17h de Brasília, inclusive o exterior) os coletores não consultam o TSE:
   `eleicoes-coletor` e `eleicoes-municipios` têm o drop-in `espera-17h.conf` (`ferramentas/espera_ate.sh`,
   cópia em `ferramentas/systemd/`), que segura a partida até 25/10 17:00 — vale também se o servidor reiniciar.
   Às 16:00 o timer permanente `eleicoes-desliga-sim.timer` (Persistent: roda no boot se a máquina estava
   desligada) desliga as simulações (país e municípios), põe o site local em modo oficial e congela o `/simulacao/`.
   Reinício do servidor: todos os serviços `eleicoes-*` são `enabled` e o usuário tem linger, então voltam sozinhos.
2. ⚙️ **Detecta mudança**: compara data/hora/seções de cada abrangência (BR, 27 UFs, exterior)
   com o último publicado e baixa só o `-u.json` de quem mudou.
3. ⚙️ **Guarda o bruto** em `saida/oficial/bruto/<abr>/` + log em `saida/oficial/coleta.jsonl`.
4. ⚙️ **Confere** (contrato): somas fecham, seções/votos nunca diminuem, hora não volta,
   eleição/turno certos. Falhou → **não publica** aquela abrangência e mantém a última válida.
   Brasil ≠ soma das UFs durante a apuração = só aviso (o TSE não solta tudo junto).
5. ⚙️ **Publica** em `saida/oficial/data/`: `uf/<uf>/vNNNNNN.json` imutáveis → histórico →
   `latest.json` por último. Versões oficiais começam em 100001 e nunca se repetem.
6. ⚙️ **Site** (`eleicoes-web`, porta 8470) lê `site/data/` a cada 15 s e baixa só o que mudou.
7. 🧠 **Trocar simulação ↔ oficial**: `ferramentas/modo.sh oficial` (ou `sim`).
   Sem argumento mostra o modo atual. Quem estiver com a página aberta recarrega.
8. 🧠 **Acompanhar na noite**: `cat saida/oficial/status.json` (último ok, erros, bloqueios,
   pendentes) e `journalctl --user -u eleicoes-coletor -f`.
9. 🧠 **Estado travado por bloqueio** (ex.: TSE corrigiu um número para baixo): conferir no
   `coleta.jsonl` e, se o dado oficial estiver certo, `touch saida/oficial/aceitar/<abr>` (vale 1 vez).
10. ⚙️ **Publicar na internet** (eleicoes.inema.club, Cloudflare): serviço `eleicoes-publicar`
    (`ferramentas/publicar_cf.py --laco`) envia a cada mudança — ver `ANALISE.md` §4–5.
11. ⚙️ **Municípios (sistema à parte)**: serviço `eleicoes-municipios` lê os 27 índices por estado
    e baixa só as cidades que mudaram; site local `eleicoes-municipios-web` (porta 8471).
    Acompanhar: `cat saida/municipios/status.json`. Detalhes: `municipios/README.md`.
12. ⚙️ **Publicar os municípios**: serviço `eleicoes-municipios-publicar`
    (`municipios/publicar_mun.py --laco 20`) envia a municipios.inema.club (Worker separado) a cada mudança.
14. ⚙️ **Contador de acessos** (os dois sites): `contador.js` no Worker de cada um (Durable Object), só em
    `/api/acessos`; a página soma 1 por sessão do navegador e mostra na lateral (no celular, na linha do título).
    Ler: `python3 -c "import urllib.request;print(urllib.request.urlopen('https://eleicoes.inema.club/api/acessos').read())"`.
13. 🧠 **Ligação com o painel**: item "Municípios" no menu e botão "Ver os municípios de <estado>" no card
    do estado levam ao mesmo estado em municipios.inema.club (com `?sim=1` na simulação).
15. ⚙️ **Botão Compartilhar** (`site/compartilhar.js`): abaixo da Simulação no menu; no celular, na linha do
    título. Só no navegador (menu de compartilhar do aparelho ou copia o link, sem `?sim=1`), sem servidor nem custo.
16. ⚙️ **Fonte e auditoria** (seção `#fonte` da Central): dado da tela com link para o arquivo do TSE, horários,
    versão e sha256 (`auditoria()` em `site/central.js`), mais como buscamos, o que conferimos e como conferir.
17. ⚙️ **Projeção INEMA** (menu "Projeção", `site/projecao.html`): serviço `eleicoes-projecao`
    (`projecao/projetar.py --laco 60`, só lê arquivos locais) estima a transferência de votos 1º→2º turno
    nas cidades já encerradas (país → região → estado → porte → perfil) e projeta as que faltam; grava
    `saida/oficial/data/projecao.json`, que o publicador leva junto. Liga com ≥250 cidades encerradas, ≥15 por
    região, ≥3 em 20 estados e ≥1% do eleitorado; faixa = incerteza das taxas + desvio das cidades que faltam,
    com piso pelo pior erro dos testes. Calibração: `python3 projecao/calibracao.py saida/backtest2022/bruto 14`
    (224 cenários, faixa conteve o final em 98,7%). Cada projeção publicada entra em `data/projecao-historico.json`
    (só acrescenta; gráfico da noite) e, completa, em `saida/projecao-log.jsonl`. Também calcula "o que falta para a virada".
    Botão "Ver por estado": projeção e faixa de cada estado (piso por % do eleitorado do estado encerrado,
    `PISO_UF` em `projetar.py`, medido em 6.048 casos: cobertura 95,5%); abaixo de 1% ou <3 cidades = "instável".
    Cada estado tem uma linha com a evolução da sua projeção na noite (o histórico guarda `ufs` a cada cálculo).
18. ⚙️ **Reserva operacional na VPS4** (mkt3, 62.238.25.84, `/opt/eleicoes2026`, instalada por
    `ferramentas/vps/instalar.sh`): coletores próprios (versões a partir de 500001, esperam 17:00 -0300), projeção e
    nginx servindo os dois sites com os mesmos caches. Já responde em **https://eleicoes2026.inema.club** e **https://municipios2026.inema.club** (DNS A com
    proxy no Cloudflare). Em pane daqui: apontar `eleicoes.inema.club` (e `municipios.inema.club`) para 62.238.25.84
    no Cloudflare — com um comando: `ferramentas/vps/trocar_dominios.sh vps --executar` (sem argumento mostra os comandos) (para os publicadores
    daqui, solta os domínios dos Workers e cria CNAME com proxy para eleicoes2026/municipios2026); volta com
    `... trocar_dominios.py volta --executar`; ver onde está com `... status`; sem `--executar` só simula. Precisa
    desta máquina (login do wrangler + token de DNS) ou de `CF_TOKEN` com Workers e DNS. Atualizar: `ferramentas/vps/instalar.sh vps` (sem argumento mostra os comandos), ou `ssh root@62.238.25.84 'cd /opt/eleicoes2026 && git pull && bash ferramentas/vps/instalar.sh --executar'`.
    Teste: `python3 projecao/backtest_2022.py saida/backtest2022/bruto` (dados abertos do TSE 2022 em
    `saida/backtest2022/bruto/{partido,detalhe}`). Sem pesquisa de opinião; na simulação, não aparece.

## Testes

```bash
# 1º turno real (dados finais, 12 candidatos): 29 publicados, 0 bloqueios; 2º ciclo = 304
python3 coleta/coletor.py --saida saida/teste1t --eleicao 6257 --turno 1 --pleito 3220 --n-cand 0 --uma-vez

# TSE falso com falhas de propósito (índice antes dos arquivos, BR atrasado, SP corrompido, RJ diminuindo)
python3 coleta/servidor_local.py --pasta saida/tsefalso --porta 8471 &
python3 coleta/simular.py --saida saida/simlixo/data --intervalo 6 --uma-vez --modo-tse saida/tsefalso &
python3 coleta/coletor.py --saida saida/testemock --base http://127.0.0.1:8471/ --intervalo 3
```

## Simulação

`coleta/simular.py` gera uma apuração inventada (nomes reais ou `--ficticio`), com eleitorado,
comparecimento, brancos e nulos de cada UF tirados do 1º turno. Tudo sai como `fonte.tipo =
"simulacao"`: o site mostra faixa e marca d'água **SIMULAÇÃO**, e nunca marca "Eleito".

## Mapa

`site/assets/mapa-br.json` (14 KB gzip) gerado por `ferramentas/gerar_mapa.py` a partir de
`brazil-states.geojson` (click_that_hood, MIT; malha IBGE).
