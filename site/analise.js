/* Análise do resultado, 1º x 2º turno (data/analise.json, gerado por analise/gerar.py). */
(function () {
  "use strict";
  var A = "13", B = "22", d = null, mapa = null, cand = A, reg = "BR";
  var $ = function (id) { return document.getElementById(id); };
  var nf = new Intl.NumberFormat("pt-BR");
  var n = function (x) { return x == null ? "—" : nf.format(Math.round(x)); };
  var p1 = function (x) { return x == null ? "—" : x.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%"; };
  var sn = function (x) { return (x > 0 ? "+" : x < 0 ? "−" : "") + nf.format(Math.abs(Math.round(x))); };
  var mi = function (x) { var a = Math.abs(x); return (x < 0 ? "−" : "") + (a >= 1e6 ? (a / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + " mi" : a >= 1e3 ? Math.round(a / 1e3) + " mil" : nf.format(a)); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var COR = { "13": "var(--c13, #0fa89a)", "22": "var(--c22, #8e6cf0)", brancos_nulos: "var(--branco, #cfcfd6)", nao_votou: "var(--abst, #5a5a66)" };
  var UF = { ac: "Acre", al: "Alagoas", am: "Amazonas", ap: "Amapá", ba: "Bahia", ce: "Ceará", df: "Distrito Federal", es: "Espírito Santo", go: "Goiás", ma: "Maranhão", mg: "Minas Gerais", ms: "Mato Grosso do Sul", mt: "Mato Grosso", pa: "Pará", pb: "Paraíba", pe: "Pernambuco", pi: "Piauí", pr: "Paraná", rj: "Rio de Janeiro", rn: "Rio Grande do Norte", ro: "Rondônia", rr: "Roraima", rs: "Rio Grande do Sul", sc: "Santa Catarina", se: "Sergipe", sp: "São Paulo", to: "Tocantins" };

  function bonito(s) { s = String(s || ""); return s.charAt(0) + s.slice(1).toLowerCase().replace(/ (\S+)/g, function (m, w) { return " " + (/^(de|da|do|das|dos|e|d')$/.test(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)); }); }
  function nome(num) { var c = (d.candidatos || []).filter(function (x) { return x.numero === num; })[0]; return bonito(c ? c.nome_urna : num); }
  function curto(num) { return nome(num).split(" ")[0]; }
  function hora(iso) { return iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + " " + iso.slice(11, 16) : "—"; }
  function botoes(el, itens, atual, cb) {
    el.innerHTML = itens.map(function (i) { return '<button type="button" data-v="' + i[0] + '" aria-pressed="' + (i[0] === atual) + '">' + esc(i[1]) + "</button>"; }).join("");
    el.onclick = function (e) { var b = e.target.closest("button"); if (b) cb(b.dataset.v); };
  }

  // ---------- resumo ----------
  function resumo() {
    var f = d.fatos, t = f.totais;
    $("an-resumo-sub").textContent = n(f.cidades_comparadas) + " de " + n(f.cidades_total) + " cidades já finalizadas nos dois turnos (" + n(t.eleitores) + " eleitores). Exterior fora desta conta.";
    var card = function (tit, val, sub, cor) { return '<div class="an-card"' + (cor ? ' style="--cor:' + cor + '"' : "") + '><div class="t">' + tit + '</div><div class="v num">' + val + '</div><div class="s">' + sub + "</div></div>"; };
    $("an-cards").innerHTML =
      card(esc(nome(A)), sn(t.lula_2t - t.lula_1t), "votos a mais · de " + mi(t.lula_1t) + " para " + mi(t.lula_2t), COR[A]) +
      card(esc(nome(B)), sn(t.flavio_2t - t.flavio_1t), "votos a mais · de " + mi(t.flavio_1t) + " para " + mi(t.flavio_2t), COR[B]) +
      card("Votos dos outros candidatos", mi(t.outros_1t), "ficaram livres para o 2º turno") +
      card("Comparecimento", sn(t.comp_2t - t.comp_1t), "eleitores a mais votaram no 2º turno") +
      card("Brancos e nulos", sn(t.bn_2t - t.bn_1t), "de " + mi(t.bn_1t) + " para " + mi(t.bn_2t)) +
      card("Cidades que viraram", n(f.viradas.para_lula + f.viradas.para_flavio), n(f.viradas.para_lula) + " para " + esc(curto(A)) + " · " + n(f.viradas.para_flavio) + " para " + esc(curto(B))) +
      card(esc(curto(B)) + " perdeu votos em", n(f.flavio_perdeu_cidades) + " cidades", "teve menos votos que no 1º turno", COR[B]) +
      card(esc(curto(A)) + " perdeu votos em", n(f.lula_perdeu_cidades) + " cidades", "teve menos votos que no 1º turno", COR[A]);
  }

  // ---------- cascata ----------
  function cascata() {
    var cs = d.estimativa && d.estimativa.cascata;
    if (!cs) { $("an-cascata").hidden = true; return; }
    botoes($("an-cand"), [[A, curto(A)], [B, curto(B)]], cand, function (v) { cand = v; cascata(); });
    var c = cs[cand], linhas = [], soma = c.base_1t, max = c.base_1t;
    linhas.push({ nm: "Votos dele no 1º turno", de: 0, ate: c.base_1t, v: c.base_1t, tipo: "base" });
    c.partes.forEach(function (p) {
      var de = soma; soma += p.votos; max = Math.max(max, soma);
      linhas.push({ nm: p.origem === "Não votou" ? "Quem não votou no 1º turno" : p.origem === "Brancos e nulos" ? "Quem votou branco ou nulo no 1º turno" : /^Eleitores/.test(p.origem) ? p.origem : "Eleitores de " + bonito(p.origem), de: Math.min(de, soma), ate: Math.max(de, soma), v: p.votos, tipo: p.votos < 0 ? "neg" : "pos" });
    });
    max = Math.max(max, c.apurado || 0);
    linhas.push({ nm: "2º turno, pela estimativa", de: 0, ate: c.estimado, v: c.estimado, tipo: "tot" });
    if (c.apurado != null) linhas.push({ nm: "2º turno, apurado pelo TSE", de: 0, ate: c.apurado, v: c.apurado, tipo: "real" });
    var pc = function (x) { return (100 * x / max).toFixed(2) + "%"; };
    $("an-casc").style.setProperty("--cor", COR[cand]);
    $("an-casc").innerHTML = linhas.map(function (l) {
      return '<div class="an-cl ' + l.tipo + '"><div class="nm">' + esc(l.nm) + '</div><div class="tr"><span style="left:' + pc(l.de) + ";width:" + pc(Math.max(l.ate - l.de, max * 0.003)) + '"></span></div><div class="vl num">' + (l.tipo === "pos" || l.tipo === "neg" ? sn(l.v) : n(l.v)) + "</div></div>";
    }).join("");
    $("an-casc-nota").textContent = "Estimativa sobre o país inteiro, incluindo o exterior. A diferença entre a estimativa e o apurado (" + sn(c.diferenca_modelo || 0) + " votos) é o erro do modelo.";
  }

  // ---------- fluxo ----------
  function fluxo() {
    var tr = d.estimativa && d.estimativa.transferencias;
    if (!tr || !tr.BR) { $("an-fluxo").hidden = true; return; }
    var nr = d.estimativa.nome_regiao || {};
    botoes($("an-reg"), [["BR", "Brasil"]].concat(Object.keys(nr).map(function (k) { return [k, nr[k]]; })), reg, function (v) { reg = v; fluxo(); });
    var dest = [[A, curto(A)], [B, curto(B)], ["brancos_nulos", "Branco ou nulo"], ["nao_votou", "Não votou"]];
    $("an-fluxo-leg").innerHTML = dest.map(function (x) { return '<span><i style="background:' + COR[x[0]] + '"></i>' + esc(x[1]) + "</span>"; }).join("");
    $("an-fluxo-barras").innerHTML = (tr[reg] || []).map(function (o) {
      var nm = o.origem === "Não votou" ? "Não votou no 1º turno" : o.origem === "Brancos e nulos" ? "Branco ou nulo no 1º turno" : bonito(o.origem);
      return '<div class="an-fl"><div class="nm">' + esc(nm) + "<small>" + mi(o.votos_1t) + " de votos no 1º turno</small></div><div class=\"bx\">" +
        dest.map(function (x) {
          var v = o.para[x[0]] || 0;
          return v > 0 ? '<span style="flex-basis:' + v + "%;background:" + COR[x[0]] + '" title="' + esc(x[1]) + ": " + p1(v) + " ≈ " + mi(o.votos_1t * v / 100) + ' votos">' + (v >= 12 ? p1(v).replace(",0%", "%") : "") + "</span>" : "";
        }).join("") + "</div></div>";
    }).join("");
  }

  // ---------- mapa e ranking de perdas ----------
  function perdas() {
    var f = d.fatos, pu = f.por_uf;
    $("an-perdas-sub").textContent = curto(B) + " teve menos votos no 2º turno do que no 1º em " + n(f.flavio_perdeu_cidades) + " das " + n(f.cidades_comparadas) + " cidades comparadas. No mapa: % das cidades de cada estado em que isso aconteceu.";
    var max = Math.max.apply(null, Object.keys(pu).map(function (k) { return pu[k].pct_flavio_perdeu; }).concat([1]));
    if (mapa) {
      $("an-mapa").innerHTML = '<svg viewBox="' + mapa.viewBox + '" role="img" aria-label="Mapa: % das cidades onde Flávio perdeu votos">' + Object.keys(mapa.ufs).map(function (uf) {
        var u = pu[uf], v = u ? u.pct_flavio_perdeu : null;
        var op = v == null ? 0 : 0.12 + 0.88 * v / max;
        return '<path d="' + mapa.ufs[uf].d + '" fill="' + (v == null ? "var(--pend)" : "rgba(250,204,21," + op.toFixed(2) + ")") + '" stroke="var(--bg)" stroke-width="1"><title>' + UF[uf] + ": " + (u ? p1(v) + " das cidades (" + n(u.flavio_perdeu) + " de " + n(u.cidades) + ")" : "sem dados") + "</title></path>";
      }).join("") + "</svg>";
      $("an-escala").innerHTML = '<span>0%</span><i></i><span>' + p1(max) + " das cidades</span>";
    }
    var top = f.top_perdas_flavio.slice(0, 15);
    $("an-top").querySelector("thead").innerHTML = "<tr><th>Cidade</th><th>" + esc(curto(B)) + " 1º</th><th>" + esc(curto(B)) + " 2º</th><th>Perdeu</th><th>" + esc(curto(A)) + " ganhou</th></tr>";
    $("an-top").querySelector("tbody").innerHTML = top.map(function (c) {
      return "<tr><td>" + esc(bonito(c.nm)) + " <small>" + c.uf.toUpperCase() + "</small></td><td>" + n(c.f1) + "</td><td>" + n(c.f2) + '</td><td class="an-neg">' + sn(c.df) + '</td><td class="' + (c.dl >= 0 ? "an-pos" : "an-neg") + '">' + sn(c.dl) + "</td></tr>";
    }).join("");
  }

  function viradas() {
    var v = d.fatos.viradas_lista;
    $("an-vir-sub").textContent = n(d.fatos.viradas.para_lula) + " cidades passaram de " + curto(B) + " para " + curto(A) + " e " + n(d.fatos.viradas.para_flavio) + " de " + curto(A) + " para " + curto(B) + ". Maiores cidades primeiro.";
    $("an-vir").querySelector("thead").innerHTML = "<tr><th>Cidade</th><th>Eleitores</th><th>1º turno</th><th>2º turno</th><th>Virou para</th></tr>";
    $("an-vir").querySelector("tbody").innerHTML = v.slice(0, 30).map(function (c) {
      var t1 = curto(A) + " " + p1(c.pl1) + " · " + curto(B) + " " + p1(c.pf1), t2 = curto(A) + " " + p1(c.pl2) + " · " + curto(B) + " " + p1(c.pf2);
      return "<tr><td>" + esc(bonito(c.nm)) + " <small>" + c.uf.toUpperCase() + "</small></td><td>" + n(c.te) + "</td><td>" + t1 + "</td><td>" + t2 + '</td><td><b style="color:' + COR[c.para] + '">' + esc(curto(c.para)) + "</b></td></tr>";
    }).join("");
  }

  function ufs() {
    var pu = d.fatos.por_uf;
    $("an-uf").querySelector("thead").innerHTML = "<tr><th>Estado</th><th>Cidades</th><th>" + esc(curto(A)) + " (variação)</th><th>" + esc(curto(B)) + " (variação)</th><th>" + esc(curto(B)) + " perdeu em</th><th>Viradas</th></tr>";
    $("an-uf").querySelector("tbody").innerHTML = Object.keys(pu).sort(function (a, b) { return (pu[b].dl - pu[b].df) - (pu[a].dl - pu[a].df); }).map(function (uf) {
      var u = pu[uf];
      return "<tr><td>" + UF[uf] + "</td><td>" + n(u.cidades) + (u.cidades < u.cid_total ? " <small>de " + n(u.cid_total) + "</small>" : "") + '</td><td class="' + (u.dl >= 0 ? "an-pos" : "an-neg") + '">' + sn(u.dl) + '</td><td class="' + (u.df >= 0 ? "an-pos" : "an-neg") + '">' + sn(u.df) + "</td><td>" + n(u.flavio_perdeu) + " <small>(" + p1(u.pct_flavio_perdeu) + ")</small></td><td>" + (u.viradas_lula + u.viradas_flavio) + "</td></tr>";
    }).join("");
  }

  function desenha() {
    $("an-hora").textContent = hora(d.tse.totalizado_tse);
    $("an-sub").textContent = "Presidente 2026 · apuração " + p1(d.tse.pct_secoes) + " das seções · " + curto(A) + " " + p1(d.tse.pct_validos[A]) + " x " + curto(B) + " " + p1(d.tse.pct_validos[B]);
    resumo(); cascata(); fluxo(); perdas(); viradas(); ufs();
  }

  function vivo(estado, txt) { var el = $("vivo"); el.dataset.estado = estado; el.querySelector("span").textContent = txt; }

  function carrega() {
    var pm = mapa ? Promise.resolve() : fetch("assets/mapa-br.json", { cache: "force-cache" }).then(function (r) { return r.json(); }).then(function (m) { mapa = m; }).catch(function () {});
    var pd = fetch("data/analise.json?t=" + Date.now(), { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); });
    Promise.all([pd, pm]).then(function (x) {
      d = x[0];
      if (d.schema !== 1 || d.tipo !== "analise") throw new Error("formato novo, atualize a página");
      $("faixa-erro").hidden = true;
      desenha();
      vivo(d.tse.final ? "final" : "vivo", d.tse.final ? "resultado final" : "atualizado " + hora(d.gerado_em).slice(6));
    }).catch(function (e) {
      $("faixa-erro").hidden = false;
      $("faixa-erro").textContent = "Não consegui carregar a análise agora (" + e.message + "). Tento de novo em 2 min.";
      vivo("erro", "sem conexão");
    });
  }
  carrega();
  setInterval(carrega, 120000);
})();
