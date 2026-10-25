"""Projeção INEMA do 2º turno por transferência de votos (só leitura de arquivos locais).

Ideia: em cada cidade, o eleitorado do 1º turno se divide em grupos de ORIGEM
(cada candidato grande, os pequenos juntos, brancos+nulos, abstenção) e o do 2º turno
em DESTINOS (candidato A, candidato B, brancos+nulos, abstenção). Com as cidades que já
FECHARAM o 2º turno, estimamos a matriz T (origem → destino) que melhor explica todas
ao mesmo tempo (cada linha soma 1, nada negativo). Depois aplicamos T no 1º turno das
cidades que ainda não fecharam e somamos o país.

T é estimada em camadas: país → região → estado → estado × porte → estado × porte × perfil
(terço mais A, do meio, mais B no 1º turno), cada camada puxada
para a de cima (encolhimento), para que poucas cidades não gerem taxas malucas.

Formato das cidades (igual ao coletor de municípios): {cd: {"te", "ts", "st", "and",
"vb", "vn", "abst", "c": {"<numero>": votos}}}.
"""
import numpy as np
from scipy.optimize import minimize

REGIAO = {
    "ac": "N", "am": "N", "ap": "N", "pa": "N", "ro": "N", "rr": "N", "to": "N",
    "al": "NE", "ba": "NE", "ce": "NE", "ma": "NE", "pb": "NE", "pe": "NE", "pi": "NE", "rn": "NE", "se": "NE",
    "df": "CO", "go": "CO", "ms": "CO", "mt": "CO",
    "es": "SE", "mg": "SE", "rj": "SE", "sp": "SE",
    "pr": "S", "rs": "S", "sc": "S",
}
REGIOES = ["N", "NE", "CO", "SE", "S"]
NOME_REGIAO = {"N": "Norte", "NE": "Nordeste", "CO": "Centro-Oeste", "SE": "Sudeste", "S": "Sul"}
DESTINOS = ["a", "b", "bn", "abst"]


def porte(te):
    """0 = até 20 mil eleitores, 1 = até 100 mil, 2 = maior."""
    return 0 if te < 20000 else (1 if te < 100000 else 2)


def origens(c, grupos):
    """Vetor de origem (votos) do 1º turno: grupos..., pequenos, brancos+nulos, abstenção."""
    v = [c["c"].get(g, 0) for g in grupos]
    pequenos = sum(n for k, n in c["c"].items() if k not in grupos)
    return np.array(v + [pequenos, c["vb"] + c["vn"], c["abst"]], float)


def destinos(c, a, b):
    return np.array([c["c"].get(a, 0), c["c"].get(b, 0), c["vb"] + c["vn"], c["abst"]], float)


def prior(grupos, a, b):
    """Ponto de partida fraco (só vale até chegarem cidades): eleitor de A fica com A, de B com B,
    terceiros se dividem, branco/nulo tende a repetir, abstenção tende a repetir."""
    k = len(grupos) + 3
    T = np.zeros((k, 4))
    for i, g in enumerate(grupos):
        T[i] = [.92, .02, .02, .04] if g == a else ([.02, .92, .02, .04] if g == b else [.35, .35, .12, .18])
    T[len(grupos)] = [.35, .35, .12, .18]      # pequenos
    T[len(grupos) + 1] = [.12, .12, .5, .26]   # brancos + nulos
    T[len(grupos) + 2] = [.04, .04, .02, .9]   # abstenção
    return T


def ajusta(X, Y, w, Tp, lam):
    """min Σ w·|y − x·T|² + lam·|T − Tp|²  com T ≥ 0 e linhas somando 1.
    X, Y em frações do eleitorado da cidade; w = peso da cidade (eleitorado relativo)."""
    k = X.shape[1]
    if len(X) == 0:
        return Tp.copy()
    Xw = X * w[:, None]
    A, B = Xw.T @ X, Xw.T @ Y

    def f(t):
        T = t.reshape(k, 4)
        D = T - Tp
        val = np.sum(T * (A @ T)) - 2 * np.sum(T * B) + lam * np.sum(D * D)
        g = 2 * (A @ T) - 2 * B + 2 * lam * D
        return val, g.ravel()

    J = np.kron(np.eye(k), np.ones((1, 4)))
    r = minimize(f, Tp.ravel(), jac=True, method="SLSQP", bounds=[(0, 1)] * (k * 4),
                 constraints=[{"type": "eq", "fun": lambda t: J @ t - 1, "jac": lambda t: J}],
                 options={"maxiter": 300, "ftol": 1e-14})
    T = np.clip(r.x.reshape(k, 4), 0, None)
    return T / T.sum(1, keepdims=True)


class Modelo:
    def __init__(self, base1t, grupos, a, b, lam=(1.0, 3.0, 3.0, 3.0, 3.0)):
        """base1t: {cd: (uf, cidade_1t)}; grupos: números (str) dos candidatos com grupo próprio;
        a, b: números dos dois candidatos do 2º turno; lam: força do puxão país/região/estado/porte."""
        self.grupos, self.a, self.b, self.lam = list(grupos), a, b, lam
        self.cds = list(base1t)
        self.uf = np.array([base1t[cd][0] for cd in self.cds])
        self.reg = np.array([REGIAO[u] for u in self.uf])
        c1 = [base1t[cd][1] for cd in self.cds]
        self.te1 = np.array([c["te"] for c in c1], float)
        self.V1 = np.array([origens(c, self.grupos) for c in c1])          # votos de origem
        self.X = self.V1 / self.te1[:, None]                               # frações
        self.porte = np.array([porte(t) for t in self.te1])
        # perfil da cidade no 1º turno: terço da força relativa de A sobre B (0 = mais B, 2 = mais A)
        ia, ib = self.grupos.index(a), self.grupos.index(b)
        forca = self.V1[:, ia] / np.maximum(1, self.V1[:, ia] + self.V1[:, ib])
        cortes = np.percentile(forca, [100 / 3, 200 / 3])
        self.perfil = np.digitize(forca, cortes)
        self.peso_medio = self.te1.mean()
        self.Tprior = prior(self.grupos, a, b)
        self.idx = {cd: i for i, cd in enumerate(self.cds)}
        self.lista_uf = sorted(set(self.uf)) + ["zz"]           # zz = exterior (última linha)
        self.iuf = np.array([self.lista_uf.index(u) for u in self.uf] + [len(self.lista_uf) - 1])
        self.cid_uf = {u: int(np.sum(self.uf == u)) for u in self.lista_uf[:-1]}
        self.te_uf = {u: float(self.te1[self.uf == u].sum()) for u in self.lista_uf[:-1]}

    # ---------- ajuste em camadas ----------
    def ajusta_camadas(self, fin, Y):
        """fin: índices das cidades finalizadas; Y: destinos (frações) dessas cidades, na mesma ordem."""
        X, w = self.X[fin], self.te1[fin] / self.peso_medio
        reg, uf, por = self.reg[fin], self.uf[fin], self.porte[fin]
        l0, l1, l2 = self.lam[:3]
        l3 = self.lam[3] if len(self.lam) > 3 else l2
        l4 = self.lam[4] if len(self.lam) > 4 else l3
        perf = self.perfil[fin]
        T = {"BR": ajusta(X, Y, w, self.Tprior, l0)}
        for r in REGIOES:
            m = reg == r
            T[r] = ajusta(X[m], Y[m], w[m], T["BR"], l1)
        for u in sorted(set(self.uf)):
            m = uf == u
            T[u] = ajusta(X[m], Y[m], w[m], T[REGIAO[u]], l2)
            for p in range(3):
                mp = m & (por == p)
                T[(u, p)] = ajusta(X[mp], Y[mp], w[mp], T[u], l3)
                for q in range(3):
                    mq = mp & (perf == q)
                    T[(u, p, q)] = ajusta(X[mq], Y[mq], w[mq], T[(u, p)], l4)
        return T

    # ---------- projeção ----------
    def projeta(self, atual2t, T, exterior=None):
        """atual2t: {cd: cidade_2t}. Finalizada → voto real; parcial → real + resto projetado;
        sem dado → projetada pelo 1º turno. exterior: (votos_origem_1t, te, destinos_2t_ou_None)."""
        contrib = np.zeros((len(self.cds) + 1, 4))   # votos (reais + projetados) de cada cidade; última = exterior
        resto = np.zeros(len(self.cds) + 1)          # eleitores ainda projetados (não apurados) por cidade
        for i, cd in enumerate(self.cds):
            c2 = atual2t.get(cd)
            Tc = T[(self.uf[i], self.porte[i], self.perfil[i])]
            te = c2["te"] if c2 and c2.get("te") else self.te1[i]
            prev = (self.X[i] @ Tc) * te
            if c2 and c2.get("and") == "finalizada":
                contrib[i] = destinos(c2, self.a, self.b)
            elif c2 and c2.get("st") and c2.get("ts"):
                d2 = destinos(c2, self.a, self.b)
                # parte já apurada = eleitorado das seções apuradas (comparecimento + abstenção nelas,
                # como o TSE informa); seções têm tamanhos diferentes, então st/ts só como reserva
                frac = d2.sum() / te if 0 < d2.sum() <= te else min(1.0, c2["st"] / c2["ts"])
                contrib[i] = d2 + (1 - frac) * prev
                resto[i] = (1 - frac) * te
            else:
                contrib[i] = prev
                resto[i] = te
        if exterior is not None:
            v1, te, d2 = exterior
            if d2 is not None:
                contrib[-1] = d2
            else:
                contrib[-1] = (v1 / te) @ T["BR"] * te
                resto[-1] = te
        self.ultimo_resto = resto
        self.ultimo_uf = np.zeros((len(self.lista_uf), 4))
        np.add.at(self.ultimo_uf, self.iuf, contrib)
        self.ultimo_resto_uf = np.zeros(len(self.lista_uf))
        np.add.at(self.ultimo_resto_uf, self.iuf, resto ** 2)
        return contrib.sum(0)

    def desvio_cidade(self, fin, Y, T):
        """Quanto uma cidade foge do padrão: desvio-padrão do resíduo de (A − B), em fração do
        eleitorado, nas cidades encerradas (média ponderada pelo eleitorado)."""
        if len(fin) < 2:
            return 0.05
        pred = np.array([self.X[i] @ T[(self.uf[i], self.porte[i], self.perfil[i])] for i in fin])
        r = (Y[:, 0] - Y[:, 1]) - (pred[:, 0] - pred[:, 1])
        w = self.te1[fin]
        return float(np.sqrt(np.sum(w * r * r) / np.sum(w)))

    def finalizadas(self, atual2t):
        fin, Y = [], []
        for cd, c2 in atual2t.items():
            i = self.idx.get(cd)
            if i is None or c2.get("and") != "finalizada" or not c2.get("te"):
                continue
            fin.append(i)
            Y.append(destinos(c2, self.a, self.b) / c2["te"])
        return np.array(fin, int), np.array(Y).reshape(-1, 4)

    def roda(self, atual2t, exterior=None, n_boot=0, semente=7):
        """Devolve dict com totais projetados, % válidos, matriz nacional e (opcional) faixa por bootstrap."""
        fin, Y = self.finalizadas(atual2t)
        T = self.ajusta_camadas(fin, Y)
        tot = self.projeta(atual2t, T, exterior)
        pa = 100 * tot[0] / (tot[0] + tot[1])
        # incerteza 1: as cidades que faltam fogem do padrão (independentes entre si)
        sig = self.desvio_cidade(fin, Y, T)
        dp_resto = 100 * sig * np.sqrt(np.sum(self.ultimo_resto ** 2)) / (2 * (tot[0] + tot[1]))
        res = {"tot": tot, "pct_a": pa, "T": T, "n_fin": len(fin), "fin": fin, "desvio_cidade": sig, "dp_resto": dp_resto}
        tuf, ruf = self.ultimo_uf.copy(), self.ultimo_resto_uf.copy()
        valid_uf = np.maximum(1.0, tuf[:, 0] + tuf[:, 1])
        pa_uf = 100 * tuf[:, 0] / valid_uf
        dp_resto_uf = 100 * sig * np.sqrt(ruf) / (2 * valid_uf)
        # incerteza 2: as próprias taxas (reamostrando as cidades encerradas)
        dp_taxas, dp_taxas_uf = 0.0, np.zeros(len(self.lista_uf))
        if n_boot and len(fin):
            rng = np.random.default_rng(semente)
            amostra, amostra_uf = [], []
            for _ in range(n_boot):
                j = rng.integers(0, len(fin), len(fin))
                Tb = self.ajusta_camadas(fin[j], Y[j])
                tb = self.projeta(atual2t, Tb, exterior)
                amostra.append(100 * tb[0] / (tb[0] + tb[1]))
                u = self.ultimo_uf
                amostra_uf.append(100 * u[:, 0] / np.maximum(1.0, u[:, 0] + u[:, 1]))
            dp_taxas = float(np.std(amostra))
            dp_taxas_uf = np.std(np.array(amostra_uf), axis=0)
            self.projeta(atual2t, T, exterior)  # devolve ultimo_resto ao ajuste principal
        meia = 1.645 * float(np.sqrt(dp_resto ** 2 + dp_taxas ** 2))
        res["dp_taxas"] = dp_taxas
        res["faixa_a"] = (pa - meia, pa + meia)
        # por estado: cidades encerradas e eleitorado já em cidades encerradas
        fin_uf = {u: 0 for u in self.lista_uf[:-1]}
        el_uf = {u: 0.0 for u in self.lista_uf[:-1]}
        for i in fin:
            fin_uf[self.uf[i]] += 1
            el_uf[self.uf[i]] += self.te1[i]
        res["ufs"] = {u: {"pct_a": float(pa_uf[k]), "meia_modelo": 1.645 * float(np.sqrt(dp_resto_uf[k] ** 2 + dp_taxas_uf[k] ** 2)),
                          "tot": tuf[k], "cid_fin": fin_uf.get(u, 0), "cid_tot": self.cid_uf.get(u, 0),
                          "pct_el": 100 * el_uf[u] / self.te_uf[u] if u in el_uf and self.te_uf[u] else 0.0}
                      for k, u in enumerate(self.lista_uf) if u != "zz" or exterior is not None}
        return res
