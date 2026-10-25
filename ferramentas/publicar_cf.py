"""Monta saida/publicar/ e envia ao Cloudflare (wrangler deploy) quando os dados mudam.

  /              site + dados OFICIAIS   (saida/oficial/data)
  /simulacao/    site + simulação com nomes FICTÍCIOS (saida/simficticio/data)

Só vão os arquivos de dados referenciados pelo manifesto atual + as últimas versões de cada
abrangência (limite de arquivos do Cloudflare). Ordem segura: o wrangler sobe tudo de uma vez,
então manifesto e arquivos chegam juntos.

Uso: python3 ferramentas/publicar_cf.py [--laco 20]
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, time

P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(P, "site")
DEST = os.path.join(P, "saida", "publicar")
FONTES = {"": os.path.join(P, "saida", "oficial", "data"), "simulacao": os.path.join(P, "saida", "simficticio", "data")}
MANTER = 4  # versões por abrangência

HEADERS = """/data/latest.json
  Cache-Control: no-cache, max-age=0
/data/projecao.json
  Cache-Control: no-cache, max-age=0
/data/projecao-historico.json
  Cache-Control: no-cache, max-age=0
/data/exterior.json
  Cache-Control: no-cache, max-age=0
/data/historico/*
  Cache-Control: no-cache, max-age=0
/data/br/*
  Cache-Control: public, max-age=31536000, immutable
/data/uf/*
  Cache-Control: public, max-age=31536000, immutable
/simulacao/data/latest.json
  Cache-Control: no-cache, max-age=0
/simulacao/data/historico/*
  Cache-Control: no-cache, max-age=0
/*.html
  Cache-Control: no-cache
/
  Cache-Control: no-cache
"""


def copia_site(alvo):
    os.makedirs(alvo, exist_ok=True)
    for nome in os.listdir(SITE):
        if nome == "data":
            continue
        o, d = os.path.join(SITE, nome), os.path.join(alvo, nome)
        if os.path.isdir(o):
            shutil.copytree(o, d, dirs_exist_ok=True)
        else:
            shutil.copy2(o, d)


def copia_dados(fonte, alvo):
    m = json.load(open(os.path.join(fonte, "latest.json")))
    os.makedirs(alvo, exist_ok=True)
    quer = set()
    for abr, info in m["abrangencias"].items():
        pasta = os.path.dirname(info["arquivo"])
        vs = sorted(f for f in os.listdir(os.path.join(fonte, pasta)) if f.startswith("v"))
        quer |= {f"{pasta}/{f}" for f in vs[-MANTER:]}
        quer.add(info["arquivo"])
    quer |= set(m.get("historico", {}).values())
    for rel in quer:
        d = os.path.join(alvo, rel)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(os.path.join(fonte, rel), d)
    shutil.copy2(os.path.join(fonte, "latest.json"), os.path.join(alvo, "latest.json"))  # manifesto
    proj = os.path.join(fonte, "projecao.json")  # Projeção INEMA (projecao/projetar.py), só no oficial
    if os.path.exists(proj):
        shutil.copy2(proj, os.path.join(alvo, "projecao.json"))
    hist = os.path.join(fonte, "projecao-historico.json")
    if os.path.exists(hist):
        shutil.copy2(hist, os.path.join(alvo, "projecao-historico.json"))
    ext = os.path.join(fonte, "exterior.json")  # boletins do exterior (exterior/coletor_ext.py), só no oficial
    if os.path.exists(ext):
        shutil.copy2(ext, os.path.join(alvo, "exterior.json"))
    return m["versao"]


def monta():
    if os.path.exists(DEST):
        shutil.rmtree(DEST)
    vers = {}
    for sub, fonte in FONTES.items():
        if not os.path.exists(os.path.join(fonte, "latest.json")):
            continue
        base = os.path.join(DEST, sub) if sub else DEST
        copia_site(base)
        vers[sub or "/"] = copia_dados(fonte, os.path.join(base, "data"))
    open(os.path.join(DEST, "_headers"), "w").write(HEADERS)
    return vers


def envia():
    r = subprocess.run(["npx", "--yes", "wrangler@4", "deploy"], cwd=os.path.join(P, "ferramentas", "cloudflare"),
                       capture_output=True, text=True, timeout=300)
    saida = (r.stdout + r.stderr).strip().splitlines()
    return r.returncode, [l for l in saida if any(k in l for k in ("Uploaded", "Deployed", "https://", "rror", "Current Version"))][-6:]


def assinatura():
    h = hashlib.sha256()
    for f in sorted(FONTES.values()):
        try:
            h.update(open(os.path.join(f, "latest.json"), "rb").read())
            for extra in ("projecao.json", "exterior.json"):
                if os.path.exists(os.path.join(f, extra)):
                    h.update(open(os.path.join(f, extra), "rb").read())
        except FileNotFoundError:
            pass
    h.update(str(max((os.path.getmtime(os.path.join(SITE, x)) for x in os.listdir(SITE) if x != "data"), default=0)).encode())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--laco", type=float, help="fica vigiando e publica a cada mudança (segundos)")
    a = ap.parse_args()
    ultimo = None
    while True:
        sig = assinatura()
        if sig != ultimo:
            t0 = time.time()
            vers = monta()
            rc, linhas = envia()
            print(json.dumps({"t": time.strftime("%H:%M:%S"), "versoes": vers, "rc": rc, "s": round(time.time() - t0, 1), "saida": linhas}, ensure_ascii=False), flush=True)
            if rc == 0:
                ultimo = sig
        if not a.laco:
            return rc
        time.sleep(a.laco)


if __name__ == "__main__":
    sys.exit(main() or 0)
