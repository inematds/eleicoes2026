#!/usr/bin/env bash
# Operação definitiva na VPS4 (depois da apuração): análise, publicação no Cloudflare e download das conversas do chat.
# Os coletores e a projeção não rodam mais (a apuração terminou). Rodar como root, dentro de /opt/eleicoes2026:
#   bash ferramentas/vps/operacao.sh --executar
# Credenciais (fora do repositório, permissão 600):
#   /etc/eleicoes2026/cloudflare.env   CLOUDFLARE_API_TOKEN=...  CLOUDFLARE_ACCOUNT_ID=...   (para o wrangler deploy)
#   /root/.config/eleicoes2026/chat.env CHAT_EXPORT_TOKEN=...                              (para baixar as conversas)
# Sem o cloudflare.env os publicadores ficam instalados mas desligados.
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
[ "${1:-}" = "--executar" ] || { sed -n 2,9p "$0"; exit 0; }

apt-get install -y -q nginx python3-numpy python3-scipy rsync >/dev/null
mkdir -p /etc/eleicoes2026 "$R/saida/oficial/data" "$R/saida/municipios/data" "$R/saida/chat"
ln -sfn ../saida/oficial/data "$R/site/data"
ln -sfn ../../saida/municipios/data "$R/municipios/site/data"
(cd "$R/ferramentas/cloudflare" && npm install --silent --no-audit --no-fund)

# a operação da apuração (coletores, projeção, exterior) fica desligada
for u in eleicoes-coletor eleicoes-municipios eleicoes-projecao eleicoes-exterior.timer eleicoes-exterior; do
  systemctl disable --now "$u" 2>/dev/null || true
done

servico() {  # nome descrição comando [laço: sim|nao] [env extra]
  local reinicia="" tipo="Type=oneshot"
  [ "$4" = "sim" ] && { tipo="Type=simple"; reinicia=$'Restart=always\nRestartSec=20'; }
  cat > "/etc/systemd/system/$1.service" <<EOF
[Unit]
Description=$2
After=network-online.target
Wants=network-online.target

[Service]
$tipo
WorkingDirectory=$R
ExecStart=$3
$reinicia
MemoryMax=700M
Environment=PYTHONUNBUFFERED=1
Environment=HOME=/root
EnvironmentFile=-/etc/eleicoes2026/cloudflare.env
EOF
}
temporizador() {  # nome descrição OnCalendar
  cat > "/etc/systemd/system/$1.timer" <<EOF
[Unit]
Description=$2

[Timer]
OnCalendar=$3
AccuracySec=30s
Persistent=true

[Install]
WantedBy=timers.target
EOF
}

servico eleicoes-analise "Eleições 2026 INEMA — análises e contexto do chat (só arquivos locais)" "/usr/bin/python3 $R/analise/gerar.py" nao
temporizador eleicoes-analise "Eleições 2026 INEMA — análises a cada 30 min" "*:0/30"
servico eleicoes-chat-baixar "Eleições 2026 INEMA — baixa as conversas do chat" "/usr/bin/python3 $R/ferramentas/chat_baixar.py" nao
temporizador eleicoes-chat-baixar "Eleições 2026 INEMA — baixa as conversas do chat de hora em hora" "hourly"
servico eleicoes-publicar "Eleições 2026 INEMA — publica eleicoes.inema.club no Cloudflare quando os dados mudam" "/usr/bin/python3 $R/ferramentas/publicar_cf.py --laco 60" sim
servico eleicoes-municipios-publicar "Eleições 2026 INEMA — publica municipios.inema.club no Cloudflare quando os dados mudam" "/usr/bin/python3 $R/municipios/publicar_mun.py --laco 60" sim

systemctl daemon-reload
systemctl enable --now eleicoes-analise.timer eleicoes-chat-baixar.timer
if [ -s /etc/eleicoes2026/cloudflare.env ]; then
  systemctl enable --now eleicoes-publicar eleicoes-municipios-publicar
else
  echo "AVISO: sem /etc/eleicoes2026/cloudflare.env — publicadores instalados, mas desligados"
fi
systemctl list-units --all --no-legend 'eleicoes*' | awk '{print $1, $3, $4}'
