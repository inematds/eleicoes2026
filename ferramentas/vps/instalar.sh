#!/usr/bin/env bash
# Reserva operacional numa VPS (Ubuntu): coletores + projeção + nginx servindo os dois sites.
# Em pane da máquina principal, basta apontar eleicoes.inema.club e municipios.inema.club para o IP da VPS
# no Cloudflare (ferramentas/vps/trocar_dominios.sh). Sem argumento: mostra os comandos.
# - versões a partir de 500000 (não colidem com os arquivos imutáveis já publicados pela máquina principal)
# - coletores só consultam o TSE a partir de ABERTURA (horário de Brasília, fuso explícito: a VPS fica em UTC)
# - sem publicador (Cloudflare) e sem simulação
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
ABERTURA="${ABERTURA:-2026-10-25 17:00:00 -0300}"
BASE="${VERSAO_INICIAL:-500000}"
VPS="${VPS:-root@62.238.25.84}"
DIR_VPS=/opt/eleicoes2026

ajuda() {
  cat <<EOF
Reserva na VPS4 ($VPS, $DIR_VPS) — coletores + projeção + nginx

Daqui (máquina principal):
  $0 vps        atualiza a VPS4 (git pull) e reinstala tudo lá
  $0 status     mostra serviços e sites da VPS4

Dentro da VPS4 (como root):
  bash ferramentas/vps/instalar.sh --executar

Comandos equivalentes:
  ssh $VPS 'cd $DIR_VPS && git pull && bash ferramentas/vps/instalar.sh --executar'
  ssh $VPS 'systemctl is-active nginx eleicoes-coletor eleicoes-municipios eleicoes-projecao'

Sites da reserva: https://eleicoes2026.inema.club  https://municipios2026.inema.club
Troca de domínios: ferramentas/vps/trocar_dominios.sh
EOF
}

case "${1:-}" in
  --executar) ;;  # segue para a instalação abaixo
  vps)
    echo "\$ ssh $VPS 'cd $DIR_VPS && git pull && bash ferramentas/vps/instalar.sh --executar'"
    exec ssh "$VPS" "cd $DIR_VPS && git pull -q && bash ferramentas/vps/instalar.sh --executar" ;;
  status)
    echo "\$ ssh $VPS (serviços e sites)"
    exec ssh "$VPS" "cd $DIR_VPS && git log -1 --oneline
      for s in nginx eleicoes-coletor eleicoes-municipios eleicoes-projecao; do printf '%-22s %s\n' \$s \"\$(systemctl is-active \$s)\"; done
      echo '(activating = esperando as 17h)'
      for h in eleicoes2026.inema.club municipios2026.inema.club; do
        curl -s -o /dev/null -w \"\$h /data/latest.json -> %{http_code}\n\" -H \"Host: \$h\" http://127.0.0.1/data/latest.json; done" ;;
  *) ajuda; exit 0 ;;
esac

apt-get install -y -q nginx python3-numpy python3-scipy >/dev/null
mkdir -p "$R/saida/oficial/data" "$R/saida/municipios/data"
ln -sfn ../saida/oficial/data "$R/site/data"
ln -sfn ../../saida/municipios/data "$R/municipios/site/data"
chmod +x "$R/ferramentas/espera_ate.sh"

unit() {  # nome descrição comando
  cat > "/etc/systemd/system/$1.service" <<EOF
[Unit]
Description=$2
After=network-online.target

[Service]
WorkingDirectory=$R
ExecStartPre=$R/ferramentas/espera_ate.sh "$ABERTURA"
ExecStart=$3
Restart=always
RestartSec=10
TimeoutStartSec=infinity
MemoryMax=${4:-400M}
Environment=PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2

[Install]
WantedBy=multi-user.target
EOF
}
unit eleicoes-coletor "Eleições 2026 INEMA (reserva) — coletor oficial do TSE" \
  "/usr/bin/python3 $R/coleta/coletor.py --saida $R/saida/oficial --intervalo 15 --versao-inicial $BASE" 300M
unit eleicoes-municipios "Eleições 2026 INEMA (reserva) — coletor de municípios do TSE" \
  "/usr/bin/python3 $R/municipios/coletor_mun.py --saida $R/saida/municipios --intervalo 15 --versao-inicial $BASE" 400M
unit eleicoes-projecao "Eleições 2026 INEMA (reserva) — Projeção (só lê arquivos locais)" \
  "/usr/bin/python3 $R/projecao/projetar.py --laco 60" 800M
# Exterior (boletins de urna por seção): uma rodada na hora cheia e na meia hora
cat > /etc/systemd/system/eleicoes-exterior.service <<EOF
[Unit]
Description=Eleições 2026 INEMA (reserva) — exterior por país (boletins de urna)
[Service]
Type=oneshot
WorkingDirectory=$R
ExecStart=/usr/bin/python3 $R/exterior/coletor_ext.py
TimeoutStartSec=900
MemoryMax=400M
Environment=PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
EOF
cat > /etc/systemd/system/eleicoes-exterior.timer <<EOF
[Unit]
Description=Eleições 2026 INEMA (reserva) — exterior de hora em hora em 25/10
[Timer]
OnCalendar=2026-10-25 *:00,30:00 America/Sao_Paulo
AccuracySec=30s
[Install]
WantedBy=timers.target
EOF

# HTTPS: usa o certificado do Let's Encrypt se já existir; senão, um autoassinado (vale no modo Full do Cloudflare)
mkdir -p /var/www/certbot /etc/ssl/eleicoes
LE=/etc/letsencrypt/live/eleicoes2026.inema.club
if [ -f "$LE/fullchain.pem" ]; then CERT="$LE/fullchain.pem"; CHAVE="$LE/privkey.pem"
else
  CERT=/etc/ssl/eleicoes/autoassinado.crt; CHAVE=/etc/ssl/eleicoes/autoassinado.key
  [ -f "$CERT" ] || openssl req -x509 -nodes -newkey rsa:2048 -days 365 -subj "/CN=eleicoes2026.inema.club" \
    -addext "subjectAltName=DNS:eleicoes2026.inema.club,DNS:eleicoes.inema.club,DNS:municipios.inema.club" \
    -keyout "$CHAVE" -out "$CERT" 2>/dev/null
fi
sed -e "s#__RAIZ__#$R#g" -e "s#__CERT__#$CERT#g" -e "s#__CHAVE__#$CHAVE#g" "$R/ferramentas/vps/nginx-eleicoes.conf" > /etc/nginx/sites-available/eleicoes
ln -sfn /etc/nginx/sites-available/eleicoes /etc/nginx/sites-enabled/eleicoes
rm -f /etc/nginx/sites-enabled/default
# o nginx (www-data) precisa atravessar a pasta do projeto
chmod o+x "$R" "$R/saida" 2>/dev/null || true
nginx -t
systemctl daemon-reload
systemctl enable --now nginx
systemctl reload nginx
systemctl enable eleicoes-coletor eleicoes-municipios eleicoes-projecao
systemctl enable --now eleicoes-exterior.timer
systemctl restart eleicoes-coletor eleicoes-municipios eleicoes-projecao --no-block
echo "reserva instalada em $R · coletores esperam até $ABERTURA · versões a partir de $((BASE + 1))"
