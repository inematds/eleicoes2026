"""Monta saida/municipios-publicar/ e envia ao Cloudflare num Worker SEPARADO do painel oficial.

O painel oficial (ferramentas/publicar_cf.py, Worker "eleicoes2026") não é tocado: outro Worker
("eleicoes2026-municipios"), outra pasta, outro domínio (municipios/cloudflare/wrangler.toml).

Vai: o site de municipios/site (sem as pastas de teste data-*), o manifesto e as últimas versões
de cada estado. Use --montar para só montar a pasta e conferir, sem enviar nada.

Uso: python3 municipios/publicar_mun.py --montar           # só monta (nada sai da máquina)
     python3 municipios/publicar_mun.py --laco 20          # vigia e publica a cada mudança
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
P = os.path.dirname(AQUI)
SITE = os.path.join(AQUI, "site")
FONTE = os.path.join(P, "saida", "municipios", "data")
DEST = os.path.join(P, "saida", "municipios-publicar")
MANTER = 2  # versões por estado (o manifesto aponta a última)

HEADERS = """/data/latest.json
  Cache-Control: no-cache, max-age=0
/data/historico/*
  Cache-Control: no-cache, max-age=0
/data/uf/*
  Cache-Control: public, max-age=31536000, immutable
/assets/malha/*
  Cache-Control: public, max-age=3600
/assets/sim/*
  Cache-Control: public, max-age=3600
/*.html
  Cache-Control: no-cache
/
  Cache-Control: no-cache
"""


def monta():
    if os.path.exists(DEST):
        shutil.rmtree(DEST)
    os.makedirs(DEST)
    for nome in os.listdir(SITE):
        if nome == "data" or nome.startswith("data-"):
            continue  # dados vêm abaixo; pastas de teste (1º turno, simulação) não vão
        o, d = os.path.join(SITE, nome), os.path.join(DEST, nome)
        if os.path.isdir(o):
            shutil.copytree(o, d)
        else:
            shutil.copy2(o, d)
    m = json.load(open(os.path.join(FONTE, "latest.json")))
    if m.get("fonte", {}).get("tipo") == "simulacao" or m.get("eleicao", {}).get("eleicao") != "6258":
        raise SystemExit("o manifesto é de simulação ou de outra eleição: nada publicado")
    for uf, info in m["ufs"].items():
        pasta = os.path.dirname(info["arquivo"])
        vs = sorted(f for f in os.listdir(os.path.join(FONTE, pasta)) if f.startswith("v"))
        for f in set(vs[-MANTER:]) | {os.path.basename(info["arquivo"])}:
            d = os.path.join(DEST, "data", pasta, f)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(os.path.join(FONTE, pasta, f), d)
    hist = os.path.join(FONTE, "historico")
    if os.path.isdir(hist):
        shutil.copytree(hist, os.path.join(DEST, "data", "historico"))
    shutil.copy2(os.path.join(FONTE, "latest.json"), os.path.join(DEST, "data", "latest.json"))  # manifesto
    open(os.path.join(DEST, "_headers"), "w").write(HEADERS)
    n = sum(len(fs) for _, _, fs in os.walk(DEST))
    return m["versao"], n


def envia():
    r = subprocess.run(["npx", "--yes", "wrangler@4", "deploy"], cwd=os.path.join(AQUI, "cloudflare"),
                       capture_output=True, text=True, timeout=300)
    saida = (r.stdout + r.stderr).strip().splitlines()
    return r.returncode, [l for l in saida if any(k in l for k in ("Uploaded", "Deployed", "https://", "rror", "Current Version"))][-6:]


def assinatura():
    h = hashlib.sha256()
    try:
        h.update(open(os.path.join(FONTE, "latest.json"), "rb").read())
    except FileNotFoundError:
        pass
    for raiz, _, fs in os.walk(SITE):
        if os.path.basename(raiz).startswith("data"):
            continue
        for f in fs:
            h.update(str(os.path.getmtime(os.path.join(raiz, f))).encode())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--montar", action="store_true", help="só monta a pasta, não envia")
    ap.add_argument("--laco", type=float, help="vigia e publica a cada mudança (segundos)")
    a = ap.parse_args()
    if a.montar:
        v, n = monta()
        print(json.dumps({"montado": DEST, "versao": v, "arquivos": n}, ensure_ascii=False))
        return 0
    ultimo, rc = None, 0
    while True:
        sig = assinatura()
        if sig != ultimo:
            t0 = time.time()
            v, n = monta()
            rc, linhas = envia()
            print(json.dumps({"t": time.strftime("%H:%M:%S"), "versao": v, "arquivos": n, "rc": rc,
                              "s": round(time.time() - t0, 1), "saida": linhas}, ensure_ascii=False), flush=True)
            if rc == 0:
                ultimo = sig
        if not a.laco:
            return rc
        time.sleep(a.laco)


if __name__ == "__main__":
    sys.exit(main() or 0)
