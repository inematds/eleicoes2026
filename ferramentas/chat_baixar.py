#!/usr/bin/env python3
"""Baixa as conversas do chat "Tire suas dúvidas" gravadas no Cloudflare -> saida/chat/conversas.jsonl.

Incremental: guarda o último id baixado e só pega as novas. Token em ~/.config/eleicoes2026/chat.env
(CHAT_EXPORT_TOKEN), fora do repositório. Também imprime um resumo (perguntas, sessões, erros, tokens).

  python3 ferramentas/chat_baixar.py            # baixa as novas
  python3 ferramentas/chat_baixar.py --resumo   # só o resumo do que já está no disco
"""
import argparse
import json
import os
import urllib.request

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(P, "saida", "chat")
ARQ = os.path.join(DEST, "conversas.jsonl")
URL = "https://eleicoes.inema.club/api/chat/exporta"


def token():
    for l in open(os.path.expanduser("~/.config/eleicoes2026/chat.env")):
        if l.startswith("CHAT_EXPORT_TOKEN="):
            return l.split("=", 1)[1].strip()
    raise SystemExit("CHAT_EXPORT_TOKEN não encontrado em ~/.config/eleicoes2026/chat.env")


def ultimo_id():
    try:
        return max(json.loads(l)["id"] for l in open(ARQ) if l.strip())
    except (OSError, ValueError):
        return 0


def baixa():
    os.makedirs(DEST, exist_ok=True)
    tok, novas, desde = token(), 0, ultimo_id()
    while True:
        req = urllib.request.Request(f"{URL}?desde={desde}", headers={
            "authorization": "Bearer " + tok, "user-agent": "Mozilla/5.0 (inema eleicoes chat_baixar)"})
        rows = json.load(urllib.request.urlopen(req, timeout=60))["conversas"]
        if not rows:
            break
        with open(ARQ, "a") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        novas += len(rows)
        desde = rows[-1]["id"]
        if len(rows) < 1000:
            break
    return novas


def resumo():
    rs = [json.loads(l) for l in open(ARQ)] if os.path.exists(ARQ) else []
    soma = lambda k: sum(r.get(k) or 0 for r in rs)
    return {"perguntas": len(rs), "sessoes": len({r["sessao"] for r in rs}), "visitantes": len({r["visitante"] for r in rs}),
            "erros": sum(1 for r in rs if r.get("erro")), "tokens_entrada": soma("entrada"), "tokens_cache_lida": soma("cache_lida"),
            "tokens_cache_criada": soma("cache_criada"), "tokens_saida": soma("saida"),
            "ultima": rs[-1]["ts"] if rs else None}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--resumo", action="store_true")
    a = ap.parse_args()
    out = {} if a.resumo else {"novas": baixa()}
    out.update(resumo())
    print(json.dumps(out, ensure_ascii=False))
