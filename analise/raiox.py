#!/usr/bin/env python3
"""Raio-X do 2º turno (só lê arquivos locais, não consulta o TSE; tudo é conta direta, nada de estimativa).

Blocos:
  saldo          de onde veio a diferença: Lula − Flávio por estado (arquivos oficiais do TSE por UF) e por região
  concentracao   quantas cidades bastam para somar metade do saldo bruto de cada um; top 10 de cada lado
  cenario        exercício matemático sobre a margem nacional (não é previsão)
  comparecimento 1º x 2º turno por estado e cidade; brancos e nulos
  crescimento    onde um candidato cresceu em votos mas caiu em % (ou o inverso)

Grava <oficial>/raiox.json (padrão: saida/oficial/data/raiox.json).
"""
import argparse
import glob
import json
import os
from datetime import datetime, timedelta, timezone

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRT = timezone(timedelta(hours=-3))
A, B = "13", "22"
REGIAO = {"ac": "N", "am": "N", "ap": "N", "pa": "N", "ro": "N", "rr": "N", "to": "N",
          "al": "NE", "ba": "NE", "ce": "NE", "ma": "NE", "pb": "NE", "pe": "NE", "pi": "NE", "rn": "NE", "se": "NE",
          "df": "CO", "go": "CO", "ms": "CO", "mt": "CO", "es": "SE", "mg": "SE", "rj": "SE", "sp": "SE",
          "pr": "S", "rs": "S", "sc": "S", "zz": "EX"}
NOME_REGIAO = {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul", "EX": "Exterior"}


def ultimo(pasta):
    fs = sorted(glob.glob(os.path.join(pasta, "v*.json")))
    return json.load(open(fs[-1])) if fs else None


def carrega(base):
    """{codigo_ibge: cidade}, {uf: arquivo do estado sem as cidades} — último arquivo de cada UF (mesma lógica de gerar.py)."""
    cid, est = {}, {}
    for d in sorted(glob.glob(os.path.join(base, "data", "uf", "*"))):
        x = ultimo(d)
        if not x:
            continue
        uf = os.path.basename(d)
        est[uf] = {k: v for k, v in x.items() if k != "cidades"}
        for k, c in x["cidades"].items():
            cid[k] = dict(c, uf=uf)
    return cid, est


def g(c, n):
    return (c.get("c") or {}).get(n, 0) or 0


def pc(a, b, nd=2):
    return round(100 * a / b, nd) if b else None


def fin(c):
    return c is not None and c.get("and") == "finalizada"


def hora_cidades(est):
    hs = [e.get("publicado_em") for e in est.values() if e.get("publicado_em")]
    return max(hs) if hs else None


# ---------- 1. saldo por estado ----------
def bloco_saldo(oficial, lat, br):
    ufs, regs = [], {}
    horas = []
    for abr, info in lat["abrangencias"].items():
        if abr == "br":
            continue
        x = json.load(open(os.path.join(oficial, info["arquivo"])))
        v = {c["numero"]: c["votos"] for c in x["candidatos"]}
        l, f = v.get(A, 0), v.get(B, 0)
        horas.append(x["fonte"]["totalizado_tse"])
        r = {"uf": abr, "reg": REGIAO.get(abr), "l": l, "f": f, "s": l - f, "vv": x["votos"]["validos"],
             "pl": next((c["pct_validos"] for c in x["candidatos"] if c["numero"] == A), None),
             "pf": next((c["pct_validos"] for c in x["candidatos"] if c["numero"] == B), None),
             "pct_secoes": x["secoes"]["pct_totalizadas"], "totalizado_tse": x["fonte"]["totalizado_tse"],
             "situacao": x["situacao"]["andamento"]}
        ufs.append(r)
        rg = regs.setdefault(r["reg"], {"reg": r["reg"], "nome": NOME_REGIAO[r["reg"]], "l": 0, "f": 0, "s": 0, "vv": 0, "ufs": 0})
        for k in ("l", "f", "s", "vv"):
            rg[k] += r[k]
        rg["ufs"] += 1
    ufs.sort(key=lambda r: -r["s"])
    regs = sorted(regs.values(), key=lambda r: -r["s"])
    for rg in regs:
        rg["pl"] = pc(rg["l"], rg["vv"])
    soma = sum(r["s"] for r in ufs)
    vb = {c["numero"]: c["votos"] for c in br["candidatos"]}
    return {
        "fonte": "TSE, resultado oficial de cada estado e do exterior (arquivos por UF)",
        "totalizado_tse": max(horas) if horas else None, "totalizado_min": min(horas) if horas else None,
        "cobertura": {"abrangencias": len(ufs), "finalizadas": sum(1 for r in ufs if r["situacao"] == "finalizada")},
        "ufs": ufs, "regioes": regs, "soma_ufs": soma,
        "margem_br": vb.get(A, 0) - vb.get(B, 0),
        "estados_lula": sum(1 for r in ufs if r["s"] > 0), "estados_flavio": sum(1 for r in ufs if r["s"] < 0),
    }


# ---------- 2. concentração ----------
def bloco_concentracao(t2, est2):
    fins = [c for c in t2.values() if fin(c)]
    out = {"fonte": "TSE, resultado por cidade do 2º turno (só cidades finalizadas)",
           "totalizado": hora_cidades(est2),
           "cobertura": {"fin": len(fins), "total": len(t2), "eleitores_fin": sum(c.get("te") or 0 for c in fins)},
           "por": {}}
    for num, outro in ((A, B), (B, A)):
        lado = []
        for c in fins:
            s = g(c, num) - g(c, outro)
            if s > 0:
                lado.append((s, c))
        lado.sort(key=lambda x: -x[0])
        bruto = sum(s for s, _ in lado)
        acc, k, el = 0, 0, 0
        for s, c in lado:
            acc += s
            k += 1
            el += c.get("te") or 0
            if acc * 2 >= bruto:
                break
        out["por"][num] = {
            "saldo_bruto": bruto, "cidades_venceu": len(lado), "cidades_metade": k, "eleitores_metade": el,
            "pct_cidades_metade": pc(k, len(lado), 1), "saldo_metade": acc,
            "top10_saldo": sum(s for s, _ in lado[:10]),
            "top": [{"nm": c["nm"], "uf": c["uf"], "te": c.get("te") or 0, "cap": bool(c.get("cap")), "s": s,
                     "l": g(c, A), "f": g(c, B), "pl": (c.get("p") or {}).get(A), "pf": (c.get("p") or {}).get(B)}
                    for s, c in lado[:10]],
        }
    empates = sum(1 for c in fins if g(c, A) == g(c, B))
    out["empates"] = empates
    return out


# ---------- 3. cenário aritmético ----------
def bloco_cenario(br):
    vb = {c["numero"]: c["votos"] for c in br["candidatos"]}
    lider = A if vb.get(A, 0) >= vb.get(B, 0) else B
    m = abs(vb.get(A, 0) - vb.get(B, 0))
    el, comp, abst, vv = br["eleitorado"]["total"], br["eleitorado"]["comparecimento"], br["eleitorado"]["abstencao"], br["votos"]["validos"]
    troca_empate = m / 2
    troca_virar = m // 2 + 1
    secoes = br["secoes"]["total"]
    return {
        "fonte": "TSE, resultado oficial do Brasil (inclui exterior)",
        "totalizado_tse": br["fonte"]["totalizado_tse"], "pct_secoes": br["secoes"]["pct_totalizadas"],
        "lider": lider, "margem": m, "pp_validos": round(abs((vb.get(A, 0) - vb.get(B, 0)) * 100 / vv), 2) if vv else None,
        "eleitorado": el, "comparecimento": comp, "abstencao": abst, "validos": vv,
        "brancos_nulos": br["votos"]["brancos"] + br["votos"]["nulos"],
        "troca_empate": troca_empate, "troca_virar": troca_virar,
        "troca_pct_eleitorado": round(100 * troca_virar / el, 3), "troca_pct_comparecimento": round(100 * troca_virar / comp, 3),
        "troca_pct_validos": round(100 * troca_virar / vv, 3),
        "troca_por_secao": round(troca_virar / secoes, 1) if secoes else None, "secoes": secoes,
        "abst_virar": m + 1, "abst_pct_comparecimento": round(100 * (m + 1) / comp, 3),
        "abst_pct_abstencao": round(100 * (m + 1) / abst, 2),
        "bn_virar": m + 1, "bn_pct_bn": round(100 * (m + 1) / (br["votos"]["brancos"] + br["votos"]["nulos"]), 1),
    }


# ---------- 4. comparecimento ----------
def exterior_1t():
    f = os.path.join(P, "saida", "exterior", "primeiro_turno.json")
    if not os.path.exists(f):
        return None
    s = json.load(open(f)).get("secoes") or {}
    t = {"te": 0, "comp": 0, "vb": 0, "vn": 0, "vv": 0, "l": 0, "f": 0, "secoes": len(s),
         "totalizadas": sum(1 for x in s.values() if x.get("situacao") == "Totalizada")}
    for x in s.values():
        t["te"] += x.get("aptos") or 0
        t["comp"] += x.get("comparecimento") or 0
        t["vb"] += x.get("brancos") or 0
        t["vn"] += x.get("nulos") or 0
        vs = x.get("votos") or {}
        t["vv"] += sum(vs.values())
        t["l"] += vs.get(A, 0)
        t["f"] += vs.get(B, 0)
    return t


def bloco_comparecimento(oficial, lat, br, t1, t2, est2):
    # 1º turno por UF = soma das cidades (todas finalizadas); exterior = soma das seções
    s1 = {}
    for c in t1.values():
        u = s1.setdefault(c["uf"], {"te": 0, "comp": 0, "vb": 0, "vn": 0, "vv": 0, "l": 0, "f": 0, "cid": 0, "fin": 0})
        u["te"] += c.get("te") or 0
        u["comp"] += c.get("comp") or 0
        u["vb"] += c.get("vb") or 0
        u["vn"] += c.get("vn") or 0
        u["vv"] += c.get("vv") or 0
        u["l"] += g(c, A)
        u["f"] += g(c, B)
        u["cid"] += 1
        u["fin"] += fin(c)
    ex = exterior_1t()
    if ex:
        s1["zz"] = dict(ex, cid=0, fin=0)
    ufs = []
    for abr, info in lat["abrangencias"].items():
        if abr == "br" or abr not in s1:
            continue
        x = json.load(open(os.path.join(oficial, info["arquivo"])))
        a = s1[abr]
        e2, v2 = x["eleitorado"], x["votos"]
        cv = {c["numero"]: c["votos"] for c in x["candidatos"]}
        r = {"uf": abr, "reg": REGIAO.get(abr),
             "te1": a["te"], "comp1": a["comp"], "pc1": pc(a["comp"], a["te"]),
             "te2": e2["total"], "comp2": e2["comparecimento"], "pc2": pc(e2["comparecimento"], e2["total"]),
             "bn1": a["vb"] + a["vn"], "bn2": v2["brancos"] + v2["nulos"],
             "pbn1": pc(a["vb"] + a["vn"], a["comp"]), "pbn2": pc(v2["brancos"] + v2["nulos"], v2["total"]),
             "pct_secoes2": x["secoes"]["pct_totalizadas"],
             # para o bloco de crescimento
             "l1": a["l"], "f1": a["f"], "vv1": a["vv"], "l2": cv.get(A, 0), "f2": cv.get(B, 0), "vv2": v2["validos"]}
        r["dcomp"] = r["comp2"] - r["comp1"]
        r["dpp"] = round(r["pc2"] - r["pc1"], 2) if r["pc1"] is not None and r["pc2"] is not None else None
        r["dbn"] = r["bn2"] - r["bn1"]
        ufs.append(r)
    ufs.sort(key=lambda r: -(r["dpp"] or 0))
    n1 = {k: sum(r[k] for r in ufs) for k in ("te1", "comp1", "bn1", "te2", "comp2", "bn2")}
    nac = {"te1": n1["te1"], "comp1": n1["comp1"], "pc1": pc(n1["comp1"], n1["te1"]), "bn1": n1["bn1"],
           "pbn1": pc(n1["bn1"], n1["comp1"]),
           "te2": br["eleitorado"]["total"], "comp2": br["eleitorado"]["comparecimento"],
           "pc2": pc(br["eleitorado"]["comparecimento"], br["eleitorado"]["total"]),
           "bn2": br["votos"]["brancos"] + br["votos"]["nulos"],
           "pbn2": pc(br["votos"]["brancos"] + br["votos"]["nulos"], br["votos"]["total"]),
           "b1": sum(s1[u]["vb"] for u in s1), "n1": sum(s1[u]["vn"] for u in s1),
           "b2": br["votos"]["brancos"], "n2": br["votos"]["nulos"],
           "abst1": n1["te1"] - n1["comp1"], "abst2": br["eleitorado"]["abstencao"]}
    nac["dcomp"] = nac["comp2"] - nac["comp1"]
    nac["dpp"] = round(nac["pc2"] - nac["pc1"], 2)
    nac["dbn"] = nac["bn2"] - nac["bn1"]

    # cidades finalizadas nos dois turnos
    cids = []
    for k, b in t2.items():
        a = t1.get(k)
        if not fin(a) or not fin(b) or not a.get("te") or not b.get("te"):
            continue
        p1, p2 = 100 * (a.get("comp") or 0) / a["te"], 100 * (b.get("comp") or 0) / b["te"]
        cids.append({"nm": b["nm"], "uf": b["uf"], "te": b["te"], "comp1": a.get("comp") or 0, "comp2": b.get("comp") or 0,
                     "pc1": round(p1, 2), "pc2": round(p2, 2), "dcomp": (b.get("comp") or 0) - (a.get("comp") or 0),
                     "dpp": round(p2 - p1, 2)})
    grandes = [c for c in cids if c["te"] >= 10000]
    top = lambda lst, key, rev: sorted(lst, key=lambda c: c[key], reverse=rev)[:10]
    subiu = sum(1 for c in cids if c["dcomp"] > 0)
    caiu = sum(1 for c in cids if c["dcomp"] < 0)
    return {
        "fonte": "2º turno: TSE, resultado oficial de cada estado. 1º turno: soma das cidades do TSE (todas finalizadas) e, no exterior, soma das seções",
        "totalizado_tse": br["fonte"]["totalizado_tse"], "totalizado_cidades": hora_cidades(est2),
        "cobertura": {"ufs": len(ufs), "cidades_comparadas": len(cids), "cidades_total": len(t2),
                      "cidades_10mil": len(grandes), "exterior_1t_secoes": ex["secoes"] if ex else 0,
                      "exterior_1t_totalizadas": ex["totalizadas"] if ex else 0},
        "nacional": nac, "ufs": ufs,
        "cidades": {"subiu": subiu, "caiu": caiu, "igual": len(cids) - subiu - caiu,
                    "mais_votos": top(cids, "dcomp", True), "menos_votos": top(cids, "dcomp", False),
                    "mais_pp": top(grandes, "dpp", True), "menos_pp": top(grandes, "dpp", False)},
    }


# ---------- 5. crescimento em votos x em % ----------
def bloco_crescimento(t1, t2, ufs_comp, est2):
    quad = lambda dv, dp: ("vs_pd" if dv > 0 and dp < 0 else "vd_ps" if dv < 0 and dp > 0 else
                           "ambos_s" if dv > 0 and dp > 0 else "ambos_d" if dv < 0 and dp < 0 else "outro")
    por_uf, ex = {}, {A: {"vs_pd": [], "vd_ps": []}, B: {"vs_pd": [], "vd_ps": []}}
    cont = {A: {}, B: {}}
    n = 0
    for k, b in t2.items():
        a = t1.get(k)
        if not fin(a) or not fin(b) or not a.get("vv") or not b.get("vv"):
            continue
        n += 1
        u = por_uf.setdefault(b["uf"], {"cid": 0, A: {"vs_pd": 0, "vd_ps": 0}, B: {"vs_pd": 0, "vd_ps": 0}})
        u["cid"] += 1
        for num in (A, B):
            v1, v2 = g(a, num), g(b, num)
            p1, p2 = 100 * v1 / a["vv"], 100 * v2 / b["vv"]
            q = quad(v2 - v1, p2 - p1)
            cont[num][q] = cont[num].get(q, 0) + 1
            if q in ("vs_pd", "vd_ps"):
                u[num][q] += 1
                ex[num][q].append({"nm": b["nm"], "uf": b["uf"], "te": b.get("te") or 0, "v1": v1, "v2": v2,
                                   "p1": round(p1, 2), "p2": round(p2, 2)})
    for num in ex:
        for q in ex[num]:
            ex[num][q] = sorted(ex[num][q], key=lambda c: -c["te"])[:8]
    estados = []
    for r in ufs_comp:
        lin = {"uf": r["uf"]}
        for num, k1, k2 in ((A, "l1", "l2"), (B, "f1", "f2")):
            p1, p2 = pc(r[k1], r["vv1"]), pc(r[k2], r["vv2"])
            lin[num] = {"v1": r[k1], "v2": r[k2], "dv": r[k2] - r[k1], "p1": p1, "p2": p2,
                        "dp": round(p2 - p1, 2) if p1 is not None and p2 is not None else None,
                        "q": quad(r[k2] - r[k1], (p2 or 0) - (p1 or 0))}
        u = por_uf.get(r["uf"])
        lin["cid"] = u["cid"] if u else 0
        lin["cid_q"] = {A: u[A], B: u[B]} if u else None
        estados.append(lin)
    return {
        "fonte": "TSE: votos de cada candidato e votos válidos, 1º e 2º turno (estados: 2º turno oficial, 1º turno soma das cidades; cidades: só finalizadas nos dois turnos)",
        "totalizado": hora_cidades(est2),
        "cobertura": {"cidades": n, "cidades_total": len(t2)},
        "contagem": cont, "exemplos": ex, "estados": estados,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oficial", default=os.path.join(P, "saida", "oficial", "data"))
    ap.add_argument("--t1", default=os.path.join(P, "saida", "municipios-1t"))
    ap.add_argument("--t2", default=os.path.join(P, "saida", "municipios"))
    a = ap.parse_args()
    t1, _ = carrega(a.t1)
    t2, est2 = carrega(a.t2)
    lat = json.load(open(os.path.join(a.oficial, "latest.json")))
    br = json.load(open(os.path.join(a.oficial, lat["abrangencias"]["br"]["arquivo"])))
    comp = bloco_comparecimento(a.oficial, lat, br, t1, t2, est2)
    ufs_comp = comp["ufs"]
    out = {
        "schema": 1, "tipo": "raiox",
        "gerado_em": datetime.now(BRT).isoformat(timespec="seconds"),
        "tse": {"totalizado_tse": br["fonte"]["totalizado_tse"], "pct_secoes": br["secoes"]["pct_totalizadas"],
                "pct_validos": {c["numero"]: c["pct_validos"] for c in br["candidatos"]},
                "votos": {c["numero"]: c["votos"] for c in br["candidatos"]},
                "final": br["situacao"]["totalizacao_final"]},
        "candidatos": [{"numero": c["numero"], "nome_urna": c["nome_urna"]} for c in br["candidatos"]],
        "saldo": bloco_saldo(a.oficial, lat, br),
        "concentracao": bloco_concentracao(t2, est2),
        "cenario": bloco_cenario(br),
        "comparecimento": comp,
        "crescimento": bloco_crescimento(t1, t2, ufs_comp, est2),
    }
    for u in comp["ufs"]:  # campos usados só no bloco de crescimento
        for k in ("l1", "f1", "vv1", "l2", "f2", "vv2"):
            u.pop(k, None)
    dest = os.path.join(a.oficial, "raiox.json")
    tmp = dest + ".tmp"
    json.dump(out, open(tmp, "w"), ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, dest)
    s, c, ce, cp = out["saldo"], out["concentracao"], out["cenario"], comp["nacional"]
    print(json.dumps({"margem_br": s["margem_br"], "soma_ufs": s["soma_ufs"],
                      "top_lula": [(r["uf"], r["s"]) for r in s["ufs"][:3]],
                      "top_flavio": [(r["uf"], r["s"]) for r in s["ufs"][-3:]],
                      "metade": {k: (v["cidades_metade"], v["cidades_venceu"]) for k, v in c["por"].items()},
                      "troca_virar": ce["troca_virar"], "dcomp": cp["dcomp"], "dpp": cp["dpp"],
                      "bytes": os.path.getsize(dest)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
