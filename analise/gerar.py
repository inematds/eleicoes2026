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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t1", default=os.path.join(P, "saida", "municipios-1t"))
    ap.add_argument("--t2", default=os.path.join(P, "saida", "municipios"))
    ap.add_argument("--oficial", default=os.path.join(P, "saida", "oficial", "data"))
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
    }
    dest = os.path.join(a.oficial, "analise.json")
    tmp = dest + ".tmp"
    json.dump(out, open(tmp, "w"), ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, dest)
    f = out["fatos"]
    print(json.dumps({"cidades": f["cidades_comparadas"], "flavio_perdeu": f["flavio_perdeu_cidades"],
                      "viradas": f["viradas"], "bytes": os.path.getsize(dest)}))


if __name__ == "__main__":
    main()
