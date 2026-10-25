#!/usr/bin/env bash
# Troca o tráfego de eleicoes.inema.club e municipios.inema.club entre o Cloudflare (normal) e a VPS4 (reserva).
# Sem argumento: mostra os comandos. Quem faz o trabalho é o trocar_dominios.py, na mesma pasta.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/../.." && pwd)"
PY="$AQUI/trocar_dominios.py"

ajuda() {
  cat <<EOF
Troca de domínios — eleicoes.inema.club e municipios.inema.club

  $0 status          onde cada domínio está agora (Cloudflare ou VPS4)
  $0 vps             SIMULA a ida para a VPS4 (não muda nada)
  $0 vps --executar  manda o tráfego para a VPS4
  $0 volta           SIMULA a volta para o Cloudflare (não muda nada)
  $0 volta --executar devolve o tráfego aos Workers do Cloudflare

Comandos equivalentes (de $RAIZ):
  python3 ferramentas/vps/trocar_dominios.py status
  python3 ferramentas/vps/trocar_dominios.py vps --executar
  python3 ferramentas/vps/trocar_dominios.py volta --executar

Endereços da reserva (sempre na VPS4): https://eleicoes2026.inema.club  https://municipios2026.inema.club
Atualizar a VPS4: ssh root@62.238.25.84 'cd /opt/eleicoes2026 && git pull && bash ferramentas/vps/instalar.sh --executar'
EOF
}

case "${1:-}" in
  status|vps|volta)
    echo "\$ python3 ferramentas/vps/trocar_dominios.py $*"
    cd "$RAIZ" && exec python3 "$PY" "$@" ;;
  *) ajuda ;;
esac
