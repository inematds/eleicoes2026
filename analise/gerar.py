#!/usr/bin/env python3
"""Análise do resultado: 1º turno x 2º turno (só lê arquivos locais, não consulta o TSE).

Fatos (cidade a cidade, só cidades finalizadas nos dois turnos):
  variação de votos de Lula e Flávio, comparecimento, brancos/nulos, cidades que viraram,
  onde Flávio perdeu votos, onde Lula mais ganhou.
Estimativa (modelo da Projeção, que compara milhares de cidades — o voto é secreto):
  para onde foram os votos de cada candidato do 1º turno, e a "cascata" de cada finalista.

Grava <saida>/analise.json (padrão: saida/oficial/data/analise.json).
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
          "pr": "S", "rs": "S", "sc": "S"}


def ultimo(pasta):
    fs = sorted(glob.glob(os.path.join(pasta, "v*.json")))
    return json.load(open(fs[-1])) if fs else None


def carrega(base):
    """{codigo_ibge: cidade} e nomes dos candidatos, do último arquivo de cada UF."""
    cid, nomes = {}, {}
    for d in sorted(glob.glob(os.path.join(base, "data", "uf", "*"))):
        x = ultimo(d)
        if not x:
            continue
        for c in x.get("candidatos", []):
            nomes[c["numero"]] = c["nome_urna"]
        uf = os.path.basename(d)
        for k, c in x["cidades"].items():
            c = dict(c, uf=uf)
            cid[k] = c
    return cid, nomes


def g(c, n):
    return (c.get("c") or {}).get(n, 0) or 0


def fatos(t1, t2):
    tot = {k: 0 for k in ("lula_1t", "lula_2t", "flavio_1t", "flavio_2t", "outros_1t", "bn_1t", "bn_2t",
                          "comp_1t", "comp_2t", "eleitores")}
    por_uf, cidades = {}, []
    for k, b in t2.items():
        a = t1.get(k)
        if not a or b.get("and") != "finalizada" or a.get("and") != "finalizada":
            continue
        l1, l2, f1, f2 = g(a, A), g(b, A), g(a, B), g(b, B)
        outros = (a.get("vv") or 0) - l1 - f1
        bn1, bn2 = (a.get("vb") or 0) + (a.get("vn") or 0), (b.get("vb") or 0) + (b.get("vn") or 0)
        for kk, v in (("lula_1t", l1), ("lula_2t", l2), ("flavio_1t", f1), ("flavio_2t", f2), ("outros_1t", outros),
                      ("bn_1t", bn1), ("bn_2t", bn2), ("comp_1t", a.get("comp") or 0), ("comp_2t", b.get("comp") or 0),
                      ("eleitores", b.get("te") or 0)):
            tot[kk] += v
        lid1 = A if l1 > f1 else B if f1 > l1 else None
        lid2 = A if l2 > f2 else B if f2 > l2 else None
        s1 = 100 * l1 / (l1 + f1) if l1 + f1 else None  # parte de Lula entre os dois no 1º turno
        s2 = 100 * l2 / (l2 + f2) if l2 + f2 else None
        reg = {"nm": b["nm"], "uf": b["uf"], "te": b.get("te") or 0, "cap": bool(b.get("cap")),
               "l1": l1, "l2": l2, "f1": f1, "f2": f2, "dl": l2 - l1, "df": f2 - f1,
               "pl1": round(100 * l1 / a["vv"], 2) if a.get("vv") else None,
               "pl2": b.get("p", {}).get(A), "pf1": round(100 * f1 / a["vv"], 2) if a.get("vv") else None,
               "pf2": b.get("p", {}).get(B), "lid1": lid1, "lid2": lid2,
               "dcomp": (b.get("comp") or 0) - (a.get("comp") or 0),
               "subiu_lula_pp": round(s2 - s1, 2) if s1 is not None and s2 is not None else None}
        cidades.append(reg)
        u = por_uf.setdefault(b["uf"], {"cidades": 0, "flavio_perdeu": 0, "lula_perdeu": 0, "viradas_lula": 0,
                                         "viradas_flavio": 0, "dl": 0, "df": 0, "l1": 0, "l2": 0, "f1": 0, "f2": 0})
        u["cidades"] += 1
        u["flavio_perdeu"] += reg["df"] < 0
        u["lula_perdeu"] += reg["dl"] < 0
        u["viradas_lula"] += lid1 == B and lid2 == A
        u["viradas_flavio"] += lid1 == A and lid2 == B
        for kk in ("dl", "df", "l1", "l2", "f1", "f2"):
            u[kk] += reg[kk]
    for uf, u in por_uf.items():
        u["cid_total"] = sum(1 for c in t2.values() if c["uf"] == uf)
        u["pct_flavio_perdeu"] = round(100 * u["flavio_perdeu"] / u["cidades"], 1) if u["cidades"] else 0
    corta = lambda c: {k: c[k] for k in ("nm", "uf", "te", "cap", "l1", "l2", "f1", "f2", "dl", "df", "pl1", "pl2",
                                          "pf1", "pf2", "dcomp", "subiu_lula_pp")}
    perdas_f = sorted((c for c in cidades if c["df"] < 0), key=lambda c: c["df"])
    perdas_l = sorted((c for c in cidades if c["dl"] < 0), key=lambda c: c["dl"])
    ganhos_l = sorted(cidades, key=lambda c: -c["dl"])
    sobe_pp = sorted((c for c in cidades if c["te"] >= 20000 and c["subiu_lula_pp"] is not None),
                     key=lambda c: -c["subiu_lula_pp"])
    viradas = sorted((c for c in cidades if c["lid1"] and c["lid2"] and c["lid1"] != c["lid2"]), key=lambda c: -c["te"])
    return {
        "cidades_comparadas": len(cidades), "cidades_total": len(t2),
        "totais": tot,
        "flavio_perdeu_cidades": len(perdas_f), "lula_perdeu_cidades": len(perdas_l),
        "viradas": {"para_lula": sum(1 for c in viradas if c["lid2"] == A),
                    "para_flavio": sum(1 for c in viradas if c["lid2"] == B)},
        "por_uf": por_uf,
        "top_perdas_flavio": [corta(c) for c in perdas_f[:25]],
        "top_perdas_lula": [corta(c) for c in perdas_l[:10]],
        "top_ganhos_lula": [corta(c) for c in ganhos_l[:15]],
        "top_subiu_lula_pp": [corta(c) for c in sobe_pp[:15]],
        "viradas_lista": [dict(corta(c), para=c["lid2"]) for c in viradas[:60]],
    }


def cascata(trans, num, apurado):
    """Votos de um finalista no 2º turno decompostos pela origem no 1º turno (estimativa)."""
    nome_proprio = None
    partes = []
    base = 0
    for o in trans:
        v = o["votos_1t"] * o["para"].get(num, 0) / 100
        perde = o["votos_1t"] * (100 - o["para"].get(num, 0)) / 100
        if o["para"].get(num, 0) >= 90:  # o próprio candidato
            nome_proprio = o["origem"]
            base = o["votos_1t"]
            if perde >= 1:
                partes.append({"origem": "Eleitores dele no 1º turno que não repetiram", "votos": -round(perde)})
            continue
        if v >= 1:
            partes.append({"origem": o["origem"], "votos": round(v)})
    est = base + sum(p["votos"] for p in partes)
    return {"proprio": nome_proprio, "base_1t": base, "partes": partes, "estimado": round(est),
            "apurado": apurado, "diferenca_modelo": apurado - round(est) if apurado is not None else None}


def campo(partido, coligacao):
    """L = campo de Lula (coligação com o PT ou federação dele), F = campo de Flávio (coligação com o PL), O = outros."""
    toks = {t.strip().upper().replace(" DO ", "").replace(" ", "") for t in (coligacao or partido or "").split("/")}
    toks.add((partido or "").upper().replace(" DO ", "").replace(" ", ""))
    l, f = "PT" in toks or (not coligacao and toks & {"PCDOB", "PV"}), "PL" in toks
    return "M" if l and f else "L" if l else "F" if f else "O"


def estaduais(t1, t2, pasta):
    """Senador e governador x presidente, cidade a cidade e por estado (FATO, só contas sobre o TSE)."""
    if not os.path.isdir(pasta):
        return None
    por_cd1 = {c["cd"]: c for c in t1.values()}
    por_cd2 = {c["cd"]: c for c in t2.values()}
    ufs, pontos = {}, []
    for arq in sorted(glob.glob(os.path.join(pasta, "*.json"))):
        uf = os.path.basename(arq)[:2]
        dados = json.load(open(arq))
        u = {"cidades": 0, "te": 0, "lula1": 0, "flavio1": 0, "vv1": 0, "lula2": 0, "flavio2": 0,
             "senL": 0, "senF": 0, "senV": 0, "govL": 0, "govF": 0, "govV": 0, "gov2L": 0, "gov2F": 0, "gov2V": 0,
             "div_gov": 0, "div_gov_base": 0, "div_sen": 0, "div_sen_base": 0, "eleitos_sen": {}, "gov": {}, "gov2": {}}
        for cd, r in dados.items():
            a, b = por_cd1.get(cd), por_cd2.get(cd)
            if not a or not b or b.get("and") != "finalizada" or a.get("and") != "finalizada":
                continue
            s1, g1, g2 = r.get("s1"), r.get("g1"), r.get("g2")
            if not s1 or not g1 or not s1.get("vv") or not g1.get("vv"):
                continue
            l1, f1, l2, f2 = g(a, A), g(a, B), g(b, A), g(b, B)
            sl = sum(c[4] for c in s1["c"] if campo(c[2], c[3]) == "L")
            sf = sum(c[4] for c in s1["c"] if campo(c[2], c[3]) == "F")
            gl = sum(c[4] for c in g1["c"] if campo(c[2], c[3]) == "L")
            gf = sum(c[4] for c in g1["c"] if campo(c[2], c[3]) == "F")
            u["cidades"] += 1; u["te"] += b.get("te") or 0
            u["lula1"] += l1; u["flavio1"] += f1; u["vv1"] += a.get("vv") or 0; u["lula2"] += l2; u["flavio2"] += f2
            u["senL"] += sl; u["senF"] += sf; u["senV"] += s1["vv"]; u["govL"] += gl; u["govF"] += gf; u["govV"] += g1["vv"]
            for c in s1["c"]:
                if c[5]:
                    u["eleitos_sen"][c[1]] = [c[2], campo(c[2], c[3])]
            for c in g1["c"]:
                u["gov"].setdefault(c[1], [c[2], campo(c[2], c[3]), 0, c[5]])
                u["gov"][c[1]][2] += c[4]
            vence_pres = A if l2 > f2 else B
            # governador: vencedor na cidade é de um dos campos? compara com o vencedor de presidente no 2º turno
            gv = g2 if g2 and g2.get("c") else g1
            gcamp = campo(gv["c"][0][2], gv["c"][0][3]) if gv["c"] else "O"
            if gcamp in ("L", "F"):
                u["div_gov_base"] += 1
                u["div_gov"] += (gcamp == "L") != (vence_pres == A)
            if g2 and g2.get("c") and g2.get("vv"):
                u["gov2L"] += sum(c[4] for c in g2["c"] if campo(c[2], c[3]) == "L")
                u["gov2F"] += sum(c[4] for c in g2["c"] if campo(c[2], c[3]) == "F")
                u["gov2V"] += g2["vv"]
                for c in g2["c"]:
                    u["gov2"].setdefault(c[1], [c[2], campo(c[2], c[3]), 0, c[5]])
                    u["gov2"][c[1]][2] += c[4]
            if sl or sf:
                u["div_sen_base"] += 1
                u["div_sen"] += (sl > sf) != (vence_pres == A)
            pontos.append([uf, round(100 * l2 / (l2 + f2), 1) if l2 + f2 else None,
                           round(100 * sl / s1["vv"], 1), round(100 * sf / s1["vv"], 1),
                           round(100 * gl / g1["vv"], 1), round(100 * gf / g1["vv"], 1), b.get("te") or 0])
        if not u["cidades"]:
            continue
        pc = lambda x, y: round(100 * x / y, 2) if y else None
        gov = sorted(u["gov"].items(), key=lambda kv: -kv[1][2])
        gov2 = sorted(u["gov2"].items(), key=lambda kv: -kv[1][2])
        ufs[uf] = {
            "cidades": u["cidades"], "eleitores": u["te"],
            "lula_1t": pc(u["lula1"], u["vv1"]), "flavio_1t": pc(u["flavio1"], u["vv1"]),
            "lula_2t": pc(u["lula2"], u["lula2"] + u["flavio2"]), "flavio_2t": pc(u["flavio2"], u["lula2"] + u["flavio2"]),
            "senado_L": pc(u["senL"], u["senV"]), "senado_F": pc(u["senF"], u["senV"]),
            "gov1_L": pc(u["govL"], u["govV"]), "gov1_F": pc(u["govF"], u["govV"]),
            "gov2_L": pc(u["gov2L"], u["gov2V"]), "gov2_F": pc(u["gov2F"], u["gov2V"]),
            "senadores_eleitos": [{"nome": k, "partido": v[0], "campo": v[1]} for k, v in u["eleitos_sen"].items()],
            "governador_1t": [{"nome": k, "partido": v[0], "campo": v[1], "votos": v[2], "pct": pc(v[2], u["govV"])} for k, v in gov[:2]],
            "governador_2t": [{"nome": k, "partido": v[0], "campo": v[1], "votos": v[2], "pct": pc(v[2], u["gov2V"])} for k, v in gov2[:2]] or None,
            "voto_dividido_gov": pc(u["div_gov"], u["div_gov_base"]), "cidades_div_gov": u["div_gov"],
            "voto_dividido_sen": pc(u["div_sen"], u["div_sen_base"]), "cidades_div_sen": u["div_sen"],
        }
    return {"ufs": ufs, "pontos": pontos,
            "campos": {"L": "campo de Lula (coligação com o PT)", "F": "campo de Flávio (coligação com o PL)",
                       "O": "outros", "M": "coligação com PT e PL"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t1", default=os.path.join(P, "saida", "municipios-1t"))
    ap.add_argument("--t2", default=os.path.join(P, "saida", "municipios"))
    ap.add_argument("--oficial", default=os.path.join(P, "saida", "oficial", "data"))
    ap.add_argument("--estaduais", default=os.path.join(P, "saida", "estaduais"))
    a = ap.parse_args()
    t1, nomes1 = carrega(a.t1)
    t2, _ = carrega(a.t2)
    proj = json.load(open(os.path.join(a.oficial, "projecao.json")))
    lat = json.load(open(os.path.join(a.oficial, "latest.json")))
    br = json.load(open(os.path.join(a.oficial, lat["abrangencias"]["br"]["arquivo"])))
    votos2 = {c["numero"]: c["votos"] for c in br["candidatos"]}
    trans = proj.get("transferencias") or {}
    out = {
        "schema": 1, "tipo": "analise",
        "gerado_em": datetime.now(BRT).isoformat(timespec="seconds"),
        "tse": {"totalizado_tse": br["fonte"]["totalizado_tse"], "pct_secoes": br["secoes"]["pct_totalizadas"],
                "pct_validos": {c["numero"]: c["pct_validos"] for c in br["candidatos"]}, "votos": votos2,
                "final": br["situacao"]["totalizacao_final"]},
        "candidatos": [{"numero": c["numero"], "nome_urna": c["nome_urna"]} for c in br["candidatos"]],
        "candidatos_1t": nomes1,
        "fatos": fatos(t1, t2),
        "estimativa": {
            "projecao_calculada_em": proj.get("calculado_em"), "status": proj.get("status"),
            "nome_regiao": proj.get("nome_regiao"),
            "transferencias": trans,
            "cascata": {n: cascata(trans.get("BR", []), n, votos2.get(n)) for n in (A, B)} if trans.get("BR") else None,
        },
        "estaduais": estaduais(t1, t2, a.estaduais),
    }
    dest = os.path.join(a.oficial, "analise.json")
    tmp = dest + ".tmp"
    json.dump(out, open(tmp, "w"), ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, dest)
    f = out["fatos"]
    print(json.dumps({"cidades": f["cidades_comparadas"], "flavio_perdeu": f["flavio_perdeu_cidades"],
                      "viradas": f["viradas"], "bytes": os.path.getsize(dest)}))
    # as outras páginas de análise (Raio-X, Conferência, Por que perdeu): uma falha não derruba as outras
    import subprocess
    import sys
    for extra in ("raiox.py", "conferencia.py", "derrota.py"):
        arq = os.path.join(P, "analise", extra)
        if os.path.exists(arq):
            r = subprocess.run([sys.executable, arq], capture_output=True, text=True, timeout=240)
            print(json.dumps({"extra": extra, "rc": r.returncode, "erro": r.stderr.strip()[-300:]}))


if __name__ == "__main__":
    main()
