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

Análisis inicial y decisiones: `ANALISE.md`. Fallas corregidas: `FALHAS.md`.

## El proceso, de principio a fin

🧠 sesión con Nei · ⚙️ script/servicio · 🤖 `claude -p`

1. ⚙️ **Colector activo** (servicio permanente, se reinicia solo):
   `systemctl --user status eleicoes-coletor` — cada 15 s le pide al TSE el índice
   `oficial/ele2026/6258/dados/br/br-e006258-ab.json` (con ETag; sin novedades = 304).
2. ⚙️ **Detecta cambios**: compara fecha/hora/secciones de cada ámbito (BR, 27 UF, exterior)
   con lo último publicado y descarga solo el `-u.json` de los que cambiaron.
3. ⚙️ **Guarda el original** en `saida/oficial/bruto/<abr>/` + registro en `saida/oficial/coleta.jsonl`.
4. ⚙️ **Verifica** (contrato): las sumas cuadran, las secciones/votos nunca disminuyen, la hora no retrocede,
   elección/vuelta correctas. Si falla → **no publica** ese ámbito y mantiene el último válido.
   Brasil ≠ suma de las UF durante el conteo = solo aviso (el TSE no lo publica todo a la vez).
5. ⚙️ **Publica** en `saida/oficial/data/`: `uf/<uf>/vNNNNNN.json` inmutables → historial →
   `latest.json` al final. Las versiones oficiales empiezan en 100001 y nunca se repiten.
6. ⚙️ **Sitio** (`eleicoes-web`, puerto 8470) lee `site/data/` cada 15 s y descarga solo lo que cambió.
7. 🧠 **Cambiar simulación ↔ oficial**: `ferramentas/modo.sh oficial` (o `sim`).
   Sin argumento muestra el modo actual. Quien tenga la página abierta la recarga.
8. 🧠 **Seguimiento durante la noche**: `cat saida/oficial/status.json` (último ok, errores, bloqueos,
   pendientes) y `journalctl --user -u eleicoes-coletor -f`.
9. 🧠 **Estado trabado por un bloqueo** (ej.: el TSE corrigió una cifra a la baja): revisar en
   `coleta.jsonl` y, si el dato oficial es correcto, `touch saida/oficial/aceitar/<abr>` (vale 1 vez).
10. 🧠 **Publicar en internet** (eleicoes.inema.club, Cloudflare): pendiente de autorización
    de la API de Cloudflare — ver `ANALISE.md` §4–5.

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
