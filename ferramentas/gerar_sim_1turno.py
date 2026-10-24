"""Gera site/assets/sim-1turno.json: a simulação inteira (0% → 100%) num arquivo só,
para o botão "Simulação" tocar acelerado no navegador (site/replay.js), sem servidor.

Base: simular.py (eleitorado, comparecimento, brancos, nulos e proporção entre os dois do
1º turno real, andamento inventado), sempre com nomes FICTÍCIOS (o site é público).

Uso: python3 ferramentas/gerar_sim_1turno.py
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(P, "site", "assets", "sim-1turno.json")


def main():
    tmp = tempfile.mkdtemp(prefix="sim1t-", dir=os.path.join(P, "saida"))
    dados = os.path.join(tmp, "data")
    subprocess.run([sys.executable, os.path.join(P, "coleta", "simular.py"), "--saida", dados,
                    "--intervalo", "0", "--uma-vez", "--ficticio"], check=True, stdout=subprocess.DEVNULL)
    m = json.load(open(os.path.join(dados, "latest.json")))
    hist = {abr: json.load(open(os.path.join(dados, f))) for abr, f in m["historico"].items()}
    arquivos = {}
    for f in glob.glob(os.path.join(dados, "**", "v*.json"), recursive=True):
        rel = os.path.relpath(f, dados)
        arquivos[rel] = json.load(open(f))
    # um passo por ponto do histórico do Brasil; cada abrangência usa a última versão até aquele horário
    passos = []
    for pt in hist["br"]["pontos"]:
        t = pt["totalizado_tse"] or ""
        v = {}
        for abr, h in hist.items():
            ok = [p["versao"] for p in h["pontos"] if (p["totalizado_tse"] or "") <= t]
            if ok:
                v[abr] = max(ok)
        passos.append({"t": t, "v": v})
    pacote = {"schema": 1, "tipo": "pacote_simulacao", "eleicao": m["eleicao"],
              "fonte": {"tipo": "simulacao", "orgao": "TSE", "nota": m["fonte"].get("nota", "")},
              "passos": passos, "arquivos": arquivos, "historico": hist}
    json.dump(pacote, open(DEST, "w"), ensure_ascii=False, separators=(",", ":"))
    shutil.rmtree(tmp)
    print(f"{DEST}: {len(passos)} passos, {len(arquivos)} arquivos, {os.path.getsize(DEST) // 1024} KB")


if __name__ == "__main__":
    main()
