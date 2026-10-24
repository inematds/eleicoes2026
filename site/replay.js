/* Simulação acelerada (botão "Simulação"): com ?sim=1, entrega ao painel os dados de
   assets/sim-1turno.json como se viessem do servidor, um passo a cada PASSO_MS.
   O painel (app.js / central.js) não muda: só o fetch de "data/..." é atendido daqui.
   Nomes fictícios; tudo sai marcado como simulação. */
(function () {
  "use strict";
  const q = new URLSearchParams(location.search);
  const ativo = q.has("sim");
  // botão do menu: liga/desliga a simulação mantendo a página e o estado aberto
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("a.sim-btn").forEach((a) => {
      if (ativo) { a.classList.add("ativo-sim"); a.lastChild.textContent = "Sair da simulação"; a.href = location.pathname + location.hash; }
      else a.href = location.pathname + "?sim=1" + location.hash;
    });
  });
  if (!ativo) return;

  const PASSO_MS = 1500, PAUSA_FIM = 6;          // ~1 min do 0% ao 100%, para 9 s no fim e recomeça
  window.ELEICOES_INTERVALO = PASSO_MS;
  const fetchOrig = window.fetch.bind(window);
  let pacote = null, t0 = 0;
  const pronto = fetchOrig("assets/sim-1turno.json?v=1").then((r) => r.json()).then((p) => { pacote = p; t0 = Date.now(); });

  const tick = () => Math.floor((Date.now() - t0) / PASSO_MS);
  function passo() {
    const n = pacote.passos.length, ciclo = n + PAUSA_FIM;
    return pacote.passos[Math.min(tick() % ciclo, n - 1)];
  }
  const caminho = (abr, v) => (abr === "br" ? "br" : "uf/" + abr) + "/v" + String(v).padStart(5, "0") + ".json";

  function manifesto() {
    const ps = passo(), ab = {};
    for (const [abr, v] of Object.entries(ps.v)) {
      const arq = caminho(abr, v), r = pacote.arquivos[arq];
      if (!r) continue;
      ab[abr] = { versao: v, arquivo: arq, totalizado_tse: r.fonte.totalizado_tse, pct_secoes: r.secoes.pct_totalizadas, lider: r.derivados.lider };
    }
    const br = ab.br && pacote.arquivos[ab.br.arquivo];
    return {
      schema: 1, tipo: "manifesto", versao: 900000 + tick(), // sempre sobe, até quando recomeça
      publicado_em: new Date().toISOString(), eleicao: pacote.eleicao,
      fonte: { tipo: "simulacao", orgao: "TSE", nota: "Simulação acelerada: andamento inventado; eleitorado, comparecimento, brancos, nulos e proporção entre os dois tirados do 1º turno (04/10). Nomes fictícios. Não é resultado do 2º turno." },
      situacao: br ? br.situacao.andamento : "aguardando",
      abrangencias: ab,
      historico: Object.fromEntries(Object.keys(ab).map((a) => [a, "historico/" + a + ".json"])),
    };
  }
  function historico(abr) {
    const h = pacote.historico[abr], lim = passo().v[abr] || 0;
    return h ? Object.assign({}, h, { pontos: h.pontos.filter((p) => p.versao <= lim) }) : null;
  }

  window.fetch = async function (u, o) {
    const url = String(u);
    if (!url.startsWith("data/")) return fetchOrig(u, o);
    await pronto;
    const rel = url.slice(5).split("?")[0];
    let corpo = null;
    if (rel === "latest.json") corpo = manifesto();
    else if (rel.startsWith("historico/")) corpo = historico(rel.slice(10, -5));
    else corpo = pacote.arquivos[rel] || null;
    return corpo ? new Response(JSON.stringify(corpo), { status: 200, headers: { "Content-Type": "application/json" } })
                 : new Response("", { status: 404 });
  };
})();
