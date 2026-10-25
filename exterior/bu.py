"""Lê o boletim de urna (bu.dat) do TSE: BER/ASN.1 (EntidadeEnvelopeGenerico com EntidadeBoletimUrna dentro).

Sem biblioteca externa: percorre o BER e acha as estruturas pela forma, conforme a especificação pública do TSE:
  ResultadoVotacaoPorEleicao ::= SEQUENCE { idEleicao, qtdEleitoresAptos, ..., resultadosVotacao SEQUENCE OF ResultadoVotacao }
  ResultadoVotacao           ::= SEQUENCE { tipoVoto, qtdComparecimento, totaisVotosCargo SEQUENCE OF TotalVotosCargo }
  TotalVotosCargo            ::= SEQUENCE { [1] codigoCargo, ordemImpressao, votosVotaveis SEQUENCE OF TotalVotosVotavel }
  TotalVotosVotavel          ::= SEQUENCE { [1] tipoVoto, [2] quantidadeVotos, [3] identificacaoVotavel {partido, codigo} OPCIONAL, ... }
  tipoVoto: 1 nominal, 2 branco, 3 nulo, 4 legenda, 5 cargo sem candidato.
"""
UNIV, CTX = 0, 2
SEQ, INT, ENUM, OCTET = 16, 2, 10, 4


def _tag(b, i):
    t = b[i]
    i += 1
    cls, cons, num = t >> 6, bool(t & 0x20), t & 0x1F
    if num == 0x1F:
        num = 0
        while True:
            x = b[i]
            i += 1
            num = (num << 7) | (x & 0x7F)
            if not x & 0x80:
                break
    n = b[i]
    i += 1
    if n & 0x80:
        k = n & 0x7F
        n = int.from_bytes(b[i:i + k], "big")
        i += k
    return cls, cons, num, i, n


def arvore(b, i=0, fim=None):
    """Lista de nós (cls, num, filhos|bytes)."""
    fim = len(b) if fim is None else fim
    nos = []
    while i < fim:
        cls, cons, num, j, n = _tag(b, i)
        if j + n > fim:
            raise ValueError("BER truncado")
        nos.append((cls, num, arvore(b, j, j + n) if cons else b[j:j + n]))
        i = j + n
    return nos


def _int(no):
    return int.from_bytes(no[2], "big", signed=True)


def _eh_int(no, cls=UNIV, num=INT):
    return no[0] == cls and no[1] == num and isinstance(no[2], bytes) and len(no[2]) <= 8


def _seqs(nos):
    for no in nos:
        if isinstance(no[2], list):
            yield no
            yield from _seqs(no[2])


def conteudo(envelope):
    """O BU vem dentro de um OCTET STRING do envelope genérico."""
    raiz = arvore(envelope)
    for no in _seqs(raiz):
        for f in no[2]:
            if f[0] == UNIV and f[1] == OCTET and isinstance(f[2], bytes) and len(f[2]) > 40 and f[2][0] == 0x30:
                return f[2]
    raise ValueError("envelope sem conteúdo BER")


def ler(dados, id_eleicao, cargo=1):
    """Devolve {aptos, comparecimento, votos{numero: n}, brancos, nulos} da eleição/cargo pedidos."""
    bu = arvore(conteudo(dados))
    for no in _seqs(bu):
        f = no[2]
        if not (no[0] == UNIV and no[1] == SEQ and len(f) >= 3 and _eh_int(f[0]) and _int(f[0]) == id_eleicao
                and _eh_int(f[1])):
            continue
        res = {"aptos": _int(f[1]), "comparecimento": 0, "votos": {}, "brancos": 0, "nulos": 0}
        lista = next((x for x in f[2:] if isinstance(x[2], list) and x[1] == SEQ), None)
        for rv in (lista[2] if lista else []):  # ResultadoVotacao
            g = rv[2]
            if len(g) < 3 or not _eh_int(g[1]):
                continue
            res["comparecimento"] += _int(g[1])
            for tvc in g[2][2]:  # TotalVotosCargo
                h = tvc[2]
                if not (h and _eh_int(h[0], CTX, 1) and _int(h[0]) == cargo):
                    continue
                for vv in h[-1][2]:  # TotalVotosVotavel
                    c = {x[1]: x for x in vv[2] if x[0] == CTX}
                    tipo, qtd = _int(c[1]), _int(c[2])
                    if tipo == 1 and 3 in c:
                        num = str(_int(c[3][2][-1]))
                        res["votos"][num] = res["votos"].get(num, 0) + qtd
                    elif tipo == 2:
                        res["brancos"] += qtd
                    elif tipo == 3:
                        res["nulos"] += qtd
        return res
    raise ValueError(f"eleição {id_eleicao} não encontrada no boletim")


if __name__ == "__main__":
    import json, sys
    print(json.dumps(ler(open(sys.argv[1], "rb").read(), int(sys.argv[2]) if len(sys.argv) > 2 else 6258)))
