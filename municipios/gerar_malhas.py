"""Gera o desenho dos municípios de cada estado (um arquivo por UF) para o mapa municipal.

Fonte: API de malhas do IBGE (v3, qualidade "minima"), uma vez por estado, guardada em
saida/geo/ibge/<UF>.json. Liga ao TSE pelo código IBGE (`cdi` do mun-e006258-cm.json).
O site só lê o que este script gera: municipios/site/assets/malha/<uf>.json.

Uso: python3 municipios/gerar_malhas.py            # baixa o que faltar e gera os 27
     python3 municipios/gerar_malhas.py --so sp mg  # só alguns
"""
import argparse
import gzip
import json
import math
import os
import sys
import time
import urllib.request

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(P, "ferramentas"))
sys.path.insert(0, os.path.join(P, "coleta"))
from gerar_mapa import area, centroide, dp_anel  # noqa: E402
import nucleo as N  # noqa: E402

CACHE = os.path.join(P, "saida", "geo", "ibge")
CM = os.path.join(P, "saida", "geo", "mun-e006258-cm.json")
DEST = os.path.join(P, "municipios", "site", "assets", "malha")
URL_IBGE = ("https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}"
            "?formato=application/vnd.geo%2Bjson&intrarregiao=municipio&qualidade=minima")
URL_CM = N.BASE_TSE + "config/mun-e006258-cm.json"
UA = "INEMA-Eleicoes/1.0 (+https://eleicoes.inema.club; mapa municipal)"
LADO = 1000      # maior lado do desenho, em unidades do SVG
TOL = 0.55       # simplificação (unidades do SVG)
AREA_MIN = 0.4   # ilhotas menores que isso saem (o maior anel de cada cidade sempre fica)


def baixa(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    corpo = urllib.request.urlopen(req, timeout=60).read()
    if corpo[:2] == b"\x1f\x8b":  # o IBGE manda gzip mesmo sem pedir
        corpo = gzip.decompress(corpo)
    json.loads(corpo)  # tem que ser JSON válido
    with open(dest + ".tmp", "wb") as f:
        f.write(corpo)
    os.replace(dest + ".tmp", dest)
    time.sleep(0.3)  # gentil com o IBGE


def gera_uf(uf, cm_uf):
    g = json.load(open(os.path.join(CACHE, uf.upper() + ".json")))
    lats = [c[1] for f in g["features"] for poly in _polys(f["geometry"]) for c in poly[0]]
    coslat = math.cos(math.radians((min(lats) + max(lats)) / 2))
    aneis, xs, ys = {}, [], []
    for f in g["features"]:
        cdi = f["properties"]["codarea"]
        aneis[cdi] = []
        for poly in _polys(f["geometry"]):
            anel = [(c[0] * coslat, -c[1]) for c in poly[0]]  # só o contorno externo
            aneis[cdi].append(anel)
            xs += [x for x, _ in anel]; ys += [y for _, y in anel]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    esc = LADO / max(x1 - x0, y1 - y0)
    W, H = round((x1 - x0) * esc), round((y1 - y0) * esc)
    mun = {}
    for cdi, lista in aneis.items():
        partes, maior, maior_a, a_total = [], None, -1, 0.0
        for anel in lista:
            pts = [((x - x0) * esc, (y - y0) * esc) for x, y in anel]
            s = dp_anel(pts, TOL)
            if len(s) < 4:
                s = pts  # cidade minúscula: fica sem simplificar
            a = area(s)
            if a > maior_a:
                maior, maior_a = s, a
            if a >= AREA_MIN:
                partes.append(s)
                a_total += a
        if not partes:
            partes = [maior]
            a_total = maior_a
        d = "".join("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in s[:-1]) + "Z" for s in partes)
        cx, cy = centroide(maior)
        mun[cdi] = {"d": d, "cx": round(cx, 1), "cy": round(cy, 1), "a": round(a_total, 1)}
    # TSE x IBGE: confere os dois conjuntos de códigos
    tse = {m["cdi"]: m for m in cm_uf}
    so_ibge = sorted(set(mun) - set(tse))
    so_tse = sorted(set(tse) - set(mun))
    for cdi in mun:
        if cdi in tse:
            mun[cdi]["nm"] = tse[cdi]["nm"]
            mun[cdi]["cd"] = tse[cdi]["cd"]
    out = {"uf": uf, "fonte": "IBGE, API de malhas v3 (qualidade mínima); nomes e códigos do TSE",
           "viewBox": f"0 0 {W} {H}", "mun": mun}
    os.makedirs(DEST, exist_ok=True)
    arq = os.path.join(DEST, uf + ".json")
    json.dump(out, open(arq, "w"), ensure_ascii=False, separators=(",", ":"))
    return {"uf": uf, "cidades": len(mun), "kb": os.path.getsize(arq) // 1024,
            "so_ibge": so_ibge, "so_tse": [f"{c} {tse[c]['nm']}" for c in so_tse]}


def _polys(geo):
    return geo["coordinates"] if geo["type"] == "MultiPolygon" else [geo["coordinates"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--so", nargs="*", help="só estas UFs (ex.: sp mg)")
    a = ap.parse_args()
    ufs = [u.lower() for u in a.so] if a.so else N.UFS
    baixa(URL_CM, CM)
    cm = {g["cd"]: g["mu"] for g in json.load(open(CM))["abr"]}
    rel = []
    for uf in ufs:
        baixa(URL_IBGE.format(uf=uf.upper()), os.path.join(CACHE, uf.upper() + ".json"))
        r = gera_uf(uf, cm[uf])
        rel.append(r)
        aviso = ""
        if r["so_ibge"] or r["so_tse"]:
            aviso = f"  ATENÇÃO só IBGE={r['so_ibge']} só TSE={r['so_tse']}"
        print(f"{uf}: {r['cidades']} cidades, {r['kb']} KB{aviso}", flush=True)
    print(f"total: {sum(r['cidades'] for r in rel)} cidades, {sum(r['kb'] for r in rel)} KB")


if __name__ == "__main__":
    main()
