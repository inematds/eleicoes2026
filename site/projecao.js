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
    $("#pj-aguardando").hidden = false; $("#pj-resultado").hidden = true; $("#pj-transf").hidden = true; $("#pj-hist").hidden = true; $("#pj-ufs").hidden = true;
    const b = d.base, nomes = { N: "Norte", NE: "Nordeste", CO: "Centro-Oeste", SE: "Sudeste", S: "Sul" };
    $("#pj-ag-txt").innerHTML = "A projeção liga sozinha com pelo menos <b>" + b.minimo_cidades + " cidades</b> com a apuração encerrada, <b>" +
      b.minimo_por_regiao + " em cada região</b>" + (b.minimo_ufs ? ", " + (b.minimo_por_uf || 3) + " em cada um de <b>" + b.minimo_ufs + " estados</b> e <b>" + p1.format(b.minimo_pct_eleitorado) + "% do eleitorado</b>" : "") +
      ". Agora: <b>" + nf.format(b.cidades_finalizadas) + "</b> cidades encerradas" + (b.minimo_ufs ? ", " + (b.ufs_com_minimo || 0) + " estados com o mínimo e " + p1.format(b.pct_eleitorado_finalizado || 0) + "% do eleitorado" : "") + ".";
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
    virada(d);
    historico();
    estados();
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

  function virada(d) {
    const v = d.virada, el = $("#pj-virada");
    if (!v) { el.hidden = true; return; }
    const nome = (n) => esc(titulo((d.candidatos.find((c) => c.numero === n) || {}).nome_urna || n));
    let h;
    if (v.situacao === "praticamente_apurado") h = "<b>Praticamente tudo apurado:</b> restam menos de 0,2% dos votos válidos estimados.";
    else if (v.situacao === "impossivel") h = "<b>O que falta para a virada:</b> faltam cerca de <b>" + nf.format(v.faltam_validos) + "</b> votos válidos (" + p1.format(v.pct_faltam) +
      "% do total estimado). Nem com 100% deles " + nome(v.atras) + " alcançaria " + nome(v.lider) + " pelos números de agora.";
    else if (v.situacao === "ja_a_frente") h = "<b>Atenção:</b> no número apurado pelo TSE, " + nome(v.atras) + " está à frente, mas a projeção indica que os votos que faltam favorecem " + nome(v.lider) + ".";
    else h = "<b>O que falta para a virada:</b> faltam cerca de <b>" + nf.format(v.faltam_validos) + "</b> votos válidos (" + p1.format(v.pct_faltam) + "% do total estimado). Para virar, " +
      nome(v.atras) + " precisaria de <b>" + p1.format(v.precisa_pct) + "%</b> deles; a projeção indica <b>" + p1.format(v.projecao_pct) + "%</b>.";
    el.innerHTML = h + ' <span class="pj-v-nota">(conta com o apurado oficial do TSE e o total de válidos projetado)</span>';
    el.hidden = false;
  }

  async function historico() {
    try {
      const r = await fetch("data/projecao-historico.json?t=" + Date.now(), { cache: "no-store" });
      if (!r.ok) return;
      const h = await r.json(), e = (h.entradas || []).filter((x) => x.a != null);
      histo = e; estados();
      if (e.length < 2) { $("#pj-hist").hidden = true; return; }
      $("#pj-hist").hidden = false;
      const W = Math.max(320, Math.min(1100, $("#pj-graf").clientWidth || 900)), H = W < 600 ? 220 : 240, pl = 44, pr = 12, pt = 12, pb = 28;
      const ts = e.map((x) => new Date(x.t).getTime()), t0 = Math.min(...ts), t1 = Math.max(...ts) || t0 + 1;
      const vals = e.flatMap((x) => [x.lo, x.hi, x.tse_a].filter((v) => v != null)).concat([50]);
      let y0 = Math.floor(Math.min(...vals) - 0.5), y1 = Math.ceil(Math.max(...vals) + 0.5);
      const X = (t) => pl + ((t - t0) / Math.max(1, t1 - t0)) * (W - pl - pr), Y = (v) => pt + (1 - (v - y0) / (y1 - y0)) * (H - pt - pb);
      const area = e.map((x, i) => X(ts[i]) + "," + Y(x.hi)).join(" ") + " " + e.slice().reverse().map((x, i) => X(ts[e.length - 1 - i]) + "," + Y(x.lo)).join(" ");
      const linha = (k) => e.map((x, i) => (x[k] == null ? null : X(ts[i]) + "," + Y(x[k]))).filter(Boolean).join(" ");
      let grade = "";
      for (let v = y0; v <= y1; v += Math.max(1, Math.round((y1 - y0) / 5))) grade += '<line x1="' + pl + '" x2="' + (W - pr) + '" y1="' + Y(v) + '" y2="' + Y(v) + '" class="g"/><text x="' + (pl - 6) + '" y="' + (Y(v) + 4) + '" class="ty">' + v + "%</text>";
      const hh = (t) => new Date(t).toTimeString().slice(0, 5);
      $("#pj-graf").innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Projeção ao longo da noite">' + grade +
        '<line x1="' + pl + '" x2="' + (W - pr) + '" y1="' + Y(50) + '" y2="' + Y(50) + '" class="m50"/>' +
        '<polygon points="' + area + '" class="ar"/><polyline points="' + linha("a") + '" class="lp"/><polyline points="' + linha("tse_a") + '" class="lt"/>' +
        '<text x="' + pl + '" y="' + (H - 8) + '" class="tx">' + hh(t0) + '</text><text x="' + (W - pr) + '" y="' + (H - 8) + '" class="tx" text-anchor="end">' + hh(t1) + "</text></svg>";
      const a = dados.candidatos[0];
      $("#pj-hist-sub").textContent = "% dos válidos de " + titulo(a.nome_urna) + " a cada cálculo (" + e.length + " registros). Cada cálculo publicado fica guardado; nada é reescrito.";
    } catch (err) { /* histórico é opcional */ }
  }

  const NOMES_UF = { ac: "Acre", al: "Alagoas", am: "Amazonas", ap: "Amapá", ba: "Bahia", ce: "Ceará", df: "Distrito Federal", es: "Espírito Santo",
    go: "Goiás", ma: "Maranhão", mg: "Minas Gerais", ms: "Mato Grosso do Sul", mt: "Mato Grosso", pa: "Pará", pb: "Paraíba", pe: "Pernambuco",
    pi: "Piauí", pr: "Paraná", rj: "Rio de Janeiro", rn: "Rio Grande do Norte", ro: "Rondônia", rr: "Roraima", rs: "Rio Grande do Sul",
    sc: "Santa Catarina", se: "Sergipe", sp: "São Paulo", to: "Tocantins", zz: "Exterior" };
  let ordemUf = "disputa", ufsAberto = false, histo = [];

  // linha da evolução da projeção de um estado (cada cálculo publicado)
  function linhaUf(u) {
    const pts = histo.map((x) => (x.ufs && x.ufs[u] != null ? x.ufs[u] : null)).filter((v) => v != null);
    if (pts.length < 2) return '<div class="pj-spark pj-spark-vazio" title="A linha aparece a partir do segundo cálculo">—</div>';
    // escala do próprio estado, com altura mínima de 3 pontos (ruído pequeno não vira drama)
    const W = 120, H = 30, mn = Math.min(...pts), mx = Math.max(...pts), meio = (mn + mx) / 2;
    const meia = Math.max(1.5, (mx - mn) / 2 + 0.3), lo = meio - meia, hi = meio + meia;
    const X = (i) => 2 + (i / (pts.length - 1)) * (W - 4), Y = (v) => 2 + (1 - (v - lo) / (hi - lo)) * (H - 4);
    const ult = pts[pts.length - 1], cor = ult >= 50 ? "var(--c13)" : "var(--c22)";
    const d = pts.map((v, i) => X(i).toFixed(1) + "," + Y(v).toFixed(1)).join(" ");
    return '<svg class="pj-spark" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Evolução da projeção: de ' + p1.format(pts[0]) + "% para " + p1.format(ult) + '%">' +
      "<title>Projeção ao longo da noite: " + p1.format(pts[0]) + "% → " + p1.format(ult) + "%</title>" +
      (50 > lo && 50 < hi ? '<line x1="0" x2="' + W + '" y1="' + Y(50) + '" y2="' + Y(50) + '" class="m50"/>' : "") +
      '<polyline points="' + d + '" style="stroke:' + cor + '"/><circle cx="' + X(pts.length - 1) + '" cy="' + Y(ult) + '" r="2.5" style="fill:' + cor + '"/></svg>';
  }

  function estados() {
    if (!dados || !dados.ufs) return;
    const [a, b] = dados.candidatos, lista = Object.entries(dados.ufs);
    lista.sort((x, y) => {
      if (ordemUf === "az") return NOMES_UF[x[0]].localeCompare(NOMES_UF[y[0]], "pt");
      if (x[1].estavel !== y[1].estavel) return x[1].estavel ? -1 : 1;
      const dx = x[1].estavel ? Math.abs(x[1].pct_a - 50) : 99, dy = y[1].estavel ? Math.abs(y[1].pct_a - 50) : 99;
      return dx - dy || NOMES_UF[x[0]].localeCompare(NOMES_UF[y[0]], "pt");
    });
    const na = esc(titulo(a.nome_urna)), nb = esc(titulo(b.nome_urna));
    $("#pj-ufs-sub").textContent = "% dos válidos de " + titulo(a.nome_urna) + " (vermelho) × " + titulo(b.nome_urna) + " (azul) em cada estado: a linha mostra a projeção ao longo da noite e a barra, a projeção de agora com a faixa provável";
    $("#pj-ufs-ord").querySelectorAll("button").forEach((bt) => bt.setAttribute("aria-pressed", String(bt.dataset.o === ordemUf)));
    $("#pj-ufs-lista").innerHTML = lista.map(([u, e]) => {
      const ap = e.tse && e.tse.pct_a != null ? "Apurado " + p2.format(e.tse.pct_a) + "% · " + p1.format(e.tse.pct_secoes) + "% das seções" : "Sem apuração ainda";
      const cid = u === "zz" ? "" : nf.format(e.cid_fin) + " de " + nf.format(e.cid_tot) + " cidades encerradas";
      let barra, num;
      if (e.estavel) {
        barra = '<div class="pj-b pj-b-uf"><i class="ba" style="width:' + e.pct_a + '%"></i><i class="bb" style="width:' + (100 - e.pct_a) + '%"></i>' +
          (e.final ? "" : '<span class="pj-band" style="left:' + e.lo + "%;width:" + Math.max(0.4, e.hi - e.lo) + '%"></span>') + '<span class="pj-meio"></span></div>';
        const ra = Math.round(e.pct_a * 10) / 10;
        num = '<b class="ca">' + p1.format(ra) + '%</b> × <b class="cb">' + p1.format(100 - ra) + "%</b>" +
          (e.final ? ' <small>(final)</small>' : ' <small>entre ' + p1.format(e.lo) + " e " + p1.format(e.hi) + "</small>");
      } else {
        const t = e.tse && e.tse.pct_a != null ? e.tse.pct_a : null;
        barra = '<div class="pj-b pj-b-uf pj-inst">' + (t != null ? '<i class="ba" style="width:' + t + '%"></i><i class="bb" style="width:' + (100 - t) + '%"></i>' : "") + '<span class="pj-meio"></span></div>';
        num = '<span class="pj-inst-t">projeção instável</span>';
      }
      const link = u === "zz" ? "index.html#/uf/zz" : "index.html#/uf/" + u;
      return '<a class="pj-uf" href="' + link + '"><div class="pj-uf-n"><b>' + NOMES_UF[u] + "</b><small>" + cid + '</small></div><div class="pj-uf-s">' + linhaUf(u) + '</div><div class="pj-uf-b">' + barra +
        '</div><div class="pj-uf-v">' + num + "<small>" + ap + "</small></div></a>";
    }).join("");
    $("#pj-ufs").hidden = !ufsAberto;
  }

  $("#pj-ver-ufs").addEventListener("click", () => {
    ufsAberto = !ufsAberto;
    $("#pj-ver-ufs").setAttribute("aria-expanded", String(ufsAberto));
    $("#pj-ver-ufs").textContent = ufsAberto ? "Esconder estados" : "Ver por estado";
    estados();
    if (ufsAberto) $("#pj-ufs").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  $("#pj-ufs-ord").addEventListener("click", (ev) => { const bt = ev.target.closest("button[data-o]"); if (bt) { ordemUf = bt.dataset.o; estados(); } });

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
