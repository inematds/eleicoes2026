"""Simulador da apuração do 2º turno — SÓ PARA TESTE E DEMONSTRAÇÃO.

Gera arquivos no formato bruto do TSE (-u.json) com números FICTÍCIOS e passa
pelo mesmo consolidador/publicador da coleta real. Tudo sai marcado
fonte.tipo = "simulacao" e o site mostra a faixa SIMULAÇÃO.

Base usada (real, 1º turno 6257): eleitorado, seções, taxa de comparecimento,
brancos e nulos por UF. A divisão de votos entre os dois candidatos é inventada
a partir da proporção entre eles no 1º turno, com ruído.

Uso:
  python3 simular.py --saida ../saida/data --intervalo 15 --inicio 14
"""
import argparse
import json
import os
import random
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nucleo as N  # noqa: E402

NOTA = ""
T1 = "https://resultados.tse.jus.br/oficial/ele2026/6257/dados/{a}/{a}-c0001-e006257-u.json"
PASSOS = 36


def baixa(url, cache):
    if os.path.exists(cache):
        return json.load(open(cache))
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    b = urllib.request.urlopen(url, timeout=30).read()
    open(cache, "wb").write(b)
    return json.loads(b)


def pct(n, d):
    return f"{(n * 100 / d if d else 0):.9f}".replace(".", ",")


def base_1t(cache_dir):
    base = {}
    for a in N.UFS + ["zz"]:
        d = baixa(T1.format(a=a), os.path.join(cache_dir, f"1t-{a}.json"))
        cs = {c["n"]: int(c["vap"]) for c, _ in N.candidatos_tse(d)}
        tv = int(d["v"]["tv"])
        base[a] = {
            "te": int(d["e"]["te"]), "esa": int(d["e"]["esa"]), "ts": int(d["s"]["ts"]),
            "pc": int(d["e"]["c"]) / int(d["e"]["esa"]),
            "pb": int(d["v"]["vb"]) / tv, "pn": int(d["v"]["tvn"]) / tv,
            "s13": cs["13"] / (cs["13"] + cs["22"]),
        }
    c2 = baixa(N.url_tse("br"), os.path.join(cache_dir, "2t-br.json"))
    return base, c2


def gera_bruto(a, b, st, esa, c, vb, tvn, vnt, v13, v22, rel, cands2, tpabr="uf"):
    ts = b["ts"]
    tv = c
    vv = v13 + v22
    andamento = "n" if st == 0 else ("f" if st == ts else "p")
    dg = rel.strftime("%d/%m/%Y"); hg = (rel + timedelta(seconds=17)).strftime("%H:%M:%S")
    par = []
    for n, sg, nm, nmu, nf in cands2:
        vap = v13 if n == "13" else v22
        par.append({"n": nf, "sg": sg, "cand": [{
            "n": nf, "nm": nm, "nmu": nmu, "e": "n", "st": "",
            "vap": str(vap), "pvap": pct(vap, vv)[:5], "pvapn": pct(vap, vv)}]})
    return {
        "ele": "6258", "t": "2", "f": "s", "tpabr": tpabr, "cdabr": a,
        "dg": dg, "hg": hg, "idg": str(int(rel.timestamp())),
        "dt": dg if st else "", "ht": rel.strftime("%H:%M:%S") if st else "",
        "and": andamento, "tf": "s" if andamento == "f" else "n",
        "s": {"ts": str(ts), "st": str(st), "snt": str(ts - st), "pstn": pct(st, ts)},
        "e": {"te": str(b["te"]), "esa": str(esa), "c": str(c), "a": str(esa - c),
              "pcn": pct(c, esa), "pan": pct(esa - c, esa)},
        "v": {"tv": str(tv), "vv": str(vv), "vb": str(vb), "tvn": str(tvn), "vn": str(tvn - vnt),
              "vnt": str(vnt), "pvvcn": pct(vv, tv), "pvbn": pct(vb, tv), "ptvnn": pct(tvn, tv)},
        "carg": [{"cd": "1", "agr": [{"par": par}]}],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", required=True)
    ap.add_argument("--intervalo", type=float, default=15)
    ap.add_argument("--inicio", type=int, default=0)
    ap.add_argument("--semente", type=int, default=2026)
    ap.add_argument("--uma-vez", action="store_true", help="para no fim em vez de recomeçar")
    ap.add_argument("--ficticio", action="store_true", help="nomes fictícios (Candidato A/B)")
    ap.add_argument("--modo-tse", help="em vez de publicar, escreve arquivos no formato do TSE nesta pasta "
                    "(para testar o coletor com servidor_local.py), com falhas de propósito")
    args = ap.parse_args()
    cache = os.path.join(os.path.dirname(os.path.abspath(args.saida)), "cache")
    base, c2 = base_1t(cache)
    if args.ficticio:
        cands2 = [("13", "PART-A", "CANDIDATO A (SIMULADO)", "CANDIDATO A", "88"),
                  ("22", "PART-B", "CANDIDATO B (SIMULADO)", "CANDIDATO B", "99")]
    else:  # nomes reais do arquivo oficial do 2º turno; números reais
        cands2 = [(c["n"], sg, c["nm"], c.get("nmu", c["nm"]), c["n"]) for c, sg in N.candidatos_tse(c2)]
    global NOTA
    NOTA = ("Simulação: andamento inventado. Proporção entre os dois candidatos, eleitorado, "
            "comparecimento, brancos e nulos de cada estado tirados do 1º turno (04/10). "
            "Não é resultado do 2º turno.")

    while True:
        rnd = random.Random(args.semente)
        if os.path.exists(args.saida):
            shutil.rmtree(args.saida)
        est = os.path.join(args.saida, "..", "estado.json")
        if os.path.exists(est):
            os.remove(est)
        pub = N.Publicador(args.saida)
        # versões nunca se repetem entre rodadas (o site trata cada versão como imutável)
        rod_arq = os.path.join(os.path.dirname(os.path.abspath(args.saida)), "rodada.txt")
        try:
            rodada = int(open(rod_arq).read()) + 1
        except (FileNotFoundError, ValueError):
            rodada = 1
        open(rod_arq, "w").write(str(rodada))
        pub.base = rodada * 1000
        pub.estado["versao"] = pub.base
        perfil = {a: {"k": rnd.uniform(0.6, 1.6), "vies": rnd.uniform(-0.04, 0.04),
                      "s": b["s13"]}
                  for a, b in base.items()}
        perfil["zz"]["k"] = 0.45  # exterior apura mais tarde
        acum = {a: dict(st=0, esa=0, c=0, vb=0, tvn=0, vnt=0, v13=0, v22=0) for a in base}
        relogio = datetime(2026, 10, 25, 17, 0, 40)
        for passo in range(PASSOS + 1):
            relogio += timedelta(seconds=rnd.randint(140, 260))
            brutos = {}
            for a, b in base.items():
                pf = perfil[a]
                p = 1 - (1 - passo / PASSOS) ** pf["k"] if passo else 0
                x = acum[a]
                st = round(b["ts"] * p)
                esa = round(b["esa"] * p)
                c = round(esa * b["pc"])
                d_c = c - x["c"]
                d_vb = round(d_c * b["pb"]); d_tvn = round(d_c * b["pn"])
                d_vv = d_c - d_vb - d_tvn
                share = min(0.95, max(0.05, pf["s"] + pf["vies"] * (1 - p)))
                d13 = round(d_vv * share)
                x.update(st=st, esa=esa, c=c, vb=x["vb"] + d_vb, tvn=x["tvn"] + d_tvn,
                         v13=x["v13"] + d13, v22=x["v22"] + d_vv - d13)
                x["vnt"] = round(x["tvn"] * 0.0015)
                brutos[a] = gera_bruto(a, b, x["st"], x["esa"], x["c"], x["vb"], x["tvn"], x["vnt"],
                                       x["v13"], x["v22"], relogio, cands2)
            soma = {k: sum(acum[a][k] for a in base) for k in acum["sp"]}
            bbr = {"te": sum(b["te"] for b in base.values()), "ts": sum(b["ts"] for b in base.values())}
            brutos["br"] = gera_bruto("br", bbr, soma["st"], soma["esa"], soma["c"], soma["vb"],
                                      soma["tvn"], soma["vnt"], soma["v13"], soma["v22"], relogio,
                                      cands2, tpabr="br")
            if args.modo_tse:
                escreve_tse(args.modo_tse, brutos, passo, args.intervalo)
            else:
                publica(pub, brutos)
            if passo >= args.inicio:
                print(f"passo {passo}/{PASSOS} br {brutos['br']['s']['pstn'][:5]}% seções", flush=True)
                time.sleep(args.intervalo)
        if args.uma_vez:
            break
        time.sleep(args.intervalo * 4)


_BR_ANT = {}


def escreve_tse(pasta, brutos, passo, intervalo):
    """Imita o TSE: índice ab.json + um -u.json por abrangência, com 4 problemas reais:
    1) o índice sai ANTES dos arquivos (CDN atrasado); 2) o br só atualiza a cada 2 passos;
    3) passo 6: arquivo de SP corrompido; 4) passo 8: RJ com seções diminuindo."""
    base = os.path.join(pasta, "dados")
    if passo % 2 == 1 and _BR_ANT:
        brutos = dict(brutos, br=_BR_ANT["raw"])  # br atrasado em relação às UFs
    else:
        _BR_ANT["raw"] = brutos["br"]
    rj_ant = _BR_ANT.get("rj_st")
    _BR_ANT["rj_st"] = int(brutos["rj"]["s"]["st"])
    if passo == 8 and rj_ant:
        rj = json.loads(json.dumps(brutos["rj"]))
        st = max(0, rj_ant - 100)  # menos seções do que o passo anterior
        rj["s"]["st"], rj["s"]["snt"] = str(st), str(int(rj["s"]["ts"]) - st)
        brutos = dict(brutos, rj=rj)
    ab = {"ele": "6258", "t": "2", "f": "o", "abr": [
        {"cdabr": a, "tpabr": r.get("tpabr", "uf"), "dt": r["dt"], "ht": r["ht"], "s": r["s"], "e": r["e"]}
        for a, r in brutos.items()]}
    def grava(caminho, dados):
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        tmp = caminho + ".tmp"
        with open(tmp, "wb") as f:
            f.write(dados)
        os.replace(tmp, caminho)
    def grava_u():
        for a, r in brutos.items():
            corpo = json.dumps(r, ensure_ascii=False).encode()
            if passo == 6 and a == "sp":
                corpo = corpo[: len(corpo) // 2]  # JSON cortado
            grava(os.path.join(base, a, f"{a}-c0001-e006258-u.json"), corpo)
    def grava_ab():
        grava(os.path.join(base, "br", "br-e006258-ab.json"), json.dumps(ab).encode())
    if passo in (10, 11):  # 5) ao contrário: arquivos ANTES do índice
        grava_u(); time.sleep(min(4, intervalo * 0.3)); grava_ab()
    else:
        grava_ab(); time.sleep(min(4, intervalo * 0.3)); grava_u()  # índice novo, arquivos velhos
    print(f"[tse-falso] passo {passo}", "(br atrasado)" if passo % 2 else "", "(SP corrompido)" if passo == 6 else "", "(RJ diminuiu)" if passo == 8 else "", "(arquivos antes do índice)" if passo in (10, 11) else "", flush=True)


def publica(pub, brutos):
    coletado = N.agora()
    novos, problemas = {}, []
    for a, raw in brutos.items():
        bruto = json.dumps(raw, ensure_ascii=False).encode()
        ant = pub.ultimo(a)
        versao = (pub.estado["abr"].get(a, {}).get("versao", getattr(pub, "base", 0))) + 1
        res, r = N.consolidar(bruto, a, coletado, versao, fonte_tipo="simulacao")
        if ant and ant["fonte"]["sha256_bruto"] == res["fonte"]["sha256_bruto"]:
            continue
        p = N.conferir(r, res, ant)
        if p:
            problemas.append((a, p))
            continue
        novos[a] = res
    if "br" in novos:
        ufs = {a: novos.get(a) or pub.ultimo(a) for a in N.UFS + ["zz"]}
        ufs = {a: u for a, u in ufs.items() if u}
        p = N.conferir_br(novos["br"], ufs)
        if p:
            problemas.append(("br", p)); novos.pop("br")
    if problemas:
        print("BLOQUEADO:", problemas, flush=True)
    if novos:
        pub.publicar(novos, fonte_tipo="simulacao", nota=NOTA)


if __name__ == "__main__":
    main()
