#!/usr/bin/env python3
"""A virada de 10,4 milhões: o que a matemática explica e o que ainda dá para investigar (só arquivos locais).

Três níveis, como na investigação proposta:
  1. Brasil: placar oficial do 1º e do 2º turno, a conta que sempre fecha (identidade contábil) e por que
     a "coincidência" de qualquer divisão dos votos não prova transferência nenhuma.
  2. Estados, regiões e cidades: onde cada um ganhou votos, como votou cada estado, a lupa por estado.
  3. Boletins de urna x totalização: o que já está conferido (menu Conferência) e o que ainda falta.
Mais a checagem dos gráficos que circularam nas redes (afirmação x número oficial final).

Fontes: 1º turno oficial final (saida/teste1t/data: br + 27 UFs + exterior), 2º turno oficial
(saida/oficial/data via latest.json), cidades (saida/municipios-1t e saida/municipios) e a estimativa
de transferências já calculada pela Projeção (analise.json). Grava <oficial>/virada.json de forma atômica.
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(P, "analise"))
from gerar import REGIAO  # noqa: E402

BRT = timezone(timedelta(hours=-3))
A, B = "13", "22"
NOME_REG = {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul", "EX": "Exterior"}


def ultimo(pasta):
    fs = sorted(glob.glob(os.path.join(pasta, "v*.json")))
    return json.load(open(fs[-1])) if fs else None


def pc(x, y, nd=2):
    return round(100 * x / y, nd) if y else None


def resumo(r):
    """Números de um arquivo de abrangência (br ou uf) do TSE."""
    v = {c["numero"]: c["votos"] for c in r["candidatos"]}
    vv = r["votos"]["validos"]
    l, f = v.get(A, 0), v.get(B, 0)
    return {"lula": l, "flavio": f, "outros": vv - l - f, "validos": vv, "brancos": r["votos"]["brancos"],
            "nulos": r["votos"]["nulos"], "comp": r["eleitorado"]["comparecimento"],
            "abst": r["eleitorado"]["abstencao"], "eleitores": r["eleitorado"]["total"],
            "pl": pc(l, vv), "pf": pc(f, vv), "cand": v,
            "final": bool(r["situacao"].get("totalizacao_final")), "pct_secoes": r["secoes"]["pct_totalizadas"],
            "totalizado_tse": r["fonte"].get("totalizado_tse")}


def cidades(base):
    out = {}
    for d in sorted(glob.glob(os.path.join(base, "data", "uf", "*"))):
        x = ultimo(d)
        if not x:
            continue
        uf = os.path.basename(d)
        for c in x["cidades"].values():
            out[c["cd"]] = dict(c, uf=uf)
    return out


def g(c, n):
    return (c.get("c") or {}).get(n, 0) or 0


def divisao(nome, lula_de, flavio_de, D, dl, df):
    """Uma forma de dividir as categorias entre os dois: o que sobra é sempre igual e de sinal oposto."""
    al = sum(D[k] for k in lula_de)
    af = sum(D[k] for k in flavio_de)
    return {"nome": nome, "lula_de": lula_de, "flavio_de": flavio_de, "atrib_lula": al, "atrib_flavio": af,
            "sobra_lula": dl - al, "sobra_flavio": df - af}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t1", default=os.path.join(P, "saida", "teste1t", "data"), help="1º turno oficial final (br/ e uf/)")
    ap.add_argument("--oficial", default=os.path.join(P, "saida", "oficial", "data"))
    ap.add_argument("--mun1", default=os.path.join(P, "saida", "municipios-1t"))
    ap.add_argument("--mun2", default=os.path.join(P, "saida", "municipios"))
    a = ap.parse_args()

    br1 = resumo(ultimo(os.path.join(a.t1, "br")))
    lat = json.load(open(os.path.join(a.oficial, "latest.json")))
    ab = lat["abrangencias"]
    br2 = resumo(json.load(open(os.path.join(a.oficial, ab["br"]["arquivo"]))))
    nomes1 = {c["numero"]: c["nome_urna"] for c in ultimo(os.path.join(a.t1, "br"))["candidatos"]}

    # ---------- nível 1: Brasil ----------
    dl, df = br2["lula"] - br1["lula"], br2["flavio"] - br1["flavio"]
    D = {"outros": br1["outros"], "comp": br2["comp"] - br1["comp"],
         "brancos": br1["brancos"] - br2["brancos"], "nulos": br1["nulos"] - br2["nulos"]}
    # identidade: ΔLula + ΔFlávio = Δcomparecimento − Δbrancos − Δnulos + votos dos outros no 1º turno
    lado_dir = D["comp"] + D["brancos"] + D["nulos"] + D["outros"]
    assert dl + df == lado_dir, (dl + df, lado_dir)
    divs = [
        divisao("A do texto que circula", ["outros", "nulos"], ["comp", "brancos"], D, dl, df),
        divisao("Outra divisão possível", ["outros"], ["comp", "brancos", "nulos"], D, dl, df),
        divisao("Mais uma", ["outros", "brancos", "nulos"], ["comp"], D, dl, df),
        divisao("Tudo para Lula, nada para Flávio", ["outros", "brancos", "nulos", "comp"], [], D, dl, df),
    ]
    for x in divs:
        assert x["sobra_lula"] == -x["sobra_flavio"]

    quatro = ["14", "55", "30", "70"]  # Renan Santos, Caiado, Zema, Cury (os do gráfico)
    soma4 = sum(br1["cand"].get(n, 0) for n in quatro)
    bolo = dl + df
    alegacao = {
        "quatro": [{"numero": n, "nome": nomes1.get(n), "votos": br1["cand"].get(n, 0)} for n in quatro],
        "soma_quatro": soma4, "outros_seis": br1["outros"] - soma4, "outros_todos": br1["outros"],
        "bolo": bolo, "parte_lula": pc(dl, bolo, 1), "parte_flavio": pc(df, bolo, 1),
        "lula_alem_dos_outros": dl - br1["outros"],
        "abst_1t": br1["abst"], "abst_2t": br2["abst"], "abst_caiu": br1["abst"] - br2["abst"],
        "eleitores_1t": br1["eleitores"], "eleitores_2t": br2["eleitores"],
    }
    outros_cand = sorted(({"numero": n, "nome": nomes1.get(n), "votos": v} for n, v in br1["cand"].items() if n not in (A, B)),
                         key=lambda x: -x["votos"])

    # estimativa da Projeção (já calculada; aqui só convertida em votos)
    an = json.load(open(os.path.join(a.oficial, "analise.json")))
    trans = (an.get("estimativa") or {}).get("transferencias", {}).get("BR") or []
    est = []
    for o in trans:
        if o["para"].get(A, 0) >= 90 or o["para"].get(B, 0) >= 90:
            continue
        est.append({"origem": o["origem"], "votos_1t": o["votos_1t"], "para": o["para"],
                    "lula": round(o["votos_1t"] * o["para"].get(A, 0) / 100),
                    "flavio": round(o["votos_1t"] * o["para"].get(B, 0) / 100)})

    # ---------- nível 2: estados e regiões ----------
    ufs, soma1, soma2 = {}, {"lula": 0, "flavio": 0}, {"lula": 0, "flavio": 0}
    for uf in sorted(k for k in ab if k != "br"):
        r1 = ultimo(os.path.join(a.t1, "uf", uf))
        if not r1:
            continue
        u1 = resumo(r1)
        u2 = resumo(json.load(open(os.path.join(a.oficial, ab[uf]["arquivo"]))))
        for s, u in ((soma1, u1), (soma2, u2)):
            s["lula"] += u["lula"]; s["flavio"] += u["flavio"]
        nome = r1["abrangencia"]["nome"] if uf != "zz" else "Exterior"
        ufs[uf] = {
            "nome": nome, "regiao": REGIAO.get(uf, "EX"),
            "l1": u1["lula"], "l2": u2["lula"], "f1": u1["flavio"], "f2": u2["flavio"], "o1": u1["outros"],
            "vv1": u1["validos"], "vv2": u2["validos"], "comp1": u1["comp"], "comp2": u2["comp"],
            "bn1": u1["brancos"] + u1["nulos"], "bn2": u2["brancos"] + u2["nulos"],
            "pl1": u1["pl"], "pf1": u1["pf"], "pl2": u2["pl"], "pf2": u2["pf"],
            "dl": u2["lula"] - u1["lula"], "df": u2["flavio"] - u1["flavio"],
            "dl_pct": pc(u2["lula"] - u1["lula"], u1["lula"], 2), "df_pct": pc(u2["flavio"] - u1["flavio"], u1["flavio"], 2),
            "dif2": u2["lula"] - u2["flavio"], "dif1": u1["lula"] - u1["flavio"],
            "final": u2["final"], "pct_secoes": u2["pct_secoes"],
        }
    # as UFs + exterior têm de bater com o Brasil nos dois turnos
    conferido = soma1 == {"lula": br1["lula"], "flavio": br1["flavio"]} and soma2 == {"lula": br2["lula"], "flavio": br2["flavio"]}
    regioes = {}
    for uf, u in ufs.items():
        r = regioes.setdefault(u["regiao"], {"nome": NOME_REG[u["regiao"]], "ufs": [], "l1": 0, "l2": 0, "f1": 0, "f2": 0, "o1": 0})
        r["ufs"].append(uf)
        for k in ("l1", "l2", "f1", "f2", "o1"):
            r[k] += u[k]
    for r in regioes.values():
        r["dl"], r["df"] = r["l2"] - r["l1"], r["f2"] - r["f1"]
        r["dl_pct"], r["df_pct"] = pc(r["dl"], r["l1"]), pc(r["df"], r["f1"])
        r["parte_do_ganho_lula"] = pc(r["dl"], dl, 1)
    estados = {k: v for k, v in ufs.items() if k != "zz"}
    venceu = {"lula": sorted(k for k, v in estados.items() if v["l2"] > v["f2"]),
              "flavio": sorted(k for k, v in estados.items() if v["f2"] > v["l2"])}
    venceu_1t = {"lula": sorted(k for k, v in estados.items() if v["l1"] > v["f1"]),
                 "flavio": sorted(k for k, v in estados.items() if v["f1"] > v["l1"])}

    # cidades (só as finalizadas nos dois turnos)
    c1, c2 = cidades(a.mun1), cidades(a.mun2)
    lst = []
    for cd, b in c2.items():
        x = c1.get(cd)
        if not x or x.get("and") != "finalizada" or b.get("and") != "finalizada":
            continue
        l1, l2, f1, f2 = g(x, A), g(b, A), g(x, B), g(b, B)
        s1 = pc(l1, l1 + f1) if l1 + f1 else None
        s2 = pc(l2, l2 + f2) if l2 + f2 else None
        lst.append({"nm": b["nm"], "uf": b["uf"], "te": b.get("te") or 0, "l1": l1, "l2": l2, "f1": f1, "f2": f2,
                    "dl": l2 - l1, "df": f2 - f1, "o1": (x.get("vv") or 0) - l1 - f1,
                    "pp": round(s2 - s1, 2) if s1 is not None and s2 is not None else None})
    corta = lambda c: {k: c[k] for k in ("nm", "uf", "te", "l1", "l2", "f1", "f2", "dl", "df", "o1", "pp")}
    grandes = [c for c in lst if c["te"] >= 20000 and c["pp"] is not None]
    cid = {
        "comparadas": len(lst),
        "lula_cresceu_mais": sum(1 for c in lst if c["dl"] > c["df"]),
        "flavio_cresceu_mais": sum(1 for c in lst if c["df"] > c["dl"]),
        "lula_ganhou_mais_que_outros": sum(1 for c in lst if c["dl"] > c["o1"]),
        "top_dl": [corta(c) for c in sorted(lst, key=lambda c: -c["dl"])[:15]],
        "top_df": [corta(c) for c in sorted(lst, key=lambda c: -c["df"])[:15]],
        "top_pp_lula": [corta(c) for c in sorted(grandes, key=lambda c: -c["pp"])[:15]],
        "top_pp_flavio": [corta(c) for c in sorted(grandes, key=lambda c: c["pp"])[:15]],
    }

    # ---------- checagem dos gráficos que circularam ----------
    sc = ufs.get("sc", {})
    chk = [
        {"grafico": "Postagem “Lula fez 11 milhões de votos a mais”", "afirmacao": "Lula fez 11 milhões de votos a mais que no 1º turno",
         "oficial": dl, "tipo": "votos", "situacao": "arredondado para cima",
         "nota": "O ganho final foi de %s votos." % f"{dl:,}".replace(",", ".")},
        {"grafico": "Postagem “Lula fez 11 milhões de votos a mais”", "afirmacao": "Renan Santos + Caiado + Zema + Cury = 9.056.092 votos",
         "oficial": soma4, "tipo": "votos", "situacao": "confere" if soma4 == 9056092 else "diferente",
         "nota": "A soma está certa, mas faltam os outros 6 candidatos (%s votos). Todos os que não eram Lula nem Flávio somaram %s."
                 % (f"{br1['outros'] - soma4:,}".replace(",", "."), f"{br1['outros']:,}".replace(",", "."))},
        {"grafico": "Postagem “Lula fez 11 milhões de votos a mais”", "afirmacao": "Então ele pegou todos esses votos e mais as abstenções",
         "oficial": None, "tipo": "texto", "situacao": "a conta não sustenta",
         "nota": "Lula ganhou %s votos além do total dos outros candidatos. Mas a abstenção caiu %s e brancos e nulos caíram %s: havia %s votos novos em jogo para os dois, e Flávio ficou com %s deles. O total nacional não diz quem votou em quem."
                 % (f"{dl - br1['outros']:,}".replace(",", "."), f"{br1['abst'] - br2['abst']:,}".replace(",", "."),
                    f"{D['brancos'] + D['nulos']:,}".replace(",", "."), f"{bolo:,}".replace(",", "."), f"{df:,}".replace(",", "."))},
        {"grafico": "“Como votou cada estado” (99,94% das urnas)", "afirmacao": "Lula 51,78% x Flávio 48,22%",
         "oficial": br2["pl"], "tipo": "pct", "situacao": "parcial, quase igual ao final",
         "nota": "Final: Lula %s%% x Flávio %s%%, diferença de %s votos." % (str(br2["pl"]).replace(".", ","), str(br2["pf"]).replace(".", ","),
                                                                            f"{br2['lula'] - br2['flavio']:,}".replace(",", "."))},
        {"grafico": "“Como votou cada estado” (99,94% das urnas)", "afirmacao": "Lula venceu em 13 estados e Flávio em 14",
         "oficial": len(venceu["lula"]), "tipo": "estados",
         "situacao": "confere" if (len(venceu["lula"]), len(venceu["flavio"])) == (13, 14) else "diferente",
         "nota": "Final: Lula em %d (com o DF contado como estado) e Flávio em %d." % (len(venceu["lula"]), len(venceu["flavio"]))},
        {"grafico": "“Onde Lula ganhou mais votos” (95,33% das seções)", "afirmacao": "Lula: 64.065.122 votos no 2º turno, +10.185.584 (+18,9%)",
         "oficial": br2["lula"], "tipo": "votos", "situacao": "parcial",
         "nota": "O gráfico usou uma parcial das 21h06, com o RJ incompleto. Final: %s votos, +%s (+%s%%). No RJ, Lula foi de %s para %s."
                 % (f"{br2['lula']:,}".replace(",", "."), f"{dl:,}".replace(",", "."), str(pc(dl, br1["lula"], 1)).replace(".", ","),
                    f"{ufs['rj']['l1']:,}".replace(",", "."), f"{ufs['rj']['l2']:,}".replace(",", "."))},
        {"grafico": "Tabela “Diferença do 1º para o 2º – SC”", "afirmacao": "Flávio 3.000.020 → 3.220.071; Lula 1.127.168 → 1.418.314",
         "oficial": sc.get("f2"), "tipo": "votos",
         "situacao": "confere" if (sc.get("f1"), sc.get("l1"), sc.get("f2"), sc.get("l2")) == (3000020, 1127168, 3220071, 1418314) else "diferente",
         "nota": "Oficial SC: Flávio %s → %s (+%s%%); Lula %s → %s (+%s%%)." % (
             f"{sc.get('f1', 0):,}".replace(",", "."), f"{sc.get('f2', 0):,}".replace(",", "."), str(sc.get("df_pct")).replace(".", ","),
             f"{sc.get('l1', 0):,}".replace(",", "."), f"{sc.get('l2', 0):,}".replace(",", "."), str(sc.get("dl_pct")).replace(".", ","))},
    ]

    # ---------- nível 3: boletins ----------
    conf = {}
    try:
        cj = json.load(open(os.path.join(a.oficial, "conferencia.json")))
        conf = {"resumo": cj.get("resumo"), "gerado_em": cj.get("gerado_em")}
    except (OSError, ValueError):
        pass

    out = {
        "schema": 1, "tipo": "virada", "gerado_em": datetime.now(BRT).isoformat(timespec="seconds"),
        "tse": {"t1_totalizado": br1["totalizado_tse"], "t2_totalizado": br2["totalizado_tse"],
                "t2_final": br2["final"], "t2_pct_secoes": br2["pct_secoes"]},
        "brasil": {"t1": {k: br1[k] for k in ("lula", "flavio", "outros", "validos", "brancos", "nulos", "comp", "abst", "eleitores", "pl", "pf")},
                   "t2": {k: br2[k] for k in ("lula", "flavio", "outros", "validos", "brancos", "nulos", "comp", "abst", "eleitores", "pl", "pf")},
                   "dl": dl, "df": df, "dl_pct": pc(dl, br1["lula"]), "df_pct": pc(df, br1["flavio"]),
                   "categorias": D, "identidade_ok": True, "outros_candidatos": outros_cand},
        "divisoes": divs, "alegacao": alegacao, "estimativa": est,
        "ufs": ufs, "regioes": regioes, "venceu": venceu, "venceu_1t": venceu_1t,
        "somas_conferidas": conferido, "cidades": cid, "checagem": chk, "conferencia": conf,
    }
    dest = os.path.join(a.oficial, "virada.json")
    tmp = dest + ".tmp"
    json.dump(out, open(tmp, "w"), ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, dest)
    print(json.dumps({"dl": dl, "df": df, "sobra_texto": divs[0]["sobra_lula"], "somas_conferidas": conferido,
                      "estados": {k: len(v) for k, v in venceu.items()}, "bytes": os.path.getsize(dest)}))


if __name__ == "__main__":
    main()
