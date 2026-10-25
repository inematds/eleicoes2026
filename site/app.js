/* Eleições 2026 — Parte 2 (apresentação). Lê só data/ (contrato schema 1). Nunca acessa o TSE. */
(function () {
  "use strict";
  let ultGraf = null;
  const SCHEMA = 1;
  const INTERVALO = window.ELEICOES_INTERVALO || 15000;
  const ATRASO_MS = 3 * 60 * 1000;
  const UFS = ["ac","al","am","ap","ba","ce","df","es","go","ma","mg","ms","mt","pa","pb","pe","pi","pr","rj","rn","ro","rr","rs","sc","se","sp","to"];
  const NOMES = {br:"Brasil",zz:"Exterior",ac:"Acre",al:"Alagoas",am:"Amazonas",ap:"Amapá",ba:"Bahia",ce:"Ceará",df:"Distrito Federal",es:"Espírito Santo",go:"Goiás",ma:"Maranhão",mg:"Minas Gerais",ms:"Mato Grosso do Sul",mt:"Mato Grosso",pa:"Pará",pb:"Paraíba",pe:"Pernambuco",pi:"Piauí",pr:"Paraná",rj:"Rio de Janeiro",rn:"Rio Grande do Norte",ro:"Rondônia",rr:"Roraima",rs:"Rio Grande do Sul",sc:"Santa Catarina",se:"Sergipe",sp:"São Paulo",to:"Tocantins"};
  // cartograma: [coluna, linha]
  const GRADE = {rr:[2,0],ap:[4,0],am:[1,1],pa:[3,1],ma:[4,1],ce:[5,1],rn:[6,1],ac:[0,2],ro:[1,2],mt:[2,2],to:[3,2],pi:[4,2],pe:[5,2],pb:[6,2],ms:[2,3],go:[3,3],df:[4,3],ba:[5,3],al:[6,3],sp:[3,4],mg:[4,4],es:[5,4],se:[6,4],pr:[3,5],rj:[4,5],sc:[3,6],rs:[3,7]};
  const CORES = ["var(--ca)", "var(--cb)"];
  // Cor do candidato vem do estilo (--c13, --c22 em estilo.css); sem cor própria usa o par neutro.
  function aplicaCores(cands) {
    cands.forEach((c, i) => document.documentElement.style.setProperty(i ? "--cb" : "--ca",
      "var(--c" + String(c.numero).replace(/\D/g, "") + ", var(" + (i ? "--cb0" : "--ca0") + "))"));
  }
  // ---------- estilos ----------
  const ESTILOS = [["noite", "Noite"], ["papel", "Papel"], ["telejornal", "Telejornal"], ["contraste", "Alto contraste"]];
  function aplicaEstilo(id) {
    if (!ESTILOS.some((e) => e[0] === id)) id = "noite";
    document.documentElement.dataset.estilo = id;
    try { localStorage.setItem("eleicoes-estilo", id); } catch (e) {}
    document.querySelectorAll(".estilos button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.id === id));
    const sel = $("#estilo-sel"); if (sel) sel.value = id;
    if (ultGraf) grafico(ultGraf[0], ultGraf[1]);
  }
  function montaEstilos() {
    $("#estilos").innerHTML = ESTILOS.map((e) => '<button type="button" data-id="' + e[0] + '">' + e[1] + "</button>").join("");
    $("#estilo-sel").innerHTML = ESTILOS.map((e) => '<option value="' + e[0] + '">' + e[1] + "</option>").join("");
    $("#estilos").addEventListener("click", (ev) => { const b = ev.target.closest("button"); if (b) aplicaEstilo(b.dataset.id); });
    $("#estilo-sel").addEventListener("change", (ev) => aplicaEstilo(ev.target.value));
    aplicaEstilo(document.documentElement.dataset.estilo || "noite");
  }

  const $ = (s) => document.querySelector(s);
  const nf = new Intl.NumberFormat("pt-BR");
  const pf = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const n = (x) => nf.format(x);
  const p = (x) => pf.format(x) + "%";
  const hora = (iso) => (iso ? iso.slice(11, 19) : "—");
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

  let manifesto = null;
  let versaoDesenhada = null;
  const cache = new Map(); // arquivos versionados são imutáveis

  async function pega(caminho, imutavel) {
    if (imutavel && cache.has(caminho)) return cache.get(caminho);
    const r = await fetch("data/" + caminho + (imutavel ? "" : "?t=" + Date.now()), { cache: imutavel ? "force-cache" : "no-store" });
    if (!r.ok) throw new Error(caminho + " → HTTP " + r.status);
    const j = await r.json();
    if (j.schema !== SCHEMA) throw new Error("formato de dados novo (schema " + j.schema + "). Atualize a página.");
    if (imutavel) cache.set(caminho, j);
    return j;
  }

  function abrAtual() {
    const m = location.hash.match(/^#\/uf\/([a-z]{2})$/);
    return m && (UFS.includes(m[1]) || m[1] === "zz") ? m[1] : "br";
  }

  function corDe(res, numero) {
    const i = res.candidatos.findIndex((c) => c.numero === numero);
    return CORES[i] || "var(--mut)";
  }

  // ---------- desenho ----------
  function trilha(abr) {
    $("#trilha").classList.toggle("estado", abr !== "br");
    $("#trilha").innerHTML = abr === "br"
      ? "<b>Brasil</b>"
      : '<a href="#/">Brasil</a><span>›</span><b>' + esc(NOMES[abr]) + "</b>";
  }

  function placar(res) {
    const [a, b] = res.candidatos;
    const d = res.derivados;
    const fim = res.situacao.andamento === "finalizada";
    const card = (c, i) => {
      const lider = d.lider === c.numero;
      const selo = c.eleito ? '<span class="selo selo-eleito">Eleito</span>'
        : (lider && !fim && res.votos.total ? '<span class="selo selo-lider">À frente</span>' : "");
      return '<article class="cand" style="--cor:' + CORES[i] + '">' +
        '<div class="cand-topo"><span class="cand-num" style="background:' + CORES[i] + ';color:var(--sobre-cand);border-color:transparent">' + esc(c.numero) + '</span><span class="partido">' + esc(c.partido) + "</span>" + selo + "</div>" +
        '<h1 class="cand-nome">' + esc(c.nome_urna) + "</h1>" +
        '<div class="cand-pct num">' + pf.format(c.pct_validos) + "<small>% dos válidos</small></div>" +
        '<div class="cand-votos num"><b>' + n(c.votos) + "</b> votos</div></article>";
    };
    const meio = '<div class="meio"><div class="rot">Diferença</div>' +
      '<div class="dif num">' + n(d.diferenca_votos) + '</div><div class="difpp num">' + pf.format(d.diferenca_pp_validos) + ' p.p.</div>' +
      '<div class="calc">calculado</div></div>';
    $("#placar").innerHTML = card(a, 0) + meio + card(b, 1);
  }

  function progresso(res) {
    const s = res.secoes;
    $("#progresso").innerHTML =
      '<div class="trilho" role="progressbar" aria-valuenow="' + s.pct_totalizadas + '" aria-valuemin="0" aria-valuemax="100"><div class="feito" style="width:' + s.pct_totalizadas + '%"></div></div>' +
      '<div class="linha num"><span><b>' + p(s.pct_totalizadas) + "</b> das seções</span><span>" + n(s.totalizadas) + " de " + n(s.total) + " · faltam " + n(s.pendentes) + "</span></div>";
    $("#sec-nota").textContent = "% de seções não é % de votos nem de eleitores";
  }

  function barra100(res) {
    // 100% = eleitorado total. Todos os pedaços são números oficiais; só o % do eleitorado é calculado aqui.
    const v = res.votos, e = res.eleitorado;
    const [a, b] = res.candidatos;
    const te = e.total || 1;
    const falta = Math.max(0, e.total - e.apurado);
    const segs = [
      { nm: a.nome_urna, vl: a.votos, cls: "", cor: CORES[0], rotulo: true },
      { nm: b.nome_urna, vl: b.votos, cls: "", cor: CORES[1], rotulo: true },
      { nm: "Brancos", vl: v.brancos, cls: "seg-branco" },
      { nm: "Nulos", vl: v.nulos, cls: "seg-nulo" },
      { nm: "Abstenção", vl: e.abstencao, cls: "seg-abst", rotulo: true },
      { nm: "Ainda não apurado", vl: falta, cls: "seg-pend", rotulo: true },
    ];
    segs.forEach((s) => (s.pc = s.vl * 100 / te));
    $("#barra100").innerHTML =
      '<div class="b100" role="img" aria-label="Eleitorado: votos, abstenção e o que falta apurar">' +
      segs.map((s) => '<div class="' + s.cls + '" style="flex-basis:' + s.pc + "%;" + (s.cor ? "background:" + s.cor : "") + '" data-dica="' + esc(s.nm) + "|" + n(s.vl) + "|" + p(s.pc) + '">' +
        (s.rotulo && s.pc >= 6 ? '<span class="seg-rot">' + pf.format(s.pc) + "%</span>" : "") + "</div>").join("") +
      '</div><div class="leg100">' +
      segs.map((s) => '<div class="it"><span class="q ' + s.cls + '" style="' + (s.cor ? "background:" + s.cor : "") + '"></span><div><div class="nm">' + esc(s.nm) + '</div><div class="vl num">' + n(s.vl) + " · " + p(s.pc) + "</div></div></div>").join("") +
      "</div>";
  }

  function tiles(res) {
    const e = res.eleitorado, v = res.votos;
    const parc = res.situacao.parcial ? '<span class="parcial">parcial</span>' : "";
    const t = (rot, vl, sub) => '<div class="tile"><div class="rot">' + rot + '</div><div class="vl num">' + vl + '</div><div class="sub">' + sub + "</div></div>";
    $("#tiles").innerHTML =
      t("Eleitorado", n(e.total), "aptos a votar") +
      t("Votos computados", n(v.total), "válidos: " + p(v.pct_validos_sobre_total) + parc) +
      t("Comparecimento", p(e.pct_comparecimento), n(e.comparecimento) + " nas seções apuradas" + parc) +
      t("Abstenção", p(e.pct_abstencao), n(e.abstencao) + " nas seções apuradas" + parc);
  }

  // botões do mapa (Brancos, Nulos, Abstenção, %), lembrados no navegador
  const MOPT = { brancos: true, nulos: true, abst: true, pct: true };
  try { Object.assign(MOPT, JSON.parse(localStorage.getItem("eleicoes-mapa-c2") || "{}")); } catch (e) {}
  let ultMapa = null;
  function mapaETabela(br, ufs) {
    ultMapa = [br, ufs];
    $("#bloco-mapa").hidden = false;
    document.querySelectorAll("#map-opts button").forEach((bt) => bt.setAttribute("aria-pressed", MOPT[bt.dataset.opt]));
    const [a, b] = br.candidatos;
    $("#th-a").innerHTML = '<span class="pt" style="background:' + CORES[0] + '"></span>' + esc(a.nome_urna.split(" ")[0]); $("#th-a").title = a.nome_urna;
    $("#th-b").innerHTML = '<span class="pt" style="background:' + CORES[1] + '"></span>' + esc(b.nome_urna.split(" ")[0]); $("#th-b").title = b.nome_urna;
    let html = "";
    const linhas = [];
    for (const uf of UFS.concat(["zz"])) {
      const r = ufs[uf];
      const pos = GRADE[uf];
      const estilo = pos ? "grid-column:" + (pos[0] + 1) + ";grid-row:" + (pos[1] + 1) + ";" : "";
      const zz = uf === "zz";
      const sg = zz ? "Exterior" : uf.toUpperCase();
      if (!r || !r.votos.total) {
        html += '<button class="uf vazio' + (zz ? " zz" : "") + '" style="' + estilo + '" data-uf="' + uf + '" role="listitem" aria-label="' + NOMES[uf] + ', sem votos apurados"><span class="sg">' + sg +
          "</span></button>";
      } else {
        // mini barra na base do eleitorado da UF: vermelho/azul = votos de cada um, escuro = brancos+nulos+abstenção, cinza = não apurado
        const [ca, cb] = r.candidatos;
        const te = r.eleitorado.total || 1;
        const pend = Math.max(0, r.eleitorado.total - r.eleitorado.apurado);
        const outros = Math.max(0, te - pend - ca.votos - cb.votos);
        const w = (x) => (x * 100 / te).toFixed(2) + "%";
        const lid = r.derivados.lider;
        const cl = lid ? r.candidatos.find((c) => c.numero === lid) : null;
        const forca = cl ? Math.min(35, 8 + r.derivados.diferenca_pp_validos * 1.2) : 0;
        const linha = (c, k) => '<span class="l' + (c.numero === lid ? " ld1" : "") + '"><i>' + esc(c.numero) + "</i>" + pf.format(c.pct_validos) + "</span>";
        // o quadradinho inteiro é a barra: vermelho | azul | brancos+nulos+abstenção | não apurado
        const seg = [[CORES[0], ca.votos], [CORES[1], cb.votos]];
        if (MOPT.brancos) seg.push(["var(--branco)", r.votos.brancos]);
        if (MOPT.nulos) seg.push(["var(--nulo)", r.votos.nulos]);
        if (MOPT.abst) seg.push(["var(--abst-on)", r.eleitorado.abstencao]);
        seg.push(["var(--pend)", pend]);
        const base = seg.reduce((t, x) => t + x[1], 0) || 1;  // faixa desligada some; o resto volta a somar 100%
        let acc = 0;
        const enche = "background:linear-gradient(90deg," + seg.map(([c, q]) => { const i = acc; acc = Math.min(100, acc + q * 100 / base); return c + " " + i.toFixed(2) + "% " + acc.toFixed(2) + "%"; }).join(",") + ");";
        html += '<button class="uf cheio' + (zz ? " zz" : "") + '" style="' + estilo + enche + '" data-uf="' + uf + '" role="listitem" aria-label="' + NOMES[uf] + ": " + esc(ca.nome_urna) + " " + p(ca.pct_validos) + ", " + esc(cb.nome_urna) + " " + p(cb.pct_validos) + " dos válidos; " + p(r.secoes.pct_totalizadas) + ' das seções">' +
          '<span class="sg">' + sg + "</span>" + (MOPT.pct ? '<span class="pcs num">' + linha(ca, 0) + linha(cb, 1) + "</span>" : "") +
          "</button>";
      }
      if (r) linhas.push(r);
    }
    const it = (cor, nm) => '<span class="li"><i style="background:' + cor + '"></i>' + nm + "</span>";
    html += '<div class="mapa-leg">Cada quadradinho se preenche com (desligue uma faixa nos botões e o resto volta a somar 100%):<br>' + it(CORES[0], esc(a.nome_urna)) + it(CORES[1], esc(b.nome_urna)) +
      (MOPT.brancos ? it("var(--branco)", "Brancos") : "") + (MOPT.nulos ? it("var(--nulo)", "Nulos") : "") + (MOPT.abst ? it("var(--abst-on)", "Abstenção") : "") +
      it("var(--pend)", "Falta apurar") +
      (MOPT.pct ? "<br>Números = % dos válidos." : "") + "</div>";
    $("#mapa").innerHTML = html;
    $("#tab-uf tbody").innerHTML = linhas.map((r) => {
      const [ca, cb] = r.candidatos;
      const m = r.derivados.lider;
      return '<tr data-uf="' + r.abrangencia.cd + '"><td>' + (r.abrangencia.cd === "zz" ? "Exterior" : r.abrangencia.cd.toUpperCase()) + "</td><td>" + p(r.secoes.pct_totalizadas) +
        '</td><td class="' + (m === ca.numero ? "ma" : "") + '">' + p(ca.pct_validos) + '</td><td class="' + (m === cb.numero ? "ma" : "") + '">' + p(cb.pct_validos) + "</td><td>" + n(r.derivados.diferenca_votos) + "</td></tr>";
    }).join("");
  }

  function resumo(abr, res, ufs) {
    const d = res.derivados, lider = res.candidatos.find((c) => c.numero === d.lider);
    const t = (rot, vl) => '<div class="rc"><div class="t">' + rot + '</div><div class="v">' + vl + "</div></div>";
    const comDados = ufs ? UFS.filter((u) => ufs[u] && ufs[u].votos.total).length : 0;
    $("#res-cards").innerHTML =
      t("Liderança", lider ? '<span style="color:' + CORES[res.candidatos.indexOf(lider)] + '">' + esc(lider.nome_urna) + "</span>" : "Empate") +
      t("Diferença", (d.lider ? "+" : "") + pf.format(d.diferenca_pp_validos) + " p.p. · " + n(d.diferenca_votos) + " votos") +
      t(abr === "br" ? "Estados com dados" : "Seções apuradas", abr === "br" ? comDados + " / 27" : n(res.secoes.totalizadas) + " / " + n(res.secoes.total)) +
      t("Última atualização oficial", hora(res.fonte.totalizado_tse)) +
      t("Fonte", res.fonte.tipo === "oficial" ? "TSE" : "Simulação");
  }

  function grafico(res, hist) {
    ultGraf = [res, hist];
    const pts = hist.pontos.filter((x) => x.votos_total > 0);
    const [a, b] = res.candidatos;
    $("#leg-evo").innerHTML = [a, b].map((c, i) => '<span><span class="pt" style="background:' + CORES[i] + '"></span>' + esc(c.numero) + " · " + esc(c.nome_urna) + "</span>").join("");
    const W = Math.max(300, Math.round($("#grafico").clientWidth || 900)), H = W < 600 ? 220 : 300, m = { l: 40, r: 12, t: 14, b: 28 };
    if (pts.length < 2) { $("#grafico").innerHTML = '<p class="nota">A evolução aparece depois da segunda atualização.</p>'; return; }
    const vals = pts.flatMap((x) => [x.pct_validos[a.numero], x.pct_validos[b.numero]]);
    let lo = Math.min(45, ...vals), hi = Math.max(55, ...vals);
    lo = Math.floor(lo / 5) * 5; hi = Math.ceil(hi / 5) * 5;
    const X = (v) => m.l + (v / 100) * (W - m.l - m.r);
    const Y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
    let g = "";
    for (let y = lo; y <= hi; y += 5) g += '<line class="grade" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(y) + '" y2="' + Y(y) + '"/><text x="' + (m.l - 8) + '" y="' + (Y(y) + 4) + '" text-anchor="end">' + y + "%</text>";
    for (let x = 0; x <= 100; x += 25) g += '<text x="' + X(x) + '" y="' + (H - 8) + '" text-anchor="' + (x === 0 ? "start" : x === 100 ? "end" : "middle") + '">' + x + "%</text>";
    g += '<line class="meta" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(50) + '" y2="' + Y(50) + '"/>';
    const linha = (c, i) => '<path d="' + pts.map((x, k) => (k ? "L" : "M") + X(x.pct_secoes).toFixed(1) + "," + Y(x.pct_validos[c.numero]).toFixed(1)).join("") + '" fill="none" stroke="' + CORES[i] + '" stroke-width="2.25" stroke-linejoin="round"/>';
    const fim = pts[pts.length - 1];
    const rotulo = (c, i) => '<circle cx="' + X(fim.pct_secoes) + '" cy="' + Y(fim.pct_validos[c.numero]) + '" r="4.5" fill="' + CORES[i] + '" stroke="var(--card)" stroke-width="2"/>';
    $("#grafico").innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Evolução dos percentuais de votos válidos">' + g + linha(a, 0) + linha(b, 1) + rotulo(a, 0) + rotulo(b, 1) +
      '<line class="mira" id="mira" y1="' + m.t + '" y2="' + (H - m.b) + '" x1="-10" x2="-10"/><rect id="alvo" x="' + m.l + '" y="0" width="' + (W - m.l - m.r) + '" height="' + H + '" fill="transparent"/></svg>';
    const svg = $("#grafico svg");
    const dica = $("#dica");
    const mostra = (ev) => {
      const r = svg.getBoundingClientRect();
      const xv = ((ev.clientX - r.left) / r.width * W - m.l) / (W - m.l - m.r) * 100;
      let best = pts[0];
      for (const x of pts) if (Math.abs(x.pct_secoes - xv) < Math.abs(best.pct_secoes - xv)) best = x;
      $("#mira").setAttribute("x1", X(best.pct_secoes)); $("#mira").setAttribute("x2", X(best.pct_secoes));
      dica.innerHTML = '<div class="t">' + hora(best.totalizado_tse) + " · " + p(best.pct_secoes) + " das seções</div>" +
        [a, b].map((c, i) => '<div class="r"><span><span class="pt" style="background:' + CORES[i] + '"></span>' + esc(c.nome_urna) + "</span><b class=\"num\">" + p(best.pct_validos[c.numero]) + "</b></div>").join("") +
        '<div class="r"><span>votos computados</span><span class="num">' + n(best.votos_total) + "</span></div>";
      dica.hidden = false;
      dica.style.left = Math.min(ev.clientX + 14, innerWidth - 200) + "px";
      dica.style.top = ev.clientY + 14 + "px";
    };
    $("#alvo").addEventListener("pointermove", mostra);
    $("#alvo").addEventListener("pointerleave", () => { dica.hidden = true; $("#mira").setAttribute("x1", -10); $("#mira").setAttribute("x2", -10); });

    const ult = hist.pontos.slice(-10).reverse();
    $("#tab-hist thead").innerHTML = "<tr><th>Versão</th><th>Horário TSE</th><th>Seções</th><th>" + esc(a.nome_urna) + "</th><th>" + esc(b.nome_urna) + "</th><th>Votos</th></tr>";
    $("#tab-hist tbody").innerHTML = ult.map((x) => "<tr><td>" + x.versao + "</td><td>" + hora(x.totalizado_tse) + "</td><td>" + p(x.pct_secoes) + "</td><td>" + p(x.pct_validos[a.numero]) + "</td><td>" + p(x.pct_validos[b.numero]) + "</td><td>" + n(x.votos_total) + "</td></tr>").join("");
  }

  function fonte(res) {
    const f = res.fonte;
    $("#fonte").innerHTML =
      "<div><b>Horário oficial da totalização</b><br>" + hora(f.totalizado_tse) + "</div>" +
      "<div><b>Coletado pelo INEMA</b><br>" + hora(f.coletado_em) + "</div>" +
      "<div><b>Versão</b><br>" + res.versao + " · " + esc(res.situacao.andamento.replace("_", " ")) + (res.situacao.parcial ? " · parcial" : " · final") + "</div>" +
      "<div><b>Arquivo de origem</b><br><code>" + esc(f.url) + "</code></div>" +
      "<div><b>Impressão digital do bruto (sha256)</b><br><code>" + esc((f.sha256_bruto || "").slice(0, 24)) + "…</code></div>";
  }

  function estadoVivo() {
    const el = $("#vivo");
    if (!manifesto) return;
    const idade = Date.now() - new Date(manifesto.publicado_em).getTime();
    let est = "vivo", txt = "ao vivo · " + hora(manifesto.publicado_em);
    if (manifesto.situacao === "finalizada") { est = "final"; txt = "apuração encerrada"; }
    else if (manifesto.situacao === "aguardando") { est = "carregando"; txt = "aguardando apuração"; }
    else if (idade > ATRASO_MS) { est = "atrasado"; txt = "sem novidade há " + Math.round(idade / 60000) + " min"; }
    el.dataset.estado = est; el.querySelector("span").textContent = txt;
  }

  async function desenha(forcar) {
    const abr = abrAtual();
    const chave = manifesto.versao + "|" + abr;
    if (!forcar && chave === versaoDesenhada) return;
    const info = manifesto.abrangencias[abr];
    trilha(abr);
    if (!info) { $("#placar").innerHTML = '<p class="nota">Ainda sem dados para ' + esc(NOMES[abr]) + ".</p>"; return; }
    const [res, hist] = await Promise.all([pega(info.arquivo, true), pega(manifesto.historico[abr], false)]);
    const sim = manifesto.fonte.tipo !== "oficial" || res.fonte.tipo !== "oficial";
    $("#faixa-sim").hidden = !sim; $("#marca-sim").hidden = !sim;
    if (sim && !$("#faixa-sim").textContent.trim()) $("#faixa-sim").innerHTML = "<strong>SIMULAÇÃO</strong> Nomes e números fictícios, para teste do painel. Não é resultado da eleição.";
    if (sim && manifesto.fonte.nota) $("#faixa-sim").innerHTML = "<strong>SIMULAÇÃO</strong> " + esc(manifesto.fonte.nota.replace(/^Simulação: /, ""));
    aplicaCores(res.candidatos);
    placar(res); progresso(res); barra100(res); tiles(res); grafico(res, hist); fonte(res);
    if (abr === "br") {
      const lista = UFS.concat(["zz"]).filter((u) => manifesto.abrangencias[u]);
      const rs = await Promise.all(lista.map((u) => pega(manifesto.abrangencias[u].arquivo, true)));
      const ufs = {}; lista.forEach((u, i) => (ufs[u] = rs[i]));
      mapaETabela(res, ufs);
      resumo(abr, res, ufs);
    } else {
      $("#bloco-mapa").hidden = true;
      resumo(abr, res, null);
    }
    document.querySelectorAll(".menu a[data-nav]").forEach((x) => x.classList.toggle("ativo", x.dataset.nav === (abr === "br" ? "br" : "estados")));
    document.title = (abr === "br" ? "Brasil" : NOMES[abr]) + " · " + p(res.secoes.pct_totalizadas) + " · Eleições 2026 INEMA";
    if (versaoDesenhada && versaoDesenhada.split("|")[1] === abr) $("#placar").classList.add("pisca");
    setTimeout(() => $("#placar").classList.remove("pisca"), 1300);
    versaoDesenhada = chave;
  }

  async function ciclo() {
    try {
      const m = await pega("latest.json", false);
      if (m.tipo !== "manifesto") throw new Error("manifesto inválido");
      if (!manifesto || m.versao >= manifesto.versao) manifesto = m; // nunca volta versão
      $("#faixa-erro").hidden = true;
      await desenha(false);
    } catch (e) {
      const fe = $("#faixa-erro");
      fe.hidden = false;
      fe.textContent = "Não consegui atualizar agora (" + e.message + "). Mostrando o último dado válido; tento de novo em 15 s.";
    }
    estadoVivo();
  }

  document.addEventListener("click", (ev) => {
    const alvo = ev.target.closest("[data-uf]");
    if (alvo) { location.hash = "#/uf/" + alvo.dataset.uf; scrollTo({ top: 0, behavior: "smooth" }); }
  });
  // dica dos quadradinhos dos estados (igual à Central)
  document.addEventListener("pointermove", (ev) => {
    const t = ev.target.closest && ev.target.closest(".uf[data-uf]");
    if (!t) return;
    const dica = $("#dica"), uf = t.dataset.uf;
    const info = manifesto && manifesto.abrangencias[uf], r = info && cache.get(info.arquivo);
    let h = '<div class="t">' + NOMES[uf] + (uf !== "zz" ? " (" + uf.toUpperCase() + ")" : "") + "</div>";
    if (!r || !r.votos.total) h += '<div class="r"><span>sem votos apurados</span></div>';
    else {
      const [a, b] = r.candidatos;
      const lin = (nm, vl) => '<div class="r"><span>' + nm + '</span><b class="num">' + vl + "</b></div>";
      h += lin(esc(a.nome_urna), p(a.pct_validos)) + lin(esc(b.nome_urna), p(b.pct_validos)) +
        lin("Brancos", p(r.votos.pct_brancos_sobre_total)) + lin("Nulos", p(r.votos.pct_nulos_sobre_total)) +
        lin("Seções apuradas", p(r.secoes.pct_totalizadas)) + lin("Diferença", n(r.derivados.diferenca_votos) + " votos");
    }
    dica.innerHTML = h; dica.hidden = false;
    dica.style.left = Math.min(ev.clientX + 16, innerWidth - 220) + "px"; dica.style.top = ev.clientY + 16 + "px";
  });
  document.addEventListener("pointerover", (ev) => {
    if (ev.target.closest && ev.target.closest(".uf[data-uf]")) return;
    const s = ev.target.closest("[data-dica]");
    const dica = $("#dica");
    if (!s) { if (!ev.target.closest("#grafico")) dica.hidden = true; return; }
    const [nm, vl, pc] = s.dataset.dica.split("|");
    dica.innerHTML = '<div class="t">' + nm + '</div><div class="r"><span>votos</span><b class="num">' + vl + '</b></div><div class="r"><span>do total computado</span><b class="num">' + pc + "</b></div>";
    const r = s.getBoundingClientRect();
    dica.hidden = false; dica.style.left = Math.min(r.left, innerWidth - 200) + "px"; dica.style.top = r.bottom + 8 + "px";
  });
  addEventListener("hashchange", () => manifesto && desenha(true));
  $("#map-opts").addEventListener("click", (ev) => {
    const bt = ev.target.closest("button"); if (!bt) return;
    MOPT[bt.dataset.opt] = !MOPT[bt.dataset.opt];
    try { localStorage.setItem("eleicoes-mapa-c2", JSON.stringify(MOPT)); } catch (e) {}
    if (ultMapa) mapaETabela(ultMapa[0], ultMapa[1]);
  });
  $("#btn-tv").addEventListener("click", () => {
    document.body.classList.toggle("tv");
    if (document.body.classList.contains("tv")) document.documentElement.requestFullscreen?.().catch(() => {});
    else if (document.fullscreenElement) document.exitFullscreen();
  });

  let tRes;
  addEventListener("resize", () => { clearTimeout(tRes); tRes = setTimeout(() => ultGraf && grafico(ultGraf[0], ultGraf[1]), 200); });
  montaEstilos();
  ciclo();
  setInterval(ciclo, INTERVALO);
  setInterval(estadoVivo, 5000);
})();
