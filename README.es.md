# INEMA Elecciones 2026 — conteo en vivo

[![Conteo en vivo](guia/assets/banner-es.jpg)](https://inematds.github.io/eleicoes2026/guia/es/)

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

## Qué es

INEMA Elecciones 2026 es un panel abierto para seguir el conteo de la segunda vuelta para Presidente de Brasil con los datos oficiales del TSE (Tribunal Superior Electoral, el órgano que organiza las elecciones en Brasil). Sirve para quien quiere ver el resultado de Brasil y de cada estado en un mapa, sin cifras inventadas. Un colector busca los archivos públicos del TSE cada 15 segundos, verifica las cuentas y publica archivos listos; el sitio solo lee esos archivos. Para seguirlo, basta con abrir eleicoes.inema.club; para ejecutar el tuyo, solo necesitas Python 3.

- **Panel en línea:** https://eleicoes.inema.club · simulación acelerada: botón **Simulación** en el menú (o `?sim=1`)
- **📖 Guía de uso** (landing + paso a paso): **https://inematds.github.io/eleicoes2026/guia/es/**

Panel independiente, sin vínculo con el TSE.

Dos partes separadas, unidas solo por los archivos JSON del contrato:

| Parte | Carpeta | Hace |
|---|---|---|
| 1. Datos | `coleta/` | lee el TSE, guarda el original, verifica, consolida y publica JSON versionado |
| Contrato | `contrato/README.md` | formato de los JSON (schema 1), reglas de cada cifra, bloqueos |
| 2. Presentación | `site/` | `index.html` (Central, predeterminada) y `classica.html`; nunca accede al TSE |
| 3. Municipios (aparte) | `municipios/` | colector, mapa y sitio propios, ciudad por ciudad; no toca el panel — ver `municipios/README.md` |

Análisis inicial y decisiones: `ANALISE.md`. Fallas corregidas: `FALHAS.md`.

## El proceso, de principio a fin

🧠 sesión con Nei · ⚙️ script/servicio · 🤖 `claude -p`

1. ⚙️ **Recolector encendido** (servicio permanente, vuelve solo):
   `systemctl --user status eleicoes-coletor` — cada 15 s pide al TSE el índice
   `oficial/ele2026/6258/dados/br/br-e006258-ab.json` (con ETag; sin novedad = 304).
   Antes de la apertura (el TSE solo divulga a las 17h de Brasilia, incluido el exterior) los recolectores permanecen
   detenidos; el timer `eleicoes-religar-17h` enciende `eleicoes-coletor` + `eleicoes-municipios` ese día a las 17:00
   (`systemctl --user list-timers eleicoes-religar-17h`; encender a mano: `systemctl --user start eleicoes-coletor eleicoes-municipios`).
   A las 16:00 el timer `eleicoes-desliga-sim-16h` apaga las simulaciones (país y municipios): `modo.sh oficial`,
   detiene `eleicoes-simpub` (el `/simulacao/` público queda congelado) y `municipios/simulacao.sh parar`.
2. ⚙️ **Detecta cambios**: compara fecha/hora/secciones de cada ámbito (BR, 27 UFs, exterior)
   con lo último publicado y descarga solo el `-u.json` de quien cambió.
3. ⚙️ **Guarda el bruto** en `saida/oficial/bruto/<abr>/` + registro en `saida/oficial/coleta.jsonl`.
4. ⚙️ **Verifica** (contrato): las sumas cuadran, secciones/votos nunca disminuyen, la hora no retrocede,
   elección/turno correctos. Si falla → **no publica** ese ámbito y mantiene la última versión válida.
   Brasil ≠ suma de las UFs durante el escrutinio = solo aviso (el TSE no libera todo junto).
5. ⚙️ **Publica** en `saida/oficial/data/`: `uf/<uf>/vNNNNNN.json` inmutables → historial →
   `latest.json` al final. Las versiones oficiales empiezan en 100001 y nunca se repiten.
6. ⚙️ **Sitio** (`eleicoes-web`, puerto 8470) lee `site/data/` cada 15 s y descarga solo lo que cambió.
7. 🧠 **Cambiar simulación ↔ oficial**: `ferramentas/modo.sh oficial` (o `sim`).
   Sin argumento muestra el modo actual. Quien tenga la página abierta la recarga.
8. 🧠 **Seguimiento en la noche**: `cat saida/oficial/status.json` (último ok, errores, bloqueos,
   pendientes) y `journalctl --user -u eleicoes-coletor -f`.
9. 🧠 **Estado trabado por bloqueo** (ej.: el TSE corrigió un número a la baja): verificar en
   `coleta.jsonl` y, si el dato oficial es correcto, `touch saida/oficial/aceitar/<abr>` (vale 1 vez).
10. ⚙️ **Publicar en internet** (eleicoes.inema.club, Cloudflare): servicio `eleicoes-publicar`
    (`ferramentas/publicar_cf.py --laco`) envía en cada cambio — ver `ANALISE.md` §4–5.
11. ⚙️ **Municipios (sistema aparte)**: servicio `eleicoes-municipios` lee los 27 índices por estado
    y descarga solo las ciudades que cambiaron; sitio local `eleicoes-municipios-web` (puerto 8471).
    Seguimiento: `cat saida/municipios/status.json`. Detalles: `municipios/README.md`.
12. ⚙️ **Publicar los municipios**: servicio `eleicoes-municipios-publicar`
    (`municipios/publicar_mun.py --laco 20`) envía a municipios.inema.club (Worker separado) en cada cambio.
14. ⚙️ **Contador de accesos** (los dos sitios): `contador.js` en el Worker de cada uno (Durable Object), solo en
    `/api/acessos`; la página suma 1 por sesión del navegador y lo muestra en la barra lateral (en el celular, en la línea del título).
    Leer: `python3 -c "import urllib.request;print(urllib.request.urlopen('https://eleicoes.inema.club/api/acessos').read())"`.
13. 🧠 **Vínculo con el panel**: el ítem "Municípios" del menú y el botón "Ver los municípios de <estado>" en la tarjeta
    del estado llevan al mismo estado en municipios.inema.club (con `?sim=1` en la simulación).
15. ⚙️ **Botón Compartir** (`site/compartilhar.js`): debajo de la Simulación en el menú; en el celular, en la línea del
    título. Solo en el navegador (menú de compartir del dispositivo o copia el enlace, sin `?sim=1`), sin servidor ni costo.
16. ⚙️ **Fuente y auditoría** (sección `#fonte` de la Central): dato de la pantalla con enlace al archivo del TSE, horarios,
    versión y sha256 (`auditoria()` en `site/central.js`), además de cómo lo obtenemos, qué verificamos y cómo verificarlo.
17. ⚙️ **Proyección INEMA** (menú "Projeção", `site/projecao.html`): servicio `eleicoes-projecao`
    (`projecao/projetar.py --laco 60`, solo lee archivos locales) estima la transferencia de votos 1.º→2.º turno
    en las ciudades ya cerradas (país → región → estado → tamaño → perfil) y proyecta las que faltan; graba
    `saida/oficial/data/projecao.json`, que el publicador lleva junto. Se activa con ≥250 ciudades cerradas, ≥15 por
    región, ≥3 en 20 estados y ≥1% del electorado; banda = incertidumbre de las tasas + desvío de las ciudades que faltan,
    con piso según el peor error de las pruebas. Calibración: `python3 projecao/calibracao.py saida/backtest2022/bruto 14`
    (224 escenarios, la banda contuvo el resultado final en 98,7%). Cada proyección publicada entra en `data/projecao-historico.json`
    (solo se agrega; gráfico de la noche) y, completa, en `saida/projecao-log.jsonl`. También calcula "lo que falta para la vuelta".
    Botón "Ver por estado": proyección y banda de cada estado (piso por % del electorado del estado cerrado,
    `PISO_UF` en `projetar.py`, medido en 6.048 casos: cobertura 95,5%); por debajo de 1% o <3 ciudades = "inestable".
    Prueba: `python3 projecao/backtest_2022.py saida/backtest2022/bruto` (datos abiertos del TSE 2022 en
    `saida/backtest2022/bruto/{partido,detalhe}`). Sin encuestas de opinión; en la simulación, no aparece.

## Pruebas

```bash
# primera vuelta real (datos finales, 12 candidatos): 29 publicados, 0 bloqueos; 2º ciclo = 304
python3 coleta/coletor.py --saida saida/teste1t --eleicao 6257 --turno 1 --pleito 3220 --n-cand 0 --uma-vez

# TSE falso con fallas a propósito (índice antes que los archivos, BR atrasado, SP corrupto, RJ disminuyendo)
python3 coleta/servidor_local.py --pasta saida/tsefalso --porta 8471 &
python3 coleta/simular.py --saida saida/simlixo/data --intervalo 6 --uma-vez --modo-tse saida/tsefalso &
python3 coleta/coletor.py --saida saida/testemock --base http://127.0.0.1:8471/ --intervalo 3
```

## Simulación

`coleta/simular.py` genera un conteo inventado (nombres reales o `--ficticio`), con padrón,
participación, votos en blanco y nulos de cada UF tomados de la primera vuelta. Todo sale como `fonte.tipo =
"simulacao"`: el sitio muestra una franja y la marca de agua **SIMULAÇÃO**, y nunca marca "Eleito" (electo).

## Mapa

`site/assets/mapa-br.json` (14 KB gzip) generado por `ferramentas/gerar_mapa.py` a partir de
`brazil-states.geojson` (click_that_hood, MIT; malla del IBGE).
