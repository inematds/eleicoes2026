# INEMA Elections 2026 — live vote count

[![Live vote count](guia/assets/banner-en.jpg)](https://inematds.github.io/eleicoes2026/guia/en/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## What it is

INEMA Elections 2026 is an open dashboard for following the count of the presidential runoff using official data from the TSE (Brazil's Superior Electoral Court). It is for anyone who wants to see the results for Brazil and for each state on a map, with no made-up numbers. A collector fetches the TSE's public files every 15 seconds, checks the sums, and publishes ready-made files; the site only reads those files. To follow along, just open eleicoes.inema.club; to run your own, all you need is Python 3.

- **Live dashboard:** https://eleicoes.inema.club · accelerated simulation: **Simulação** (Simulation) button in the menu (or `?sim=1`)
- **📖 User guide** (landing page + step by step): **https://inematds.github.io/eleicoes2026/guia/en/**

Independent dashboard, not affiliated with the TSE.

Two separate parts, linked only by the contract's JSON files:

| Part | Folder | Does |
|---|---|---|
| 1. Data | `coleta/` | reads the TSE, stores the raw data, checks, consolidates and publishes versioned JSON |
| Contract | `contrato/README.md` | JSON format (schema 1), rules for each number, blocks |
| 2. Presentation | `site/` | `index.html` (Central, default) and `classica.html`; never accesses the TSE |
| 3. Municipalities (separate) | `municipios/` | own collector, map and site, city by city; never touches the dashboard — see `municipios/README.md` |

Initial analysis and decisions: `ANALISE.md`. Fixed failures: `FALHAS.md`.

## 🏗️ How it was built (and why it handles millions)

A single collector reads the TSE and writes versioned files; the files sit on Cloudflare's edge; the browser
only reads those files. None of our servers sits in the path of visitors, so the number of people changes neither the
load on the TSE nor on our machine. From the first commit to the live dashboard took about 37 hours. Scale, costs,
the backup VPS, the one-command switchover and the techniques used:

- **Page:** https://inematds.github.io/eleicoes2026/guia/arquitetura/en/
- **Full document:** [`ARQUITETURA.md`](ARQUITETURA.md) (in Portuguese)

## The process, start to finish

🧠 session with Nei · ⚙️ script/service · 🤖 `claude -p`

1. ⚙️ **Collector on** (permanent service, restarts on its own):
   `systemctl --user status eleicoes-coletor` — every 15 s it asks the TSE for the index
   `oficial/ele2026/6258/dados/br/br-e006258-ab.json` (with ETag; nothing new = 304).
   Before the opening (the TSE only releases results at 5 p.m. Brasília time, including abroad) the collectors stay
   stopped; the `eleicoes-religar-17h` timer starts `eleicoes-coletor` + `eleicoes-municipios` on the day at 17:00
   (`systemctl --user list-timers eleicoes-religar-17h`; to start by hand: `systemctl --user start eleicoes-coletor eleicoes-municipios`).
   At 16:00 the `eleicoes-desliga-sim-16h` timer turns off the simulations (country and municipalities): `modo.sh oficial`,
   stops `eleicoes-simpub` (the public `/simulacao/` stays frozen) and `municipios/simulacao.sh parar`.
2. ⚙️ **Detects changes**: compares the date/time/sections of each scope (BR, 27 states, abroad)
   with the last one published and downloads only the `-u.json` of those that changed.
3. ⚙️ **Stores the raw data** in `saida/oficial/bruto/<abr>/` + log in `saida/oficial/coleta.jsonl`.
4. ⚙️ **Checks** (contract): sums add up, sections/votes never decrease, time doesn't go backwards,
   correct election/round. If it fails → **does not publish** that scope and keeps the last valid one.
   Brazil ≠ sum of the states during the count = warning only (the TSE doesn't release everything at once).
5. ⚙️ **Publishes** to `saida/oficial/data/`: immutable `uf/<uf>/vNNNNNN.json` → history →
   `latest.json` last. Official versions start at 100001 and are never repeated.
6. ⚙️ **Site** (`eleicoes-web`, port 8470) reads `site/data/` every 15 s and downloads only what changed.
7. 🧠 **Switch simulation ↔ official**: `ferramentas/modo.sh oficial` (or `sim`).
   With no argument it shows the current mode. Anyone with the page open reloads.
8. 🧠 **Monitor during the night**: `cat saida/oficial/status.json` (last ok, errors, blocks,
   pending) and `journalctl --user -u eleicoes-coletor -f`.
9. 🧠 **State stuck by a block** (e.g., the TSE corrected a number downward): check
   `coleta.jsonl` and, if the official data is right, `touch saida/oficial/aceitar/<abr>` (valid once).
10. ⚙️ **Publish to the internet** (eleicoes.inema.club, Cloudflare): service `eleicoes-publicar`
    (`ferramentas/publicar_cf.py --laco`) sends on every change — see `ANALISE.md` §4–5.
11. ⚙️ **Municipalities (separate system)**: service `eleicoes-municipios` reads the 27 per-state indexes
    and downloads only the cities that changed; local site `eleicoes-municipios-web` (port 8471).
    Monitor: `cat saida/municipios/status.json`. Details: `municipios/README.md`.
12. ⚙️ **Publish the municipalities**: service `eleicoes-municipios-publicar`
    (`municipios/publicar_mun.py --laco 20`) sends to municipios.inema.club (separate Worker) on every change.
14. ⚙️ **Visit counter** (both sites): `contador.js` in each one's Worker (Durable Object), only at
    `/api/acessos`; the page adds 1 per browser session and shows it in the sidebar (on mobile, in the title row).
    Read: `python3 -c "import urllib.request;print(urllib.request.urlopen('https://eleicoes.inema.club/api/acessos').read())"`.
13. 🧠 **Link with the dashboard**: the "Municípios" menu item and the "Ver os municípios de <estado>" button on the state card
    lead to the same state on municipios.inema.club (with `?sim=1` in the simulation).
15. ⚙️ **Share button** (`site/compartilhar.js`): below Simulation in the menu; on mobile, in the title row.
    Browser-only (the device's share menu or copies the link, without `?sim=1`), no server and no cost.
16. ⚙️ **Source and audit** (`#fonte` section of the Central): the on-screen data with a link to the TSE file, times,
    version and sha256 (`auditoria()` in `site/central.js`), plus how we fetch it, what we check and how to verify.
17. ⚙️ **INEMA Projection** (menu "Projeção", `site/projecao.html`): service `eleicoes-projecao`
    (`projecao/projetar.py --laco 60`, reads local files only) estimates the 1st→2nd round vote transfer
    in the cities already closed (country → region → state → size → profile) and projects the ones still missing; it writes
    `saida/oficial/data/projecao.json`, which the publisher carries along. It turns on with ≥250 closed cities, ≥15 per
    region, ≥3 in 20 states and ≥1% of the electorate; range = uncertainty of the rates + deviation of the missing cities,
    with a floor set by the worst error in the tests. Calibration: `python3 projecao/calibracao.py saida/backtest2022/bruto 14`
    (224 scenarios, the range contained the final result in 98.7%). Each published projection goes into `data/projecao-historico.json`
    (append-only; chart of the night) and, when complete, into `saida/projecao-log.jsonl`. It also computes "what is needed for the comeback".
    "Ver por estado" button: projection and range for each state (floor by % of the state's closed electorate,
    `PISO_UF` in `projetar.py`, measured over 6,048 cases: coverage 95.5%); below 1% or <3 cities = "unstable".
    Test: `python3 projecao/backtest_2022.py saida/backtest2022/bruto` (TSE 2022 open data in
    `saida/backtest2022/bruto/{partido,detalhe}`). No opinion polls; in the simulation, it does not appear.

## Tests

```bash
# Real 1st round (final data, 12 candidates): 29 published, 0 blocks; 2nd cycle = 304
python3 coleta/coletor.py --saida saida/teste1t --eleicao 6257 --turno 1 --pleito 3220 --n-cand 0 --uma-vez

# Fake TSE with deliberate failures (index before the files, BR delayed, SP corrupted, RJ decreasing)
python3 coleta/servidor_local.py --pasta saida/tsefalso --porta 8471 &
python3 coleta/simular.py --saida saida/simlixo/data --intervalo 6 --uma-vez --modo-tse saida/tsefalso &
python3 coleta/coletor.py --saida saida/testemock --base http://127.0.0.1:8471/ --intervalo 3
```

## Simulation

`coleta/simular.py` generates a made-up count (real names or `--ficticio`), with each UF's electorate,
turnout, blank and null votes taken from the 1st round. Everything comes out as `fonte.tipo =
"simulacao"`: the site shows a banner and watermark **SIMULAÇÃO** (SIMULATION), and never marks "Eleito" (Elected).

## Map

`site/assets/mapa-br.json` (14 KB gzip) generated by `ferramentas/gerar_mapa.py` from
`brazil-states.geojson` (click_that_hood, MIT; IBGE mesh).
