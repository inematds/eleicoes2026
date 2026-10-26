#!/usr/bin/env python3
"""Contexto do chat "Tire suas dúvidas" -> saida/oficial/data/chat-contexto.json (só arquivos locais).

Junta, em um JSON compacto, os números das páginas de análise (A virada, Análise, Raio-X, Por que perdeu,
Conferência, Projeção, Exterior). O Worker do site manda esse texto ao Claude como base das respostas.

Sem carimbos de hora que mudam a cada rodada (gerado_em etc.): o texto só muda quando os dados mudam,
e assim o cache de prompt da API continua valendo. Só regrava o arquivo se o conteúdo mudou.
"""
import json
import os

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(P, "saida", "oficial", "data")
FORA = {"gerado_em", "analise_gerada_em", "horario", "calculado_em", "ultima_consulta_tse", "schema", "versao", "coletado_em"}


def le(nome):
    try:
        return json.load(open(os.path.join(D, nome)))
    except (OSError, ValueError):
        return None


def limpa(x):
    if isinstance(x, dict):
        return {k: limpa(v) for k, v in x.items() if k not in FORA}
    if isinstance(x, list):
        return [limpa(v) for v in x]
    if isinstance(x, float):
        return round(x, 2)
    return x


def so(d, *ks):
    return {k: d[k] for k in ks if d and k in d}


def main():
    lat = le("latest.json")
    br = le(lat["abrangencias"]["br"]["arquivo"]) if lat else None
    an, rx, dr, cf, vr, pj, ex = (le(n) for n in ("analise.json", "raiox.json", "derrota.json", "conferencia.json",
                                                  "virada.json", "projecao.json", "exterior.json"))
    est = (an or {}).get("estaduais") or {}
    ctx = {
        "sobre": "Números oficiais do TSE da eleição presidencial de 2026 (1º turno 4/10, 2º turno 25/10, Lula x Flávio Bolsonaro), "
                 "coletados e analisados pelo site eleicoes.inema.club. Números 13 = Lula, 22 = Flávio. Percentuais em % dos votos válidos "
                 "salvo indicação. Campos L/F/O: L = coligação com o PT, F = coligação com o PL, O = outros.",
        "paginas": {
            "Visão geral": "https://eleicoes.inema.club/", "Análise (1º x 2º turno)": "https://eleicoes.inema.club/analise.html",
            "Raio-X": "https://eleicoes.inema.club/raiox.html", "Por que perdeu": "https://eleicoes.inema.club/derrota.html",
            "A virada": "https://eleicoes.inema.club/virada.html", "Conferência": "https://eleicoes.inema.club/conferencia.html",
            "Projeção": "https://eleicoes.inema.club/projecao.html", "Exterior": "https://eleicoes.inema.club/exterior.html",
            "Municípios": "https://municipios.inema.club/",
        },
        "explicacoes_das_paginas": [
            "A virada / a conta que sempre fecha: ganho de Lula + ganho de Flávio = votos dos outros 10 candidatos no 1º turno "
            "+ aumento do comparecimento + queda dos brancos + queda dos nulos. Fecha exatamente com os números oficiais "
            "(ver a_virada.brasil.categorias e a_virada.alegacao.bolo).",
            "A 'coincidência de 38 mil votos' (38.390) circulou num texto nas redes: ele dava a Lula os votos dos outros candidatos "
            "e a queda dos nulos, e a Flávio o aumento do comparecimento e a queda dos brancos, e achava a mesma sobra dos dois lados. "
            "O 38.390 vinha de uma apuração parcial; com os números finais essa mesma divisão dá 109.003 (a_virada.divisoes[0]). "
            "Qualquer divisão dá sobra igual e de sinal trocado, porque é uma identidade contábil: a coincidência não prova nem "
            "desmente transferência de votos. O total nacional não mostra trocas que se anulam.",
            "Postagem 'Lula fez 11 milhões de votos a mais / pegou todos os votos e mais as abstenções': ver a_virada.checagem e "
            "a_virada.alegacao (a soma dos 4 candidatos do gráfico confere, mas faltam 6; a abstenção caiu e Flávio também cresceu).",
            "Níveis de investigação (página A virada): 1) Brasil; 2) estados, regiões e cidades; 3) boletins de urna seção a seção "
            "x totalização — o nível 3 só está feito para o exterior (página Conferência); para o Brasil ainda falta.",
            "Projeção INEMA e 'para onde foram os votos' são ESTIMATIVAS de um modelo que compara cidades; o voto é secreto.",
        ],
        "resultado_2t_brasil": so(br, "situacao", "secoes", "eleitorado", "votos", "candidatos", "derivados") if br else None,
        "a_virada": vr,
        "analise_1x2_turno": {"fatos": (an or {}).get("fatos"), "estimativa": (an or {}).get("estimativa"),
                              "senado_governador_por_uf": est.get("ufs"), "campos": est.get("campos")},
        "raio_x": so(rx, "saldo", "concentracao", "cenario", "comparecimento", "crescimento"),
        "por_que_perdeu": so(dr, "campos", "placar", "ufs", "divisao", "conta", "virada", "hipoteses"),
        "conferencia": so(cf, "resumo", "itens", "brasil", "ufs", "integridade", "exterior"),
        "projecao_inema": so(pj, "status", "base", "apurado_tse", "projecao", "nome_regiao", "virada"),
        "exterior": so(ex, "fonte", "candidatos", "total", "previsto"),
    }
    txt = json.dumps(limpa(ctx), ensure_ascii=False, separators=(",", ":"))
    dest = os.path.join(D, "chat-contexto.json")
    try:
        if open(dest).read() == txt:
            print(json.dumps({"mudou": False, "bytes": len(txt.encode())}))
            return
    except OSError:
        pass
    tmp = dest + ".tmp"
    open(tmp, "w").write(txt)
    os.chmod(tmp, 0o644)
    os.replace(tmp, dest)
    print(json.dumps({"mudou": True, "bytes": len(txt.encode())}))


if __name__ == "__main__":
    main()
