/* Municípios — Eleições 2026 INEMA.
   Lê data/latest.json (manifesto) e data/uf/<uf>/vNNNNN.json (todas as cidades do estado),
   e o desenho do IBGE em assets/malha/<uf>.json. Só carrega o estado escolhido.
   Cinza = nenhuma seção apurada. Cor = quem lidera na cidade; mais forte = mais apurada. */
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const q = new URLSearchParams(location.search);
  const DADOS = /^[a-z0-9-]+$/.test(q.get("dados") || "") ? q.get("dados") : "data";
  const INTERVALO = 15000;
  const NOMES = { ac: "Acre", al: "Alagoas", am: "Amazonas", ap: "Amapá", ba: "Bahia", ce: "Ceará", df: "Distrito Federal",
    es: "Espírito Santo", go: "Goiás", ma: "Maranhão", mg: "Minas Gerais", ms: "Mato Grosso do Sul", mt: "Mato Grosso",
    pa: "Pará", pb: "Paraíba", pe: "Pernambuco", pi: "Piauí", pr: "Paraná", rj: "Rio de Janeiro", rn: "Rio Grande do Norte",
    ro: "Rondônia", rr: "Roraima", rs: "Rio Grande do Sul", sc: "Santa Catarina", se: "Sergipe", sp: "São Paulo", to: "Tocantins" };
  const UFS = Object.keys(NOMES);
  const n = new Intl.NumberFormat("pt-BR");
  const p1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const p2 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const semAcento = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const COR = (num) => (num === "13" ? "var(--c13)" : num === "22" ? "var(--c22)" : "var(--coutro)");

  // ---------- simulação no navegador (?sim=1): nomes fictícios, números inventados ----------
  const SIM = q.has("sim");
  const SIM_T = 90000, SIM_PAUSA = 10000, SIM_PASSO = 1500; // 0% → 100% em 90 s, para 10 s e recomeça
  const CANDS_SIM = [{ numero: "13", nome_urna: "CANDIDATO A", partido: "PARTIDO A" }, { numero: "22", nome_urna: "CANDIDATO B", partido: "PARTIDO B" }];
  const SIM_NOTA = "Simulação acelerada com nomes fictícios e números inventados a partir do 1º turno. Não é resultado.";
  let simBase = null, simT0 = 0;
  const h32 = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967296; };
  const simTempo = () => Math.min((Date.now() - simT0) % (SIM_T + SIM_PAUSA), SIM_T);
  function simCidade(cdi, a, t, nm) {
    const [te, ts, A, B, VB, VN] = a, peso = Math.log10(Math.max(10, te));
    const ini = h32(cdi) * 0.55 * SIM_T * (0.6 + peso / 12), dur = SIM_T * (0.08 + h32(cdi + "d") * 0.17) * (0.5 + peso / 6);
    const f = t >= SIM_T ? 1 : Math.min(1, Math.max(0, (t - ini) / dur));
    const st = f >= 1 ? ts : Math.floor(ts * f), fr = st / ts;
    const va = Math.round(A * fr), vb = Math.round(B * fr), br = Math.round(VB * fr), nu = Math.round(VN * fr);
    const vv = va + vb, tv = vv + br + nu, esa = Math.max(tv, Math.round(te * fr));
    return { cd: "", cdi, nm: nm || cdi, te, ts, st, pst: Math.round(fr * 10000) / 100,
      and: st === 0 ? "aguardando" : st === ts ? "finalizada" : "em_andamento", ht: st ? new Date().toISOString() : null,
      tv, vv, vb: br, vn: nu, comp: tv, abst: esa - tv, c: { 13: va, 22: vb },
      p: { 13: vv ? Math.round((va / vv) * 10000) / 100 : 0, 22: vv ? Math.round((vb / vv) * 10000) / 100 : 0 },
      lider: va > vb ? "13" : vb > va ? "22" : null };
  }
  function simUF(uf, t, comNomes) {
    const malha = E.malhas[uf], cid = {};
    let ts = 0, st = 0, te = 0, ini = 0, comp = 0; const lid = {};
    const sc = { votos: { 13: 0, 22: 0 }, validos: 0, total: 0, brancos: 0, nulos: 0 };
    for (const [cdi, a] of Object.entries(simBase[uf])) {
      const r = simCidade(cdi, a, t, comNomes && malha && malha.mun[cdi] && malha.mun[cdi].nm);
      if (comNomes) cid[cdi] = r;
      ts += r.ts; st += r.st; te += r.te;
      sc.votos[13] += r.c[13]; sc.votos[22] += r.c[22]; sc.validos += r.vv; sc.total += r.tv; sc.brancos += r.vb; sc.nulos += r.vn;
      if (r.st) { ini++; if (r.lider) lid[r.lider] = (lid[r.lider] || 0) + 1; }
      if (r.st === r.ts) comp++;
    }
    const n = Object.keys(simBase[uf]).length, pst = ts ? Math.round((st / ts) * 10000) / 100 : 0;
    return { uf, versao: Math.floor(t / SIM_PASSO) + 1, publicado_em: new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().replace("Z", ""),
      fonte: { tipo: "simulacao", indice: "#" }, candidatos: CANDS_SIM, bloqueadas: [],
      estado: { ts, st, pst, te, and: st === ts ? "finalizada" : st ? "em_andamento" : "aguardando" },
      resumo: { cidades: n, iniciadas: ini, completas: comp, lider_cidades: lid, soma_cidades: sc }, cidades: cid };
  }
  function simManifesto(t) {
    const ufs = {};
    for (const uf of UFS) { const d = simUF(uf, t, false); ufs[uf] = { versao: d.versao, cidades: d.resumo.cidades, iniciadas: d.resumo.iniciadas, completas: d.resumo.completas }; }
    return { fonte: { tipo: "simulacao", nota: SIM_NOTA }, ufs };
  }

  const E = { man: null, uf: null, dados: null, malha: null, malhas: {}, sel: null, modo: "maiores", ultimoOk: 0, vb: null, vb0: null };

  async function pega(url, semCache) {
    const r = await fetch(url, semCache ? { cache: "no-store" } : {});
    if (!r.ok) throw new Error(url + " → " + r.status);
    return r.json();
  }

  // ---------- estado escolhido ----------
  function ufDoHash() {
    const h = location.hash.replace(/^#/, "").split("/");
    const uf = UFS.includes(h[0]) ? h[0] : null;
    return { uf, cdi: h[1] && /^\d{7}$/.test(h[1]) ? h[1] : null };
  }

  function chips() {
    $("#ufs").innerHTML = UFS.map((u) => {
      const i = E.man && E.man.ufs[u];
      const fr = i && i.cidades ? (i.iniciadas / i.cidades) * 100 : 0;
      return '<button type="button" data-uf="' + u + '" aria-pressed="' + (u === E.uf) + '" title="' + esc(NOMES[u]) +
        (i ? " — " + i.iniciadas + " de " + i.cidades + " cidades com apuração" : "") + '">' + u.toUpperCase() +
        '<i style="width:' + fr.toFixed(1) + '%"></i></button>';
    }).join("");
  }

  async function abreUF(uf, cdi) {
    if (uf !== E.uf) {
      E.uf = uf; E.sel = null; E.dados = null;
      $("#p-cidade").hidden = true;
      chips();
      $("#cab-sigla").textContent = uf.toUpperCase();
      $("#cab-titulo").textContent = NOMES[uf] + " — Municípios";
      if (!E.malhas[uf]) E.malhas[uf] = await pega("assets/malha/" + uf + ".json");
      E.malha = E.malhas[uf];
      desenha();
      await atualizaUF(true);
      preencheBusca();
    }
    if (cdi) seleciona(cdi, true);
  }

  // ---------- mapa ----------
  function desenha() {
    const svg = $("#mapa-mun");
    const m = E.malha;
    svg.setAttribute("viewBox", m.viewBox);
    E.vb0 = m.viewBox.split(" ").map(Number);
    E.vb = E.vb0.slice();
    const ord = Object.entries(m.mun).sort((a, b) => b[1].a - a[1].a); // maiores embaixo: enclaves ficam visíveis
    svg.innerHTML = ord.map(([cdi, c]) => '<path data-cdi="' + cdi + '" d="' + c.d + '" class="sem"/>').join("");
    $("#mapa-tit").textContent = "Mapa dos municípios — " + NOMES[E.uf];
  }

  function corCidade(r) {
    if (!r || !r.st) return null;
    return r.lider ? COR(r.lider) : "var(--empate)";
  }

  function pinta() {
    if (!E.dados) return;
    const cid = E.dados.cidades;
    for (const p of $("#mapa-mun").children) {
      const r = cid[p.dataset.cdi];
      const c = corCidade(r);
      if (!c) { p.classList.add("sem"); p.style.fill = ""; p.style.fillOpacity = ""; continue; }
      p.classList.remove("sem");
      p.style.fill = c;
      p.style.fillOpacity = (0.35 + 0.65 * Math.min(100, r.pst) / 100).toFixed(2);
    }
    const cands = E.dados.candidatos;
    const principais = cands.filter((c) => c.numero === "13" || c.numero === "22");
    const outros = cands.length > principais.length;
    $("#mapa-leg").innerHTML = principais.map((c) => '<span><i style="background:' + COR(c.numero) + '"></i>' + esc(c.nome_urna) + " lidera</span>").join("") +
      (outros ? '<span><i style="background:var(--coutro)"></i>Outro candidato lidera</span>' : "") +
      '<span><i style="background:var(--empate)"></i>Empate</span>' +
      '<span><i style="background:var(--semdado)"></i>Sem apuração</span>' +
      '<span>Pouco apurado <i class="escala" style="background:linear-gradient(90deg,rgba(229,72,77,.35),rgba(229,72,77,1))"></i> 100%</span>';
  }

  // zoom e arrasto (viewBox)
  function aplicaVB() {
    $("#mapa-mun").setAttribute("viewBox", E.vb.map((x) => x.toFixed(1)).join(" "));
    $("#mapa-caixa").classList.toggle("zoomado", E.vb[2] < E.vb0[2] * 0.98);
  }
  function zoom(f, cx, cy) {
    const [x, y, w, h] = E.vb;
    const nw = Math.min(E.vb0[2] * 1.2, Math.max(E.vb0[2] / 40, w / f));
    const nh = (nw / w) * h;
    cx = cx == null ? x + w / 2 : cx; cy = cy == null ? y + h / 2 : cy;
    E.vb = [cx - ((cx - x) * nw) / w, cy - ((cy - y) * nh) / h, nw, nh];
    aplicaVB();
  }
  function pontoSVG(ev) {
    const svg = $("#mapa-mun"), r = svg.getBoundingClientRect();
    const [x, y, w, h] = E.vb, s = Math.max(w / r.width, h / r.height);
    const ox = (r.width * s - w) / 2, oy = (r.height * s - h) / 2;
    return [x - ox + (ev.clientX - r.left) * s, y - oy + (ev.clientY - r.top) * s, s];
  }
  function ligaMapa() {
    const svg = $("#mapa-mun");
    let arr = null, moveu = false;
    svg.addEventListener("wheel", (ev) => { ev.preventDefault(); const [px, py] = pontoSVG(ev); zoom(ev.deltaY < 0 ? 1.25 : 0.8, px, py); }, { passive: false });
    svg.addEventListener("pointerdown", (ev) => { arr = { x: ev.clientX, y: ev.clientY, vb: E.vb.slice(), s: pontoSVG(ev)[2] }; moveu = false; });
    window.addEventListener("pointermove", (ev) => {
      if (!arr) return;
      const dx = ev.clientX - arr.x, dy = ev.clientY - arr.y;
      if (!moveu && Math.hypot(dx, dy) < 5) return;
      moveu = true; svg.classList.add("arrasta"); $("#dica").hidden = true;
      E.vb = [arr.vb[0] - dx * arr.s, arr.vb[1] - dy * arr.s, arr.vb[2], arr.vb[3]];
      aplicaVB();
    });
    window.addEventListener("pointerup", () => { arr = null; svg.classList.remove("arrasta"); });
    svg.addEventListener("click", (ev) => {
      if (moveu) return;
      const p = ev.target.closest("path");
      if (p) { seleciona(p.dataset.cdi); if (ev.pointerType !== "mouse") dica(ev, p.dataset.cdi); }
    });
    svg.addEventListener("pointerover", (ev) => { const p = ev.target.closest("path"); if (p && ev.pointerType === "mouse" && !arr) dica(ev, p.dataset.cdi); });
    svg.addEventListener("pointermove", (ev) => { if (ev.pointerType === "mouse" && !arr && ev.target.closest("path")) posDica(ev); });
    svg.addEventListener("pointerleave", () => { $("#dica").hidden = true; });
    document.querySelectorAll(".zoom button").forEach((b) => b.addEventListener("click", () => {
      const z = +b.dataset.z;
      if (z === 0) { E.vb = E.vb0.slice(); aplicaVB(); } else zoom(z > 0 ? 1.5 : 1 / 1.5);
    }));
  }

  // ---------- dica ----------
  function linhasCands(r, max) {
    const cands = E.dados.candidatos.slice().sort((a, b) => (r.c[b.numero] || 0) - (r.c[a.numero] || 0));
    return cands.slice(0, max);
  }
  function dica(ev, cdi) {
    const r = E.dados && E.dados.cidades[cdi];
    const nm = (r && r.nm) || (E.malha.mun[cdi] && E.malha.mun[cdi].nm) || cdi;
    let h = '<div class="t">' + esc(nm) + "</div>";
    if (!r || !r.st) h += '<div class="r">Ainda sem seções apuradas</div>' + (r ? '<div class="r">Eleitorado <b>' + n.format(r.te) + "</b></div>" : "");
    else {
      h += '<div class="r">Seções apuradas <b>' + p2.format(r.pst) + "%</b></div>";
      h += linhasCands(r, 2).map((c) => '<div class="r"><span style="color:' + COR(c.numero) + '">' + esc(c.nome_urna) + "</span><b>" + p2.format(r.p[c.numero] || 0) + "%</b></div>").join("");
      h += '<div class="r">Eleitorado <b>' + n.format(r.te) + "</b></div>";
    }
    const d = $("#dica"); d.innerHTML = h; d.hidden = false; posDica(ev);
  }
  function posDica(ev) {
    const d = $("#dica"), w = d.offsetWidth, h = d.offsetHeight;
    d.style.left = Math.min(window.innerWidth - w - 8, ev.clientX + 14) + "px";
    d.style.top = Math.min(window.innerHeight - h - 8, ev.clientY + 14) + "px";
  }

  // ---------- cidade escolhida ----------
  function seleciona(cdi, centraliza) {
    E.sel = cdi;
    document.querySelectorAll("#mapa-mun path.sel").forEach((p) => p.classList.remove("sel"));
    const p = $('#mapa-mun path[data-cdi="' + cdi + '"]');
    if (p) {
      p.classList.add("sel"); p.parentNode.appendChild(p); // por cima, para a borda aparecer inteira
      if (centraliza) {
        const b = p.getBBox(), lado = Math.max(b.width, b.height, E.vb0[2] / 12) * 3.2;
        const asp = E.vb0[3] / E.vb0[2];
        E.vb = [b.x + b.width / 2 - lado / 2, b.y + b.height / 2 - (lado * asp) / 2, lado, lado * asp];
        aplicaVB();
        p.classList.remove("pisca"); void p.getBBox(); p.classList.add("pisca");
      }
    }
    const novo = "#" + E.uf + "/" + cdi;
    if (location.hash !== novo) history.replaceState(null, "", novo);
    cidade();
    lista();
  }

  function barraCands(r) {
    const cands = linhasCands(r, 99);
    const top = cands.slice(0, 2), resto = cands.slice(2);
    const seg = top.map((c) => [COR(c.numero), r.p[c.numero] || 0, c.nome_urna]);
    const pr = resto.reduce((s, c) => s + (r.p[c.numero] || 0), 0);
    if (pr > 0.05) seg.push(["var(--coutro)", pr, "Outros"]);
    return { top, resto, seg };
  }

  function cidade() {
    const r = E.dados && E.dados.cidades[E.sel];
    const pc = $("#p-cidade");
    if (!E.sel) { pc.hidden = true; return; }
    pc.hidden = false;
    const nm = (r && r.nm) || (E.malha.mun[E.sel] && E.malha.mun[E.sel].nm) || E.sel;
    $("#cid-nome").textContent = nm;
    if (!r) { $("#cid-sub").textContent = "Sem dados do TSE para esta cidade"; return; }
    $("#cid-sub").textContent = n.format(r.te) + " eleitores · " + n.format(r.st) + " de " + n.format(r.ts) + " seções" +
      (r.ht ? " · totalizado às " + r.ht.slice(11, 16) : "");
    $("#cid-pst").textContent = p2.format(r.pst) + "%";
    if (!r.st) {
      $("#cid-barra").innerHTML = "";
      $("#cid-itens").innerHTML = '<div class="di"><div class="vt">Nenhuma seção apurada ainda. A cidade fica cinza no mapa até a primeira apuração.</div></div>';
      $("#cid-ext").innerHTML = "";
      return;
    }
    const { top, seg } = barraCands(r);
    $("#cid-barra").innerHTML = seg.map(([cor, x]) => '<div style="flex-basis:' + x + "%;background:" + cor + '">' + (x >= 9 ? p1.format(x) + "%" : "") + "</div>").join("");
    $("#cid-itens").innerHTML = top.map((c) => '<div class="di"><div class="nm"><i style="background:' + COR(c.numero) + '"></i>' + esc(c.nome_urna) +
      '</div><div class="pc num">' + p2.format(r.p[c.numero] || 0) + '%</div><div class="vt num">' + n.format(r.c[c.numero] || 0) + " votos</div></div>").join("");
    const ext = [["Votos válidos", n.format(r.vv)], ["Brancos", n.format(r.vb)], ["Nulos", n.format(r.vn)],
      ["Comparecimento", n.format(r.comp)], ["Abstenção", n.format(r.abst)], ["Situação", r.and === "finalizada" ? "Finalizada" : r.and === "em_andamento" ? "Em andamento" : "Aguardando"]];
    $("#cid-ext").innerHTML = ext.map(([t, v]) => '<div><div class="t">' + t + '</div><div class="v num">' + v + "</div></div>").join("");
  }

  // ---------- lista das 10 ----------
  function lista() {
    if (!E.dados) return;
    const todas = Object.entries(E.dados.cidades);
    let l, sub;
    if (E.modo === "maiores") { l = todas.sort((a, b) => b[1].te - a[1].te); sub = "As 10 com mais eleitores no estado"; }
    else if (E.modo === "apuradas") { l = todas.filter(([, r]) => r.st > 0).sort((a, b) => b[1].pst - a[1].pst || b[1].te - a[1].te); sub = "Maior % de seções apuradas (empate: a maior primeiro)"; }
    else { l = todas.filter(([, r]) => r.ts && r.st === r.ts).sort((a, b) => b[1].te - a[1].te); sub = n.format(l.length) + " cidades já com 100% das seções apuradas"; }
    $("#lista-sub").textContent = sub;
    const top = l.slice(0, 10);
    if (!top.length) {
      $("#lista").innerHTML = '<li class="vazio">' + (E.modo === "completas" ? "Nenhuma cidade com 100% apurado ainda." : "Nenhuma cidade com apuração ainda.") + "</li>";
      return;
    }
    $("#lista").innerHTML = top.map(([cdi, r], i) => {
      let mini = "", ld = '<span>Sem apuração ainda</span>';
      if (r.st) {
        const { top: t2, seg } = barraCands(r);
        mini = seg.map(([cor, x]) => '<div style="flex-basis:' + x + "%;background:" + cor + '"></div>').join("");
        ld = t2.map((c) => '<span><b style="color:' + COR(c.numero) + '">' + esc(c.nome_urna) + "</b> " + p2.format(r.p[c.numero] || 0) + "%</span>").join("");
      }
      return '<li data-cdi="' + cdi + '"' + (cdi === E.sel ? ' class="sel"' : "") + '><span class="pos">' + (i + 1) + '</span><span class="nm">' + esc(r.nm) +
        "<small>" + n.format(r.te) + ' eleitores</small></span><span class="ap">' + p1.format(r.pst) + '%</span><div class="mini">' + mini + '</div><div class="ld">' + ld + "</div></li>";
    }).join("");
  }

  // ---------- topo ----------
  function kpis() {
    const d = E.dados, e = d.estado || {}, rs = d.resumo;
    const lid = d.candidatos.filter((c) => rs.lider_cidades[c.numero]).sort((a, b) => rs.lider_cidades[b.numero] - rs.lider_cidades[a.numero]).slice(0, 3);
    const k = (rot, vl, sub) => '<div class="kpi"><div class="rot">' + rot + '</div><div class="vl num">' + vl + '</div><div class="sub">' + sub + "</div></div>";
    $("#kpis").innerHTML =
      k("Seções apuradas no estado", e.pst != null ? p2.format(e.pst) + "%" : "—", e.ts ? n.format(e.st) + " de " + n.format(e.ts) + " seções" : "índice do TSE") +
      k("Cidades com apuração", n.format(rs.iniciadas) + "<small>de " + n.format(rs.cidades) + "</small>", "pelo menos 1 seção apurada") +
      k("Cidades 100% apuradas", n.format(rs.completas), rs.cidades ? p1.format((rs.completas / rs.cidades) * 100) + "% das cidades" : "") +
      '<div class="kpi"><div class="rot">Cidades onde cada um lidera</div><div class="vl lid">' +
      (lid.length ? lid.map((c) => '<span><i style="background:' + COR(c.numero) + '"></i>' + n.format(rs.lider_cidades[c.numero]) + "</span>").join("") : "—") +
      '</div><div class="sub">' + (lid.length ? lid.map((c) => esc(c.nome_urna)).join(" · ") : "ainda sem apuração") + "</div></div>";
    $("#cab-hora").textContent = d.publicado_em ? d.publicado_em.slice(11, 19) : "—";
    const f = d.fonte || {};
    $("#fonte").innerHTML = "Fonte: TSE, arquivos públicos de resultados (<a href=\"" + esc(f.indice) + "\" rel=\"noopener\">índice do estado</a>), versão " +
      n.format(d.versao) + ". Mapa: IBGE, malha municipal. Totais por cidade lidos do TSE sem recalcular; contagens de cidades são do INEMA." +
      (d.bloqueadas && d.bloqueadas.length ? " Cidades com conferência pendente (mostram o último valor válido): " + d.bloqueadas.length + "." : "");
  }

  // ---------- votos apurados no estado (soma das cidades) ----------
  function distEstado() {
    const sc = E.dados.resumo.soma_cidades || { votos: {}, validos: 0, total: 0, brancos: 0, nulos: 0 };
    const cands = E.dados.candidatos.slice().sort((a, b) => (sc.votos[b.numero] || 0) - (sc.votos[a.numero] || 0));
    const top = cands.slice(0, 2), outros = cands.slice(2).reduce((t, c) => t + (sc.votos[c.numero] || 0), 0);
    const tot = sc.total || 0, vv = sc.validos || 1;
    $("#dist-total").textContent = n.format(tot);
    $("#dist-sub").textContent = "Soma das " + n.format(E.dados.resumo.iniciadas) + " cidades com apuração · cálculo INEMA";
    if (!tot) {
      $("#dist-barra").innerHTML = ""; $("#dif").innerHTML = "";
      $("#dist-itens").innerHTML = '<div class="di"><div class="vt">Nenhum voto apurado ainda neste estado.</div></div>';
      return;
    }
    const seg = top.map((c) => [COR(c.numero), sc.votos[c.numero] || 0, ""]);
    if (outros) seg.push(["var(--coutro)", outros, ""]);
    seg.push(["", sc.brancos, "s-branco"], ["", sc.nulos, "s-nulo"]);
    $("#dist-barra").innerHTML = seg.map(([cor, v, cls]) => {
      const x = (v * 100) / tot;
      return '<div class="' + cls + '" style="flex-basis:' + x + "%;" + (cor ? "background:" + cor : "") + '">' + (x >= 7 ? p1.format(x) + "%" : x >= 2.5 ? "<small>" + p1.format(x) + "</small>" : "") + "</div>";
    }).join("");
    const item = (nm, cor, pcv, ex, v) => '<div class="di"><div class="nm"><i style="background:' + cor + '"></i>' + esc(nm) + '</div><div class="pc num">' + pcv + '</div><div class="ex">' + ex + '</div><div class="vt num">' + n.format(v) + " votos</div></div>";
    $("#dist-itens").innerHTML = top.map((c) => item(c.nome_urna, COR(c.numero), p2.format(((sc.votos[c.numero] || 0) * 100) / vv) + "%", "dos válidos", sc.votos[c.numero] || 0)).join("") +
      item("Brancos", "var(--branco)", p1.format((sc.brancos * 100) / tot) + "%", "do total", sc.brancos) +
      item("Nulos", "var(--nulo)", p1.format((sc.nulos * 100) / tot) + "%", "do total", sc.nulos);
    const [a, b] = top, va = sc.votos[a.numero] || 0, vb = b ? sc.votos[b.numero] || 0 : 0;
    $("#dif").innerHTML = '<div class="t">Diferença' + (va !== vb ? " · " + esc(a.nome_urna.split(" ")[0]) : "") + '</div><div class="v num">' +
      (va !== vb ? "+" : "") + p1.format(((va - vb) * 100) / vv) + ' p.p.</div><div class="s num">(' + n.format(va - vb) + " votos)</div>";
  }

  // ---------- evolução no estado ----------
  function simHist(uf, t) {
    const pts = [];
    for (let tt = SIM_PASSO; tt <= t + 1; tt += SIM_PASSO * 2) {
      const d = simUF(uf, tt, false), sc = d.resumo.soma_cidades;
      if (!sc.total) continue;
      pts.push({ t: new Date(Date.UTC(2026, 9, 25, 20) + (tt / SIM_T) * 4 * 3600000).toISOString(), pst: d.estado.pst, vt: sc.total,
        pv: { 13: (sc.votos[13] * 100) / (sc.validos || 1), 22: (sc.votos[22] * 100) / (sc.validos || 1) } });
    }
    return { pontos: pts };
  }
  function hhmm(iso) {
    const d = new Date(/Z|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + "-03:00");
    return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" });
  }
  function grafico() {
    const el = $("#grafico"), pts = (E.hist && E.hist.pontos) || [];
    const d = E.dados, sc = d.resumo.soma_cidades || { votos: {} };
    const cands = d.candidatos.slice().sort((a, b) => (sc.votos[b.numero] || 0) - (sc.votos[a.numero] || 0)).slice(0, 2);
    $("#evo-leg").innerHTML = cands.map((c) => '<span><i style="background:' + COR(c.numero) + '"></i>' + esc(c.nome_urna) + "</span>").join("") + '<span><i class="trac"></i>% de seções apuradas</span>';
    if (pts.length < 2) { el.innerHTML = "<p>A evolução aparece depois da segunda atualização com votos.</p>"; return; }
    const W = Math.max(300, Math.round(el.clientWidth || 520)), H = W < 460 ? 200 : 220, m = { l: 36, r: 58, t: 10, b: 24 };
    const tm = (x) => new Date(/Z|[+-]\d\d:\d\d$/.test(x.t) ? x.t : x.t + "-03:00").getTime();
    const t0 = tm(pts[0]), t1 = tm(pts[pts.length - 1]);
    const X = (x) => m.l + ((tm(x) - t0) / (t1 - t0 || 1)) * (W - m.l - m.r);
    const Y = (v) => m.t + (1 - v / 100) * (H - m.t - m.b);
    let g = "";
    for (let y = 0; y <= 100; y += 25) g += '<line class="grade-l" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + Y(y) + '" y2="' + Y(y) + '"/><text x="' + (m.l - 5) + '" y="' + (Y(y) + 4) + '" text-anchor="end">' + y + "%</text>";
    for (let k = 0; k <= 3; k++) g += '<text x="' + (m.l + ((W - m.l - m.r) * k) / 3) + '" y="' + (H - 5) + '" text-anchor="middle">' + hhmm(new Date(t0 + ((t1 - t0) * k) / 3).toISOString()) + "</text>";
    const linha = (f, cor, tr) => '<path d="' + pts.map((x, k) => (k ? "L" : "M") + X(x).toFixed(1) + "," + Y(f(x)).toFixed(1)).join("") + '" style="fill:none;stroke:' + cor + ";stroke-width:" + (tr ? 1.8 : 2.4) + (tr ? ";stroke-dasharray:6 5" : "") + ';stroke-linejoin:round"/>';
    const fim = pts[pts.length - 1];
    const marcas = [{ v: fim.pst, c: "var(--ouro)" }].concat(cands.map((c) => ({ v: fim.pv[c.numero] || 0, c: COR(c.numero) })));
    marcas.forEach((o) => (o.y = Y(o.v)));
    marcas.sort((u, w) => u.y - w.y);
    for (let k = 1; k < marcas.length; k++) if (marcas[k].y - marcas[k - 1].y < 21) marcas[k].y = marcas[k - 1].y + 21;
    const tag = (o) => '<g><rect x="' + (W - m.r + 5) + '" y="' + (o.y - 10) + '" width="50" height="20" rx="4" style="fill:' + o.c + '"/><text x="' + (W - m.r + 30) + '" y="' + (o.y + 4) + '" text-anchor="middle" style="fill:#0b0b0e;font:700 11px Sora">' + p1.format(o.v) + "%</text></g>";
    el.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Evolução da apuração no estado">' + g +
      linha((x) => x.pst, "var(--ouro)", true) + cands.map((c) => linha((x) => x.pv[c.numero] || 0, COR(c.numero))).join("") +
      marcas.map(tag).join("") + '<line id="mira" stroke="var(--mut)" y1="' + m.t + '" y2="' + (H - m.b) + '" x1="-9" x2="-9"/><rect id="alvo" x="' + m.l + '" y="0" width="' + (W - m.l - m.r) + '" height="' + H + '" fill="transparent"/></svg>';
    const svg = el.querySelector("svg"), dc = $("#dica");
    $("#alvo").addEventListener("pointermove", (ev) => {
      const r = svg.getBoundingClientRect(), xv = ((ev.clientX - r.left) / r.width) * W;
      let best = pts[0]; for (const x of pts) if (Math.abs(X(x) - xv) < Math.abs(X(best) - xv)) best = x;
      $("#mira").setAttribute("x1", X(best)); $("#mira").setAttribute("x2", X(best));
      dc.innerHTML = '<div class="t">' + hhmm(best.t) + "</div>" + cands.map((c) => '<div class="r"><span style="color:' + COR(c.numero) + '">' + esc(c.nome_urna) + "</span><b>" + p2.format(best.pv[c.numero] || 0) + "%</b></div>").join("") +
        '<div class="r"><span>Seções apuradas</span><b>' + p2.format(best.pst) + "%</b></div>";
      dc.hidden = false; posDica(ev);
    });
    $("#alvo").addEventListener("pointerleave", () => { dc.hidden = true; $("#mira").setAttribute("x1", -9); $("#mira").setAttribute("x2", -9); });
  }

  function vivo(est, txt) { const v = $("#vivo"); v.dataset.estado = est; v.querySelector("span").textContent = txt; }

  async function atualizaUF(forca) {
    const info = E.man && E.man.ufs[E.uf];
    if (!info) { E.dados = null; return; }
    if (SIM) {
      const t = simTempo();
      E.dados = simUF(E.uf, t, true); pinta(); kpis(); distEstado(); lista(); cidade();
      E.hist = simHist(E.uf, t); grafico();
      return;
    }
    if (!forca && E.dados && E.dados.versao === info.versao) return;
    const d = await pega(DADOS + "/" + info.arquivo);
    if (d.uf !== E.uf) return; // trocou de estado no meio
    E.dados = d;
    pinta(); kpis(); distEstado(); lista(); cidade();
    try { E.hist = await pega(DADOS + "/historico/" + E.uf + ".json?v=" + d.versao); } catch (e) { E.hist = null; }
    grafico();
  }

  async function ciclo() {
    try {
      E.man = SIM ? simManifesto(simTempo()) : await pega(DADOS + "/latest.json?t=" + Date.now(), true);
      const sim = E.man.fonte && E.man.fonte.tipo === "simulacao";
      $("#marca-sim").hidden = !sim;
      $("#faixa-sim").hidden = !sim;
      if (sim) $("#faixa-sim").innerHTML = "<strong>SIMULAÇÃO</strong>" + esc(E.man.fonte.nota || "Dados fictícios para teste. Não é resultado.");
      chips();
      await atualizaUF(false);
      E.ultimoOk = Date.now();
      $("#faixa-erro").hidden = true;
      const fim = E.dados && E.dados.estado && E.dados.estado.and === "finalizada";
      vivo(fim ? "final" : "vivo", fim ? "apuração finalizada" : "ao vivo");
    } catch (e) {
      if (Date.now() - E.ultimoOk > 60000) {
        vivo("atrasado", "sem atualização");
        $("#faixa-erro").hidden = false;
        $("#faixa-erro").textContent = "Não foi possível atualizar agora. Mostrando os últimos dados recebidos. Nova tentativa em 15 s.";
      }
    }
  }

  // ---------- busca ----------
  function preencheBusca() {
    const nomes = Object.values(E.malha.mun).map((c) => c.nm).filter(Boolean).sort((a, b) => a.localeCompare(b, "pt-BR"));
    $("#lista-cidades").innerHTML = nomes.map((x) => '<option value="' + esc(x) + '">').join("");
    $("#busca").value = "";
  }
  function busca() {
    const v = semAcento($("#busca").value.trim());
    if (v.length < 2) return;
    const ent = Object.entries(E.malha.mun);
    const ach = ent.find(([, c]) => c.nm && semAcento(c.nm) === v) || ent.find(([, c]) => c.nm && semAcento(c.nm).startsWith(v));
    if (ach) seleciona(ach[0], true);
  }

  // ---------- início ----------
  async function inicio() {
    ligaMapa();
    document.querySelectorAll("a.sim-btn").forEach((a) => {
      if (SIM) { a.classList.add("ativo-sim"); a.lastChild.textContent = "Sair da simulação"; a.href = location.pathname + (DADOS !== "data" ? "?dados=" + DADOS : ""); }
      else a.href = location.pathname + "?sim=1";
      a.addEventListener("click", () => { a.href += location.hash; });
    });
    if (SIM) {
      const ps = await Promise.all(UFS.map((u) => pega("assets/sim/" + u + ".json?v=1")));
      simBase = Object.fromEntries(UFS.map((u, i) => [u, ps[i]]));
      simT0 = Date.now();
    }
    $("#ufs").addEventListener("click", (ev) => { const b = ev.target.closest("button[data-uf]"); if (b) location.hash = b.dataset.uf; });
    document.querySelectorAll(".abas button").forEach((b) => b.addEventListener("click", () => {
      E.modo = b.dataset.modo;
      document.querySelectorAll(".abas button").forEach((x) => x.setAttribute("aria-selected", x === b));
      lista();
    }));
    $("#lista").addEventListener("click", (ev) => { const li = ev.target.closest("li[data-cdi]"); if (li) seleciona(li.dataset.cdi, true); });
    $("#busca").addEventListener("change", busca);
    $("#busca").addEventListener("keydown", (ev) => { if (ev.key === "Enter") busca(); });
    window.addEventListener("hashchange", () => { const h = ufDoHash(); if (h.uf) abreUF(h.uf, h.cdi); });
    await ciclo();
    const h = ufDoHash();
    await abreUF(h.uf || "sp", h.cdi);
    setInterval(ciclo, SIM ? SIM_PASSO : INTERVALO);
  }
  inicio().catch((e) => { $("#faixa-erro").hidden = false; $("#faixa-erro").textContent = "Erro ao abrir: " + e.message; });
})();
