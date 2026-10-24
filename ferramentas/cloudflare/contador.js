// Contador de acessos do site (Cloudflare Worker + Durable Object).
// Só responde em /api/acessos; todo o resto continua servido como arquivo estático
// (os arquivos que existem nem passam por aqui). O site chama POST uma vez por sessão
// do navegador (soma 1) e GET nas outras vezes (só lê). Conta acessos desde o lançamento,
// não pessoas online agora.

export class Contador {
  constructor(state) {
    this.state = state;
  }

  async fetch(request) {
    let n = (await this.state.storage.get("n")) || 0;
    if (request.method === "POST") {
      n += 1;
      await this.state.storage.put("n", n);
    }
    return new Response(JSON.stringify({ acessos: n }), { headers: { "content-type": "application/json" } });
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/acessos") {
      if (request.method !== "GET" && request.method !== "POST") {
        return new Response(null, { status: 405, headers: { allow: "GET, POST" } });
      }
      const obj = env.CONTADOR.get(env.CONTADOR.idFromName("total"));
      const r = await obj.fetch("https://contador/total", { method: request.method });
      return new Response(await r.text(), {
        headers: { "content-type": "application/json", "cache-control": "no-store" },
      });
    }
    return env.ASSETS.fetch(request);
  },
};
