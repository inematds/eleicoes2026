#!/usr/bin/env python3
"""Roda de hora em hora depois da eleição: quando o TSE fecha a apuração, desliga os coletores.

- Brasil com totalização final do TSE  -> para eleicoes-coletor (aqui e na VPS4)
- todas as cidades finalizadas         -> para eleicoes-municipios (aqui e na VPS4)
Antes de parar, refaz a análise uma última vez. Quando os dois pararem, desliga o próprio timer.
Só lê arquivos locais; não consulta o TSE. Registro em saida/fim-apuracao.jsonl.
"""
import glob
import json
import os
import subprocess
from datetime import datetime

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(P, "saida")
VPS = "root@62.238.25.84"
LOG = os.path.join(S, "fim-apuracao.jsonl")


def log(**d):
    d = {"t": datetime.now().isoformat(timespec="seconds"), **d}
    open(LOG, "a").write(json.dumps(d, ensure_ascii=False) + "\n")
    print(json.dumps(d, ensure_ascii=False), flush=True)


def ativo(unit):
    return subprocess.run(["systemctl", "--user", "is-active", "--quiet", unit]).returncode == 0


def para(unit):
    subprocess.run(["systemctl", "--user", "stop", unit])
    r = subprocess.run(["ssh", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", VPS, f"systemctl stop {unit}"],
                       capture_output=True, text=True, timeout=60)
    log(evento="PAROU", unit=unit, vps_rc=r.returncode, vps_err=r.stderr.strip()[:200])


def main():
    lat = json.load(open(os.path.join(S, "oficial", "data", "latest.json")))
    br = json.load(open(os.path.join(S, "oficial", "data", lat["abrangencias"]["br"]["arquivo"])))
    br_final = bool(br["situacao"]["totalizacao_final"])
    tot = fin = 0
    for d in glob.glob(os.path.join(S, "municipios", "data", "uf", "*")):
        fs = sorted(glob.glob(os.path.join(d, "v*.json")))
        if fs:
            for c in json.load(open(fs[-1]))["cidades"].values():
                tot += 1
                fin += c.get("and") == "finalizada"
    cid_final = tot > 0 and fin == tot
    log(evento="CHECAGEM", br_pct=br["secoes"]["pct_totalizadas"], br_final=br_final,
        totalizado_tse=br["fonte"]["totalizado_tse"], cidades_finalizadas=fin, cidades=tot)
    if (br_final and ativo("eleicoes-coletor")) or (cid_final and ativo("eleicoes-municipios")):
        subprocess.run(["systemctl", "--user", "start", "eleicoes-analise.service"])
    if br_final and ativo("eleicoes-coletor"):
        para("eleicoes-coletor")
    if cid_final and ativo("eleicoes-municipios"):
        para("eleicoes-municipios")
    if not ativo("eleicoes-coletor") and not ativo("eleicoes-municipios"):
        log(evento="FIM", msg="apuração fechada no TSE; coletores parados; timer desligado")
        subprocess.run(["systemctl", "--user", "disable", "--now", "eleicoes-fim-apuracao.timer"])


if __name__ == "__main__":
    main()
