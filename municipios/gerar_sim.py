"""Gera os resultados FINAIS fictícios por cidade para a simulação no navegador (?sim=1).

Parte dos votos reais do 1º turno (saída do coletor_mun com --eleicao 6257): os votos de 13 e 22
viram o 2º turno e os dos outros candidatos são repartidos na mesma proporção, com um pequeno
desvio sorteado por cidade. Nomes ficam FICTÍCIOS na página (Candidato A/B). Não é resultado.

Saída: municipios/site/assets/sim/<uf>.json  →  {"cdi": [eleitorado, seções, votosA, votosB, brancos, nulos]}
Uso:   python3 municipios/gerar_sim.py saida/municipios-1t/data
"""
import json
import os
import random
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(AQUI, "site", "assets", "sim")


def main(origem):
    rnd = random.Random(2026)
    man = json.load(open(os.path.join(origem, "latest.json")))
    os.makedirs(DEST, exist_ok=True)
    total = 0
    for uf, info in sorted(man["ufs"].items()):
        d = json.load(open(os.path.join(origem, info["arquivo"])))
        out = {}
        for cdi, r in sorted(d["cidades"].items()):
            a, b = r["c"].get("13", 0), r["c"].get("22", 0)
            vv = r["vv"] or (a + b) or 1
            quota = min(0.97, max(0.03, (a / (a + b) if a + b else 0.5) + rnd.uniform(-0.04, 0.04)))
            va = round(vv * quota)
            out[cdi] = [r["te"], max(1, r["ts"]), va, vv - va, r["vb"], r["vn"]]
        json.dump(out, open(os.path.join(DEST, uf + ".json"), "w"), separators=(",", ":"))
        total += len(out)
    kb = sum(os.path.getsize(os.path.join(DEST, f)) for f in os.listdir(DEST)) // 1024
    print(f"{total} cidades, {kb} KB em {DEST}")


if __name__ == "__main__":
    main(sys.argv[1])
