"""Teste da projeção com a eleição real de 2022 (Lula 13 × Bolsonaro 22).

Lê os dados abertos do TSE (votacao_partido_munzona + detalhe_votacao_munzona, 2022),
monta 1º e 2º turno por cidade no mesmo formato do coletor e simula a noite: cidades
"fecham" numa ordem desequilibrada (pequenas primeiro, Sul/Sudeste antes). Em cada ponto
compara a projeção e o número parcial com o resultado final (sem o exterior).

Uso: python3 -I projecao/backtest_2022.py saida/backtest2022/bruto
"""
import csv, os, sys, time
from collections import defaultdict
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelo as M  # noqa: E402

GRUPOS_1T = ["13", "22", "12", "15"]  # Lula, Bolsonaro, Ciro, Tebet; o resto vira "pequenos"
VIES_REGIAO = {"S": 0.5, "SE": 0.7, "CO": 0.9, "NE": 1.2, "N": 1.4}  # < 1 chega antes


def le_csv(caminho):
    with open(caminho, encoding="latin-1", newline="") as f:
        yield from csv.DictReader(f, delimiter=";")


def monta(bruto):
    cid = {1: defaultdict(lambda: {"te": 0, "vb": 0, "vn": 0, "abst": 0, "ts": 0, "c": defaultdict(int)}),
           2: defaultdict(lambda: {"te": 0, "vb": 0, "vn": 0, "abst": 0, "ts": 0, "c": defaultdict(int)})}
    uf_de = {}
    for r in le_csv(os.path.join(bruto, "detalhe", "detalhe_votacao_munzona_2022_BRASIL.csv")):
        if r["CD_CARGO"] != "1" or r["SG_UF"] == "ZZ":
            continue
        t, cd = int(r["NR_TURNO"]), str(int(r["CD_MUNICIPIO"]))
        c = cid[t][cd]
        c["te"] += int(r["QT_APTOS"]); c["abst"] += int(r["QT_ABSTENCOES"])
        c["vb"] += int(r["QT_VOTOS_BRANCOS"]); c["vn"] += int(r["QT_TOTAL_VOTOS_NULOS"])
        c["ts"] += int(r["QT_TOTAL_SECOES"])
        uf_de[cd] = r["SG_UF"].lower()
    for r in le_csv(os.path.join(bruto, "partido", "votacao_partido_munzona_2022_BRASIL.csv")):
        if r["CD_CARGO"] != "1" or r["SG_UF"] == "ZZ":
            continue
        cid[int(r["NR_TURNO"])][str(int(r["CD_MUNICIPIO"]))]["c"][r["NR_PARTIDO"]] += int(r["QT_VOTOS_NOMINAIS_VALIDOS"])
    for t in (1, 2):
        for c in cid[t].values():
            c["c"] = dict(c["c"]); c["st"] = c["ts"]; c["and"] = "finalizada"
    comum = sorted(set(cid[1]) & set(cid[2]))
    return {cd: (uf_de[cd], cid[1][cd]) for cd in comum}, {cd: cid[2][cd] for cd in comum}


def ordem(base, semente):
    rng = np.random.default_rng(semente)
    cds = list(base)
    chave = [base[cd][1]["te"] ** 0.6 * VIES_REGIAO[M.REGIAO[base[cd][0]]] * rng.lognormal(0, 0.8) for cd in cds]
    return [cds[i] for i in np.argsort(chave)]


def main():
    bruto = sys.argv[1]
    t0 = time.time()
    base, final2 = monta(bruto)
    v = np.sum([M.destinos(c, "13", "22") for c in final2.values()], 0)
    verdade = 100 * v[0] / (v[0] + v[1])
    te_tot = sum(c["te"] for c in final2.values())
    print(f"cidades: {len(base)} · final 2º turno (sem exterior): Lula {verdade:.2f}% dos válidos · lido em {time.time()-t0:.0f}s")
    lam = tuple(float(x) for x in os.environ.get("LAM", "1,3,3").split(","))
    mod = M.Modelo(base, GRUPOS_1T, "13", "22", lam=lam)
    pontos = [0.02, 0.05, 0.10, 0.20, 0.30, 0.45, 0.60, 0.80]
    erros_p, erros_b = defaultdict(list), defaultdict(list)
    for s in range(5):
        seq = ordem(base, s)
        for frac in pontos:
            n = int(frac * len(seq))
            atual = {cd: final2[cd] for cd in seq[:n]}
            r = mod.roda(atual)
            vb_ = np.sum([M.destinos(c, "13", "22") for c in atual.values()], 0)
            bruto_pct = 100 * vb_[0] / (vb_[0] + vb_[1])
            pct_el = 100 * sum(c["te"] for c in atual.values()) / te_tot
            erros_p[frac].append(r["pct_a"] - verdade); erros_b[frac].append(bruto_pct - verdade)
            if s == 0:
                print(f"  ordem 0 · {frac:4.0%} cidades ({pct_el:4.1f}% do eleitorado): projeção {r['pct_a']:.2f} · parcial {bruto_pct:.2f}")
    print("\nerro médio absoluto (pontos percentuais) em 5 ordens:  projeção | parcial bruto | pior projeção")
    for frac in pontos:
        p, b = np.abs(erros_p[frac]), np.abs(erros_b[frac])
        print(f"  {frac:4.0%} das cidades:  {p.mean():5.2f} | {b.mean():5.2f} | {p.max():5.2f}")
    T = mod.roda(final2)["T"]["BR"]
    nomes = ["Lula", "Bolsonaro", "Ciro", "Tebet", "pequenos", "brancos+nulos", "abstenção"]
    print("\ntransferência estimada com todas as cidades (→ Lula, Bolsonaro, branco/nulo, não votou):")
    for n_, row in zip(nomes, T):
        print(f"  {n_:14s}" + "  ".join(f"{100*x:5.1f}%" for x in row))
    print(f"\ntempo total {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
