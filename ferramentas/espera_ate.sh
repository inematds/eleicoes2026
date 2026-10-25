#!/usr/bin/env bash
# espera_ate.sh "AAAA-MM-DD HH:MM:SS" — só termina quando chegar o horário (já passou = sai na hora).
# Usado antes dos coletores do TSE (drop-in do systemd): se o servidor reiniciar antes da abertura
# da apuração, os coletores sobem mas só começam a consultar o TSE no horário.
set -u
alvo="$(date -d "${1:?uso: espera_ate.sh 'AAAA-MM-DD HH:MM:SS'}" +%s)" || exit 1
while [ "$(date +%s)" -lt "$alvo" ]; do sleep "${ESPERA_PASSO:-20}"; done
