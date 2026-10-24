#!/usr/bin/env bash
# Simulação LOCAL do mapa de municípios (nomes fictícios, números inventados a partir do 1º turno).
#   municipios/simulacao.sh [minutos]   → recomeça do zero (padrão 20 min de apuração)
#   municipios/simulacao.sh parar       → desliga os 3 serviços da simulação
# Ver em: http://localhost:8471/?dados=data-sim
# Precisa de saida/municipios-1t/ (coletor_mun rodado com --eleicao 6257 --turno 1 --n-cand 0).
set -e
P="$(cd "$(dirname "$0")/.." && pwd)"
PORTA=8479   # TSE falso (só na máquina)
for u in eleicoes-mun-tsefalso eleicoes-mun-tseweb eleicoes-mun-sim; do
  systemctl --user stop "$u" 2>/dev/null || true
  systemctl --user reset-failed "$u" 2>/dev/null || true
done
[ "${1:-}" = parar ] && { echo "simulação parada"; exit 0; }
rm -rf "$P/saida/mun-tsefalso" "$P/saida/municipios-sim"
mkdir -p "$P/saida/mun-tsefalso"
ln -sfn ../../saida/municipios-sim/data "$P/municipios/site/data-sim"
systemd-run --user --unit eleicoes-mun-tsefalso -p MemoryMax=400M --working-directory="$P" \
  python3 municipios/simular_tse.py --origem saida/municipios-1t/data --saida saida/mun-tsefalso --minutos "${1:-20}" --passo 10 >/dev/null
systemd-run --user --unit eleicoes-mun-tseweb -p MemoryMax=200M --working-directory="$P" \
  python3 coleta/servidor_local.py --pasta "$P/saida/mun-tsefalso" --porta "$PORTA" >/dev/null
sleep 3
systemd-run --user --unit eleicoes-mun-sim -p MemoryMax=400M -E PYTHONUNBUFFERED=1 --working-directory="$P" \
  python3 municipios/coletor_mun.py --saida saida/municipios-sim --base "http://127.0.0.1:$PORTA/oficial/ele2026/6258/" \
  --intervalo 10 --simulacao >/dev/null
echo "simulação ligada (${1:-20} min). Abra http://localhost:8471/?dados=data-sim"
