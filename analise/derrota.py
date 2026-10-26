#!/usr/bin/env python3
"""Por que Flávio perdeu? O que os números mostram (só lê arquivos locais, sem rede).

Junta, sobre os resultados do TSE já coletados:
  - placar dos aliados: governadores e senadores eleitos por campo, votos de cada campo x presidente;
  - onde o voto se dividiu: estado a estado e cidade a cidade (governador de um campo, presidente do outro);
  - a conta que decidiu: de onde veio a diferença do 1º para o 2º turno (fatos + estimativa da Projeção);
  - onde a virada aconteceu no mapa (cidades e estados que trocaram de líder);
  - indicadores simples para testar hipóteses (sem provar nada: o voto é secreto).

Campo: a função `campo` de analise/gerar.py (L = coligação com o PT, F = coligação com o PL, O = outros).
Grava <oficial>/derrota.json (padrão: saida/oficial/data/derrota.json), de forma atômica.
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(P, "analise"))
from gerar import campo, REGIAO  # noqa: E402

BRT = timezone(timedelta(hours=-3))
A, B = "13", "22"
NOME_REG = {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul"}


def ultimo(pasta):
    fs = sorted(glob.glob(os.path.join(pasta, "v*.json")))
    return json.load(open(fs[-1])) if fs else None


def g(c, n):
    return (c.get("c") or {}).get(n, 0) or 0


def pc(x, y, nd=2):
    return round(100 * x / y, nd) if y else None


def cidades(base):
    """{cd_tse: cidade} (com uf) do último arquivo de cada UF."""
    out = {}
    for d in sorted(glob.glob(os.path.join(base, "data", "uf", "*"))):
        x = ultimo(d)
        if not x:
            continue
        uf = os.path.basename(d)
        for c in x["cidades"].values():
            out[c["cd"]] = dict(c, uf=uf)
    return out


def soma_cargo(dados, chave):
    """Soma por candidato de um cargo em todas as cidades do estado: {nome: [partido, campo, votos, eleito, numero]}, vv, pendentes."""
    cand, vv, pend, n = {}, 0, 0, 0
    for r in dados.values():
        x = r.get(chave)
        if not x or not x.get("c"):
            continue
        n += 1
        vv += x.get("vv") or 0
        pend += x.get("and") != "f"
        for c in x["c"]:
            e = cand.setdefault(c[1], [c[2], campo(c[2], c[3]), 0, False, c[0]])
            e[2] += c[4] or 0
            e[3] = e[3] or bool(c[5])
    return cand, vv, pend, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t1", default=os.path.join(P, "saida", "municipios-1t"))
    ap.add_argument("--t2", default=os.path.join(P, "saida", "municipios"))
    ap.add_argument("--oficial", default=os.path.join(P, "saida", "oficial", "data"))
    ap.add_argument("--estaduais", default=os.path.join(P, "saida", "estaduais"))
    a = ap.parse_args()

    an = json.load(open(os.path.join(a.oficial, "analise.json")))
    lat = json.load(open(os.path.join(a.oficial, "latest.json")))
    br = json.load(open(os.path.join(a.oficial, lat["abrangencias"]["br"]["arquivo"])))
    t1, t2 = cidades(a.t1), cidades(a.t2)
    votos_br2 = {c["numero"]: c["votos"] for c in br["candidatos"]}
    trans = (an.get("estimativa") or {}).get("transferencias") or {}
    v1_br = {}
    for o in trans.get("BR", []):  # votos do 1º turno no Brasil todo (com exterior), como o TSE totalizou
        if o["para"].get(A, 0) >= 90:
            v1_br[A] = o["votos_1t"]
        elif o["para"].get(B, 0) >= 90:
            v1_br[B] = o["votos_1t"]

    # ---------------- estado a estado ----------------
    ufs = {}
    nac = {"gov": {"L": 0, "F": 0, "O": 0, "M": 0}, "gov_vv": 0, "sen": {"L": 0, "F": 0, "O": 0, "M": 0}, "sen_vv": 0,
           "lula1": 0, "flavio1": 0, "vv1": 0, "lula2": 0, "flavio2": 0, "vv2": 0}
    div = {"F_lula": {"cidades": 0, "eleitores": 0}, "L_flavio": {"cidades": 0, "eleitores": 0},
           "F_flavio": {"cidades": 0, "eleitores": 0}, "L_lula": {"cidades": 0, "eleitores": 0},
           "O_lula": {"cidades": 0, "eleitores": 0}, "O_flavio": {"cidades": 0, "eleitores": 0}}
    cid_div = []
    for arq in sorted(glob.glob(os.path.join(a.estaduais, "*.json"))):
        uf = os.path.basename(arq)[:2]
        dados = json.load(open(arq))
        ab = lat["abrangencias"].get(uf)
        of = json.load(open(os.path.join(a.oficial, ab["arquivo"]))) if ab else None
        c1 = [c for c in t1.values() if c["uf"] == uf]
        c2 = [c for c in t2.values() if c["uf"] == uf]
        l1, f1, vv1 = sum(g(c, A) for c in c1), sum(g(c, B) for c in c1), sum(c.get("vv") or 0 for c in c1)
        if of:
            vo = {c["numero"]: c["votos"] for c in of["candidatos"]}
            l2, f2, vv2 = vo.get(A, 0), vo.get(B, 0), of["votos"]["validos"]
            eleitores = of["eleitorado"]["total"]
            pct2 = of["secoes"]["pct_totalizadas"]
        else:
            l2, f2 = sum(g(c, A) for c in c2), sum(g(c, B) for c in c2)
            vv2 = sum(c.get("vv") or 0 for c in c2)
            eleitores, pct2 = sum(c.get("te") or 0 for c in c2), None
        gov1, gv1, _, _ = soma_cargo(dados, "g1")
        gov2, gv2, gp2, gn2 = soma_cargo(dados, "g2")
        sen, sv, _, _ = soma_cargo(dados, "s1")
        # governador: se houve 2º turno, vale o mais votado nele; senão o eleito do 1º turno
        if gov2 and gv2:
            nm, e = max(gov2.items(), key=lambda kv: kv[1][2])
            status = "eleito" if e[3] else ("liderando" if gp2 else "eleito")
            gov = {"nome": nm, "partido": e[0], "campo": e[1], "pct": pc(e[2], gv2, 1), "turno": 2, "status": status,
                   "cid_pend": gp2}
        else:
            nm, e = max(gov1.items(), key=lambda kv: (kv[1][3], kv[1][2]))
            gov = {"nome": nm, "partido": e[0], "campo": e[1], "pct": pc(e[2], gv1, 1), "turno": 1,
                   "status": "eleito" if e[3] else "liderando", "cid_pend": 0}
        gov1_top = sorted(gov1.items(), key=lambda kv: -kv[1][2])[:3]
        senadores = [{"nome": k, "partido": v[0], "campo": v[1], "pct": pc(v[2], sv, 1)}
                     for k, v in sorted(sen.items(), key=lambda kv: -kv[1][2]) if v[3]]
        sen_top_F = [{"nome": k, "partido": v[0], "pct": pc(v[2], sv, 1), "eleito": v[3]}
                     for k, v in sorted(sen.items(), key=lambda kv: -kv[1][2]) if v[1] == "F"]
        gc = {k: sum(v[2] for v in gov1.values() if v[1] == k) for k in ("L", "F", "O", "M")}
        sc = {k: sum(v[2] for v in sen.values() if v[1] == k) for k in ("L", "F", "O", "M")}
        for k in gc:
            nac["gov"][k] += gc[k]
            nac["sen"][k] += sc[k]
        nac["gov_vv"] += gv1; nac["sen_vv"] += sv
        nac["lula1"] += l1; nac["flavio1"] += f1; nac["vv1"] += vv1
        nac["lula2"] += l2; nac["flavio2"] += f2; nac["vv2"] += vv2
        lid1 = A if l1 > f1 else B if f1 > l1 else None
        lid2 = A if l2 > f2 else B if f2 > l2 else None
        # cidade a cidade: governador eleito (do estado) x presidente vencedor na cidade no 2º turno
        cd_div = {"F_lula": [0, 0], "L_flavio": [0, 0]}
        for c in c2:
            cl, cf = g(c, A), g(c, B)
            if not cl and not cf:
                continue
            v = "lula" if cl > cf else "flavio" if cf > cl else None
            if not v:
                continue
            k = gov["campo"] + "_" + v
            if k in div:
                div[k]["cidades"] += 1
                div[k]["eleitores"] += c.get("te") or 0
            if k in cd_div:
                cd_div[k][0] += 1
                cd_div[k][1] += c.get("te") or 0
            if k in ("F_lula", "L_flavio") and (c.get("te") or 0) >= 100000:
                cid_div.append({"nm": c["nm"], "uf": uf, "te": c.get("te") or 0, "gov": gov["campo"],
                                "pl2": pc(cl, cl + cf, 1), "pf2": pc(cf, cl + cf, 1)})
        fl1, fl2 = pc(f1, vv1, 2), pc(f2, vv2, 2)
        ufs[uf] = {
            "nome": (of or {}).get("abrangencia", {}).get("nome") or uf.upper(), "regiao": REGIAO.get(uf),
            "eleitores": eleitores, "pct_secoes_2t": pct2,
            "lula_1t": pc(l1, vv1), "flavio_1t": fl1, "lula_1t_votos": l1, "flavio_1t_votos": f1,
            "lula_2t": pc(l2, vv2), "flavio_2t": fl2, "lula_2t_votos": l2, "flavio_2t_votos": f2,
            "lider_1t": lid1, "lider_2t": lid2, "mudou": bool(lid1 and lid2 and lid1 != lid2),
            "margem_1t": l1 - f1, "margem_2t": l2 - f2,
            "governador": gov,
            "gov1_top": [{"nome": k, "partido": v[0], "campo": v[1], "pct": pc(v[2], gv1, 1)} for k, v in gov1_top],
            "gov1_L": pc(gc["L"], gv1), "gov1_F": pc(gc["F"], gv1), "gov1_O": pc(gc["O"], gv1),
            "gov1_F_votos": gc["F"], "gov1_L_votos": gc["L"],
            "senado_L": pc(sc["L"], sv), "senado_F": pc(sc["F"], sv), "senado_O": pc(sc["O"], sv),
            "senadores": senadores, "senado_F_cands": len(sen_top_F),
            "dif_sen_F": round(pc(sc["F"], sv) - fl1, 1) if sv and fl1 is not None else None,
            "dif_gov_F": round(pc(gc["F"], gv1) - fl1, 1) if gv1 and fl1 is not None else None,
            "dif_sen_F_2t": round(pc(sc["F"], sv) - fl2, 1) if sv and fl2 is not None else None,
            "cid_F_lula": cd_div["F_lula"][0], "ele_F_lula": cd_div["F_lula"][1],
            "cid_L_flavio": cd_div["L_flavio"][0], "ele_L_flavio": cd_div["L_flavio"][1],
            "cidades": len(c2),
        }

    # ---------------- placar dos aliados ----------------
    gov_campo = {k: {"n": 0, "ufs": [], "eleitores": 0} for k in ("L", "F", "O", "M")}
    sen_campo = {k: {"n": 0} for k in ("L", "F", "O", "M")}
    for uf, u in ufs.items():
        gc = gov_campo[u["governador"]["campo"]]
        gc["n"] += 1; gc["ufs"].append(uf); gc["eleitores"] += u["eleitores"]
        for s in u["senadores"]:
            sen_campo[s["campo"]]["n"] += 1
    est_lula = [uf for uf, u in ufs.items() if u["lider_2t"] == A]
    est_flavio = [uf for uf, u in ufs.items() if u["lider_2t"] == B]
    placar = {
        "governadores": gov_campo, "senadores": sen_campo,
        "estados_presidente": {"lula": {"n": len(est_lula), "ufs": est_lula, "eleitores": sum(ufs[u]["eleitores"] for u in est_lula)},
                               "flavio": {"n": len(est_flavio), "ufs": est_flavio, "eleitores": sum(ufs[u]["eleitores"] for u in est_flavio)}},
        "eleitores_total": sum(u["eleitores"] for u in ufs.values()),
        "votos_gov_1t": dict(nac["gov"], validos=nac["gov_vv"], pct={k: pc(v, nac["gov_vv"]) for k, v in nac["gov"].items()}),
        "votos_sen_1t": dict(nac["sen"], validos=nac["sen_vv"], pct={k: pc(v, nac["sen_vv"]) for k, v in nac["sen"].items()}),
        "pres_1t": {"lula": nac["lula1"], "flavio": nac["flavio1"], "validos": nac["vv1"],
                    "pct_lula": pc(nac["lula1"], nac["vv1"]), "pct_flavio": pc(nac["flavio1"], nac["vv1"])},
        "pres_2t": {"lula": nac["lula2"], "flavio": nac["flavio2"], "validos": nac["vv2"],
                    "pct_lula": pc(nac["lula2"], nac["vv2"]), "pct_flavio": pc(nac["flavio2"], nac["vv2"])},
    }

    # ---------------- onde o voto se dividiu ----------------
    cid_div.sort(key=lambda c: -c["te"])
    divisao = {"cidades": div, "maiores": cid_div[:40],
               "estados_F_lula": [uf for uf, u in ufs.items() if u["governador"]["campo"] == "F" and u["lider_2t"] == A],
               "estados_L_flavio": [uf for uf, u in ufs.items() if u["governador"]["campo"] == "L" and u["lider_2t"] == B]}
    divisao["eleitores_estados_F_lula"] = sum(ufs[u]["eleitores"] for u in divisao["estados_F_lula"])
    divisao["eleitores_estados_L_flavio"] = sum(ufs[u]["eleitores"] for u in divisao["estados_L_flavio"])
    divisao["sen_F_acima_flavio_1t"] = sorted([uf for uf, u in ufs.items() if (u["dif_sen_F"] or 0) > 0],
                                             key=lambda k: -ufs[k]["dif_sen_F"])

    # ---------------- a conta que decidiu ----------------
    f = an["fatos"]
    t = f["totais"]
    l1, f1 = v1_br.get(A), v1_br.get(B)
    l2, f2 = votos_br2.get(A), votos_br2.get(B)
    conta = {
        "brasil": {"lula_1t": l1, "flavio_1t": f1, "lula_2t": l2, "flavio_2t": f2,
                   "ganho_lula": l2 - l1 if l1 else None, "ganho_flavio": f2 - f1 if f1 else None,
                   "margem_1t": (l1 - f1) if l1 and f1 else None, "margem_2t": l2 - f2},
        "cidades": {"comparadas": f["cidades_comparadas"], "total": f["cidades_total"], "eleitores": t["eleitores"],
                    "ganho_lula": t["lula_2t"] - t["lula_1t"], "ganho_flavio": t["flavio_2t"] - t["flavio_1t"],
                    "outros_1t": t["outros_1t"], "comp": t["comp_2t"] - t["comp_1t"], "bn": t["bn_2t"] - t["bn_1t"],
                    "lula_1t": t["lula_1t"], "flavio_1t": t["flavio_1t"], "lula_2t": t["lula_2t"], "flavio_2t": t["flavio_2t"]},
    }
    b = conta["brasil"]
    if b["ganho_lula"] is not None:
        bolo = b["ganho_lula"] + b["ganho_flavio"]  # saldo de votos novos para os dois
        precisa = (bolo + b["margem_1t"]) / 2 if b["margem_1t"] is not None else None  # mínimo para Flávio empatar
        conta["exercicio"] = {
            "bolo": bolo, "parte_flavio": pc(b["ganho_flavio"], bolo, 1), "parte_lula": pc(b["ganho_lula"], bolo, 1),
            "flavio_precisava_ganhar": round(precisa) if precisa is not None else None,
            "flavio_precisava_pct": pc(precisa, bolo, 1) if precisa is not None else None,
            "faltou": round(precisa - b["ganho_flavio"]) if precisa is not None else None,
            "virar_meia_margem": round(b["margem_2t"] / 2), "virar_margem": b["margem_2t"],
            "livres_br": sum(o["votos_1t"] for o in trans.get("BR", []) if o["para"].get(A, 0) < 90 and o["para"].get(B, 0) < 90
                             and o["origem"] not in ("Brancos e nulos", "Não votou")),
        }
    est = an.get("estimativa") or {}
    casc = est.get("cascata") or {}
    grupos = {}
    for num in (A, B):
        for p in (casc.get(num) or {}).get("partes", []):
            k = "terceiros" if p["origem"] not in ("Brancos e nulos", "Não votou") and not p["origem"].startswith("Eleitores dele") else p["origem"]
            grupos.setdefault(k, {A: 0, B: 0})[num] += p["votos"]
    conta["estimativa"] = {"grupos": grupos, "transferencias_br": trans.get("BR"), "cascata": casc,
                           "calculada_em": est.get("projecao_calculada_em")}

    # ---------------- onde a virada aconteceu ----------------
    reg = {}
    for uf, u in f["por_uf"].items():
        r = reg.setdefault(REGIAO.get(uf), {"dl": 0, "df": 0, "viradas": 0, "cidades": 0})
        r["dl"] += u["dl"]; r["df"] += u["df"]; r["viradas"] += u["viradas_lula"] + u["viradas_flavio"]; r["cidades"] += u["cidades"]
    for k, r in reg.items():
        r["nome"] = NOME_REG.get(k, k)
        r["saldo"] = r["dl"] - r["df"]
    virada = {"para_lula": f["viradas"]["para_lula"], "para_flavio": f["viradas"]["para_flavio"],
              "por_uf": {uf: {"viradas_lula": u["viradas_lula"], "viradas_flavio": u["viradas_flavio"], "dl": u["dl"], "df": u["df"],
                              "cidades": u["cidades"]} for uf, u in f["por_uf"].items()},
              "regioes": reg, "lista": f["viradas_lista"][:20],
              "estados_mudaram": [uf for uf, u in ufs.items() if u["mudou"]]}

    # ---------------- indicadores para as hipóteses ----------------
    # H governador: o eleitorado dos estados de cada campo mudou quanto entre os turnos? (parte de Lula entre os dois)
    hg = {}
    for k in ("L", "F", "O"):
        sel = [u for u in ufs.values() if u["governador"]["campo"] == k]
        a1 = sum(u["lula_1t_votos"] for u in sel); b1 = sum(u["flavio_1t_votos"] for u in sel)
        a2 = sum(u["lula_2t_votos"] for u in sel); b2 = sum(u["flavio_2t_votos"] for u in sel)
        hg[k] = {"ufs": len(sel), "lula_entre_dois_1t": pc(a1, a1 + b1, 1), "lula_entre_dois_2t": pc(a2, a2 + b2, 1),
                 "ganho_lula": a2 - a1, "ganho_flavio": b2 - b1}
    # H comparecimento: cidades em que mais gente voltou a votar mudaram mais para Lula?
    comp_q = []
    reg_c = []
    for cd, c in t2.items():
        x = t1.get(cd)
        if not x or c.get("and") != "finalizada" or x.get("and") != "finalizada" or not c.get("te"):
            continue
        dc = 100 * ((c.get("comp") or 0) - (x.get("comp") or 0)) / c["te"]
        s1 = g(x, A) + g(x, B); s2 = g(c, A) + g(c, B)
        if not s1 or not s2:
            continue
        reg_c.append((dc, 100 * g(c, A) / s2 - 100 * g(x, A) / s1, c["te"]))
    reg_c.sort()
    if reg_c:
        q = len(reg_c) // 4
        for i, (ini, fim) in enumerate(((0, q), (q, 2 * q), (2 * q, 3 * q), (3 * q, len(reg_c)))):
            fat = reg_c[ini:fim]
            pe = sum(r[2] for r in fat)
            comp_q.append({"faixa": i + 1, "cidades": len(fat), "comp_de": round(fat[0][0], 1), "comp_ate": round(fat[-1][0], 1),
                           "lula_pp": round(sum(r[1] * r[2] for r in fat) / pe, 2) if pe else None})
    # H centro: terceiros por candidato (estimativa)
    terc = [{"origem": o["origem"], "votos_1t": o["votos_1t"], "lula": o["para"].get(A), "flavio": o["para"].get(B),
             "bn": o["para"].get("brancos_nulos"), "nv": o["para"].get("nao_votou")}
            for o in trans.get("BR", []) if o["para"].get(A, 0) < 90 and o["para"].get(B, 0) < 90]
    hip = {"governador": hg, "comparecimento_quartis": comp_q, "terceiros": terc}

    out = {
        "schema": 1, "tipo": "derrota",
        "gerado_em": datetime.now(BRT).isoformat(timespec="seconds"),
        "tse": {"totalizado_tse": br["fonte"]["totalizado_tse"], "pct_secoes": br["secoes"]["pct_totalizadas"],
                "final": br["situacao"]["totalizacao_final"], "votos": votos_br2,
                "pct_validos": {c["numero"]: c["pct_validos"] for c in br["candidatos"]},
                "validos": br["votos"]["validos"], "eleitorado": br["eleitorado"]["total"]},
        "candidatos": an.get("candidatos"),
        "campos": {"L": "campo de Lula: candidato de coligação com o PT (ou da federação dele)",
                   "F": "campo de Flávio: candidato de coligação com o PL", "O": "outros: sem PT nem PL na coligação",
                   "M": "coligação com PT e PL juntos"},
        "placar": placar, "ufs": ufs, "divisao": divisao, "conta": conta, "virada": virada, "hipoteses": hip,
        "analise_gerada_em": an.get("gerado_em"),
    }
    dest = os.path.join(a.oficial, "derrota.json")
    tmp = dest + ".tmp"
    with open(tmp, "w") as fp:
        json.dump(out, fp, ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, dest)
    print(json.dumps({"ufs": len(ufs), "gov": {k: v["n"] for k, v in gov_campo.items()},
                      "sen": {k: v["n"] for k, v in sen_campo.items()},
                      "estados_mudaram": virada["estados_mudaram"], "F_lula": divisao["estados_F_lula"],
                      "bytes": os.path.getsize(dest)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
