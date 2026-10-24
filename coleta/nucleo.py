"""Núcleo da Parte 1: TSE (-u.json) -> contrato schema 1, conferências e publicação.

Sem dependências fora da biblioteca padrão. Ver contrato/README.md.
"""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta

SCHEMA = 1
BRT = timezone(timedelta(hours=-3))
ELEICAO = {"pleito": "3221", "eleicao": "6258", "turno": 2, "cargo": 1,
           "cargo_nome": "Presidente", "ano": 2026}
BASE_TSE = "https://resultados.tse.jus.br/oficial/ele2026/6258/"
N_CAND = 2  # 2º turno: exatamente 2 candidatos. 0 = qualquer quantidade (testes com o 1º turno)


def configurar(eleicao="6258", turno=2, ciclo="ele2026", pleito="3221", n_cand=2, base=None):
    """Troca a eleição alvo (ex.: 6257/1º turno para teste). Padrão = 2º turno presidente 2026."""
    global BASE_TSE, N_CAND
    ELEICAO.update({"eleicao": str(eleicao), "turno": int(turno), "pleito": str(pleito)})
    BASE_TSE = base or f"https://resultados.tse.jus.br/oficial/{ciclo}/{eleicao}/"
    N_CAND = n_cand


def url_ab():
    return f"{BASE_TSE}dados/br/br-e{int(ELEICAO['eleicao']):06d}-ab.json"
UFS = ["ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms", "mt", "pa",
       "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc", "se", "sp", "to"]
ABRS = ["br"] + UFS + ["zz"]
NOMES = {"br": "Brasil", "zz": "Exterior", "ac": "Acre", "al": "Alagoas", "am": "Amazonas",
         "ap": "Amapá", "ba": "Bahia", "ce": "Ceará", "df": "Distrito Federal",
         "es": "Espírito Santo", "go": "Goiás", "ma": "Maranhão", "mg": "Minas Gerais",
         "ms": "Mato Grosso do Sul", "mt": "Mato Grosso", "pa": "Pará", "pb": "Paraíba",
         "pe": "Pernambuco", "pi": "Piauí", "pr": "Paraná", "rj": "Rio de Janeiro",
         "rn": "Rio Grande do Norte", "ro": "Rondônia", "rr": "Roraima",
         "rs": "Rio Grande do Sul", "sc": "Santa Catarina", "se": "Sergipe",
         "sp": "São Paulo", "to": "Tocantins"}
ANDAMENTO = {"n": "aguardando", "p": "em_andamento", "f": "finalizada"}


class Bloqueio(Exception):
    """Versão não pode ser publicada."""


def url_tse(abr):
    return f"{BASE_TSE}dados/{abr}/{abr}-c0001-e{int(ELEICAO['eleicao']):06d}-u.json"


def agora():
    return datetime.now(BRT).isoformat(timespec="seconds")


def _i(x):
    return int(x) if x not in (None, "") else 0


def _pct(x):
    """'47,027772356' -> 47.03 (valor oficial, só arredondado)."""
    if x in (None, ""):
        return 0.0
    return round(float(str(x).replace(",", ".")), 2)


def _iso(d, h):
    if not d or not h:
        return None
    dd, mm, aa = d.split("/")
    return f"{aa}-{mm}-{dd}T{h}-03:00"


def candidatos_tse(raw):
    out = []
    for cargo in raw.get("carg", []):
        for agr in cargo.get("agr", []):
            for par in agr.get("par", []):
                for c in par.get("cand", []):
                    out.append((c, par.get("sg", "")))
    return out


def consolidar(raw_bytes, abr, coletado_em, versao, fonte_tipo="oficial"):
    """Converte o -u.json bruto do TSE no resultado do contrato."""
    raw = json.loads(raw_bytes)
    s, e, v = raw["s"], raw["e"], raw["v"]
    cands = [{
        "numero": c["n"], "nome": c["nm"], "nome_urna": c.get("nmu", c["nm"]),
        "partido": sg, "votos": _i(c["vap"]), "pct_validos": _pct(c.get("pvapn")),
        "eleito": c.get("e") == "s", "situacao": c.get("st", ""),
    } for c, sg in candidatos_tse(raw)]
    cands.sort(key=lambda c: c["numero"])  # ordem fixa pelo número (cor segue o candidato)

    tv = _i(v["tv"])
    ordem = sorted(cands, key=lambda c: -c["votos"])
    dif = ordem[0]["votos"] - ordem[1]["votos"] if len(ordem) > 1 else 0
    res = {
        "schema": SCHEMA, "tipo": "resultado", "versao": versao,
        "abrangencia": {"tipo": raw.get("tpabr", "uf"), "cd": abr, "nome": NOMES.get(abr, abr.upper())},
        "eleicao": dict(ELEICAO),
        "fonte": {
            "tipo": fonte_tipo, "url": url_tse(abr), "idg": raw.get("idg"),
            "gerado_tse": _iso(raw.get("dg"), raw.get("hg")),
            "totalizado_tse": _iso(raw.get("dt"), raw.get("ht")),
            "coletado_em": coletado_em,
            "sha256_bruto": hashlib.sha256(raw_bytes).hexdigest(),
        },
        "situacao": {"andamento": ANDAMENTO.get(raw.get("and"), raw.get("and")),
                     "parcial": raw.get("tf") != "s", "totalizacao_final": raw.get("tf") == "s"},
        "secoes": {"total": _i(s["ts"]), "totalizadas": _i(s["st"]), "pendentes": _i(s["snt"]),
                   "pct_totalizadas": _pct(s.get("pstn"))},
        "eleitorado": {"total": _i(e["te"]), "apurado": _i(e["esa"]),
                       "comparecimento": _i(e["c"]), "abstencao": _i(e["a"]),
                       "pct_comparecimento": _pct(e.get("pcn")), "pct_abstencao": _pct(e.get("pan"))},
        "votos": {"total": tv, "validos": _i(v["vv"]), "brancos": _i(v["vb"]), "nulos": _i(v["tvn"]),
                  "pct_validos_sobre_total": _pct(v.get("pvvcn")),
                  "pct_brancos_sobre_total": _pct(v.get("pvbn")),
                  "pct_nulos_sobre_total": _pct(v.get("ptvnn"))},
        "candidatos": cands,
        "derivados": {
            "_aviso": "calculado pelo INEMA a partir dos valores oficiais acima",
            "diferenca_votos": dif,
            "diferenca_pp_validos": round(ordem[0]["pct_validos"] - ordem[1]["pct_validos"], 2) if len(ordem) > 1 else 0,
            "pct_sobre_total": {c["numero"]: round(c["votos"] * 100 / tv, 2) if tv else 0 for c in cands},
            "lider": ordem[0]["numero"] if dif > 0 else None,
        },
    }
    return res, raw


def conferir(raw, res, anterior=None):
    """Regras do contrato. Retorna lista de problemas (vazia = ok)."""
    s, e, v = raw["s"], raw["e"], raw["v"]
    p = []
    if raw.get("ele") != ELEICAO["eleicao"] or raw.get("t") != str(ELEICAO["turno"]):
        p.append(f"eleição/turno inesperado: {raw.get('ele')}/{raw.get('t')}")
    if _i(s["st"]) + _i(s["snt"]) != _i(s["ts"]):
        p.append("seções: st + snt != ts")
    if _i(e["c"]) + _i(e["a"]) != _i(e["esa"]):
        p.append("eleitorado: c + a != esa")
    if _i(v["tv"]) != _i(e["c"]):
        p.append("votos total != comparecimento")
    if sum(c["votos"] for c in res["candidatos"]) != _i(v["vv"]):
        p.append("soma dos candidatos != válidos")
    if _i(v["vv"]) + _i(v["vb"]) + _i(v["tvn"]) != _i(v["tv"]):
        p.append("válidos + brancos + nulos != total")
    if _i(v["vn"]) + _i(v["vnt"]) != _i(v["tvn"]):
        p.append("nulos + nulos técnicos != total de nulos")
    if N_CAND and len(res["candidatos"]) != N_CAND:
        p.append(f"esperados {N_CAND} candidatos, vieram {len(res['candidatos'])}")
    if len(res["candidatos"]) < 2:
        p.append("menos de 2 candidatos no arquivo")
    if anterior:
        if res["secoes"]["totalizadas"] < anterior["secoes"]["totalizadas"]:
            p.append("seções totalizadas diminuíram")
        if res["votos"]["total"] < anterior["votos"]["total"]:
            p.append("total de votos diminuiu")
        a, b = anterior["fonte"]["totalizado_tse"], res["fonte"]["totalizado_tse"]
        if a and b and b < a:
            p.append("horário de totalização voltou no tempo")
    return p


def conferir_br(br, ufs):
    """br = soma das UFs + zz, quando todas estão na mesma geração."""
    if len(ufs) != len(UFS) + 1:
        return []
    p = []
    for bloco, campo in [("votos", "total"), ("votos", "validos"), ("votos", "brancos"),
                         ("votos", "nulos"), ("secoes", "totalizadas"), ("eleitorado", "comparecimento")]:
        soma = sum(u[bloco][campo] for u in ufs.values())
        if soma != br[bloco][campo]:
            p.append(f"br {bloco}.{campo}={br[bloco][campo]} soma UFs={soma}")
    return p


# ---------- publicação (versões imutáveis, manifesto por último) ----------

def _grava_atomico(caminho, obj):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(caminho), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, caminho)


def caminho_resultado(abr, versao):
    return f"br/v{versao:05d}.json" if abr == "br" else f"uf/{abr}/v{versao:05d}.json"


class Publicador:
    """Publica numa pasta local (data/). O envio ao Cloudflare usa a mesma ordem."""

    def __init__(self, raiz, versao_inicial=0):
        self.raiz = raiz
        self.base = versao_inicial
        self.estado_arq = os.path.join(raiz, "..", "estado.json")
        try:
            self.estado = json.load(open(self.estado_arq))
        except (FileNotFoundError, json.JSONDecodeError):
            self.estado = {"versao": versao_inicial, "abr": {}}

    def ultimo(self, abr):
        info = self.estado["abr"].get(abr)
        if not info:
            return None
        return json.load(open(os.path.join(self.raiz, info["arquivo"])))

    def publicar(self, resultados, fonte_tipo="oficial", nota=None):
        """resultados: {abr: resultado já conferido}. Grava versões, histórico e por fim o manifesto."""
        for abr, res in resultados.items():
            arq = caminho_resultado(abr, res["versao"])
            _grava_atomico(os.path.join(self.raiz, arq), res)
            if not os.path.exists(os.path.join(self.raiz, arq)):
                raise Bloqueio(f"arquivo {arq} não ficou acessível")
            hist_arq = os.path.join(self.raiz, "historico", f"{abr}.json")
            try:
                hist = json.load(open(hist_arq))
            except (FileNotFoundError, json.JSONDecodeError):
                hist = {"schema": SCHEMA, "tipo": "historico", "abrangencia": abr, "pontos": []}
            hist["pontos"].append({
                "versao": res["versao"], "totalizado_tse": res["fonte"]["totalizado_tse"],
                "pct_secoes": res["secoes"]["pct_totalizadas"], "votos_total": res["votos"]["total"],
                "votos": {c["numero"]: c["votos"] for c in res["candidatos"]},
                "pct_validos": {c["numero"]: c["pct_validos"] for c in res["candidatos"]},
            })
            _grava_atomico(hist_arq, hist)
            self.estado["abr"][abr] = {
                "versao": res["versao"], "arquivo": arq,
                "totalizado_tse": res["fonte"]["totalizado_tse"],
                "pct_secoes": res["secoes"]["pct_totalizadas"],
                "lider": res["derivados"]["lider"],
            }
        self.estado["versao"] += 1
        br = self.estado["abr"].get("br")
        sit = "aguardando"
        if br:
            ultimo_br = self.ultimo("br")
            sit = ultimo_br["situacao"]["andamento"]
        manifesto = {
            "schema": SCHEMA, "tipo": "manifesto", "versao": self.estado["versao"],
            "publicado_em": agora(), "eleicao": dict(ELEICAO),
            "fonte": {"tipo": fonte_tipo, "orgao": "TSE", "base": BASE_TSE,
                      **({"nota": nota} if nota else {})},
            "situacao": sit,
            "abrangencias": self.estado["abr"],
            "historico": {a: f"historico/{a}.json" for a in self.estado["abr"]},
        }
        _grava_atomico(os.path.join(self.raiz, "latest.json"), manifesto)  # por último
        _grava_atomico(self.estado_arq, self.estado)
        return manifesto
