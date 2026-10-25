#!/usr/bin/env python3
"""Exterior por país, a partir dos boletins de urna (BU) que o TSE publica seção a seção no arquivo-urna.

Antes das 17h o total consolidado do TSE fica zerado, mas o boletim de cada seção do exterior sai assim que ela
fecha. Este coletor (rodado de hora em hora por timer) lê o índice de seções do exterior, consulta só as seções
principais que ainda não chegaram, baixa o bu.dat das novas, soma por país e grava saida/oficial/data/exterior.json
(publicado pelo eleicoes-publicar e mostrado em site/exterior.html).

Também calcula o "previsto" para o exterior: o 1º turno do exterior (saida/teste1t) passado pela regra de
transferência da Projeção INEMA — a regra inicial (prior) e, quando a projeção estiver pronta, a matriz ajustada.

  python3 exterior/coletor_ext.py              # uma rodada
  python3 exterior/coletor_ext.py --so-montar  # só refaz o exterior.json com o que já foi baixado (sem TSE)
"""
import argparse, json, os, sys, tempfile, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
P = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(P, "projecao"))
import bu  # noqa: E402

PLEITO, ELEICAO = "3221", 6258
PLEITO_1T, ELEICAO_1T = "3220", 6257  # 1º turno: baixado uma vez (--primeiro-turno) para comparar país a país
BASE = f"https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/{PLEITO}/"
INDICE = f"{BASE}config/zz/zz-p00{PLEITO}-cs.json"
BRT = timezone(timedelta(hours=-3))
UA = {"User-Agent": "Mozilla/5.0 (INEMA Eleicoes 2026; exterior)"}
CA, CB = "13", "22"


def agora():
    return datetime.now(BRT).isoformat(timespec="seconds")


def baixa(url, tentativas=2):
    for t in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return e.code, b""
            erro = e
        except Exception as e:  # rede
            erro = e
        time.sleep(1 + t)
    raise erro


def grava(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(caminho), suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, caminho)


def le(caminho, padrao=None):
    try:
        with open(caminho) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def secoes_principais(indice):
    """[(cidade_cd, nome, zona, secao)] — só as principais (as agregadas têm 'nsp' e vão no BU da principal)."""
    out = []
    for m in indice["abr"][0]["mu"]:
        for z in m["zon"]:
            for s in z["sec"]:
                if "nsp" not in s:
                    out.append((m["cd"], m["nm"], z["cd"], s["ns"]))
    return out


def busca_secao(cd, zona, sec, pleito=PLEITO, eleicao=ELEICAO):
    """Boletim de uma seção, ou None se ainda não chegou ou deu erro (tenta de novo na próxima rodada)."""
    try:
        return _busca_secao(cd, zona, sec, pleito, eleicao)
    except Exception as e:  # TSE fora do ar, tempo esgotado, boletim com formato inesperado
        print(json.dumps({"erro_secao": f"{cd}/{zona}/{sec}", "pleito": pleito, "tipo": type(e).__name__,
                          "msg": str(e)[:120]}, ensure_ascii=False), flush=True)
        return None


def _busca_secao(cd, zona, sec, pleito, eleicao):
    pasta = f"https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/{pleito}/dados/zz/{cd}/{zona}/{sec}/"
    st, corpo = baixa(f"{pasta}p00{pleito}-zz-m{cd}-z{zona}-s{sec}-aux.json")
    if st != 200:
        return None  # ainda não chegou
    aux = json.loads(corpo)
    for h in reversed(aux.get("hashes", [])):
        arq = next((a["nm"] for a in h.get("arq", []) if a.get("tp") == "bu"), None)
        if not arq:
            continue
        st, dados = baixa(f"{pasta}{h['hash']}/{arq}")
        if st != 200:
            continue
        r = bu.ler(dados, eleicao)
        r["recebido"] = f"{h.get('dr') or aux.get('dg')} {h.get('hr') or aux.get('hg')}"
        r["situacao"] = aux.get("st")
        return r
    return None


def previstos(nomes):
    """Exterior previsto pela regra de transferência da projeção, aplicada ao 1º turno do exterior."""
    import numpy as np
    import modelo as M
    import projetar as PJ
    r1 = PJ.ultimo(os.path.join(P, "saida", "teste1t", "data"), "zz")
    if not r1:
        return {}
    v1, _ = PJ.vetor_ext_1t(r1)

    def pct(T):
        d = v1 @ T
        return {CA: round(100 * d[0] / (d[0] + d[1]), 2), CB: round(100 * d[1] / (d[0] + d[1]), 2)}

    vot1 = {c["numero"]: c["votos"] for c in r1["candidatos"]}
    val1 = r1["votos"]["validos"] or 1
    out = {"primeiro_turno": {CA: round(100 * vot1.get(CA, 0) / val1, 2), CB: round(100 * vot1.get(CB, 0) / val1, 2),
                              "nota": "1º turno no exterior (% dos válidos, com todos os candidatos)"},
           "regra_inicial": {**pct(M.prior(PJ.GRUPOS_1T, CA, CB)),
                             "nota": "regra de partida da Projeção INEMA, sem nenhum dado do 2º turno"}}
    proj = le(os.path.join(P, "saida", "oficial", "data", "projecao.json"), {})
    tr = (proj.get("transferencias") or {}).get("BR") if proj.get("status") == "ok" else None
    if tr and len(tr) == len(v1):
        T = np.array([[t["para"][CA], t["para"][CB], t["para"]["brancos_nulos"], t["para"]["nao_votou"]] for t in tr]) / 100
        out["projecao"] = {**pct(T), "calculado_em": proj.get("calculado_em"),
                           "nota": "transferências que a Projeção INEMA mediu no Brasil, aplicadas ao exterior"}
    return out


def matrizes():
    """Regras de transferência da Projeção INEMA: a inicial (prior) e, se a projeção estiver pronta, a medida no Brasil."""
    import numpy as np
    import modelo as M
    import projetar as PJ
    out = {"regra_inicial": M.prior(PJ.GRUPOS_1T, CA, CB)}
    proj = le(os.path.join(P, "saida", "oficial", "data", "projecao.json"), {})
    tr = (proj.get("transferencias") or {}).get("BR") if proj.get("status") == "ok" else None
    if tr and len(tr) == len(PJ.GRUPOS_1T) + 3:
        out["projecao"] = np.array([[t["para"][CA], t["para"][CB], t["para"]["brancos_nulos"], t["para"]["nao_votou"]]
                                    for t in tr]) / 100
    return out, PJ.GRUPOS_1T


def vetor_1t(x, grupos):
    """Origens do 1º turno de um conjunto de seções (mesma ordem da projeção)."""
    import numpy as np
    v = x["votos"]
    return np.array([v.get(g, 0) for g in grupos] + [sum(n for k, n in v.items() if k not in grupos),
                     x["brancos"] + x["nulos"], max(0, x["aptos"] - x["comparecimento"])], float)


def preve(vec, Ts):
    out = {}
    for nome, T in Ts.items():
        d = vec @ T
        if d[0] + d[1] > 0:
            out[nome] = {CA: round(100 * d[0] / (d[0] + d[1]), 2), CB: round(100 * d[1] / (d[0] + d[1]), 2)}
    return out or None


def soma(alvo, r):
    alvo["recebidas"] += 1
    alvo["aptos"] += r["aptos"]
    alvo["comparecimento"] += r["comparecimento"]
    alvo["brancos"] += r["brancos"]
    alvo["nulos"] += r["nulos"]
    for k, v in r["votos"].items():
        alvo["votos"][k] = alvo["votos"].get(k, 0) + v
    if r.get("recebido") and r["recebido"] > (alvo.get("ultimo") or ""):
        alvo["ultimo"] = r["recebido"]


def fecha(x):
    a, b = x["votos"].get(CA, 0), x["votos"].get(CB, 0)
    x["validos"] = a + b
    x["pct"] = {CA: round(100 * a / (a + b), 2), CB: round(100 * b / (a + b), 2)} if a + b else None
    x["lider"] = None if not a + b or a == b else (CA if a > b else CB)
    return x


def pct_1t(x):
    """% dos válidos no 1º turno (com todos os candidatos), igual ao TSE."""
    val = sum(x["votos"].values())
    return {CA: round(100 * x["votos"].get(CA, 0) / val, 2), CB: round(100 * x["votos"].get(CB, 0) / val, 2),
            "validos": val, "comparecimento": x["comparecimento"]} if val else None


def soma_1t(t1):
    """{cidade_cd: soma das seções do 1º turno}."""
    out = {}
    for chave, r in (t1 or {}).get("secoes", {}).items():
        c = out.setdefault(chave.split("/")[0], {"comparecimento": 0, "aptos": 0, "brancos": 0, "nulos": 0, "votos": {}})
        for k in ("comparecimento", "aptos", "brancos", "nulos"):
            c[k] += r[k]
        for k, v in r["votos"].items():
            c["votos"][k] = c["votos"].get(k, 0) + v
    return out


def monta(indice, estado, paises, candidatos, t1=None):
    c1 = soma_1t(t1)
    cid_pais = paises["cidades"]
    cont = {p: c for c, ps in paises["continentes"].items() for p in ps}
    vazio = lambda: {"secoes": 0, "recebidas": 0, "aptos": 0, "comparecimento": 0, "brancos": 0, "nulos": 0,
                     "votos": {}, "ultimo": None}
    total, por_pais, por_cid = vazio(), {}, {}
    for cd, nome, zona, sec in secoes_principais(indice):
        pais = cid_pais.get(nome, "?")
        pp = por_pais.setdefault(pais, {**vazio(), "pais": pais, "continente": cont.get(pais, "?")})
        cc = por_cid.setdefault(cd, {**vazio(), "cidade": nome, "pais": pais})
        for x in (total, pp, cc):
            x["secoes"] += 1
        r = estado["secoes"].get(f"{cd}/{zona}/{sec}")
        if r:
            for x in (total, pp, cc):
                soma(x, r)
    Ts, grupos = matrizes()
    novo = lambda: {"comparecimento": 0, "aptos": 0, "brancos": 0, "nulos": 0, "votos": {}}
    p1, tot1, vec_pais, vec_mesmas, mesmas = {}, novo(), {}, 0, 0
    for cd, c in por_cid.items():
        x = c1.get(cd)
        c["primeiro_turno"] = pct_1t(x) if x else None
        if x:
            vc = vetor_1t(x, grupos)
            c["previsto"] = preve(vc, Ts)
            vec_pais[c["pais"]] = vec_pais.get(c["pais"], 0) + vc
            if c["recebidas"]:  # cidades que já mandaram boletim: base da comparação justa
                vec_mesmas = vec_mesmas + vc
                mesmas += 1
            for alvo in (p1.setdefault(c["pais"], novo()), tot1):
                for k in ("comparecimento", "aptos", "brancos", "nulos"):
                    alvo[k] += x[k]
                for k, v in x["votos"].items():
                    alvo["votos"][k] = alvo["votos"].get(k, 0) + v
        por_pais[c["pais"]].setdefault("cidades", []).append(fecha(c))
    for p, x in p1.items():
        por_pais[p]["primeiro_turno"] = pct_1t(x)
        por_pais[p]["previsto"] = preve(vec_pais[p], Ts)
    total["primeiro_turno"] = pct_1t(tot1) if c1 else None
    prev = previstos(candidatos)
    if mesmas:
        prev["mesmas_cidades"] = {**(preve(vec_mesmas, Ts) or {}), "cidades": mesmas,
                                  "nota": "previsto só para as cidades que já mandaram boletim (compara com o apurado)"}
    lista = sorted((fecha(p) for p in por_pais.values()), key=lambda p: (-p["recebidas"] > 0, -p["comparecimento"], p["pais"]))
    for p in lista:
        p["cidades"].sort(key=lambda c: (-c["comparecimento"], c["cidade"]))
        for c in p["cidades"]:
            del c["pais"]
    return {
        "schema": 1, "tipo": "exterior", "gerado_em": agora(), "ultima_consulta_tse": estado.get("ultima_consulta"),
        "fonte": {"orgao": "TSE", "tipo": "boletins de urna por seção (arquivo-urna)", "indice": INDICE,
                  "pasta": f"{BASE}dados/zz/", "nota": "parcial: soma dos boletins já publicados; o total oficial "
                  "do TSE (painel principal) só começa às 17h de Brasília"},
        "candidatos": candidatos,
        "total": fecha(total), "previsto": prev, "paises": lista,
    }


def candidatos_atuais():
    try:
        sys.path.insert(0, os.path.join(P, "projecao"))
        import projetar as PJ
        r = PJ.ultimo(os.path.join(P, "saida", "oficial", "data"), "br")
        return [{"numero": c["numero"], "nome_urna": c["nome_urna"]} for c in r["candidatos"]]
    except Exception:
        return [{"numero": CA, "nome_urna": "LULA"}, {"numero": CB, "nome_urna": "FLAVIO BOLSONARO"}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estado", default=os.path.join(P, "saida", "exterior", "estado.json"))
    ap.add_argument("--saida", default=os.path.join(P, "saida", "oficial", "data", "exterior.json"))
    ap.add_argument("--so-montar", action="store_true")
    ap.add_argument("--paralelo", type=int, default=6)
    ap.add_argument("--primeiro-turno", action="store_true", help="baixa uma vez os boletins do 1º turno do exterior")
    a = ap.parse_args()
    paises = le(os.path.join(AQUI, "paises.json"))
    arq_1t = os.path.join(os.path.dirname(a.estado), "primeiro_turno.json")
    if a.primeiro_turno:
        st, corpo = baixa(f"https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/{PLEITO_1T}/config/zz/zz-p00{PLEITO_1T}-cs.json")
        if st != 200:
            sys.exit(f"índice do 1º turno indisponível: HTTP {st}")
        ind1 = json.loads(corpo)
        t1 = le(arq_1t, {"secoes": {}})
        faltam = [(cd, z, s) for cd, _, z, s in secoes_principais(ind1) if f"{cd}/{z}/{s}" not in t1["secoes"]]
        with ThreadPoolExecutor(a.paralelo) as ex:
            for (cd, z, s), r in zip(faltam, ex.map(lambda t: busca_secao(*t, PLEITO_1T, ELEICAO_1T), faltam)):
                if r:
                    t1["secoes"][f"{cd}/{z}/{s}"] = r
        grava(arq_1t, t1)
        v = {}
        for r in t1["secoes"].values():
            for k, n in r["votos"].items():
                v[k] = v.get(k, 0) + n
        print(json.dumps({"primeiro_turno_secoes": len(t1["secoes"]), "de": len(secoes_principais(ind1)),
                          "votos": {CA: v.get(CA), CB: v.get(CB)}}))
        return
    estado = le(a.estado, {"secoes": {}})
    t0 = time.time()
    ind_arq = os.path.join(os.path.dirname(a.estado), "indice.json")
    if a.so_montar:
        indice = le(ind_arq)
        novas = 0
    else:
        st, corpo = baixa(INDICE)
        if st != 200:
            sys.exit(f"índice do exterior indisponível: HTTP {st}")
        indice = json.loads(corpo)
        grava(ind_arq, indice)
        faltam = [(cd, z, s) for cd, _, z, s in secoes_principais(indice) if f"{cd}/{z}/{s}" not in estado["secoes"]]
        novas = 0
        with ThreadPoolExecutor(a.paralelo) as ex:
            for (cd, z, s), r in zip(faltam, ex.map(lambda t: busca_secao(*t), faltam)):
                if r:
                    estado["secoes"][f"{cd}/{z}/{s}"] = r
                    novas += 1
                    if novas % 100 == 0:
                        grava(a.estado, estado)  # não perde o que já baixou se a rodada cair
        estado["ultima_consulta"] = agora()
        grava(a.estado, estado)
    sem_pais = sorted({nm for _, nm, _, _ in secoes_principais(indice)} - set(paises["cidades"]))
    out = monta(indice, estado, paises, candidatos_atuais(), le(arq_1t))
    grava(a.saida, out)
    t = out["total"]
    print(json.dumps({"t": agora(), "novas": novas, "recebidas": t["recebidas"], "secoes": t["secoes"],
                      "pct": t["pct"], "sem_pais": sem_pais, "s": round(time.time() - t0, 1)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
