/* Projeção INEMA (25/10): lê data/projecao.json (gerado por projecao/projetar.py) a cada 30 s.
   Na simulação (?sim=1 ou /simulacao/) não há projeção: mostra aviso. */
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const p2 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const p1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const nf = new Intl.NumberFormat("pt-BR");
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const dataHora = (iso) => (iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + "/" + iso.slice(0, 4) + " " + iso.slice(11, 19) : "—");
  const titulo = (s) => (String(s) === String(s).toUpperCase() ? String(s).toLowerCase().replace(/(^|\s)\S/g, (m) => m.toUpperCase()) : String(s));
  const REG = ["BR", "N", "NE", "CO", "SE", "S"];
  let dados = null, reg = "BR";

  const naSim = /[?&]sim=1/.test(location.search) || location.pathname.indexOf("/simulacao/") === 0;

  function vivo(est, txt) { const el = $("#vivo"); el.dataset.estado = est; el.querySelector("span").textContent = txt; }

  function aguardando(d) {
    $("#pj-aguardando").hidden = false; $("#pj-resultado").hidden = true; $("#pj-transf").hidden = true;
    const b = d.base, nomes = { N: "Norte", NE: "Nordeste", CO: "Centro-Oeste", SE: "Sudeste", S: "Sul" };
    $("#pj-ag-txt").innerHTML = "A projeção liga sozinha com pelo menos <b>" + b.minimo_cidades + " cidades</b> com a apuração encerrada, e <b>" +
      b.minimo_por_regiao + " em cada região</b>. Agora: <b>" + nf.format(b.cidades_finalizadas) + "</b> cidades encerradas.";
    $("#pj-regioes").innerHTML = Object.keys(nomes).map((r) => {
      const n = b.por_regiao[r] || 0, pct = Math.min(100, (100 * n) / b.minimo_por_regiao);
      return '<div class="pj-reg"><span>' + nomes[r] + "</span><div class=\"pj-reg-b\"><i style=\"width:" + pct + '%"></i></div><b>' + n + " / " + b.minimo_por_regiao + "</b></div>";
    }).join("");
    vivo("carregando", "Aguardando apuração");
  }

  function resultado(d) {
    $("#pj-aguardando").hidden = true; $("#pj-resultado").hidden = false; $("#pj-transf").hidden = false;
    const pr = d.projecao, [a, b] = d.candidatos, ap = d.apurado_tse;
    const lider = pr.pct_validos[a.numero] >= pr.pct_validos[b.numero] ? a.numero : b.numero;
    $("#pj-cands").innerHTML = [a, b].map((c) => {
      const f = pr.faixa[c.numero];
      return '<div class="pj-cand c' + esc(c.numero) + (c.numero === lider ? " lid" : "") + '"><div class="pj-nome">' + esc(titulo(c.nome_urna)) + " <small>" + esc(c.numero) + "</small></div>" +
        '<div class="pj-pct">' + p2.format(pr.pct_validos[c.numero]) + "%</div>" +
        '<div class="pj-faixa">entre ' + p2.format(f[0]) + "% e " + p2.format(f[1]) + "%</div>" +
        '<div class="pj-votos">≈ ' + nf.format(pr.votos[c.numero]) + " votos projetados</div>" +
        (ap ? '<div class="pj-agora">Apurado agora no TSE: <b>' + p2.format(ap.pct_validos[c.numero] || 0) + "%</b></div>" : "") + "</div>";
    }).join("");
    const pa = pr.pct_validos[a.numero], fa = pr.faixa[a.numero];
    $("#pj-barra").innerHTML = '<div class="pj-b"><i class="ba" style="width:' + pa + '%"></i><i class="bb" style="width:' + (100 - pa) + '%"></i>' +
      '<span class="pj-band" style="left:' + fa[0] + "%;width:" + Math.max(0.4, fa[1] - fa[0]) + '%" title="faixa provável"></span><span class="pj-meio"></span></div>' +
      '<div class="pj-b-leg"><span>' + esc(titulo(a.nome_urna)) + "</span><span>50%</span><span>" + esc(titulo(b.nome_urna)) + "</span></div>";
    const bs = d.base;
    $("#pj-base").innerHTML = "Calculada com <b>" + nf.format(bs.cidades_finalizadas) + "</b> cidades encerradas (" + p1.format(bs.pct_cidades) + "% das cidades, " +
      p1.format(bs.pct_eleitorado_finalizado) + "% do eleitorado)" + (ap ? " · TSE com <b>" + p2.format(ap.pct_secoes) + "%</b> das seções apuradas" : "") +
      " · comparecimento projetado <b>" + p1.format(pr.pct_comparecimento) + "%</b>";
    tabela();
    const idade = Date.now() - new Date(d.calculado_em).getTime();
    if (idade > 5 * 60000) vivo("atrasado", "Sem recálculo há " + Math.round(idade / 60000) + " min");
    else vivo("vivo", "Ao vivo");
  }

  function tabela() {
    if (!dados || !dados.transferencias) return;
    const [a, b] = dados.candidatos, linhas = dados.transferencias[reg] || [];
    $("#pj-reg-opts").innerHTML = REG.map((r) => '<button type="button" data-r="' + r + '" aria-pressed="' + (r === reg) + '">' + (r === "BR" ? "Brasil" : r) + "</button>").join("");
    $("#pj-tab thead").innerHTML = "<tr><th>No 1º turno votou em</th><th>Votos no 1º turno</th><th>→ " + esc(titulo(a.nome_urna)) + "</th><th>→ " +
      esc(titulo(b.nome_urna)) + "</th><th>→ Branco/nulo</th><th>→ Não votou</th></tr>";
    $("#pj-tab tbody").innerHTML = linhas.map((l) => {
      const t = l.para, cel = (v, cls) => '<td><span class="pj-cel ' + cls + '" style="--v:' + v + '%">' + p1.format(v) + "%</span></td>";
      return "<tr><td>" + esc(titulo(l.origem)) + "</td><td>" + nf.format(l.votos_1t) + "</td>" + cel(t[a.numero], "ca") + cel(t[b.numero], "cb") + cel(t.brancos_nulos, "cn") + cel(t.nao_votou, "cx") + "</tr>";
    }).join("");
  }

  $("#pj-reg-opts").addEventListener("click", (e) => { const bt = e.target.closest("button[data-r]"); if (bt) { reg = bt.dataset.r; tabela(); } });

  function erro(msg) { const fe = $("#faixa-erro"); fe.textContent = msg; fe.hidden = !msg; }

  async function carrega() {
    try {
      const r = await fetch("data/projecao.json?t=" + Date.now(), { cache: "no-store" });
      if (r.status === 404) { dados = null; aguardando({ base: { minimo_cidades: 250, minimo_por_regiao: 15, cidades_finalizadas: 0, por_regiao: {} } }); erro(""); return; }
      if (!r.ok) throw new Error("HTTP " + r.status);
      const d = await r.json();
      if (d.schema !== 1 || d.tipo !== "projecao") throw new Error("formato novo, atualize a página");
      dados = d; erro("");
      $("#pj-hora").textContent = dataHora(d.calculado_em);
      $("#marca-sim").hidden = !d.simulacao;
      if (d.status === "ok") resultado(d); else aguardando(d);
    } catch (e) {
      erro("Não consegui atualizar a projeção agora (" + e.message + "). Tento de novo em 30 s.");
    }
  }

  if (naSim) {
    $("#pj-aguardando").hidden = false;
    $("#pj-aguardando h2").textContent = "Projeção não disponível na simulação";
    $("#pj-ag-txt").textContent = "A projeção só roda com os dados oficiais do TSE. Saia da simulação para vê-la.";
    vivo("carregando", "Simulação");
    return;
  }
  carrega();
  setInterval(carrega, 30000);
})();
