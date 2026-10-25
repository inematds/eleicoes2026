/* Central — layout "centro de comando". Lê só data/ (contrato schema 1) e assets/mapa-br.json. */
(function () {
  "use strict";
  const SCHEMA = 1, INTERVALO = window.ELEICOES_INTERVALO || 15000, ATRASO_MS = 3 * 60 * 1000;
  const UFS = ["ac","al","am","ap","ba","ce","df","es","go","ma","mg","ms","mt","pa","pb","pe","pi","pr","rj","rn","ro","rr","rs","sc","se","sp","to"];
  const NOMES = {br:"Brasil",zz:"Exterior",ac:"Acre",al:"Alagoas",am:"Amazonas",ap:"Amapá",ba:"Bahia",ce:"Ceará",df:"Distrito Federal",es:"Espírito Santo",go:"Goiás",ma:"Maranhão",mg:"Minas Gerais",ms:"Mato Grosso do Sul",mt:"Mato Grosso",pa:"Pará",pb:"Paraíba",pe:"Pernambuco",pi:"Piauí",pr:"Paraná",rj:"Rio de Janeiro",rn:"Rio Grande do Norte",ro:"Rondônia",rr:"Roraima",rs:"Rio Grande do Sul",sc:"Santa Catarina",se:"Sergipe",sp:"São Paulo",to:"Tocantins"};
  const SEM_SIGLA = ["df", "se", "al", "pb", "rn", "pe", "es", "rj"]; // pequenos demais para letreiro
  const COR = (c, i) => "var(--c" + String(c.numero).replace(/\D/g, "") + ", " + (i ? "#8e6cf0" : "#0fa89a") + ")";

  const $ = (s) => document.querySelector(s);
  const nf = new Intl.NumberFormat("pt-BR");
  const p1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const p2 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const n = (x) => nf.format(x);
  const pc = (x) => p1.format(x) + "%";
  const hora = (iso) => (iso ? iso.slice(11, 19) : "—");
  const dataHora = (iso) => (iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + "/" + iso.slice(0, 4) + " " + iso.slice(11, 19) : "—");
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const ICO = {
    gente: '<svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.2"/><circle cx="17" cy="9" r="2.4"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M14.5 14.4c.8-.3 1.6-.4 2.5-.4 2.8 0 4 2 4 5"/></svg>',
    pizza: '<svg viewBox="0 0 24 24"><path d="M12 3a9 9 0 1 0 9 9h-9z"/><path d="M15 3.5A9 9 0 0 1 20.5 9H15z"/></svg>',
    ausente: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.2"/><path d="M6 20c0-3.3 2.7-6 6-6s6 2.7 6 6M4 4l16 16"/></svg>',
    doc: '<svg viewBox="0 0 24 24"><path d="M6 2h9l5 5v15H6zM14 2v6h6M9 13h8M9 17h8"/></svg>',
    ampulheta: '<svg viewBox="0 0 24 24"><path d="M6 2h12M6 22h12M7 2c0 6 10 6 10 10S7 16 7 22M17 2c0 6-10 6-10 10s10 4 10 10"/></svg>',
    trofeu: '<svg viewBox="0 0 24 24"><path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4"/></svg>',
    barras: '<svg viewBox="0 0 24 24"><path d="M5 20V12M12 20V5M19 20v-9"/></svg>',
    pino: '<svg viewBox="0 0 24 24"><path d="M12 22s7-6.3 7-12a7 7 0 1 0-14 0c0 5.7 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></svg>',
    relogio: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  };

  let manifesto = null, desenhado = null, mapaGeo = null;
  const cache = new Map();

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

  // ---------- cabeçalho e KPIs ----------
  function cabecalho(abr, res) {
    $("#cab-sigla").textContent = abr === "zz" ? "EX" : abr.toUpperCase();
    $("#cab-titulo").textContent = NOMES[abr] + " 2026 — 2º Turno";
    $("#cab-hora").textContent = dataHora(res.fonte.totalizado_tse);
    document.querySelectorAll(".menu a").forEach((a) => a.classList.toggle("ativo", a.dataset.nav === (abr === "br" ? "br" : "estados")));
    document.title = NOMES[abr] + " · " + pc(res.secoes.pct_totalizadas) + " · Central Eleições 2026";
  }
  function kpis(res) {
    const e = res.eleitorado, s = res.secoes;
    const parc = res.situacao.parcial ? '<span class="parcial">parcial</span>' : "";
    const k = (ico, rot, vl, sub) => '<div class="kpi"><div class="kpi-ico">' + ICO[ico] + '</div><div><div class="rot">' + rot + '</div><div class="vl num">' + vl + '</div><div class="sub num">' + sub + "</div></div></div>";
    $("#kpis").innerHTML =
      k("gente", "Eleitorado total", n(e.total), "aptos a votar") +
      k("pizza", "Comparecimento" + parc, pc(e.pct_comparecimento), n(e.comparecimento) + " eleitores") +
      k("ausente", "Abstenção" + parc, pc(e.pct_abstencao), n(e.abstencao) + " eleitores") +
      k("doc", "Seções apuradas", pc(s.pct_totalizadas), n(s.totalizadas) + " de " + n(s.total)) +
      k("ampulheta", "Falta apurar", pc(100 - s.pct_totalizadas), n(s.pendentes) + " seções");
  }

  // ---------- distribuição dos votos apurados ----------
  function distribuicao(res, px) {
    px = px || "dist";
    const Q = (k) => $("#" + px + "-" + k);
    const v = res.votos, d = res.derivados, [a, b] = res.candidatos;
    const tot = v.total || 1;
    Q("total").textContent = n(v.total);
    const segs = [
      { vl: a.votos, cor: COR(a, 0), cls: "" }, { vl: b.votos, cor: COR(b, 1), cls: "" },
      { vl: v.brancos, cls: "s-branco" }, { vl: v.nulos, cls: "s-nulo" },
    ];
    Q("barra").innerHTML = segs.map((s) => {
      const x = s.vl * 100 / tot;
      return '<div class="' + s.cls + '" style="flex-basis:' + x + "%;" + (s.cor ? "background:" + s.cor : "") + '">' + (x >= 7 ? pc(x) : x >= 2.5 ? '<small>' + p1.format(x) + "</small>" : "") + "</div>";
    }).join("");
    const item = (nm, cor, cls, pcv, extra, votos) => '<div class="di"><div class="nm"><i class="' + cls + '" style="' + (cor ? "background:" + cor : "") + '"></i>' + esc(nm) + '</div><div class="pc num">' + pcv + '</div><div class="ex">' + (extra || "") + '</div><div class="vt num">' + n(votos) + " votos</div></div>";
    Q("itens").innerHTML =
      item(a.nome_urna, COR(a, 0), "", p2.format(a.pct_validos) + "%", "dos válidos", a.votos) +
      item(b.nome_urna, COR(b, 1), "", p2.format(b.pct_validos) + "%", "dos válidos", b.votos) +
      item("Brancos", null, "s-branco", pc(v.pct_brancos_sobre_total), "do total", v.brancos) +
      item("Nulos", null, "s-nulo", pc(v.pct_nulos_sobre_total), "do total", v.nulos);
    Q("itens").querySelectorAll(".s-branco").forEach((i) => (i.style.background = "var(--branco)"));
    Q("itens").querySelectorAll(".s-nulo").forEach((i) => (i.style.background = "var(--nulo)"));
    const lider = res.candidatos.find((c) => c.numero === d.lider);
    (px === "dist" ? $("#dif") : Q("dif")).innerHTML = '<div class="t">Diferença atual' + (lider ? " · " + esc(lider.nome_urna.split(" ")[0]) : "") + '</div><div class="v num">' + (d.lider ? "+" : "") + p1.format(d.diferenca_pp_validos) + ' p.p.</div><div class="s num">(' + n(d.diferenca_votos) + " votos) · calculado</div>";
  }

  // ---------- participação ----------
  function participacao(res) {
    const e = res.eleitorado, s = res.secoes;
    $("#part-sub").textContent = "Nas seções já apuradas de " + NOMES[res.abrangencia.cd] + " (" + n(e.apurado) + " de " + n(e.total) + " eleitores)";
    $("#part-barra").innerHTML =
      '<div class="s-ouro" style="flex-basis:' + e.pct_comparecimento + '%">Compareceram<span class="num">' + pc(e.pct_comparecimento) + " <small>(" + n(e.comparecimento) + ")</small></span></div>" +
      '<div class="s-abst" style="flex-basis:' + e.pct_abstencao + '%">Abstenção<span class="num">' + pc(e.pct_abstencao) + " <small>(" + n(e.abstencao) + ")</small></span></div>";
  }
  function andamento(res, alvo) {
    const s = res.secoes;
    const falta = 100 - s.pct_totalizadas;
    $(alvo).innerHTML =
      '<div class="s-ouro" style="flex-basis:' + s.pct_totalizadas + '%">' + (s.pct_totalizadas >= 18 ? 'Já apurado<span class="num">' + pc(s.pct_totalizadas) + " <small>(" + n(s.totalizadas) + " seções)</small></span>" : "") + "</div>" +
      '<div class="s-pend" style="flex-basis:' + falta + '%">' + (falta >= 18 ? 'Falta apurar<span class="num">' + pc(falta) + " <small>(" + n(s.pendentes) + ")</small></span>" : "") + "</div>";
  }

  // ---------- mapa do Brasil preenchendo ----------
  async function carregaMapa() {
    if (mapaGeo) return mapaGeo;
    const r = await fetch("assets/mapa-br.json", { cache: "force-cache" });
    mapaGeo = await r.json();
    return mapaGeo;
  }
  // botões do mapa: cada um liga/desliga uma faixa; a faixa desligada some e o resto volta a somar 100%
  const OPT = { brancos: true, nulos: true, abst: true, pct: false };
  try { Object.assign(OPT, JSON.parse(localStorage.getItem("eleicoes-mapa-v2") || "{}")); } catch (e) {}
  let ultMapa = null;
  function enche(r) {
    // eleitorado da UF = Lula + Flávio + brancos + nulos + abstenção + não apurado (partição exata)
    const [a, b] = r.candidatos, v = r.votos;
    const pend = Math.max(0, r.eleitorado.total - r.eleitorado.apurado);
    const seg = [[COR(a, 0), a.votos], [COR(b, 1), b.votos]];
    if (OPT.brancos) seg.push(["var(--branco)", v.brancos]);
    if (OPT.nulos) seg.push(["var(--nulo)", v.nulos]);
    if (OPT.abst) seg.push(["var(--abst-on)", r.eleitorado.abstencao]);
    seg.push(["var(--pend)", pend]);
    const base = seg.reduce((t, x) => t + x[1], 0) || 1;
    let x = 0;
    return seg.map(([c, q]) => { const i = x; x += q * 100 / base; return [c, i, Math.min(100, x)]; });
  }
  async function mapa(abr, ufs) {
    ultMapa = [abr, ufs];
    const g = await carregaMapa();
    $("#mapa-tit").textContent = "Mapa do Brasil";
    let defs = "", caminhos = "", rotulos = "";
    for (const uf of UFS) {
      const u = g.ufs[uf]; if (!u) continue;
      const r = ufs[uf];
      let fill = "var(--pend)";
      if (r && r.votos.total) {
        const st = enche(r).map(([c, i, f]) => { return '<stop offset="' + i.toFixed(2) + '%" stop-color="' + c + '"/><stop offset="' + f.toFixed(2) + '%" stop-color="' + c + '"/>'; }).join("");
        defs += '<linearGradient id="g-' + uf + '" x1="0" x2="1" y1="0" y2="0">' + st + "</linearGradient>";
        fill = "url(#g-" + uf + ")";
      }
      caminhos += '<path class="m-uf' + (uf === abr ? " sel" : "") + '" data-uf="' + uf + '" d="' + u.d + '" fill="' + fill + '"><title>' + NOMES[uf] + "</title></path>";
      if (OPT.pct && r && r.votos.total && !SEM_SIGLA.includes(uf)) {
        const [a, b] = r.candidatos;
        rotulos += '<text x="' + u.cx + '" y="' + (u.cy - 8) + '">' + uf.toUpperCase() + '</text><text class="pc" x="' + u.cx + '" y="' + (u.cy + 12) + '">' + p1.format(a.pct_validos) + '</text><text class="pc" x="' + u.cx + '" y="' + (u.cy + 30) + '">' + p1.format(b.pct_validos) + "</text>";
      } else if (!SEM_SIGLA.includes(uf)) rotulos += '<text x="' + u.cx + '" y="' + (u.cy + 6) + '">' + uf.toUpperCase() + "</text>";
    }
    $("#mapa").innerHTML = '<svg class="mapa-svg" viewBox="' + g.viewBox + '" role="img" aria-label="Mapa do Brasil: cada estado se preenche com os votos apurados"><defs>' + defs + "</defs>" + caminhos + '<g class="rotulos">' + rotulos + "</g></svg>";
    const svg = $("#mapa svg"); const bb = svg.getBBox();
    svg.setAttribute("viewBox", [bb.x - 6, bb.y - 6, bb.width + 12, bb.height + 12].join(" "));
    const sel = svg.querySelector(".sel"); if (sel) svg.insertBefore(sel, svg.querySelector(".rotulos"));

    const ref = Object.values(ufs).find((r) => r && r.candidatos) || null;
    const cands = ref ? ref.candidatos : [];
    $("#mapa-leg").innerHTML = cands.map((c, i) => '<span><i style="background:' + COR(c, i) + '"></i>' + esc(c.nome_urna) + "</span>").join("") +
      (OPT.brancos ? '<span><i style="background:var(--branco)"></i>Brancos</span>' : "") + (OPT.nulos ? '<span><i style="background:var(--nulo)"></i>Nulos</span>' : "") + (OPT.abst ? '<span><i style="background:var(--abst-on)"></i>Abstenção</span>' : "") +
'<span><i style="background:var(--pend)"></i>Falta apurar</span>' +
      (OPT.pct ? '<span>Números: % dos válidos ('+ esc((cands[0]||{}).nome_urna||'') +' em cima, '+ esc((cands[1]||{}).nome_urna||'') +' embaixo)</span>' : "");
    document.querySelectorAll("#map-opts button").forEach((bt) => bt.setAttribute("aria-pressed", OPT[bt.dataset.opt]));
  }

  // ---------- evolução ----------
  let ultGraf = null;
  function grafico(res, hist) {
    ultGraf = [res, hist];
    const pts = hist.pontos.filter((x) => x.votos_total > 0 && x.totalizado_tse);
    const [a, b] = res.candidatos;
    $("#evo-leg").innerHTML = '<span><i style="background:' + COR(a, 0) + '"></i>' + esc(a.nome_urna) + '</span><span><i style="background:' + COR(b, 1) + '"></i>' + esc(b.nome_urna) + '</span><span><i class="trac"></i>% de seções apuradas</span>';
    const el = $("#grafico");
    if (pts.length < 2) { el.innerHTML = '<p style="color:var(--mut)">A evolução aparece depois da segunda atualização.</p>'; return; }
    const W = Math.max(320, Math.round(el.clientWidth || 600)), H = W < 500 ? 220 : 250, m = { l: 40, r: 64, t: 12, b: 26 };
    const t = (x) => new Date(x.totalizado_tse).getTime();
    const t0 = t(pts[0]), t1 = t(pts[pts.length - 1]) || t0 + 1;
    const X = (x) => m.l + (t(x) - t0) / ((t1 - t0) || 1) * (W - m.l - m.r);
    const Y = (v) => m.t + (1 - v / 100) * (H - m.t - m.b);
    let g = "";
    for (let y = 0; y <= 100; y += 20) g += '<line class="grade-l" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(y) + '" y2="' + Y(y) + '"/><text x="' + (m.l - 6) + '" y="' + (Y(y) + 4) + '" text-anchor="end">' + y + "%</text>";
    const passos = 4;
    for (let k = 0; k <= passos; k++) {
      const tt = t0 + (t1 - t0) * k / passos, d = new Date(tt);
      const hh = String(d.getUTCHours() - 3 < 0 ? d.getUTCHours() + 21 : d.getUTCHours() - 3).padStart(2, "0") + ":" + String(d.getUTCMinutes()).padStart(2, "0");
      g += '<text x="' + (m.l + (W - m.l - m.r) * k / passos) + '" y="' + (H - 6) + '" text-anchor="middle">' + hh + "</text>";
    }
    const linha = (f, cor, tr) => '<path d="' + pts.map((x, k) => (k ? "L" : "M") + X(x).toFixed(1) + "," + Y(f(x)).toFixed(1)).join("") + '" style="fill:none;stroke:' + cor + ';stroke-width:' + (tr ? 1.8 : 2.4) + (tr ? ";stroke-dasharray:6 5" : "") + ';stroke-linejoin:round"/>';
    const fim = pts[pts.length - 1];
    const tag = (v, yp, cor) => '<g class="tag"><rect x="' + (W - m.r + 6) + '" y="' + (yp - 10) + '" width="54" height="20" rx="4" style="fill:' + cor + '"/><text x="' + (W - m.r + 33) + '" y="' + (yp + 4) + '" text-anchor="middle" style="fill:#0b0b0e;font:700 11px Sora">' + pc(v) + "</text></g>";
    // etiquetas sem sobreposição: ordena por altura e afasta no mínimo 22px
    const afasta = (lst) => { lst.sort((u, w) => u.y - w.y); for (let k = 1; k < lst.length; k++) if (lst[k].y - lst[k - 1].y < 22) lst[k].y = lst[k - 1].y + 22; return lst; };
    // desloca etiquetas que se sobrepõem
    let ya = fim.pct_validos[a.numero], yb = fim.pct_validos[b.numero], ys = fim.pct_secoes;
    el.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Evolução da apuração">' + g +
      linha((x) => x.pct_secoes, "var(--ouro)", true) + linha((x) => x.pct_validos[a.numero], COR(a, 0)) + linha((x) => x.pct_validos[b.numero], COR(b, 1)) +
      '<circle cx="' + X(fim) + '" cy="' + Y(ya) + '" r="4" style="fill:' + COR(a, 0) + '"/><circle cx="' + X(fim) + '" cy="' + Y(yb) + '" r="4" style="fill:' + COR(b, 1) + '"/>' +
      afasta([{ v: ys, y: Y(ys), c: "var(--ouro)" }, { v: ya, y: Y(ya), c: COR(a, 0) }, { v: yb, y: Y(yb), c: COR(b, 1) }]).map((o) => tag(o.v, o.y, o.c)).join("") +
      '<line id="mira" stroke="var(--mut)" y1="' + m.t + '" y2="' + (H - m.b) + '" x1="-9" x2="-9"/><rect id="alvo" x="' + m.l + '" y="0" width="' + (W - m.l - m.r) + '" height="' + H + '" fill="transparent"/></svg>';
    const svg = el.querySelector("svg"), dica = $("#dica");
    $("#alvo").addEventListener("pointermove", (ev) => {
      const r = svg.getBoundingClientRect(), xv = (ev.clientX - r.left) / r.width * W;
      let best = pts[0]; for (const x of pts) if (Math.abs(X(x) - xv) < Math.abs(X(best) - xv)) best = x;
      $("#mira").setAttribute("x1", X(best)); $("#mira").setAttribute("x2", X(best));
      dica.innerHTML = '<div class="t">' + hora(best.totalizado_tse) + '</div><div class="r"><span>' + esc(a.nome_urna) + "</span><b>" + p2.format(best.pct_validos[a.numero]) + '%</b></div><div class="r"><span>' + esc(b.nome_urna) + "</span><b>" + p2.format(best.pct_validos[b.numero]) + '%</b></div><div class="r"><span>Seções apuradas</span><b>' + pc(best.pct_secoes) + "</b></div>";
      dica.hidden = false; dica.style.left = Math.min(ev.clientX + 14, innerWidth - 210) + "px"; dica.style.top = ev.clientY + 14 + "px";
    });
    $("#alvo").addEventListener("pointerleave", () => { dica.hidden = true; $("#mira").setAttribute("x1", -9); $("#mira").setAttribute("x2", -9); });
  }

  // ---------- resumo ----------
  function resumo(abr, res, ufs) {
    const d = res.derivados, lider = res.candidatos.find((c) => c.numero === d.lider);
    const comDados = UFS.filter((u) => ufs[u] && ufs[u].votos.total).length;
    const rc = (ico, t, v, larga) => '<div class="rc' + (larga ? " larga" : "") + '">' + ICO[ico] + '<div style="min-width:0"><div class="t">' + t + '</div><div class="v">' + v + "</div></div></div>";
    $("#res-cards").innerHTML =
      rc("trofeu", "Liderança", lider ? '<span style="color:' + COR(lider, res.candidatos.indexOf(lider)) + '">' + esc(lider.nome_urna) + "</span>" : "Empate") +
      rc("barras", "Diferença", (d.lider ? "+" : "") + p1.format(d.diferenca_pp_validos) + " p.p.") +
      rc("pino", abr === "br" ? "Estados com dados" : "Seções apuradas", abr === "br" ? comDados + " / 27" : n(res.secoes.totalizadas) + " / " + n(res.secoes.total)) +
      rc("relogio", "Última atualização oficial", hora(res.fonte.totalizado_tse), true) +
      rc("doc", "Fonte", "TSE");
    const [a, b] = res.candidatos;
    $("#res-tab thead").innerHTML = "<tr><th>Estado</th><th>Seções apuradas</th><th>" + esc(a.nome_urna.split(" ")[0]) + "</th><th>" + esc(b.nome_urna.split(" ")[0]) + "</th><th>Brancos</th><th>Nulos</th></tr>";
    const lista = UFS.concat(["zz"]).map((u) => ufs[u]).filter(Boolean);
    $("#res-tab tbody").innerHTML = lista.map((r) => {
      const [ca, cb] = r.candidatos, m = r.derivados.lider;
      return '<tr data-uf="' + r.abrangencia.cd + '"' + (r.abrangencia.cd === abr ? ' class="sel"' : "") + '><td>' + esc(r.abrangencia.nome) + "</td><td>" + pc(r.secoes.pct_totalizadas) + " <small style=\"color:var(--mut)\">(" + n(r.secoes.totalizadas) + ")</small></td>" +
        '<td class="' + (m === ca.numero ? "ma c" + ca.numero : "") + '">' + pc(ca.pct_validos) + '</td><td class="' + (m === cb.numero ? "ma c" + cb.numero : "") + '">' + pc(cb.pct_validos) + "</td><td>" + pc(r.votos.pct_brancos_sobre_total) + "</td><td>" + pc(r.votos.pct_nulos_sobre_total) + "</td></tr>";
    }).join("");
    const f = res.fonte;
    auditoria(res);
    $("#fonte-linha").innerHTML = "Versão " + res.versao + " · coletado " + hora(f.coletado_em) + " · sha256 <code>" + esc((f.sha256_bruto || "").slice(0, 12)) + "…</code>" + (f.tipo !== "oficial" ? " · <b>SIMULAÇÃO — números ilustrativos</b>" : " · fonte: TSE");
  }

  // ---------- fonte e auditoria: o dado da tela, com link para o arquivo do TSE ----------
  function auditoria(res) {
    const f = res.fonte, of = f.tipo === "oficial";
    const lin = (k, v) => "<dt>" + k + "</dt><dd>" + v + "</dd>";
    const url = /^https:\/\/resultados\.tse\.jus\.br\//.test(f.url || "") ? f.url : "";
    $("#aud-dado").innerHTML =
      lin("Abrangência", esc(res.abrangencia.nome)) +
      lin("Tipo", of ? "Oficial — TSE" : "<b>SIMULAÇÃO</b> — números ilustrativos") +
      lin("Arquivo de origem", url ? '<a href="' + esc(url) + '" target="_blank" rel="noopener"><code>' + esc(url.replace("https://resultados.tse.jus.br/", "")) + "</code></a>" : "—") +
      lin("Totalizado pelo TSE", dataHora(f.totalizado_tse)) +
      lin("Arquivo gerado pelo TSE", dataHora(f.gerado_tse)) +
      lin("Coletado pelo INEMA", dataHora(f.coletado_em)) +
      lin("Versão INEMA", esc(String(res.versao))) +
      lin("Impressão digital (sha256)", "<code>" + esc(f.sha256_bruto || "—") + "</code>");
  }

  function estadoVivo() {
    if (!manifesto) return;
    const el = $("#vivo"), idade = Date.now() - new Date(manifesto.publicado_em).getTime();
    let est = "vivo", txt = "Ao vivo";
    if (manifesto.situacao === "finalizada") { est = "final"; txt = "Apuração encerrada"; }
    else if (manifesto.situacao === "aguardando") { est = "carregando"; txt = "Aguardando apuração"; }
    else if (idade > ATRASO_MS) { est = "atrasado"; txt = "Sem novidade há " + Math.round(idade / 60000) + " min"; }
    el.dataset.estado = est; el.querySelector("span").textContent = txt;
  }

  async function desenha(forcar) {
    const abr = abrAtual(), chave = manifesto.versao + "|" + abr;
    if (!forcar && chave === desenhado) return;
    const info = manifesto.abrangencias[abr];
    if (!info) return;
    const sim = manifesto.fonte.tipo !== "oficial";
    $("#faixa-sim").hidden = !sim; $("#marca-sim").hidden = !sim;
    if (sim) $("#faixa-sim").innerHTML = "<strong>SIMULAÇÃO</strong>" + esc((manifesto.fonte.nota || "Números ilustrativos.").replace(/^Simulação: /, ""));
    $("#cab-tipo").textContent = sim ? "Simulação" : "Presidente · dados oficiais do TSE";
    const lista = UFS.concat(["zz"]).filter((u) => manifesto.abrangencias[u]);
    const [res, hist, ...rs] = await Promise.all([pega(info.arquivo, true), pega(manifesto.historico[abr], false), ...lista.map((u) => pega(manifesto.abrangencias[u].arquivo, true))]);
    const ufs = {}; lista.forEach((u, i) => (ufs[u] = rs[i]));
    const brRes = abr === "br" ? res : await pega(manifesto.abrangencias.br.arquivo, true);
    cabecalho(abr, res); kpis(res); distribuicao(brRes); andamento(brRes, "#apur-barra"); participacao(res); grafico(res, hist); resumo(abr, res, ufs);
    const pUf = $("#p-uf");
    pUf.hidden = abr === "br";
    if (abr !== "br") { $("#uf-nome").textContent = NOMES[abr]; distribuicao(res, "uf"); andamento(res, "#uf-apur"); }
    linksMunicipios(abr);
    await mapa(abr, ufs);
    if (desenhado && desenhado.split("|")[1] === abr) document.querySelectorAll(".p-dist,.kpis").forEach((x) => { x.classList.add("pisca"); setTimeout(() => x.classList.remove("pisca"), 1500); });
    desenhado = chave;
  }

  // Municípios (sistema à parte): menu e botão do card do estado levam ao mesmo estado lá
  const MUNICIPIOS = window.MUNICIPIOS_URL || "https://municipios.inema.club/";
  function linksMunicipios(abr) {
    const sim = new URLSearchParams(location.search).has("sim") ? "?sim=1" : "";
    const alvo = MUNICIPIOS + sim + (abr && abr !== "br" && abr !== "zz" ? "#" + abr : "");
    document.querySelectorAll('a[data-nav="mun"]').forEach((a) => (a.href = alvo));
    const b = $("#uf-mun");
    if (b) { b.href = alvo; b.hidden = abr === "zz"; b.querySelector("span").textContent = "Ver os municípios de " + (NOMES[abr] || ""); }
  }

  async function ciclo() {
    try {
      const m = await pega("latest.json", false);
      if (m.tipo !== "manifesto") throw new Error("manifesto inválido");
      if (!manifesto || m.versao >= manifesto.versao) manifesto = m;
      $("#faixa-erro").hidden = true;
      await desenha(false);
    } catch (e) {
      $("#faixa-erro").hidden = false;
      $("#faixa-erro").textContent = "Não consegui atualizar agora (" + e.message + "). Mostrando o último dado válido; tento de novo em 15 s.";
    }
    estadoVivo();
  }

  // dica do mapa e cliques
  document.addEventListener("click", (ev) => {
    const a = ev.target.closest("[data-uf]");
    if (a) { location.hash = "#/uf/" + a.dataset.uf; scrollTo({ top: 0, behavior: "smooth" }); }
  });
  document.addEventListener("pointermove", (ev) => {
    const pth = ev.target.closest && ev.target.closest(".m-uf");
    const dica = $("#dica");
    if (!pth) { if (!ev.target.closest || !ev.target.closest("#grafico")) dica.hidden = true; return; }
    const uf = pth.dataset.uf, info = manifesto && manifesto.abrangencias[uf], r = info && cache.get(info.arquivo);
    if (!r) { dica.innerHTML = '<div class="t">' + NOMES[uf] + '</div><div class="r"><span>sem votos apurados</span></div>'; }
    else {
      const [a, b] = r.candidatos;
      dica.innerHTML = '<div class="t">' + NOMES[uf] + " (" + uf.toUpperCase() + ')</div><div class="r"><span>' + esc(a.nome_urna) + "</span><b>" + pc(a.pct_validos) + '</b></div><div class="r"><span>' + esc(b.nome_urna) + "</span><b>" + pc(b.pct_validos) + '</b></div><div class="r"><span>Brancos</span><b>' + pc(r.votos.pct_brancos_sobre_total) + '</b></div><div class="r"><span>Nulos</span><b>' + pc(r.votos.pct_nulos_sobre_total) + '</b></div><div class="r"><span>Seções apuradas</span><b>' + pc(r.secoes.pct_totalizadas) + "</b></div>";
    }
    dica.hidden = false; dica.style.left = Math.min(ev.clientX + 16, innerWidth - 210) + "px"; dica.style.top = ev.clientY + 16 + "px";
  });
  addEventListener("hashchange", () => manifesto && desenha(true));
  $("#map-opts").addEventListener("click", (ev) => {
    const bt = ev.target.closest("button"); if (!bt) return;
    OPT[bt.dataset.opt] = !OPT[bt.dataset.opt];
    try { localStorage.setItem("eleicoes-mapa-v2", JSON.stringify(OPT)); } catch (e) {}
    if (ultMapa) mapa(ultMapa[0], ultMapa[1]);
  });
  let tRes; addEventListener("resize", () => { clearTimeout(tRes); tRes = setTimeout(() => ultGraf && grafico(ultGraf[0], ultGraf[1]), 200); });

  ciclo();
  setInterval(ciclo, INTERVALO);
  setInterval(estadoVivo, 5000);
})();
