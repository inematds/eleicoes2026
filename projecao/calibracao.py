"""Mede se a faixa da Projeção cobre o resultado final na proporção prometida (90%).

Cenários: eleição real de 2022 (dados abertos do TSE) e simulação de municípios de 2026
(desvio sorteado em cada cidade), em várias ordens de chegada (pequenas e Sul/Sudeste primeiro,
ou ao acaso) e vários pontos da noite. Usa a MESMA regra de ligar e de faixa do serviço
(projetar.criterio / projetar.faixa_final). Só conta os momentos em que a projeção apareceria.

Uso: python3 projecao/calibracao.py saida/backtest2022/bruto [processos]
Saída: cobertura geral e por faixa de % de cidades; fator mínimo que dá ≥ 90%.
"""
import json, os, sys
from multiprocessing import Pool

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelo as M  # noqa: E402
import projetar as PJ  # noqa: E402
import backtest_2022 as BT  # noqa: E402

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PONTOS = [0.04, 0.06, 0.08, 0.10, 0.15, 0.20, 0.30, 0.45, 0.60, 0.80]
SEMENTES = range(8)
G = {}


def prepara(bruto):
    base22, fin22 = BT.monta(bruto)
    G["2022"] = (M.Modelo(base22, BT.GRUPOS_1T, "13", "22"), base22, fin22)
    cid, _, _ = PJ.cidades(os.path.join(P, "saida", "municipios-sim", "data"))
    base26, _, _ = PJ.cidades(os.path.join(P, "saida", "municipios-1t", "data"))
    fin26 = {k: v for k, (u, v) in cid.items() if k in base26}
    G["sim"] = (M.Modelo(base26, PJ.GRUPOS_1T, "13", "22"), base26, fin26)


def ordem_aleatoria(base, s):
    rng = np.random.default_rng(100 + s)
    cds = list(base)
    return [cds[i] for i in rng.permutation(len(cds))]


def cenario(args):
    nome, tipo, s, frac = args
    mod, base, final = G[nome]
    verdade = mod.roda(final)["pct_a"]
    seq = BT.ordem(base, s) if tipo == "vies" else ordem_aleatoria(base, s)
    atual = {cd: final[cd] for cd in seq[:int(frac * len(seq))]}
    fin, _ = mod.finalizadas(atual)
    pronto, est = PJ.criterio(mod, fin)
    if not pronto:
        return None
    res = mod.roda(atual, n_boot=PJ.N_BOOT, semente=s)
    verd_uf = G.setdefault("verd_uf_" + nome, {u: v["pct_a"] for u, v in mod.roda(final)["ufs"].items()})
    pct_cid = 100 * len(fin) / len(mod.cds)
    ufs = [{"uf": u, "erro": v["pct_a"] - verd_uf[u], "meia_modelo": v["meia_modelo"], "pct_el": v["pct_el"],
            "cid_fin": v["cid_fin"], "cid_tot": v["cid_tot"]} for u, v in res["ufs"].items() if u in verd_uf]
    return {"dados": nome, "ordem": tipo, "s": s, "frac": frac, "pct_cid": pct_cid, "pct_el": est["pct_eleitorado_finalizado"],
            "erro": res["pct_a"] - verdade, "meia_modelo": (res["faixa_a"][1] - res["faixa_a"][0]) / 2,
            "piso": PJ.faixa_minima(pct_cid), "ufs": ufs}


def cobre(r, fator):
    return abs(r["erro"]) <= max(fator * r["meia_modelo"], r["piso"])


def main():
    bruto = sys.argv[1]
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    prepara(bruto)
    tarefas = [(n, t, s, f) for n in ("2022", "sim") for t in ("vies", "acaso") for s in SEMENTES for f in PONTOS]
    with Pool(nproc, initializer=prepara, initargs=(bruto,)) as pool:
        rs = [r for r in pool.map(cenario, tarefas, chunksize=1) if r]
    print(f"cenários em que a projeção apareceria: {len(rs)} de {len(tarefas)}")
    fx = PJ.FATOR_FAIXA
    print(f"\nregra atual (fator {fx}):  cobertura geral {100*np.mean([cobre(r, fx) for r in rs]):.1f}%")
    for nome in ("2022", "sim"):
        sub = [r for r in rs if r["dados"] == nome]
        print(f"  {nome}: {100*np.mean([cobre(r, fx) for r in sub]):.1f}% · erro médio {np.mean([abs(r['erro']) for r in sub]):.2f} p.p. · pior {max(abs(r['erro']) for r in sub):.2f}")
    faixas = [(0, 10), (10, 30), (30, 60), (60, 101)]
    for a, b in faixas:
        sub = [r for r in rs if a <= r["pct_cid"] < b]
        if sub:
            print(f"  {a:>2}–{b:>3}% das cidades: {100*np.mean([cobre(r, fx) for r in sub]):5.1f}% de {len(sub)} · meia-faixa média {np.mean([max(fx*r['meia_modelo'], r['piso']) for r in sub]):.2f} p.p.")
    # menor fator que dá ≥ 90% no geral E em cada faixa de % de cidades
    escolhido = None
    for f in np.arange(1.0, 6.01, 0.1):
        ok = np.mean([cobre(r, f) for r in rs]) >= 0.9 and all(
            np.mean([cobre(r, f) for r in rs if a <= r["pct_cid"] < b]) >= 0.9
            for a, b in faixas if any(a <= r["pct_cid"] < b for r in rs))
        if ok:
            escolhido = round(float(f), 1)
            break
    print(f"\nmenor fator com ≥ 90% no geral e em cada faixa: {escolhido}")
    if escolhido:
        for a, b in faixas:
            sub = [r for r in rs if a <= r["pct_cid"] < b]
            if sub:
                print(f"  {a:>2}–{b:>3}%: {100*np.mean([cobre(r, escolhido) for r in sub]):5.1f}% · meia-faixa média {np.mean([max(escolhido*r['meia_modelo'], r['piso']) for r in sub]):.2f} p.p.")
    estados(rs)
    json.dump(rs, open(os.path.join(P, "saida", "backtest2022", "calibracao.json"), "w"))


def estados(rs):
    """Faixa por estado: cobertura com a regra atual e o menor piso que dá ≥ 90% em cada faixa de
    % do eleitorado do estado já em cidades encerradas."""
    us = [u for r in rs for u in r["ufs"]]
    print(f"\n=== por estado: {len(us)} casos (estado × momento) ===")
    cob = [abs(u["erro"]) <= PJ.faixa_uf(u["meia_modelo"], u["pct_el"]) for u in us if PJ.uf_estavel(u)]
    if cob:
        print(f"regra atual: {100*np.mean(cob):.1f}% de cobertura nos {len(cob)} casos mostrados como estáveis "
              f"({100*len(cob)/len(us):.0f}% dos casos)")
    for a, b in [(0, 5), (5, 15), (15, 30), (30, 60), (60, 101)]:
        sub = [u for u in us if a <= u["pct_el"] < b]
        if not sub:
            continue
        piso = None
        for f in np.arange(0.0, 15.01, 0.1):
            if np.mean([abs(u["erro"]) <= max(u["meia_modelo"], f) for u in sub]) >= 0.9:
                piso = round(float(f), 1)
                break
        e = np.abs([u["erro"] for u in sub])
        est = [u for u in sub if PJ.uf_estavel(u)]
        c = np.mean([abs(u["erro"]) <= PJ.faixa_uf(u["meia_modelo"], u["pct_el"]) for u in est]) if est else float("nan")
        print(f"  {a:>3}–{b:>3}% do eleitorado do estado: {len(sub):4d} casos · erro médio {e.mean():.2f} · p90 {np.percentile(e, 90):.2f} · "
              f"piso p/ 90%: {piso} · regra atual {100*c:.0f}% em {len(est)} estáveis")


if __name__ == "__main__":
    main()
