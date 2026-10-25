#!/usr/bin/env bash
# Reserva operacional numa VPS (Ubuntu): coletores + projeção + nginx servindo os dois sites.
# Em pane da máquina principal, basta apontar eleicoes.inema.club e municipios.inema.club para o IP da VPS
# no Cloudflare. Rode como root na VPS, de dentro do repositório: bash ferramentas/vps/instalar.sh
# - versões a partir de 500000 (não colidem com os arquivos imutáveis já publicados pela máquina principal)
# - coletores só consultam o TSE a partir de ABERTURA (horário de Brasília, fuso explícito: a VPS fica em UTC)
# - sem publicador (Cloudflare) e sem simulação
set -euo pipefail
R="$(cd "$(dirname "$0")/../.." && pwd)"
ABERTURA="${ABERTURA:-2026-10-25 17:00:00 -0300}"
BASE="${VERSAO_INICIAL:-500000}"

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

sed "s#__RAIZ__#$R#g" "$R/ferramentas/vps/nginx-eleicoes.conf" > /etc/nginx/sites-available/eleicoes
ln -sfn /etc/nginx/sites-available/eleicoes /etc/nginx/sites-enabled/eleicoes
rm -f /etc/nginx/sites-enabled/default
# o nginx (www-data) precisa atravessar a pasta do projeto
chmod o+x "$R" "$R/saida" 2>/dev/null || true
nginx -t
systemctl daemon-reload
systemctl enable --now nginx
systemctl reload nginx
systemctl enable eleicoes-coletor eleicoes-municipios eleicoes-projecao
systemctl restart eleicoes-coletor eleicoes-municipios eleicoes-projecao --no-block
echo "reserva instalada em $R · coletores esperam até $ABERTURA · versões a partir de $((BASE + 1))"
