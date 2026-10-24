"""Gera site/assets/mapa-br.json (contorno simplificado dos 27 estados em SVG).

Fonte: brazil-states.geojson do projeto click_that_hood (Code for Germany, licença MIT),
derivado da malha do IBGE. Rodar uma vez; o site só lê o JSON gerado.

Uso: python3 ferramentas/gerar_mapa.py saida/geo/brazil-states.geojson site/assets/mapa-br.json
"""
import json
import math
import sys

TOL = 0.9          # tolerância de simplificação (unidades do SVG, largura ~1000)
AREA_MIN = 6.0     # descarta ilhotas menores que isso (unidades²)
COSLAT = math.cos(math.radians(-15))


def proj(lon, lat):
    return lon * COSLAT, -lat


def dp(pts, tol):
    """Douglas-Peucker iterativo."""
    if len(pts) < 4:
        return pts
    manter = [False] * len(pts)
    manter[0] = manter[-1] = True
    pilha = [(0, len(pts) - 1)]
    while pilha:
        a, b = pilha.pop()
        ax, ay = pts[a]; bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        norma = math.hypot(dx, dy) or 1e-12
        maxd, idx = 0.0, None
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / norma
            if d > maxd:
                maxd, idx = d, i
        if idx is not None and maxd > tol:
            manter[idx] = True
            pilha += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, manter) if k]


def dp_anel(pts, tol):
    """Anel fechado: o 1º e o último ponto são iguais, o que zera o Douglas-Peucker.
    Divide no ponto mais distante do início e simplifica as duas metades."""
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 4:
        return pts + [pts[0]]
    x0, y0 = pts[0]
    k = max(range(len(pts)), key=lambda i: (pts[i][0] - x0) ** 2 + (pts[i][1] - y0) ** 2)
    return dp(pts[:k + 1], tol)[:-1] + dp(pts[k:] + [pts[0]], tol)


def area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


def centroide(pts):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        f = x1 * y2 - x2 * y1
        a += f; cx += (x1 + x2) * f; cy += (y1 + y2) * f
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a)) if a else pts[0]


def main(src, dst):
    g = json.load(open(src))
    aneis = {}
    xs, ys = [], []
    for f in g["features"]:
        sg = f["properties"]["sigla"].lower()
        geo = f["geometry"]
        polys = geo["coordinates"] if geo["type"] == "MultiPolygon" else [geo["coordinates"]]
        aneis[sg] = []
        for poly in polys:
            anel = [proj(*c[:2]) for c in poly[0]]  # só o contorno externo
            aneis[sg].append(anel)
            for x, y in anel:
                xs.append(x); ys.append(y)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    esc = 1000 / (x1 - x0)
    W, H = 1000, round((y1 - y0) * esc)
    out = {"fonte": "click_that_hood brazil-states.geojson (MIT), malha IBGE", "viewBox": f"0 0 {W} {H}", "ufs": {}}
    for sg, lista in aneis.items():
        partes, maior, maior_a = [], None, -1
        for anel in lista:
            pts = [((x - x0) * esc, (y - y0) * esc) for x, y in anel]
            s = dp_anel(pts, TOL)
            a = area(s)
            if a < AREA_MIN or len(s) < 4:
                continue
            if a > maior_a:
                maior, maior_a = s, a
            partes.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in s[:-1]) + "Z")
        if maior is None:  # estado pequeno (DF): mantém o maior anel com tolerância menor
            pts = max(([((x - x0) * esc, (y - y0) * esc) for x, y in anel] for anel in lista), key=area)
            maior = dp_anel(pts, TOL / 4)
            partes.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in maior[:-1]) + "Z")
        cx, cy = centroide(maior)
        out["ufs"][sg] = {"d": "".join(partes), "cx": round(cx, 1), "cy": round(cy, 1)}
    json.dump(out, open(dst, "w"), separators=(",", ":"))
    print(f"{dst}: {W}x{H}, {sum(len(u['d']) for u in out['ufs'].values()) // 1024} KB de caminho")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
