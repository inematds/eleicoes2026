#!/usr/bin/env bash
# Troca o que o site local mostra: simulação ou dados oficiais do TSE.
#   ferramentas/modo.sh oficial   → para o simulador e aponta site/data para saida/oficial/data
#   ferramentas/modo.sh sim       → aponta para saida/data e liga o simulador
#   ferramentas/modo.sh           → mostra o modo atual
set -e
P="$(cd "$(dirname "$0")/.." && pwd)"
case "${1:-}" in
  oficial)
    systemctl --user stop eleicoes-sim 2>/dev/null || true
    ln -sfn ../saida/oficial/data "$P/site/data"
    echo "modo: OFICIAL (site/data -> saida/oficial/data). Quem estiver com a página aberta deve recarregar.";;
  sim)
    ln -sfn ../saida/data "$P/site/data"
    systemctl --user reset-failed eleicoes-sim 2>/dev/null || true
    systemctl --user is-active --quiet eleicoes-sim || systemd-run --user --unit eleicoes-sim -p MemoryMax=300M \
      --working-directory="$P" python3 coleta/simular.py --saida saida/data --intervalo 15 --inicio 14 >/dev/null
    echo "modo: SIMULAÇÃO (site/data -> saida/data, simulador ligado). Quem estiver com a página aberta deve recarregar.";;
  *) echo "site/data -> $(readlink "$P/site/data")"; systemctl --user is-active eleicoes-sim eleicoes-coletor eleicoes-web | paste -sd' ' | sed 's/^/sim coletor web: /';;
esac
