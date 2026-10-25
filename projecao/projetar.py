"""Serviço da Projeção INEMA: lê arquivos locais (1º turno por cidade + 2º turno por cidade ao vivo)
e grava projecao.json. Não acessa o TSE nem a internet.

Uso (oficial):
  python3 projecao/projetar.py --laco 60
Teste com a simulação de municípios:
  python3 projecao/projetar.py --atual saida/municipios-sim/data --oficial saida/data --saida saida/projecao-teste.json
"""
import argparse, hashlib, json, os, sys, time
from datetime import datetime, timezone, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import modelo as M  # noqa: E402

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRT = timezone(timedelta(hours=-3))
GRUPOS_1T = ["13", "22", "70", "14", "55"]  # Lula, Flávio, Cury, Renan, Caiado; os outros 7 viram "pequenos"
MODELO_VERSAO = "1.1"
MIN_CIDADES = 250        # cidades FINALIZADAS no país (no teste de 2022, ~5% das cidades → erro médio 0,3 p.p.)
MIN_POR_REGIAO = 15      # e em cada uma das 5 regiões
MIN_PCT_ELEITORADO = 1.0 # % do eleitorado do país já em cidades encerradas
MIN_UFS = 20             # estados com pelo menos MIN_POR_UF cidades encerradas
MIN_POR_UF = 3
FATOR_FAIXA = 1.0        # multiplica a faixa do modelo; calibrado em projecao/calibracao.py
N_BOOT = 30


def agora():
    return datetime.now(BRT).isoformat(timespec="seconds")


def le(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def cidades(pasta):
    """{cd: (uf, cidade)} do manifesto de municípios + o manifesto."""
    m = le(os.path.join(pasta, "latest.json"))
    out = {}
    for uf, info in m["ufs"].items():
        d = le(os.path.join(pasta, info["arquivo"]))
        for cd, c in d["cidades"].items():
            out[cd] = (uf, c)
    cand = None
    for info in m["ufs"].values():
        cand = le(os.path.join(pasta, info["arquivo"])).get("candidatos")
        break
    return out, m, cand


def ultimo(pasta, abr):
    """Último resultado publicado de uma abrangência (formato do coletor principal) ou None."""
    try:
        m = le(os.path.join(pasta, "latest.json"))
        return le(os.path.join(pasta, m["abrangencias"][abr]["arquivo"]))
    except (FileNotFoundError, KeyError):
        return None


def vetor_ext_1t(r):
    """Origens do exterior no 1º turno, a partir do arquivo do coletor principal."""
    vot = {c["numero"]: c["votos"] for c in r["candidatos"]}
    pequenos = sum(v for k, v in vot.items() if k not in GRUPOS_1T)
    v = [vot.get(g, 0) for g in GRUPOS_1T] + [pequenos, r["votos"]["brancos"] + r["votos"]["nulos"], r["eleitorado"]["abstencao"]]
    return np.array(v, float), float(r["eleitorado"]["total"])


def destinos_ext_2t(r, a, b):
    if not r or r["situacao"].get("andamento") != "finalizada":
        return None
    vot = {c["numero"]: c["votos"] for c in r["candidatos"]}
    return np.array([vot.get(a, 0), vot.get(b, 0), r["votos"]["brancos"] + r["votos"]["nulos"], r["eleitorado"]["abstencao"]], float)


def faixa_minima(pct_cidades):
    """Meia-largura mínima da faixa (p.p.): pior erro visto nos testes (2022 real e simulação de
    municípios com desvio sorteado por cidade), arredondado para cima."""
    if pct_cidades < 5:
        return 1.3
    if pct_cidades < 10:
        return 1.0
    if pct_cidades < 30:
        return 0.6
    if pct_cidades < 60:
        return 0.4
    return 0.25


def criterio(mod, fin):
    """Quando a projeção pode aparecer: cidades, regiões, estados e eleitorado mínimos."""
    por_reg = {r: int(np.sum(mod.reg[fin] == r)) for r in M.REGIOES}
    ufs, n = np.unique(mod.uf[fin], return_counts=True) if len(fin) else ([], [])
    n_ufs = int(sum(1 for k in n if k >= MIN_POR_UF))
    pct_el = 100 * float(mod.te1[fin].sum() / mod.te1.sum()) if len(fin) else 0.0
    pronto = (len(fin) >= MIN_CIDADES and min(por_reg.values()) >= MIN_POR_REGIAO
              and pct_el >= MIN_PCT_ELEITORADO and n_ufs >= MIN_UFS)
    return pronto, {"por_regiao": por_reg, "ufs_com_minimo": n_ufs, "pct_eleitorado_finalizado": round(pct_el, 2)}


def faixa_final(res, pct_cid):
    """Faixa mostrada: a do modelo × FATOR_FAIXA, nunca menor que o piso dos testes."""
    pa = res["pct_a"]
    lo, hi = res.get("faixa_a", (pa, pa))
    m = max(FATOR_FAIXA * (hi - lo) / 2, faixa_minima(pct_cid))
    return pa - m, pa + m


# Faixa por estado, pelo % do eleitorado do estado já em cidades encerradas.
# PISO_UF[k] vale para FAIXAS_EL_UF[k]; None = projeção instável (não mostra número). Ver calibracao.py.
# Medido em 6.048 casos (estado × momento): piso p/ 90% = 1,4 · 1,3 · 1,0 · 0,7 · 0,4; aqui com ~20% de folga.
FAIXAS_EL_UF = [(0, 1), (1, 5), (5, 15), (15, 30), (30, 60), (60, 101)]
PISO_UF = [None, 1.7, 1.6, 1.2, 1.0, 0.5]


def _piso_uf(pct_el):
    for (a, b), p in zip(FAIXAS_EL_UF, PISO_UF):
        if a <= pct_el < b:
            return p
    return PISO_UF[-1]


def uf_estavel(u):
    return _piso_uf(u["pct_el"]) is not None and u["cid_fin"] >= min(3, u["cid_tot"])


def faixa_uf(meia_modelo, pct_el):
    p = _piso_uf(pct_el)
    return max(FATOR_FAIXA * meia_modelo, p if p is not None else 0.0)


def calcula(a):
    base_raw, _, _ = cidades(a.base1t)
    atual_raw, man2, cand2 = cidades(a.atual)
    sim = (man2.get("fonte") or {}).get("tipo") != "oficial"
    num = [c["numero"] for c in cand2]
    ca, cb = num[0], num[1]
    nomes = {c["numero"]: c["nome_urna"] for c in cand2}
    mod = M.Modelo(base_raw, GRUPOS_1T, ca, cb)
    atual = {cd: c for cd, (_, c) in atual_raw.items()}

    ext = None
    r1 = ultimo(a.oficial1t, "zz")
    if r1:
        v1, te = vetor_ext_1t(r1)
        ext = (v1, te, destinos_ext_2t(ultimo(a.oficial, "zz"), ca, cb))

    fin, _ = mod.finalizadas(atual)
    pronto, est = criterio(mod, fin)
    n_cid = len(mod.cds)
    pct_cid = 100 * len(fin) / n_cid
    br = ultimo(a.oficial, "br")
    agora_tse = None
    if br and br["votos"]["validos"]:
        agora_tse = {"pct_secoes": br["secoes"]["pct_totalizadas"],
                     "pct_validos": {c["numero"]: c["pct_validos"] for c in br["candidatos"]},
                     "votos": {c["numero"]: c["votos"] for c in br["candidatos"]},
                     "totalizado_tse": br["fonte"].get("totalizado_tse")}

    out = {"schema": 1, "tipo": "projecao", "simulacao": sim, "calculado_em": agora(),
           "candidatos": [{"numero": n, "nome_urna": nomes[n]} for n in (ca, cb)],
           "modelo_versao": MODELO_VERSAO,
           "base": {"cidades_total": n_cid, "cidades_finalizadas": len(fin), "pct_cidades": round(pct_cid, 2), **est,
                    "minimo_cidades": MIN_CIDADES, "minimo_por_regiao": MIN_POR_REGIAO,
                    "minimo_pct_eleitorado": MIN_PCT_ELEITORADO, "minimo_ufs": MIN_UFS, "minimo_por_uf": MIN_POR_UF},
           "apurado_tse": agora_tse}
    if not pronto:
        out["status"] = "aguardando"
        return out

    res = mod.roda(atual, ext, n_boot=N_BOOT)
    tot, pa = res["tot"], res["pct_a"]
    lo, hi = faixa_final(res, pct_cid)
    te_tot = float(tot.sum())
    T = res["T"]
    nomes_orig = [nomes.get(g) or g for g in GRUPOS_1T]
    nomes_1t = {}
    try:
        nomes_1t = {c["numero"]: c["nome_urna"] for c in ultimo(a.oficial1t, "br")["candidatos"]}
    except (TypeError, KeyError):
        pass
    orig = [nomes_1t.get(g, nomes_orig[i]) for i, g in enumerate(GRUPOS_1T)] + ["Outros 7 candidatos", "Brancos e nulos", "Não votou"]
    def matriz(Tm, r=None):
        v1 = (mod.V1 if r is None else mod.V1[mod.reg == r]).sum(0)
        return [{"origem": orig[i], "votos_1t": int(v1[i]),
                 "para": {ca: round(100 * Tm[i][0], 1), cb: round(100 * Tm[i][1], 1),
                          "brancos_nulos": round(100 * Tm[i][2], 1), "nao_votou": round(100 * Tm[i][3], 1)}}
                for i in range(len(orig))]

    out.update({
        "status": "ok",
        "projecao": {
            "pct_validos": {ca: round(pa, 2), cb: round(100 - pa, 2)},
            "faixa": {ca: [round(lo, 2), round(hi, 2)], cb: [round(100 - hi, 2), round(100 - lo, 2)]},
            "votos": {ca: int(tot[0]), cb: int(tot[1]), "brancos_nulos": int(tot[2]), "nao_votou": int(tot[3])},
            "pct_comparecimento": round(100 * (1 - tot[3] / te_tot), 2),
        },
        "transferencias": {"BR": matriz(T["BR"]), **{r: matriz(T[r], r) for r in M.REGIOES}},
        "nome_regiao": M.NOME_REGIAO,
    })
    out["virada"] = virada(tot, agora_tse, ca, cb)
    out["ufs"] = por_estado(res, a, ca, ext)
    return out


def por_estado(res, a, ca, ext):
    """Projeção de cada estado (e do exterior), com faixa calibrada; instável = sem número."""
    out = {}
    for u, v in res["ufs"].items():
        r = ultimo(a.oficial, u)
        tse = None
        if r and r["votos"]["validos"]:
            tse = {"pct_a": next((c["pct_validos"] for c in r["candidatos"] if c["numero"] == ca), None),
                   "pct_secoes": r["secoes"]["pct_totalizadas"]}
        e = {"pct_cid": round(100 * v["cid_fin"] / v["cid_tot"], 1) if v["cid_tot"] else None,
             "pct_el": round(v["pct_el"], 1), "cid_fin": v["cid_fin"], "cid_tot": v["cid_tot"], "tse": tse}
        if u == "zz":
            final = ext is not None and ext[2] is not None
            e["estavel"] = final
            if final:
                e.update(pct_a=round(v["pct_a"], 2), lo=round(v["pct_a"], 2), hi=round(v["pct_a"], 2), final=True)
        elif uf_estavel(v):
            m = faixa_uf(v["meia_modelo"], v["pct_el"])
            e.update(estavel=True, pct_a=round(v["pct_a"], 2), lo=round(v["pct_a"] - m, 2), hi=round(v["pct_a"] + m, 2))
        else:
            e["estavel"] = False
        out[u] = e
    return out


def virada(tot, ap, ca, cb):
    """Quanto o candidato que está atrás na projeção precisaria dos votos válidos que ainda faltam.
    Faltam = válidos projetados − válidos já apurados pelo TSE (Brasil, oficial)."""
    if not ap or not ap.get("votos"):
        return None
    va, vb = ap["votos"].get(ca, 0), ap["votos"].get(cb, 0)
    total = float(tot[0] + tot[1])
    falta = total - (va + vb)
    lider, atras = (ca, cb) if tot[0] >= tot[1] else (cb, ca)
    ap_l, ap_t = (va, vb) if lider == ca else (vb, va)
    proj_t = float(tot[1] if lider == ca else tot[0])
    if falta <= 0.002 * total:
        return {"lider": lider, "atras": atras, "faltam_validos": max(0, int(falta)), "situacao": "praticamente_apurado"}
    precisa = (ap_l - ap_t + falta) / (2 * falta)          # fatia dos que faltam para empatar
    projetado = (proj_t - ap_t) / falta                    # fatia que a projeção dá a ele
    return {"lider": lider, "atras": atras, "faltam_validos": int(falta),
            "pct_faltam": round(100 * falta / total, 2),
            "precisa_pct": round(100 * precisa, 1), "projecao_pct": round(100 * projetado, 1),
            "situacao": "impossivel" if precisa > 1 else ("ja_a_frente" if precisa < 0 else "possivel")}


def registra_historico(caminho, out):
    """Acrescenta a projeção ao histórico público (nunca reescreve entradas antigas)."""
    if out.get("status") != "ok":
        return
    pr, ap, b = out["projecao"], out.get("apurado_tse") or {}, out["base"]
    ca = out["candidatos"][0]["numero"]
    e = {"t": out["calculado_em"], "v": out["modelo_versao"], "cid": b["cidades_finalizadas"],
         "pct_cid": b["pct_cidades"], "pct_el": b["pct_eleitorado_finalizado"],
         "a": pr["pct_validos"][ca], "lo": pr["faixa"][ca][0], "hi": pr["faixa"][ca][1],
         "tse_a": (ap.get("pct_validos") or {}).get(ca), "tse_secoes": ap.get("pct_secoes")}
    try:
        h = le(caminho)
    except (FileNotFoundError, ValueError):
        h = {"schema": 1, "tipo": "projecao_historico", "candidato_a": ca, "entradas": []}
    if h["entradas"] and {k: v for k, v in h["entradas"][-1].items() if k != "t"} == {k: v for k, v in e.items() if k != "t"}:
        return  # nada mudou
    h["entradas"].append(e)
    grava(caminho, h)
    with open(os.path.join(os.path.dirname(caminho), "..", "..", "projecao-log.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(out, ensure_ascii=False) + "\n")  # cópia completa de cada projeção publicada


def assinatura(a):
    h = hashlib.sha256()
    for f in (os.path.join(a.atual, "latest.json"), os.path.join(a.oficial, "latest.json")):
        try:
            h.update(open(f, "rb").read())
        except FileNotFoundError:
            pass
    return h.hexdigest()


def grava(caminho, obj):
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, caminho)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base1t", default=os.path.join(P, "saida", "municipios-1t", "data"))
    ap.add_argument("--atual", default=os.path.join(P, "saida", "municipios", "data"))
    ap.add_argument("--oficial", default=os.path.join(P, "saida", "oficial", "data"))
    ap.add_argument("--oficial1t", default=os.path.join(P, "saida", "teste1t", "data"))
    ap.add_argument("--saida", default=os.path.join(P, "saida", "oficial", "data", "projecao.json"))
    ap.add_argument("--laco", type=float, help="recalcula quando os dados mudam (segundos entre conferências)")
    a = ap.parse_args()
    ult = None
    while True:
        s = assinatura(a)
        if s != ult:
            t0 = time.time()
            try:
                out = calcula(a)
                grava(a.saida, out)
                registra_historico(os.path.join(os.path.dirname(a.saida), "projecao-historico.json"), out)
                ult = s
                print(json.dumps({"t": agora(), "status": out["status"], "cidades": out["base"]["cidades_finalizadas"],
                                  "proj": out.get("projecao", {}).get("pct_validos"), "s": round(time.time() - t0, 1)}), flush=True)
            except Exception as e:  # nunca derruba: mantém o último arquivo bom
                print(json.dumps({"t": agora(), "erro": f"{type(e).__name__}: {e}"}), flush=True)
        if not a.laco:
            break
        time.sleep(a.laco)


if __name__ == "__main__":
    main()
