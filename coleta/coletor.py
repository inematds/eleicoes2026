"""Coletor real do TSE — Parte 1 (coleta + processamento + publicação local).

Ciclo (a cada --intervalo s, padrão 15):
  1. GET condicional (ETag) do índice ab.json. 304 e nada pendente → dorme.
  2. Compara (dt, ht, seções) de cada abrangência com o último PUBLICADO → marca "pendente".
  3. Para cada pendente: GET condicional do -u.json. Só sai de pendente quando chega um
     arquivo NOVO (sha diferente) e com hora >= a do índice (o CDN do TSE pode servir cópia velha).
  4. Guarda o bruto + log; consolida; confere; publica (versões imutáveis, manifesto por último).
  5. Falhou? Mantém o último válido, registra e tenta de novo (espera cresce até 60 s).

Bloqueios (contrato/README.md): regra que não fecha, seções/votos que diminuem, hora que volta.
Liberar à mão um estado travado: crie o arquivo <saida>/aceitar/<abr> (vale 1 vez).
Brasil ≠ soma das UFs: só AVISO durante a apuração (os arquivos do TSE não saem juntos);
bloqueia apenas quando o TSE marca totalização final.

Uso:
  python3 coletor.py --saida ../saida/oficial                      # 2º turno, oficial
  python3 coletor.py --saida ../saida/teste1t --eleicao 6257 --turno 1 --n-cand 0 --uma-vez
"""
import argparse
import gzip
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nucleo as N  # noqa: E402

UA = "INEMA-Eleicoes/1.0 (+https://eleicoes.inema.club; painel independente, consulta a cada 15 s)"
TIMEOUT = 10


def http_get(url, etag=None):
    """Retorna (status, corpo_bytes, etag, ms). 304 → corpo None."""
    h = {"User-Agent": UA, "Accept-Encoding": "gzip"}
    if etag:
        h["If-None-Match"] = etag
    t0 = time.monotonic()
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=TIMEOUT)
        b = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            b = gzip.decompress(b)
        return r.status, b, r.headers.get("ETag"), int((time.monotonic() - t0) * 1000)
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return 304, None, etag, int((time.monotonic() - t0) * 1000)
        raise


def chave_ab(item):
    return f"{item.get('dt', '')} {item.get('ht', '')} {item.get('s', {}).get('st', '')}"


def hora_tse(d, h):
    """'25/10/2026','18:42:10' -> datetime (ou None)."""
    if not d or not h:
        return None
    return datetime.strptime(f"{d} {h}", "%d/%m/%Y %H:%M:%S")


class Coletor:
    def __init__(self, saida, intervalo, versao_inicial):
        self.saida = os.path.abspath(saida)
        self.intervalo = intervalo
        os.makedirs(self.saida, exist_ok=True)
        self.pub = N.Publicador(os.path.join(self.saida, "data"), versao_inicial=versao_inicial)
        self.est_arq = os.path.join(self.saida, "coletor-estado.json")
        try:
            self.est = json.load(open(self.est_arq))
        except (FileNotFoundError, json.JSONDecodeError):
            self.est = {"etag_ab": None, "abr": {}}
        self.pendentes = {}       # abr -> chave do índice que ainda não chegou no -u.json
        self.bloqueios = {}       # abr -> problemas
        self.avisos = []
        self.erros_seguidos = 0
        self.ultimo_ok = None
        self.ultimo_erro = None

    # ---------- registro ----------
    def log(self, evento, **dados):
        linha = {"t": N.agora(), "evento": evento, **dados}
        with open(os.path.join(self.saida, "coleta.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        if evento in ("ERRO", "BLOQUEIO", "AVISO", "PUBLICADO", "INICIO"):
            print(json.dumps(linha, ensure_ascii=False), flush=True)

    def guarda_bruto(self, abr, corpo):
        sha = hashlib.sha256(corpo).hexdigest()
        d = os.path.join(self.saida, "bruto", abr)
        os.makedirs(d, exist_ok=True)
        nome = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{sha[:8]}.json"
        with open(os.path.join(d, nome), "wb") as f:
            f.write(corpo)
        return sha, nome

    def salva_estado(self):
        tmp = self.est_arq + ".tmp"
        json.dump(self.est, open(tmp, "w"))
        os.replace(tmp, self.est_arq)
        status = {
            "atualizado_em": N.agora(), "ultimo_ok": self.ultimo_ok, "ultimo_erro": self.ultimo_erro,
            "erros_seguidos": self.erros_seguidos, "pendentes": sorted(self.pendentes),
            "bloqueios": self.bloqueios, "avisos": self.avisos[-10:],
            "versao_manifesto": self.pub.estado["versao"],
            "eleicao": N.ELEICAO["eleicao"], "base": N.BASE_TSE,
        }
        json.dump(status, open(os.path.join(self.saida, "status.json"), "w"), ensure_ascii=False, indent=1)

    # ---------- um ciclo ----------
    def ciclo(self):
        st, corpo, etag, ms = http_get(N.url_ab(), self.est.get("etag_ab"))
        self.log("ab", status=st, ms=ms)
        if st == 200:
            self.est["etag_ab"] = etag
            ab = json.loads(corpo)
            if ab.get("ele") != N.ELEICAO["eleicao"]:
                raise N.Bloqueio(f"índice de outra eleição: {ab.get('ele')}")
            for item in ab.get("abr", []):
                abr = item.get("cdabr")
                if abr not in N.ABRS:
                    continue
                k = chave_ab(item)
                h = hora_tse(item.get("dt"), item.get("ht"))
                # br e zz vêm no índice com a hora local de um país do exterior (~16 h à frente):
                # hora no futuro não serve para comparar com o arquivo, senão o br nunca publica
                if h and h > datetime.now() + timedelta(minutes=10):
                    h = None
                pub =self.est["abr"].get(abr, {})
                h_pub = datetime.fromisoformat(pub["hora_pub"]) if pub.get("hora_pub") else None
                if pub.get("chave_ab") == k or (h and h_pub and h < h_pub):
                    self.pendentes.pop(abr, None)  # já temos isso (ou algo mais novo) publicado
                else:
                    self.pendentes[abr] = {"chave": k, "hora": h}
        if not self.pendentes:
            self.ultimo_ok = N.agora()
            return 0

        novos = {}
        for abr in list(self.pendentes):
            try:
                r = self.processa(abr)
            except Exception as e:  # um arquivo ruim trava só aquela abrangência, não o ciclo
                self.bloqueios[abr] = [f"{type(e).__name__}: {e}"]
                self.log("BLOQUEIO", abr=abr, problemas=self.bloqueios[abr])
                continue
            if r:
                novos[abr] = r
        return self.fecha(novos)

    def processa(self, abr):
        """Baixa e confere uma abrangência pendente. Retorna o resultado ou None."""
        info = self.est["abr"].setdefault(abr, {})
        url = N.url_tse(abr)
        st, corpo, etag, ms = http_get(url, info.get("etag"))
        if st == 304:
            return None  # CDN ainda sem o arquivo novo: segue pendente
        info["etag"] = etag
        sha = hashlib.sha256(corpo).hexdigest()
        if sha == info.get("sha") or sha == info.get("sha_ruim"):
            return None  # mesma cópia de antes: segue pendente (não guarda de novo)
        sha, nome = self.guarda_bruto(abr, corpo)
        self.log("u", abr=abr, status=st, ms=ms, bytes=len(corpo), sha=sha[:12], arquivo=nome)
        info["sha_ruim"] = sha  # vira "bom" só se passar em tudo abaixo
        raw = json.loads(corpo)
        h_raw, h_ab = hora_tse(raw.get("dt"), raw.get("ht")), self.pendentes[abr]["hora"]
        if h_ab and h_raw and h_raw < h_ab:
            return None  # arquivo mais velho que o índice: espera o CDN atualizar
        anterior = self.pub.ultimo(abr)
        versao = self.pub.estado["abr"].get(abr, {}).get("versao", self.pub.base) + 1
        res, raw = N.consolidar(corpo, abr, N.agora(), versao, fonte_tipo="oficial")
        problemas = N.conferir(raw, res, anterior)
        liberar = os.path.join(self.saida, "aceitar", abr)
        if problemas and os.path.exists(liberar):
            self.log("AVISO", abr=abr, msg="liberado à mão (arquivo aceitar)", problemas=problemas)
            os.remove(liberar)
            problemas = []
        if problemas:
            self.bloqueios[abr] = problemas
            self.log("BLOQUEIO", abr=abr, problemas=problemas, sha=sha[:12])
            info["sha"] = sha  # não reprocessa o mesmo arquivo ruim a cada ciclo
            return None
        self.bloqueios.pop(abr, None)
        info["sha"] = sha
        info.pop("sha_ruim", None)
        info["chave_ab_candidata"] = chave_ab(raw)  # do próprio arquivo, não do índice
        info["hora_candidata"] = h_raw.isoformat() if h_raw else None
        return res

    def fecha(self, novos):

        if "br" in novos:
            ufs = {a: novos.get(a) or self.pub.ultimo(a) for a in N.UFS + ["zz"]}
            ufs = {a: u for a, u in ufs.items() if u}
            dif = N.conferir_br(novos["br"], ufs)
            if dif:
                if novos["br"]["situacao"]["totalizacao_final"]:
                    self.bloqueios["br"] = dif
                    self.log("BLOQUEIO", abr="br", problemas=dif, msg="final e não bate com a soma das UFs")
                    novos.pop("br")
                else:
                    self.avisos.append({"t": N.agora(), "msg": "br ainda não bate com a soma das UFs (normal durante a apuração)", "dif": dif[:2]})
                    self.log("br_soma", dif=dif)

        if novos:
            m = self.pub.publicar(novos, fonte_tipo="oficial")
            for abr in novos:
                info = self.est["abr"][abr]
                info["chave_ab"] = info.pop("chave_ab_candidata")
                info["hora_pub"] = info.pop("hora_candidata", None)
                self.pendentes.pop(abr, None)
            br = novos.get("br")
            self.log("PUBLICADO", versao=m["versao"], abrs=sorted(novos),
                     br_secoes=br and br["secoes"]["pct_totalizadas"])
        self.ultimo_ok = N.agora()
        return len(novos)

    def rodar(self, uma_vez=False):
        self.log("INICIO", eleicao=N.ELEICAO["eleicao"], base=N.BASE_TSE, intervalo=self.intervalo)
        while True:
            espera = self.intervalo
            try:
                self.ciclo()
                self.erros_seguidos = 0
            except Exception as e:  # nunca derruba o laço: mantém o último válido
                self.erros_seguidos += 1
                self.ultimo_erro = {"t": N.agora(), "erro": f"{type(e).__name__}: {e}"}
                self.log("ERRO", erro=self.ultimo_erro["erro"], seguidos=self.erros_seguidos)
                espera = min(60, self.intervalo * (2 ** min(self.erros_seguidos, 3)))
            self.salva_estado()
            if uma_vez:
                return
            time.sleep(espera)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", required=True)
    ap.add_argument("--intervalo", type=float, default=15)
    ap.add_argument("--eleicao", default="6258")
    ap.add_argument("--turno", type=int, default=2)
    ap.add_argument("--pleito", default="3221")
    ap.add_argument("--ciclo", default="ele2026")
    ap.add_argument("--n-cand", type=int, default=2, help="0 = não confere a quantidade")
    ap.add_argument("--base", help="outra origem (teste com servidor local)")
    ap.add_argument("--versao-inicial", type=int, default=100000)
    ap.add_argument("--uma-vez", action="store_true")
    a = ap.parse_args()
    N.configurar(a.eleicao, a.turno, a.ciclo, a.pleito, a.n_cand, a.base)
    Coletor(a.saida, a.intervalo, a.versao_inicial).rodar(a.uma_vez)


if __name__ == "__main__":
    main()
