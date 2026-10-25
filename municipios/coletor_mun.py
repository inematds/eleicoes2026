"""Coletor de MUNICÍPIOS do TSE — sistema à parte do painel oficial.

Roda separado do coletor oficial (coleta/coletor.py) e não lê nada do que ele grava.
Reaproveita só o leitor do formato do TSE e as conferências (coleta/nucleo.py).

Ciclo (a cada --intervalo s, padrão 15):
  1. Pede os 27 índices por estado (dados/<uf>/<uf>-e<ele>-ab.json) com ETag (só o que mudou).
     Cada índice diz, por cidade: hora da totalização, seções apuradas e eleitorado.
  2. Cidade com apuração nova vira "pendente". Cidade ainda com 0 seções não é baixada
     (o índice já diz tudo: cinza no mapa).
  3. Baixa no máximo --max-por-ciclo cidades por ciclo, em --paralelo conexões: primeiro as que
     esperam há mais tempo e, entre as que entraram juntas, as de MAIOR eleitorado. O resto fica
     para o próximo ciclo (uma cidade que muda de novo enquanto espera não perde o lugar).
  4. Cada cidade passa pelas mesmas regras do contrato (nucleo.conferir). Cidade com problema
     fica travada com o último valor bom; o estado e as outras cidades seguem.
     Liberar à mão: crie <saida>/aceitar/<código TSE da cidade> (vale 1 vez).
  5. Grava UM arquivo por estado com todas as cidades (versões imutáveis) e o manifesto por último.

Soma das cidades ≠ estado: só aviso (os arquivos do TSE não saem juntos).

Uso:
  python3 municipios/coletor_mun.py --saida saida/municipios                    # 2º turno
  python3 municipios/coletor_mun.py --saida saida/municipios-1t --eleicao 6257 --turno 1 --n-cand 0
"""
import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "coleta"))
import nucleo as N  # noqa: E402
from coletor import chave_ab, hora_tse, http_get  # noqa: E402

MANTER = 6  # versões guardadas por estado


def eid():
    return f"{int(N.ELEICAO['eleicao']):06d}"


def url_ab_uf(uf):
    return f"{N.BASE_TSE}dados/{uf}/{uf}-e{eid()}-ab.json"


def url_mun(uf, cd):
    return f"{N.BASE_TSE}dados/{uf}/{uf}{cd}-c0001-e{eid()}-u.json"


def url_cm():
    return f"{N.BASE_TSE}config/mun-e{eid()}-cm.json"


def grava(caminho, obj):
    N._grava_atomico(caminho, obj)


class ColetorMun:
    def __init__(self, a):
        self.saida = os.path.abspath(a.saida)
        self.dados = os.path.join(self.saida, "data")
        self.intervalo = a.intervalo
        self.max_ciclo = a.max_por_ciclo
        self.paralelo = a.paralelo
        self.ufs = [u.lower() for u in a.ufs] if a.ufs else list(N.UFS)
        self.simulacao = a.simulacao
        self.a_versao_inicial = a.versao_inicial  # outra máquina (reserva) começa noutra faixa: arquivos imutáveis não colidem
        os.makedirs(self.dados, exist_ok=True)
        self.est_arq = os.path.join(self.saida, "coletor-estado.json")
        try:
            self.est = json.load(open(self.est_arq))
        except (FileNotFoundError, json.JSONDecodeError):
            self.est = {"etag_ab": {}, "mun": {}, "uf": {}, "versao": a.versao_inicial}
        # as pendências não ficam salvas: depois de reiniciar, relê os 27 índices inteiros
        # (sem ETag) para remontar a fila. Custa ~27 pedidos pequenos.
        self.est["etag_ab"] = {}
        self.cidades = {}      # uf -> cd -> registro (o que vai no arquivo)
        self.uf_info = {}      # uf -> resumo do estado vindo do índice / do -u.json do estado
        self.pendentes = {}    # cd -> {uf, chave, hora, te}
        self.bloqueios = {}    # cd -> problemas
        self.avisos = []
        self.sujos = set()     # UFs que precisam de arquivo novo
        self.erros_seguidos = 0
        self.ultimo_ok = self.ultimo_erro = None
        self.baixados_ultimo = 0
        self.carrega_cm()
        self.carrega_publicado()
        self.carrega_candidatos()

    # ---------- base ----------
    def log(self, evento, **dados):
        linha = {"t": N.agora(), "evento": evento, **dados}
        with open(os.path.join(self.saida, "coleta.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        if evento in ("ERRO", "BLOQUEIO", "AVISO", "PUBLICADO", "INICIO"):
            print(json.dumps(linha, ensure_ascii=False), flush=True)

    def carrega_cm(self):
        """Lista oficial de municípios: código TSE, código IBGE e nome."""
        arq = os.path.join(self.saida, f"mun-e{eid()}-cm.json")
        while not os.path.exists(arq):
            try:
                st, corpo, _, _ = http_get(url_cm())
                json.loads(corpo)
                open(arq, "wb").write(corpo)
            except Exception as e:  # noqa: BLE001 — sem a lista não dá para começar: tenta de novo
                self.log("ERRO", erro=f"lista de municípios: {type(e).__name__}: {e}", seguidos=1)
                time.sleep(15)
        cm = json.load(open(arq))
        for g in cm["abr"]:
            if g["cd"] not in self.ufs:
                continue
            reg = self.cidades.setdefault(g["cd"], {})
            for m in g["mu"]:
                reg[m["cd"]] = {"cd": m["cd"], "cdi": m["cdi"], "nm": m["nm"], "cap": m.get("c") == "s",
                                "te": 0, "ts": 0, "st": 0, "pst": 0.0, "and": "aguardando", "ht": None,
                                "tv": 0, "vv": 0, "vb": 0, "vn": 0, "comp": 0, "abst": 0,
                                "c": {}, "p": {}, "lider": None}

    def carrega_candidatos(self):
        """Nomes dos candidatos do arquivo do Brasil, para a legenda já ter nomes antes da 1ª cidade."""
        if self.est.get("candidatos_base"):
            return
        try:
            st, corpo, _, _ = http_get(f"{N.BASE_TSE}dados/br/br-c0001-e{eid()}-u.json")
            self.est["candidatos_base"] = [{"numero": c["n"], "nome_urna": c.get("nmu", c["nm"]), "partido": sg}
                                           for c, sg in N.candidatos_tse(json.loads(corpo))]
        except Exception as e:  # noqa: BLE001 — sem isso a legenda só espera a 1ª cidade
            self.log("AVISO", msg="não leu os candidatos do arquivo do Brasil", erro=f"{type(e).__name__}: {e}")

    def carrega_publicado(self):
        """Depois de reiniciar: volta com o último arquivo publicado de cada estado."""
        try:
            m = json.load(open(os.path.join(self.dados, "latest.json")))
        except (FileNotFoundError, json.JSONDecodeError):
            return
        for uf, info in m.get("ufs", {}).items():
            if uf not in self.cidades:
                continue
            try:
                d = json.load(open(os.path.join(self.dados, info["arquivo"])))
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            for cdi, r in d["cidades"].items():
                if r["cd"] in self.cidades[uf]:
                    self.cidades[uf][r["cd"]].update(r)
            self.uf_info[uf] = {"indice": d.get("estado", {})}
            self.est["uf"].setdefault(uf, {})["candidatos"] = d.get("candidatos", [])

    def salva_estado(self):
        tmp = self.est_arq + ".tmp"
        json.dump(self.est, open(tmp, "w"))
        os.replace(tmp, self.est_arq)
        status = {
            "atualizado_em": N.agora(), "ultimo_ok": self.ultimo_ok, "ultimo_erro": self.ultimo_erro,
            "erros_seguidos": self.erros_seguidos, "eleicao": N.ELEICAO["eleicao"], "base": N.BASE_TSE,
            "pendentes": len(self.pendentes),
            "pendentes_amostra": sorted(self.pendentes, key=lambda c: -self.pendentes[c]["te"])[:10],
            "baixados_ultimo_ciclo": self.baixados_ultimo,
            "bloqueios": self.bloqueios, "avisos": self.avisos[-10:],
            "versao_manifesto": self.est["versao"],
        }
        json.dump(status, open(os.path.join(self.saida, "status.json"), "w"), ensure_ascii=False, indent=1)

    # ---------- índices por estado ----------
    def le_indice(self, uf):
        st, corpo, etag, ms = http_get(url_ab_uf(uf), self.est["etag_ab"].get(uf))
        return uf, st, corpo, etag, ms

    def aplica_indice(self, uf, ab):
        if ab.get("ele") != N.ELEICAO["eleicao"]:
            raise N.Bloqueio(f"índice de {uf} é de outra eleição: {ab.get('ele')}")
        for item in ab.get("abr", []):
            s, e = item.get("s", {}), item.get("e", {})
            if item.get("tpabr") == "uf":
                novo = {"ts": N._i(s.get("ts")), "st": N._i(s.get("st")), "pst": N._pct(s.get("pstn")),
                        "te": N._i(e.get("te")), "and": N.ANDAMENTO.get(item.get("and"), item.get("and")),
                        "ht": N._iso(item.get("dt"), item.get("ht"))}
                if self.uf_info.get(uf, {}).get("indice") != novo:
                    self.uf_info.setdefault(uf, {})["indice"] = novo
                    self.sujos.add(uf)
                continue
            cd = item.get("cdabr")
            r = self.cidades.get(uf, {}).get(cd)
            if r is None:
                continue
            te = N._i(e.get("te"))
            # eleitorado e seções do índice só valem enquanto a cidade não tem arquivo:
            # depois, quem manda é o arquivo da cidade (o índice pode ser preliminar)
            if r["st"] == 0 and not r["tv"] and (r["te"] != te or r["ts"] != N._i(s.get("ts"))):
                r["te"], r["ts"] = te, N._i(s.get("ts"))
                self.sujos.add(uf)
            k = chave_ab(item)
            info = self.est["mun"].setdefault(cd, {})
            if N._i(s.get("st")) == 0 and not item.get("dt"):
                self.pendentes.pop(cd, None)
                continue  # nada apurado ainda: cinza, não precisa baixar
            if info.get("chave_ab") == k:
                self.pendentes.pop(cd, None)
                continue
            h = hora_tse(item.get("dt"), item.get("ht"))
            h_pub = datetime.fromisoformat(info["hora_pub"]) if info.get("hora_pub") else None
            if h and h_pub and h < h_pub:
                info["chave_ab"] = k  # temos coisa mais nova publicada
                self.pendentes.pop(cd, None)
                continue
            if cd not in self.pendentes:
                self.pendentes[cd] = {"uf": uf, "chave": k, "hora": h, "te": te, "espera_ate": 0, "tent": 0,
                                      "desde": time.time()}
            else:
                self.pendentes[cd].update(chave=k, hora=h)

    # ---------- uma cidade ----------
    def baixa_cidade(self, cd):
        p = self.pendentes[cd]
        info = self.est["mun"].setdefault(cd, {})
        try:
            st, corpo, etag, ms = http_get(url_mun(p["uf"], cd), info.get("etag"))
            return cd, st, corpo, etag, ms, None
        except Exception as e:  # noqa: BLE001 — a cidade espera, o ciclo segue
            return cd, None, None, None, 0, f"{type(e).__name__}: {e}"

    def espera(self, cd):
        p = self.pendentes[cd]
        p["tent"] += 1
        p["espera_ate"] = time.time() + min(120, 15 * 2 ** min(p["tent"], 3))

    def processa_cidade(self, cd, st, corpo, etag, erro):
        p = self.pendentes[cd]
        uf = p["uf"]
        info = self.est["mun"].setdefault(cd, {})
        if erro:
            self.log("cidade_erro", cd=cd, erro=erro)
            self.espera(cd)
            return
        sha = info.get("sha") if st == 304 else hashlib.sha256(corpo).hexdigest()
        if st != 304:
            info["etag"] = etag
        if sha and sha == info.get("sha"):
            # mesmo arquivo que já publicamos. Se ele já é tão novo quanto o índice (o TSE só
            # atualizou o índice), está resolvido; senão o CDN ainda manda a cópia velha: espera.
            h_pub = datetime.fromisoformat(info["hora_pub"]) if info.get("hora_pub") else None
            if (h_pub and p["hora"] and h_pub >= p["hora"]) or p["tent"] >= 8:
                info["chave_ab"] = p["chave"]
                self.pendentes.pop(cd, None)
            else:
                self.espera(cd)
            return
        if st == 304 or sha == info.get("sha_ruim"):
            self.espera(cd)  # o CDN ainda manda a cópia velha
            return
        raw = json.loads(corpo)
        h_raw = hora_tse(raw.get("dt"), raw.get("ht"))
        if p["hora"] and h_raw and h_raw < p["hora"]:
            info["sha_ruim"] = sha
            self.espera(cd)
            return
        r = self.cidades[uf][cd]
        anterior = None
        if r["st"] or r["tv"]:
            anterior = {"secoes": {"totalizadas": r["st"]}, "votos": {"total": r["tv"]},
                        "fonte": {"totalizado_tse": r["ht"]}}
        res, raw = N.consolidar(corpo, cd, N.agora(), 0, fonte_tipo="oficial")
        problemas = N.conferir(raw, res, anterior)
        liberar = os.path.join(self.saida, "aceitar", cd)
        if problemas and os.path.exists(liberar):
            self.log("AVISO", cd=cd, nm=r["nm"], msg="liberado à mão (arquivo aceitar)", problemas=problemas)
            os.remove(liberar)
            problemas = []
        if problemas:
            self.bloqueios[cd] = {"uf": uf, "nm": r["nm"], "problemas": problemas}
            info["sha"] = sha
            self.log("BLOQUEIO", cd=cd, uf=uf, nm=r["nm"], problemas=problemas, sha=sha[:12])
            self.pendentes.pop(cd, None)
            info["chave_ab"] = p["chave"]
            return
        self.bloqueios.pop(cd, None)
        cands = res["candidatos"]
        r.update({
            "ts": res["secoes"]["total"], "st": res["secoes"]["totalizadas"], "pst": res["secoes"]["pct_totalizadas"],
            "and": res["situacao"]["andamento"], "ht": res["fonte"]["totalizado_tse"],
            "tv": res["votos"]["total"], "vv": res["votos"]["validos"], "vb": res["votos"]["brancos"],
            "vn": res["votos"]["nulos"], "comp": res["eleitorado"]["comparecimento"],
            "abst": res["eleitorado"]["abstencao"], "te": res["eleitorado"]["total"] or r["te"],
            "c": {c["numero"]: c["votos"] for c in cands}, "p": {c["numero"]: c["pct_validos"] for c in cands},
            "lider": res["derivados"]["lider"], "sha": sha[:16],
        })
        cand_uf = self.est["uf"].setdefault(uf, {}).setdefault("candidatos", [])
        conhecidos = {c["numero"] for c in cand_uf}
        for c in cands:
            if c["numero"] not in conhecidos:
                cand_uf.append({"numero": c["numero"], "nome_urna": c["nome_urna"], "partido": c["partido"]})
        info.update(sha=sha, chave_ab=p["chave"], hora_pub=h_raw.isoformat() if h_raw else None)
        info.pop("sha_ruim", None)
        self.pendentes.pop(cd, None)
        self.sujos.add(uf)

    # ---------- ciclo ----------
    def ciclo(self):
        with ThreadPoolExecutor(self.paralelo) as ex:
            indices = list(ex.map(self.le_indice, self.ufs))
        mudou = []
        for uf, st, corpo, etag, ms in indices:
            if st == 200:
                self.aplica_indice(uf, json.loads(corpo))
                self.est["etag_ab"][uf] = etag
                mudou.append(uf)
        self.log("ab", mudaram=mudou, pendentes=len(self.pendentes))

        agora = time.time()
        # fila justa: quem espera há mais tempo primeiro; no empate (mesmo ciclo), a maior cidade
        fila = sorted((cd for cd, p in self.pendentes.items() if p["espera_ate"] <= agora),
                      key=lambda cd: (int(self.pendentes[cd]["desde"] // self.intervalo), -self.pendentes[cd]["te"]))[: self.max_ciclo]
        self.baixados_ultimo = len(fila)
        if fila:
            with ThreadPoolExecutor(self.paralelo) as ex:
                for cd, st, corpo, etag, ms, erro in ex.map(self.baixa_cidade, fila):
                    try:
                        self.processa_cidade(cd, st, corpo, etag, erro)
                    except Exception as e:  # noqa: BLE001 — um arquivo ruim trava só a cidade
                        p = self.pendentes.get(cd, {})
                        self.bloqueios[cd] = {"uf": p.get("uf"), "problemas": [f"{type(e).__name__}: {e}"]}
                        self.log("BLOQUEIO", cd=cd, problemas=self.bloqueios[cd]["problemas"])
                        self.pendentes.pop(cd, None)
        if self.sujos:
            self.publica()
        self.ultimo_ok = N.agora()

    # ---------- publicação ----------
    def arquivo_uf(self, uf):
        cid = self.cidades[uf]
        cands = list(self.est["uf"].get(uf, {}).get("candidatos", []))
        ja = {c["numero"] for c in cands}
        cands += [c for c in self.est.get("candidatos_base", []) if c["numero"] not in ja]
        ini = sum(1 for r in cid.values() if r["st"] > 0)
        comp = sum(1 for r in cid.values() if r["ts"] and r["st"] == r["ts"])
        lid = {}
        for r in cid.values():
            if r["lider"] and r["st"] > 0:
                lid[r["lider"]] = lid.get(r["lider"], 0) + 1
        soma = {c["numero"]: sum(r["c"].get(c["numero"], 0) for r in cid.values()) for c in cands}
        soma_vv = sum(r["vv"] for r in cid.values())
        soma_tv = sum(r["tv"] for r in cid.values())
        return {
            "schema": 1, "tipo": "municipios_uf", "uf": uf, "nome": N.NOMES.get(uf, uf.upper()),
            "eleicao": dict(N.ELEICAO),
            "fonte": {"orgao": "TSE", "indice": url_ab_uf(uf), "cidade_modelo": url_mun(uf, "<cd>")},
            "estado": self.uf_info.get(uf, {}).get("indice", {}),
            "candidatos": sorted(cands, key=lambda c: c["numero"]),
            "resumo": {"cidades": len(cid), "iniciadas": ini, "completas": comp, "lider_cidades": lid,
                       "soma_cidades": {"votos": soma, "validos": soma_vv, "total": soma_tv,
                                        "brancos": sum(r["vb"] for r in cid.values()),
                                        "nulos": sum(r["vn"] for r in cid.values()),
                                        "comparecimento": sum(r["comp"] for r in cid.values()),
                                        "abstencao": sum(r["abst"] for r in cid.values()),
                                        "_aviso": "soma calculada pelo INEMA; o resultado oficial do estado é o do TSE"}},
            "bloqueadas": sorted(cd for cd, b in self.bloqueios.items() if b.get("uf") == uf),
            "cidades": {r["cdi"]: {k: v for k, v in r.items() if k != "sha"} for r in cid.values()},
        }

    def historico(self, uf, d):
        """Um ponto por versão com votos novos: % de seções do estado e % dos válidos de cada um."""
        arq = os.path.join(self.dados, "historico", uf + ".json")
        try:
            h = json.load(open(arq))
        except (FileNotFoundError, json.JSONDecodeError):
            h = {"schema": 1, "tipo": "historico_municipios", "uf": uf, "pontos": []}
        sc = d["resumo"]["soma_cidades"]
        if not sc["total"]:
            return
        if h["pontos"] and h["pontos"][-1]["vt"] == sc["total"]:
            return
        vv = sc["validos"] or 1
        h["pontos"].append({"t": d["publicado_em"], "versao": d["versao"], "pst": d["estado"].get("pst", 0),
                            "vt": sc["total"], "pv": {k: round(v * 100 / vv, 2) for k, v in sc["votos"].items()}})
        if len(h["pontos"]) > 600:  # afina os pontos antigos, mantém o começo e o fim
            h["pontos"] = h["pontos"][:1] + h["pontos"][1:-100:2] + h["pontos"][-100:]
        grava(arq, h)

    def publica(self):
        novas = {}
        for uf in sorted(self.sujos):
            d = self.arquivo_uf(uf)
            assin = hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
            eu = self.est["uf"].setdefault(uf, {})
            if eu.get("assin") == assin:
                continue
            v = eu.get("versao", self.a_versao_inicial) + 1
            d["versao"], d["publicado_em"] = v, N.agora()
            arq = f"uf/{uf}/v{v:05d}.json"
            grava(os.path.join(self.dados, arq), d)
            self.historico(uf, d)
            eu.update(versao=v, arquivo=arq, assin=assin, resumo=d["resumo"] | {"pst": d["estado"].get("pst", 0)})
            novas[uf] = v
            pasta = os.path.join(self.dados, "uf", uf)
            for velho in sorted(os.listdir(pasta))[:-MANTER]:
                os.remove(os.path.join(pasta, velho))
        self.sujos.clear()
        if not novas:
            return
        self.est["versao"] += 1
        manifesto = {
            "schema": 1, "tipo": "manifesto_municipios", "versao": self.est["versao"], "publicado_em": N.agora(),
            "eleicao": dict(N.ELEICAO),
            "fonte": ({"tipo": "simulacao", "orgao": "TSE falso (teste local)", "base": N.BASE_TSE,
                       "nota": "Simulação com nomes fictícios e números inventados a partir do 1º turno. Não é resultado."}
                      if self.simulacao else {"tipo": "oficial", "orgao": "TSE", "base": N.BASE_TSE}),
            "ufs": {uf: {"versao": i["versao"], "arquivo": i["arquivo"],
                         "cidades": i["resumo"]["cidades"], "iniciadas": i["resumo"]["iniciadas"],
                         "completas": i["resumo"]["completas"], "lider_cidades": i["resumo"]["lider_cidades"],
                         "pst": i["resumo"]["pst"], "historico": f"historico/{uf}.json"}
                    for uf, i in sorted(self.est["uf"].items()) if i.get("arquivo")},
        }
        grava(os.path.join(self.dados, "latest.json"), manifesto)  # por último
        self.log("PUBLICADO", versao=manifesto["versao"], ufs=novas)

    def rodar(self, uma_vez=False):
        self.log("INICIO", eleicao=N.ELEICAO["eleicao"], base=N.BASE_TSE, ufs=len(self.ufs),
                 max_por_ciclo=self.max_ciclo, intervalo=self.intervalo)
        self.sujos |= set(self.ufs)  # garante um arquivo por estado já no 1º ciclo
        while True:
            espera = self.intervalo
            t0 = time.monotonic()
            try:
                self.ciclo()
                self.erros_seguidos = 0
            except Exception as e:  # noqa: BLE001 — nunca derruba o laço
                self.erros_seguidos += 1
                self.ultimo_erro = {"t": N.agora(), "erro": f"{type(e).__name__}: {e}"}
                self.log("ERRO", erro=self.ultimo_erro["erro"], seguidos=self.erros_seguidos)
                espera = min(60, self.intervalo * (2 ** min(self.erros_seguidos, 3)))
            self.salva_estado()
            if uma_vez:
                return
            time.sleep(max(1.0, espera - (time.monotonic() - t0)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", required=True)
    ap.add_argument("--intervalo", type=float, default=15)
    ap.add_argument("--eleicao", default="6258")
    ap.add_argument("--turno", type=int, default=2)
    ap.add_argument("--pleito", default="3221")
    ap.add_argument("--ciclo", default="ele2026")
    ap.add_argument("--n-cand", type=int, default=2, help="0 = não confere a quantidade")
    ap.add_argument("--base", help="outra origem (teste com TSE falso local)")
    ap.add_argument("--max-por-ciclo", type=int, default=300, help="cidades baixadas por ciclo, no máximo")
    ap.add_argument("--paralelo", type=int, default=8, help="conexões ao mesmo tempo")
    ap.add_argument("--ufs", nargs="*", help="só estas UFs (teste)")
    ap.add_argument("--simulacao", action="store_true", help="marca os dados como SIMULAÇÃO (TSE falso)")
    ap.add_argument("--uma-vez", action="store_true")
    ap.add_argument("--versao-inicial", type=int, default=0, help="primeira versão menos 1 (reserva na VPS: 500000)")
    a = ap.parse_args()
    N.configurar(a.eleicao, a.turno, a.ciclo, a.pleito, a.n_cand, a.base)
    ColetorMun(a).rodar(a.uma_vez)


if __name__ == "__main__":
    main()
