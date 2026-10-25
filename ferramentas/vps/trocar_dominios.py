#!/usr/bin/env python3
"""Troca o tráfego de eleicoes.inema.club e municipios.inema.club entre os Workers do Cloudflare e a reserva na VPS4.

Uso (roda na máquina principal, onde estão o login do wrangler e o token de DNS):
  python3 ferramentas/vps/trocar_dominios.py status            # onde cada domínio está agora
  python3 ferramentas/vps/trocar_dominios.py vps               # mostra o que faria (não muda nada)
  python3 ferramentas/vps/trocar_dominios.py vps --executar    # manda o tráfego para a VPS4
  python3 ferramentas/vps/trocar_dominios.py volta --executar  # devolve aos Workers do Cloudflare

Para a VPS: para os publicadores locais (senão eles prendem o domínio de volta no Worker), solta o domínio
do Worker e cria CNAME com proxy para eleicoes2026/municipios2026.inema.club (que apontam para a VPS4).
Na volta: apaga o CNAME, prende o domínio no Worker de novo e religa os publicadores.

Credenciais (nunca impressas):
  - Workers: login OAuth do wrangler (~/.config/.wrangler/config/default.toml), renovado com `wrangler whoami`.
  - DNS: CLOUDFLARE_API_TOKEN de ~/projetos/wifi/.env.
  - Em outra máquina: exporte CF_TOKEN com um token que tenha Workers Scripts:Edit e DNS:Edit na zona.
"""
import json, os, re, subprocess, sys, tomllib, urllib.error, urllib.request

ZONA = "inema.club"
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
SITES = [  # domínio, worker, alvo na VPS, publicador local
    ("eleicoes.inema.club", "eleicoes2026", "eleicoes2026.inema.club", "eleicoes-publicar"),
    ("municipios.inema.club", "eleicoes2026-municipios", "municipios2026.inema.club", "eleicoes-municipios-publicar"),
]
API = "https://api.cloudflare.com/client/v4"


def token_workers():
    if os.environ.get("CF_TOKEN"):
        return os.environ["CF_TOKEN"]
    # renova o login do wrangler se expirou (o mesmo que o publicador usa)
    subprocess.run(["npx", "--yes", "wrangler@4", "whoami"], cwd=os.path.join(RAIZ, "ferramentas", "cloudflare"),
                   capture_output=True, timeout=120)
    cfg = os.path.expanduser("~/.config/.wrangler/config/default.toml")
    with open(cfg, "rb") as f:
        return tomllib.load(f)["oauth_token"]


def token_dns():
    if os.environ.get("CF_TOKEN"):
        return os.environ["CF_TOKEN"]
    txt = open(os.path.expanduser("~/projetos/wifi/.env")).read()
    m = re.search(r"^CLOUDFLARE_API_TOKEN=[\"']?([^\"'\n]+)", txt, re.M)
    if not m:
        sys.exit("Falhou: CLOUDFLARE_API_TOKEN não está em ~/projetos/wifi/.env")
    return m.group(1).strip()


def api(tok, metodo, caminho, corpo=None):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(API + caminho, data=dados, method=metodo,
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        d = json.load(e)
    if not d.get("success"):
        sys.exit(f"Falhou: {metodo} {caminho} — {d.get('errors')}")
    return d.get("result")


def onde_esta(dominio):
    """Pergunta ao próprio site: /api/acessos só existe no Worker (na VPS é 404)."""
    req = urllib.request.Request(f"https://{dominio}/api/acessos", headers={"User-Agent": "Mozilla/5.0 trocar_dominios"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return f"Worker do Cloudflare (HTTP {r.status})"
    except urllib.error.HTTPError as e:
        return "VPS4" if e.code == 404 else f"? (HTTP {e.code})"
    except Exception as e:
        return f"sem resposta ({type(e).__name__})"


def systemctl(acao, unidade, executar):
    cmd = ["systemctl", "--user", acao, unidade]
    print(("  $ " if executar else "  (faria) $ ") + " ".join(cmd))
    if executar:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            print(f"    aviso: {r.stderr.strip() or 'falhou'} (seguindo)")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("status", "vps", "volta"):
        sys.exit(__doc__)
    modo, executar = sys.argv[1], "--executar" in sys.argv[2:]
    tw, td = token_workers(), token_dns()
    zona = api(td, "GET", f"/zones?name={ZONA}")[0]
    zid, conta = zona["id"], zona["account"]["id"]
    presos = {d["hostname"]: d for d in api(tw, "GET", f"/accounts/{conta}/workers/domains")}

    def registros(nome):
        return [r for r in api(td, "GET", f"/zones/{zid}/dns_records?name={nome}") if not (r.get("meta") or {}).get("read_only")]

    if modo == "status":
        for dom, worker, alvo, _ in SITES:
            regs = ", ".join(f"{r['type']} {r['content']}" for r in registros(dom)) or "nenhum"
            print(f"{dom}\n  preso ao Worker: {'sim (' + worker + ')' if dom in presos else 'não'}\n"
                  f"  registro DNS próprio: {regs}\n  respondendo agora: {onde_esta(dom)}")
        return

    if not executar:
        print("SIMULAÇÃO — nada será mudado. Para valer, repita com --executar.\n")

    if modo == "vps":
        for dom, worker, alvo, pub in SITES:
            print(f"{dom} → VPS4 ({alvo})")
            systemctl("stop", pub, executar)
            if dom in presos:
                print(f"  soltar do Worker {worker}")
                if executar:
                    api(tw, "DELETE", f"/accounts/{conta}/workers/domains/{presos[dom]['id']}")
            else:
                print("  já não está preso ao Worker")
            regs = registros(dom)
            if any(r["type"] == "CNAME" and r["content"] == alvo for r in regs):
                print(f"  CNAME → {alvo} já existe")
                continue
            for r in regs:  # sobra de troca anterior apontando para outro lugar
                print(f"  apagar registro antigo {r['type']} {r['content']}")
                if executar:
                    api(td, "DELETE", f"/zones/{zid}/dns_records/{r['id']}")
            print(f"  criar CNAME {dom} → {alvo} (proxy ligado)")
            if executar:
                api(td, "POST", f"/zones/{zid}/dns_records",
                    {"type": "CNAME", "name": dom, "content": alvo, "proxied": True, "ttl": 1,
                     "comment": "reserva eleicoes: trafego na VPS4 (trocar_dominios.py)"})

    else:  # volta
        for dom, worker, alvo, pub in SITES:
            print(f"{dom} → Worker {worker}")
            for r in registros(dom):
                print(f"  apagar registro {r['type']} {r['content']}")
                if executar:
                    api(td, "DELETE", f"/zones/{zid}/dns_records/{r['id']}")
            if dom in presos:
                print("  já está preso ao Worker")
            else:
                print(f"  prender no Worker {worker}")
                if executar:
                    api(tw, "PUT", f"/accounts/{conta}/workers/domains",
                        {"hostname": dom, "service": worker, "zone_id": zid, "environment": "production"})
            systemctl("start", pub, executar)

    if executar:
        print("\nPronto. Em até 1 minuto confira com: python3 ferramentas/vps/trocar_dominios.py status")
        print("Terminei: " + ("tráfego na VPS4" if modo == "vps" else "tráfego de volta aos Workers do Cloudflare"))


if __name__ == "__main__":
    main()
