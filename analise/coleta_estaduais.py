#!/usr/bin/env python3
"""Baixa do TSE, cidade a cidade, governador e senador do 1º turno (eleição 6259) e governador do 2º turno
(eleição 6260, só nos estados que tiveram 2º turno). Arquivos públicos de resultado, os mesmos do site do TSE.

Grava saida/estaduais/<uf>.json  {cd_tse: {"g1": cargo, "s1": cargo, "g2": cargo}}
  cargo = {"vv": votos válidos, "and": andamento, "c": [[numero, nome_urna, partido, coligacao, votos, eleito]]}
Retoma de onde parou: cidade já baixada e finalizada não é baixada de novo (use --refaz para forçar).
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://resultados.tse.jus.br/oficial/ele2026/"
ALVOS = {"g1": ("6259", "0003"), "s1": ("6259", "0005"), "g2": ("6260", "0003")}


def get(url, tentativas=4):
    for t in range(tentativas):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 INEMA-eleicoes2026"}), timeout=25)
            return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.5 * (t + 1))
        except Exception:
            time.sleep(1.5 * (t + 1))
    raise RuntimeError("falhou: " + url)


def compacta(d):
    if not d:
        return None
    out = []
    for cg in d.get("carg", []):
        for agr in cg.get("agr", []):
            com = agr.get("com") if agr.get("tp") == "c" else ""
            for par in agr.get("par", []):
                for c in par.get("cand", []):
                    out.append([c.get("n"), c.get("nmu") or c.get("nm"), par.get("sg", ""), com or "",
                                int(c.get("vap") or 0), c.get("e") == "s"])
    out.sort(key=lambda x: -x[4])
    return {"vv": int((d.get("v") or {}).get("vv") or 0), "and": d.get("and"), "c": out}


def cidades():
    cm = json.load(open(os.path.join(P, "saida", "municipios-1t", "mun-e006257-cm.json")))
    for a in cm["abr"]:
        if a["cd"].lower() == "zz":
            continue
        for m in a["mu"]:
            yield a["cd"].lower(), m["cd"]


def ufs_2t():
    ab = get(BASE + "6260/dados/br/br-e006260-ab.json") or {}
    return {a["cdabr"] for a in ab.get("abr", []) if a.get("cdabr") not in ("br", None)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=os.path.join(P, "saida", "estaduais"))
    ap.add_argument("--paralelo", type=int, default=8)
    ap.add_argument("--ufs", nargs="*")
    ap.add_argument("--refaz", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    com_2t = ufs_2t()
    lista = [(uf, cd) for uf, cd in cidades() if not a.ufs or uf in a.ufs]
    por_uf = {}
    for uf, cd in lista:
        por_uf.setdefault(uf, []).append(cd)
    total = {"baixados": 0, "pulados": 0, "erros": 0}

    def uma(uf, cd, atual):
        r, err = dict(atual or {}), []
        for k, (ele, cargo) in ALVOS.items():
            if k == "g2" and uf not in com_2t:
                continue
            if not a.refaz and r.get(k) and r[k].get("and") == "f":
                total["pulados"] += 1
                continue
            try:
                r[k] = compacta(get(f"{BASE}{ele}/dados/{uf}/{uf}{cd}-c{cargo}-e{int(ele):06d}-u.json"))
                total["baixados"] += 1
            except Exception as e:
                err.append(str(e))
                total["erros"] += 1
        return cd, r, err

    for uf in sorted(por_uf):
        arq = os.path.join(a.saida, uf + ".json")
        dados = json.load(open(arq)) if os.path.exists(arq) else {}
        with ThreadPoolExecutor(a.paralelo) as ex:
            for cd, r, err in ex.map(lambda cd: uma(uf, cd, dados.get(cd)), por_uf[uf]):
                dados[cd] = r
        tmp = arq + ".tmp"
        json.dump(dados, open(tmp, "w"), ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp, arq)
        print(json.dumps({"uf": uf, "cidades": len(por_uf[uf]), "2t": uf in com_2t, **total}), flush=True)


if __name__ == "__main__":
    main()
