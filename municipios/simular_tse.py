"""TSE FALSO para testar o sistema de municípios: apuração acelerada do 2º turno, cidade por cidade.

Gera, no mesmo formato e nos mesmos caminhos do TSE, os índices por estado e os arquivos de cada
cidade, a partir dos votos reais do 1º turno (saída do coletor_mun com --eleicao 6257): os votos de
13 e 22 viram o 2º turno e os dos outros candidatos são repartidos na mesma proporção, com um
pequeno desvio por cidade. Nomes FICTÍCIOS (Candidato A/B) — não é resultado.

Cada cidade começa numa hora sorteada e apura em ritmo próprio; os números fecham as regras do
contrato em todo instante. Sirva a pasta com coleta/servidor_local.py e aponte o coletor_mun com --base.

Uso:
  python3 municipios/simular_tse.py --origem saida/municipios-1t/data --saida saida/mun-tsefalso --minutos 20
"""
import argparse
import json
import math
import os
import random
import sys
import time
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "coleta"))
import nucleo as N  # noqa: E402

ELE, PLEITO = "6258", "3221"
CANDS = [("13", "CANDIDATO A", "PARTIDO A"), ("22", "CANDIDATO B", "PARTIDO B")]


def br(x):
    return f"{x:.9f}".replace(".", ",")


def br2(x):
    return f"{x:.2f}".replace(".", ",")


def grava(caminho, obj):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, caminho)


def bloco_s(ts, st):
    pct = st * 100 / ts if ts else 0
    return {"ts": str(ts), "st": str(st), "pst": br2(pct), "pstn": br(pct), "snt": str(ts - st),
            "psnt": br2(100 - pct), "psntn": br(100 - pct)}


def bloco_e(te, esa, c, a):
    pc = c * 100 / esa if esa else 0
    return {"te": str(te), "est": str(esa), "esa": str(esa), "c": str(c), "a": str(a),
            "pc": br2(pc), "pcn": br(pc), "pa": br2(100 - pc if esa else 0), "pan": br(100 - pc if esa else 0)}


class Cidade:
    def __init__(self, uf, r, rnd, dur):
        self.uf, self.cd, self.te, self.ts = uf, r["cd"], r["te"], max(1, r["ts"])
        a, b = r["c"].get("13", 0), r["c"].get("22", 0)
        vv = r["vv"] or (a + b) or 1
        base = a / (a + b) if a + b else 0.5
        quota = min(0.97, max(0.03, base + rnd.uniform(-0.04, 0.04)))  # desvio fictício por cidade
        self.F = {"13": round(vv * quota), "22": vv - round(vv * quota)}
        self.Fvb, self.Fvn = r["vb"], r["vn"]
        # cidade grande começa um pouco depois e demora mais
        peso = math.log10(max(10, self.te))
        self.ini = rnd.uniform(0.0, 0.55) * dur * (0.6 + peso / 12)
        self.dur = dur * rnd.uniform(0.08, 0.25) * (0.5 + peso / 6)
        self.st = 0
        self.dt = self.ht = ""

    def avanca(self, t):
        f = min(1.0, max(0.0, (t - self.ini) / self.dur))
        st = int(self.ts * f) if f < 1 else self.ts
        if st != self.st:
            self.st = st
            agora = datetime.now()
            self.dt, self.ht = agora.strftime("%d/%m/%Y"), agora.strftime("%H:%M:%S")
            return True
        return False

    def votos(self):
        f = self.st / self.ts
        v = {k: round(x * f) for k, x in self.F.items()}
        vv = sum(v.values())
        vb, vn = round(self.Fvb * f), round(self.Fvn * f)
        tv = vv + vb + vn
        esa = max(tv, round(self.te * f))
        return v, vv, vb, vn, tv, esa

    def andamento(self):
        return "n" if self.st == 0 else "f" if self.st == self.ts else "p"

    def arquivo(self, idg):
        v, vv, vb, vn, tv, esa = self.votos()
        cand = [{"n": n, "nm": nm, "nmu": nm, "vap": str(v[n]), "pvap": br2(v[n] * 100 / vv if vv else 0),
                 "pvapn": br(v[n] * 100 / vv if vv else 0), "e": "n", "st": ""} for n, nm, _ in CANDS]
        agr = [{"n": str(i), "nm": p, "tp": "i", "par": [{"n": n, "sg": p, "nm": p, "cand": [c]}]}
               for i, ((n, _, p), c) in enumerate(zip(CANDS, cand))]
        return {
            "ele": ELE, "t": "2", "f": "s", "sup": "n", "tpabr": "mu", "cdabr": self.cd,
            "dg": datetime.now().strftime("%d/%m/%Y"), "hg": datetime.now().strftime("%H:%M:%S"), "idg": str(idg),
            "dt": self.dt, "ht": self.ht, "dv": "s", "tf": "s" if self.st == self.ts else "n", "and": self.andamento(),
            "carg": [{"cd": "1", "nmn": "Presidente", "agr": agr}],
            "s": bloco_s(self.ts, self.st), "e": bloco_e(self.te, esa, tv, esa - tv),
            "v": {"tv": str(tv), "vv": str(vv), "vb": str(vb), "tvn": str(vn), "vn": str(vn), "vnt": "0",
                  "pvvcn": br(vv * 100 / tv if tv else 0), "pvbn": br(vb * 100 / tv if tv else 0),
                  "ptvnn": br(vn * 100 / tv if tv else 0)},
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origem", required=True, help="data/ do coletor_mun rodado no 1º turno")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--minutos", type=float, default=20, help="duração da apuração simulada")
    ap.add_argument("--passo", type=float, default=10, help="segundos entre atualizações")
    ap.add_argument("--semente", type=int, default=2026)
    a = ap.parse_args()
    rnd = random.Random(a.semente)
    base = os.path.join(a.saida, "oficial", "ele2026", ELE)
    man = json.load(open(os.path.join(a.origem, "latest.json")))
    cm = {"dg": "", "hg": "", "idg": "1", "f": "s", "abr": []}
    cidades = {}
    dur = a.minutos * 60
    for uf in N.UFS:
        d = json.load(open(os.path.join(a.origem, man["ufs"][uf]["arquivo"])))
        cm["abr"].append({"cd": uf, "ds": N.NOMES[uf].upper(),
                          "mu": [{"cd": r["cd"], "cdi": r["cdi"], "nm": r["nm"], "c": "s" if r.get("cap") else "n", "z": []}
                                 for r in d["cidades"].values()]})
        cidades[uf] = [Cidade(uf, r, rnd, dur) for r in d["cidades"].values()]
    grava(os.path.join(base, "config", f"mun-e00{ELE}-cm.json"), cm)
    br_u = Cidade("br", {"cd": "br", "te": 1, "ts": 1, "c": {}, "vv": 1, "vb": 0, "vn": 0}, rnd, dur).arquivo(1)
    br_u.update(tpabr="br", cdabr="br")
    grava(os.path.join(base, "dados", "br", f"br-c0001-e00{ELE}-u.json"), br_u)

    idg = 1
    t0 = time.time()
    print(json.dumps({"inicio": datetime.now().isoformat(timespec="seconds"), "cidades": sum(map(len, cidades.values())),
                      "minutos": a.minutos}), flush=True)
    while True:
        t = time.time() - t0
        idg += 1
        mudaram = 0
        for uf, lista in cidades.items():
            mud = [c for c in lista if c.avanca(t)]
            for c in mud:
                grava(os.path.join(base, "dados", uf, f"{uf}{c.cd}-c0001-e00{ELE}-u.json"), c.arquivo(idg))
            if mud or idg == 2:
                ts = sum(c.ts for c in lista); st = sum(c.st for c in lista); te = sum(c.te for c in lista)
                ultima = max(lista, key=lambda c: (c.dt[6:], c.dt[3:5], c.dt[:2], c.ht))
                itens = [{"and": "f" if st == ts else "p" if st else "n", "tpabr": "uf", "cdabr": uf,
                          "dt": ultima.dt, "ht": ultima.ht, "s": bloco_s(ts, st), "e": {"te": str(te)}}]
                itens += [{"and": c.andamento(), "tpabr": "mun", "cdabr": c.cd, "dt": c.dt, "ht": c.ht,
                           "s": bloco_s(c.ts, c.st), "e": {"te": str(c.te)}} for c in lista]
                grava(os.path.join(base, "dados", uf, f"{uf}-e00{ELE}-ab.json"),
                      {"ele": ELE, "t": "2", "f": "s", "dg": "", "hg": "", "idg": str(idg), "abr": itens})
            mudaram += len(mud)
        feitas = sum(1 for l in cidades.values() for c in l if c.st == c.ts)
        total = sum(map(len, cidades.values()))
        print(json.dumps({"t": round(t), "mudaram": mudaram, "completas": feitas, "total": total}), flush=True)
        if feitas == total:
            return
        time.sleep(a.passo)


if __name__ == "__main__":
    main()
