#!/usr/bin/env python3
"""Conferência independente dos resultados (fase inicial) -> saida/oficial/data/conferencia.json

Lê só arquivos locais (nada de rede):
  1. Conciliação das somas: Brasil = 27 UFs + exterior (arquivos mais recentes e momentos da noite guardados
     em bruto/), e cada UF = soma das suas cidades (2º turno), quando todas as cidades e a UF estão fechadas.
  2. Integridade da coleta: sha256 de cada arquivo bruto guardado x nome; log x disco; bloqueios do coletor.
  3. Exterior: soma dos boletins de urna (exterior.json) x total oficial do TSE (abrangência zz).
  4. Auditoria da Projeção INEMA: histórico da noite x resultado apurado.

Classificação de cada item: conferido / pendente / divergencia / insuficiente.
Um padrão atípico não é prova de nada; diferença entre arquivos de horários diferentes é esperada.

  python3 analise/conferencia.py
"""
import glob
import hashlib
import json
import os
import sys
import tempfile
from bisect import bisect_right
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
P = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(P, "coleta"))
import nucleo as N  # noqa: E402

OF = os.path.join(P, "saida", "oficial")
DATA = os.path.join(OF, "data")
BRUTO = os.path.join(OF, "bruto")
MUN = os.path.join(P, "saida", "municipios", "data")
SAIDA = os.path.join(DATA, "conferencia.json")
BRT = timezone(timedelta(hours=-3))
A, B = "13", "22"
VERSAO = "1.0"

NOMES = {"ac": "Acre", "al": "Alagoas", "am": "Amazonas", "ap": "Amapá", "ba": "Bahia", "ce": "Ceará",
         "df": "Distrito Federal", "es": "Espírito Santo", "go": "Goiás", "ma": "Maranhão", "mg": "Minas Gerais",
         "ms": "Mato Grosso do Sul", "mt": "Mato Grosso", "pa": "Pará", "pb": "Paraíba", "pe": "Pernambuco",
         "pi": "Piauí", "pr": "Paraná", "rj": "Rio de Janeiro", "rn": "Rio Grande do Norte", "ro": "Rondônia",
         "rr": "Roraima", "rs": "Rio Grande do Sul", "sc": "Santa Catarina", "se": "Sergipe", "sp": "São Paulo",
         "to": "Tocantins", "zz": "Exterior", "br": "Brasil"}

# campos comparados na conciliação (rótulo, função que extrai do resultado do contrato)
def _cand(res, num):
    return next((c["votos"] for c in res["candidatos"] if c["numero"] == num), 0)


CAMPOS = [
    ("Votos de Lula (13)", lambda r: _cand(r, A)),
    ("Votos de Flávio (22)", lambda r: _cand(r, B)),
    ("Votos válidos", lambda r: r["votos"]["validos"]),
    ("Brancos", lambda r: r["votos"]["brancos"]),
    ("Nulos", lambda r: r["votos"]["nulos"]),
    ("Total de votos", lambda r: r["votos"]["total"]),
    ("Comparecimento", lambda r: r["eleitorado"]["comparecimento"]),
    ("Eleitorado", lambda r: r["eleitorado"]["total"]),
    ("Seções totalizadas", lambda r: r["secoes"]["totalizadas"]),
    ("Seções previstas", lambda r: r["secoes"]["total"]),
]


def agora():
    return datetime.now(BRT).isoformat(timespec="seconds")


def le(caminho, padrao=None):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def grava(caminho, obj):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(caminho), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, caminho)


def le_log():
    out = []
    try:
        with open(os.path.join(OF, "coleta.jsonl"), encoding="utf-8") as f:
            for linha in f:
                try:
                    out.append(json.loads(linha))
                except json.JSONDecodeError:
                    pass  # última linha pode estar sendo escrita agora
    except FileNotFoundError:
        pass
    return out


def pct(x, tot):
    return round(100 * x / tot, 2) if tot else None


def mil(x):
    return f"{x:,}".replace(",", ".")


def r2(x):
    return round(x, 2) + 0.0 if x is not None else None  # + 0.0 tira o "-0.0"


def hora_bruto(nome):
    """'20261025-223148-ba8e7bc9.json' -> ISO em Brasília."""
    try:
        d = datetime.strptime(nome[:15], "%Y%m%d-%H%M%S").replace(tzinfo=BRT)
        return d.isoformat(timespec="seconds")
    except ValueError:
        return None


def compara(a, b):
    """Lista de campos: valor de 'a' (oficial), soma 'b' e diferença."""
    return [{"campo": rot, "oficial": f(a), "soma": f(b), "dif": f(b) - f(a)} for rot, f in CAMPOS]


def soma_res(lista):
    """Soma vários resultados do contrato num pseudo-resultado com os mesmos campos."""
    tot = {"candidatos": [{"numero": A, "votos": 0}, {"numero": B, "votos": 0}],
           "votos": {"validos": 0, "brancos": 0, "nulos": 0, "total": 0},
           "eleitorado": {"comparecimento": 0, "total": 0}, "secoes": {"totalizadas": 0, "total": 0}}
    for r in lista:
        for c in tot["candidatos"]:
            c["votos"] += _cand(r, c["numero"])
        for k in tot["votos"]:
            tot["votos"][k] += r["votos"][k]
        for k in tot["eleitorado"]:
            tot["eleitorado"][k] += r["eleitorado"][k]
        for k in tot["secoes"]:
            tot["secoes"][k] += r["secoes"][k]
    return tot


# ---------------------------------------------------------------- 2. integridade

def integridade(log, man):
    arquivos, errados, por_abr = 0, [], {}
    sha_de = {}  # caminho relativo -> sha256 completo
    for f in sorted(glob.glob(os.path.join(BRUTO, "*", "*.json"))):
        abr, nome = f.split(os.sep)[-2], os.path.basename(f)
        with open(f, "rb") as fh:
            h = hashlib.sha256(fh.read()).hexdigest()
        arquivos += 1
        por_abr[abr] = por_abr.get(abr, 0) + 1
        sha_de[f"{abr}/{nome}"] = h
        if not nome[:-5].endswith(h[:8]):
            errados.append(f"{abr}/{nome}")

    ev_u = [x for x in log if x.get("evento") == "u"]
    no_log = {f"{x['abr']}/{x['arquivo']}": x.get("sha", "") for x in ev_u}
    faltando = [k for k in no_log if k not in sha_de]
    sha_log_dif = [k for k, s in no_log.items() if k in sha_de and s and not sha_de[k].startswith(s)]
    sem_log = [k for k in sha_de if k not in no_log]

    publicados = [x for x in log if x.get("evento") == "PUBLICADO"]
    bloqueios = [{"t": x.get("t"), "abr": x.get("abr"), "problemas": x.get("problemas", []), "sha": x.get("sha"),
                  "msg": x.get("msg")} for x in log if x.get("evento") == "BLOQUEIO"]
    erros = [{"t": x.get("t"), "erro": x.get("erro")} for x in log if x.get("evento") == "ERRO"]
    br_soma = [x for x in log if x.get("evento") == "br_soma"]
    ab = [x for x in log if x.get("evento") == "ab"]

    # os arquivos publicados no manifesto atual têm o original guardado?
    shas = set(sha_de.values())  # manifesto e log lidos antes do glob: nada publicado fica sem o bruto por corrida
    pub_ok, pub_sem = 0, []
    for abr, info in (man.get("abrangencias") or {}).items():
        r = le(os.path.join(DATA, info["arquivo"]))
        s = r and r.get("fonte", {}).get("sha256_bruto")
        if s and s in shas:
            pub_ok += 1
        else:
            pub_sem.append(abr)

    return {
        "arquivos": arquivos, "por_abr": por_abr, "sha_conferidos": arquivos - len(errados), "sha_errados": errados[:50],
        "log_downloads": len(ev_u), "log_faltando_em_disco": faltando[:50], "log_sha_diferente": sha_log_dif[:50],
        "disco_sem_log": len(sem_log),
        "consultas_indice": len(ab), "publicacoes": len(publicados),
        "primeira_publicacao": publicados[0]["t"] if publicados else None,
        "ultima_publicacao": publicados[-1]["t"] if publicados else None,
        "ultima_versao": publicados[-1].get("versao") if publicados else None,
        "bloqueios": bloqueios, "erros": erros[-20:], "n_erros": len(erros),
        "avisos_br_soma": len(br_soma),
        "manifesto": {"versao": man.get("versao"), "publicado_em": man.get("publicado_em"),
                      "arquivos": len(man.get("abrangencias") or {}), "com_original": pub_ok, "sem_original": pub_sem},
        "_sha_de": sha_de,
    }


# ---------------------------------------------------------------- 1a. Brasil = UFs + zz

def conciliacao_brasil(man, integ):
    abrs = N.UFS + ["zz"]
    info = man.get("abrangencias") or {}
    atual = {a: le(os.path.join(DATA, info[a]["arquivo"])) for a in ["br"] + abrs if a in info}
    out = {"atual": None, "momentos": None}

    if all(atual.get(a) for a in ["br"] + abrs):
        br = atual["br"]
        soma = soma_res([atual[a] for a in abrs])
        campos = compara(br, soma)
        bate = all(c["dif"] == 0 for c in campos)
        horas = sorted(atual[a]["fonte"]["totalizado_tse"] or "" for a in abrs)
        mesma_geracao = soma["secoes"]["totalizadas"] == br["secoes"]["totalizadas"]
        if bate:
            st, motivo = "conferido", "Todos os campos do arquivo Brasil são iguais à soma das 27 UFs + exterior."
        elif not mesma_geracao:
            st = "pendente"
            motivo = (f"Os arquivos são de horários diferentes: o do Brasil tem {mil(br['secoes']['totalizadas'])} seções "
                      f"totalizadas e a soma das UFs, {mil(soma['secoes']['totalizadas'])}. Durante a apuração o TSE "
                      "atualiza o arquivo do Brasil antes de alguns estados; a conta só fecha quando todos estiverem "
                      "na mesma atualização.")
        else:
            st = "divergencia"
            motivo = ("Mesma quantidade de seções, mas algum campo diferente. Precisa ser reproduzido com arquivos "
                      "da mesma atualização antes de qualquer conclusão.")
        out["atual"] = {"status": st, "motivo": motivo, "campos": campos,
                        "br_totalizado": br["fonte"]["totalizado_tse"], "br_versao": br["versao"],
                        "ufs_totalizado_de": horas[0] or None, "ufs_totalizado_ate": horas[-1] or None,
                        "br_final": br["situacao"]["totalizacao_final"]}

    # momentos da noite: cada bruto do Brasil x último bruto de cada UF/zz baixado até aquele instante
    bloq = {x.get("sha") for x in integ["bloqueios"] if x.get("abr") == "br" and x.get("sha")}
    arqs = {}
    for k in integ["_sha_de"]:
        abr, nome = k.split("/")
        arqs.setdefault(abr, []).append(nome)
    for a in arqs:
        arqs[a].sort()
    cache = {}

    def res(abr, nome):
        k = f"{abr}/{nome}"
        if k not in cache:
            try:
                with open(os.path.join(BRUTO, abr, nome), "rb") as fh:
                    cache[k] = N.consolidar(fh.read(), abr, "", 0)[0]
            except Exception:  # arquivo fora do formato: fica fora da conta
                cache[k] = None
        return cache[k]

    comparaveis, conferidos, divergentes, sem_par, vazios, bloqueados = 0, 0, [], 0, 0, []
    ultimo_ok = None
    for nome in arqs.get("br", []):
        sha8 = nome[16:24]
        if any(s and s.startswith(sha8) for s in bloq):
            bloqueados.append({"arquivo": nome, "t": hora_bruto(nome)})
            continue
        rb = res("br", nome)
        if not rb:
            continue
        if rb["secoes"]["totalizadas"] == 0:
            vazios += 1
            continue
        partes = []
        for a in abrs:
            lst = arqs.get(a, [])
            i = bisect_right(lst, nome[:15] + "~") - 1  # mesmo segundo ou antes
            if i < 0:
                break
            r = res(a, lst[i])
            if not r:
                break
            partes.append(r)
        if len(partes) != len(abrs):
            sem_par += 1
            continue
        soma = soma_res(partes)
        if soma["secoes"]["totalizadas"] != rb["secoes"]["totalizadas"]:
            sem_par += 1
            continue
        comparaveis += 1
        campos = compara(rb, soma)
        if all(c["dif"] == 0 for c in campos):
            conferidos += 1
            ultimo_ok = {"arquivo": nome, "t": hora_bruto(nome), "totalizado_tse": rb["fonte"]["totalizado_tse"],
                         "secoes": rb["secoes"]["totalizadas"], "pct_secoes": pct(rb["secoes"]["totalizadas"], rb["secoes"]["total"])}
        else:
            divergentes.append({"arquivo": nome, "t": hora_bruto(nome),
                                "campos": [c for c in campos if c["dif"]]})
    total_br = len(arqs.get("br", []))
    if divergentes:
        st = "divergencia"
    elif conferidos:
        st = "conferido"
    elif comparaveis == 0:
        st = "insuficiente"
    else:
        st = "pendente"
    out["momentos"] = {"status": st, "arquivos_br": total_br, "sem_votos": vazios, "bloqueados": bloqueados,
                       "sem_par": sem_par, "comparaveis": comparaveis, "conferidos": conferidos,
                       "divergentes": divergentes[:20], "n_divergentes": len(divergentes), "ultimo_conferido": ultimo_ok}
    return out, atual


# ---------------------------------------------------------------- 1b. UF = soma das cidades

def ultimo_mun(uf):
    fs = sorted(glob.glob(os.path.join(MUN, "uf", uf, "v*.json")))
    return (le(fs[-1]), os.path.basename(fs[-1])) if fs else (None, None)


def conciliacao_ufs(atual):
    linhas = []
    for uf in N.UFS:
        u = atual.get(uf)
        d, arq = ultimo_mun(uf)
        lin = {"uf": uf, "nome": NOMES[uf], "arquivo_cidades": arq}
        if not u or not d:
            lin.update(status="insuficiente", motivo="Sem arquivo da UF ou das cidades.")
            linhas.append(lin)
            continue
        ci = list((d.get("cidades") or {}).values())
        fin = [c for c in ci if c.get("and") == "finalizada" and c.get("st") == c.get("ts") and c.get("c")]
        soma = {"candidatos": [{"numero": A, "votos": sum(c["c"].get(A, 0) for c in ci if c.get("c"))},
                               {"numero": B, "votos": sum(c["c"].get(B, 0) for c in ci if c.get("c"))}],
                "votos": {"validos": sum(c.get("vv") or 0 for c in ci), "brancos": sum(c.get("vb") or 0 for c in ci),
                          "nulos": sum(c.get("vn") or 0 for c in ci), "total": sum(c.get("tv") or 0 for c in ci)},
                "eleitorado": {"comparecimento": sum(c.get("comp") or 0 for c in ci), "total": sum(c.get("te") or 0 for c in ci)},
                "secoes": {"totalizadas": sum(c.get("st") or 0 for c in ci), "total": sum(c.get("ts") or 0 for c in ci)}}
        campos = compara(u, soma)
        cad = {c["campo"]: c["dif"] == 0 for c in campos if c["campo"] in ("Eleitorado", "Seções previstas")}
        uf_fechada = u["secoes"]["totalizadas"] == u["secoes"]["total"]
        faltam = len(ci) - len(fin)
        lin.update(cidades=len(ci), finalizadas=len(fin), faltam=faltam,
                   uf_secoes=u["secoes"]["totalizadas"], uf_secoes_total=u["secoes"]["total"],
                   uf_totalizado=u["fonte"]["totalizado_tse"], uf_final=u["situacao"]["totalizacao_final"],
                   cadastro_ok=all(cad.values()), bloqueadas=d.get("bloqueadas") or [],
                   cidades_publicado=d.get("publicado_em"), campos=campos)
        if faltam:
            lin.update(status="pendente",
                       motivo=f"Faltam {faltam} de {len(ci)} cidades com resultado final na coleta por cidade do INEMA.")
        elif not uf_fechada:
            lin.update(status="pendente",
                       motivo=f"Todas as cidades fecharam, mas o arquivo do estado ainda tem "
                              f"{u['secoes']['totalizadas']} de {u['secoes']['total']} seções (atualização mais antiga).")
        elif all(c["dif"] == 0 for c in campos):
            lin.update(status="conferido", motivo="Soma das cidades igual ao total do estado em todos os campos.")
        else:
            lin.update(status="divergencia",
                       motivo="Cidades e estado fechados, mas algum campo difere. Precisa reprocessar e conferir "
                              "as versões dos arquivos antes de qualquer conclusão.")
        linhas.append(lin)
    return linhas


# ---------------------------------------------------------------- 3. exterior

def exterior(atual):
    e = le(os.path.join(DATA, "exterior.json"))
    zz = atual.get("zz")
    if not e or not zz:
        return {"status": "insuficiente", "motivo": "Falta o arquivo do exterior (boletins) ou o total oficial (zz)."}
    t = e.get("total") or {}
    bu = {"Votos de Lula (13)": (t.get("votos") or {}).get(A, 0), "Votos de Flávio (22)": (t.get("votos") or {}).get(B, 0),
          "Brancos": t.get("brancos", 0), "Nulos": t.get("nulos", 0), "Comparecimento": t.get("comparecimento", 0),
          "Seções": t.get("recebidas", 0)}
    of = {"Votos de Lula (13)": _cand(zz, A), "Votos de Flávio (22)": _cand(zz, B), "Brancos": zz["votos"]["brancos"],
          "Nulos": zz["votos"]["nulos"], "Comparecimento": zz["eleitorado"]["comparecimento"],
          "Seções": zz["secoes"]["totalizadas"]}
    campos = [{"campo": k, "boletins": bu[k], "oficial": of[k], "dif": bu[k] - of[k]} for k in bu]
    sec, rec = t.get("secoes", 0), t.get("recebidas", 0)
    acima = [c["campo"] for c in campos if c["boletins"] > c["oficial"]]
    cobertura = pct(rec, sec)
    if rec and rec == sec and all(c["dif"] == 0 for c in campos):
        st, mot = "conferido", "Soma de todos os boletins de urna igual ao total oficial do exterior."
    elif rec == sec and rec:
        st, mot = "divergencia", "Todos os boletins lidos e algum campo difere do total oficial. Precisa reprocessar."
    elif acima:
        st = "divergencia"
        mot = "Com parte dos boletins, a soma já passa o oficial em: " + ", ".join(acima) + ". Precisa reprocessar."
    else:
        st = "pendente"
        mot = (f"Boletins lidos em {rec} de {sec} seções ({str(cobertura).replace('.', ',')}%). A conta só fecha com 100%. "
               "Até lá, a soma parcial de cada campo precisa ficar abaixo ou igual ao oficial — e fica.")
    return {"status": st, "motivo": mot, "campos": campos, "secoes": sec, "recebidas": rec, "cobertura": cobertura,
            "bu_gerado": e.get("gerado_em"), "bu_ultimo_boletim": t.get("ultimo"),
            "parcial_abaixo_do_oficial": not acima,
            "oficial_totalizado": zz["fonte"]["totalizado_tse"], "oficial_final": zz["situacao"]["totalizacao_final"],
            "oficial_secoes": zz["secoes"]["totalizadas"], "oficial_secoes_total": zz["secoes"]["total"]}


# ---------------------------------------------------------------- 4. projeção

def projecao(atual):
    h = le(os.path.join(DATA, "projecao-historico.json")) or {}
    E = [x for x in (h.get("entradas") or []) if x.get("a") is not None]
    br = atual.get("br")
    if not E or not br:
        return {"status": "insuficiente", "motivo": "Sem histórico da projeção ou sem resultado do Brasil."}
    cand = h.get("candidato_a", A)
    vv = br["votos"]["validos"]
    final = round(100 * _cand(br, cand) / vv, 4) if vv else None

    def pct_uf(r):
        v = r["votos"]["validos"]
        return round(100 * _cand(r, cand) / v, 4) if v else None

    vence_a = final > 50
    # desde quando apontou o vencedor e não mudou mais
    desde = desde_faixa = desde_tse = None
    for i in range(len(E) - 1, -1, -1):
        if (E[i]["a"] > 50) == vence_a:
            desde = i
        else:
            break
    for i in range(len(E) - 1, -1, -1):
        lo, hi = E[i].get("lo"), E[i].get("hi")
        if lo is not None and ((lo > 50) if vence_a else (hi < 50)):
            desde_faixa = i
        else:
            break
    for i in range(len(E) - 1, -1, -1):
        if E[i].get("tse_a") is not None and (E[i]["tse_a"] > 50) == vence_a:
            desde_tse = i
        else:
            break

    def ponto(i):
        if i is None:
            return None
        x = E[i]
        return {"t": x["t"], "a": x["a"], "lo": x.get("lo"), "hi": x.get("hi"), "tse_a": x.get("tse_a"),
                "tse_secoes": x.get("tse_secoes"), "pct_cid": x.get("pct_cid"), "pct_el": x.get("pct_el"), "indice": i}

    com_faixa = [x for x in E if x.get("lo") is not None and x.get("hi") is not None]
    dentro = sum(1 for x in com_faixa if x["lo"] <= final <= x["hi"])
    erros = [x["a"] - final for x in E]
    erros_tse = [x["tse_a"] - final for x in E if x.get("tse_a") is not None]

    ufs = []
    ult = E[-1].get("ufs") or {}
    for uf in sorted(set(k for x in E for k in (x.get("ufs") or {}))):
        r = atual.get(uf)
        if not r:
            continue
        fv = pct_uf(r)
        prim = next((x for x in E if uf in (x.get("ufs") or {})), None)
        ufs.append({"uf": uf, "nome": NOMES.get(uf, uf.upper()), "apurado": fv,
                    "secoes_pct": pct(r["secoes"]["totalizadas"], r["secoes"]["total"]),
                    "final": r["situacao"]["totalizacao_final"],
                    "ultima": ult.get(uf), "erro_ultima": r2(ult[uf] - fv) if uf in ult and fv is not None else None,
                    "primeira_t": prim["t"] if prim else None, "primeira": prim["ufs"][uf] if prim else None,
                    "erro_primeira": r2(prim["ufs"][uf] - fv) if prim and fv is not None else None,
                    "primeira_tse_secoes": prim.get("tse_secoes") if prim else None})
    eu = [abs(u["erro_ultima"]) for u in ufs if u["erro_ultima"] is not None]
    ep = [abs(u["erro_primeira"]) for u in ufs if u["erro_primeira"] is not None]

    serie = [{"t": x["t"], "a": x["a"], "lo": x.get("lo"), "hi": x.get("hi"), "tse_a": x.get("tse_a"),
              "tse_secoes": x.get("tse_secoes"), "pct_cid": x.get("pct_cid")} for x in E]
    versoes = sorted(set(str(x.get("v")) for x in E))
    return {
        "status": "conferido" if desde is not None else "pendente",
        "candidato": cand, "final": final, "final_secoes_pct": pct(br["secoes"]["totalizadas"], br["secoes"]["total"]),
        "final_totalizado": br["fonte"]["totalizado_tse"], "final_oficial": br["situacao"]["totalizacao_final"],
        "vencedor": cand if vence_a else (B if cand == A else A),
        "entradas": len(E), "versoes": versoes, "inicio": E[0]["t"], "fim": E[-1]["t"],
        "desde": ponto(desde), "desde_faixa": ponto(desde_faixa), "desde_tse": ponto(desde_tse),
        "primeira": ponto(0), "ultima": ponto(len(E) - 1),
        "erro_primeira": round(erros[0], 2), "erro_ultima": round(erros[-1], 2),
        "erro_medio": round(sum(erros) / len(erros), 2), "erro_medio_abs": round(sum(abs(x) for x in erros) / len(erros), 2),
        "erro_max_abs": round(max(abs(x) for x in erros), 2),
        "erro_tse_primeira": round(erros_tse[0], 2) if erros_tse else None,
        "faixa_n": len(com_faixa), "faixa_dentro": dentro, "faixa_pct": pct(dentro, len(com_faixa)),
        "ufs": ufs, "ufs_erro_medio_ultima": round(sum(eu) / len(eu), 2) if eu else None,
        "ufs_erro_medio_primeira": round(sum(ep) / len(ep), 2) if ep else None,
        "ufs_erro_max_ultima": round(max(eu), 2) if eu else None,
        "serie": serie,
    }


# ---------------------------------------------------------------- montagem

def main():
    t0 = agora()
    man = le(os.path.join(DATA, "latest.json"), {}) or {}
    log = le_log()
    integ = integridade(log, man)
    brasil, atual = conciliacao_brasil(man, integ)
    ufs = conciliacao_ufs(atual)
    ext = exterior(atual)
    proj = projecao(atual)
    integ.pop("_sha_de", None)

    br = atual.get("br")
    itens = []

    def item(bloco, titulo, status, num, den, horario, criterio):
        itens.append({"bloco": bloco, "titulo": titulo, "status": status, "num": num, "den": den,
                      "horario": horario, "criterio": criterio})

    if brasil["atual"]:
        a = brasil["atual"]
        ok = sum(1 for c in a["campos"] if c["dif"] == 0)
        item("somas", "Brasil = 27 UFs + exterior (arquivos mais recentes)", a["status"], ok, len(a["campos"]),
             a["br_totalizado"], "Campos iguais entre o arquivo do Brasil e a soma das 28 abrangências publicadas agora.")
    m = brasil["momentos"]
    item("somas", "Brasil = 27 UFs + exterior (momentos guardados da noite)", m["status"], m["conferidos"], m["comparaveis"],
         (m["ultimo_conferido"] or {}).get("t"),
         "Momentos em que todos os arquivos estavam na mesma atualização (mesma soma de seções); conferido = todos os campos iguais.")
    for u in ufs:
        item("somas", f"{u['nome']} = soma das cidades", u["status"],
             u.get("finalizadas"), u.get("cidades"), u.get("uf_totalizado"),
             "Numerador/denominador = cidades com resultado final / cidades da UF. Compara só com tudo fechado.")
    cad_ok = sum(1 for u in ufs if u.get("cadastro_ok"))
    item("somas", "Eleitorado e seções previstas: cidades x estado", "conferido" if cad_ok == len(ufs) else "divergencia",
         cad_ok, len(ufs), t0, "Soma do eleitorado e das seções previstas das cidades igual ao do estado (não depende da apuração).")
    item("integridade", "Arquivos guardados: sha256 confere com o nome",
         "conferido" if not integ["sha_errados"] else "divergencia", integ["sha_conferidos"], integ["arquivos"], t0,
         "sha256 recalculado agora de cada arquivo bruto; os 8 primeiros caracteres precisam ser os do nome.")
    item("integridade", "Downloads do log presentes em disco",
         "conferido" if not integ["log_faltando_em_disco"] and not integ["log_sha_diferente"] else "divergencia",
         integ["log_downloads"] - len(integ["log_faltando_em_disco"]) - len(integ["log_sha_diferente"]), integ["log_downloads"],
         integ["ultima_publicacao"], "Cada download registrado no log tem o arquivo em disco com o mesmo sha.")
    mf = integ["manifesto"]
    item("integridade", "Resultados publicados agora têm o original do TSE guardado",
         "conferido" if not mf["sem_original"] else "divergencia", mf["com_original"], mf["arquivos"], mf["publicado_em"],
         "O sha256_bruto de cada arquivo publicado no manifesto existe entre os brutos guardados.")
    item("exterior", "Exterior: boletins de urna x total oficial", ext["status"], ext.get("recebidas"), ext.get("secoes"),
         ext.get("bu_gerado"), "Seções com boletim lido / seções do exterior. Fecha só com 100%.")

    resumo = {k: sum(1 for i in itens if i["status"] == k) for k in ("conferido", "pendente", "divergencia", "insuficiente")}
    out = {
        "schema": 1, "tipo": "conferencia", "versao": VERSAO, "gerado_em": t0,
        "tse": {"totalizado_tse": br["fonte"]["totalizado_tse"] if br else None,
                "pct_secoes": pct(br["secoes"]["totalizadas"], br["secoes"]["total"]) if br else None,
                "secoes": br["secoes"]["totalizadas"] if br else None, "secoes_total": br["secoes"]["total"] if br else None,
                "final": br["situacao"]["totalizacao_final"] if br else False,
                "pct_validos": {c["numero"]: c["pct_validos"] for c in br["candidatos"]} if br else {},
                "manifesto": man.get("versao")},
        "resumo": resumo, "itens": itens,
        "brasil": brasil, "ufs": ufs, "integridade": integ, "exterior": ext, "projecao": proj,
    }
    grava(SAIDA, out)
    print(json.dumps({"t": t0, "resumo": resumo, "arquivo": SAIDA}, ensure_ascii=False))


if __name__ == "__main__":
    main()
