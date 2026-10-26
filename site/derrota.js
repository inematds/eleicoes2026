/* Por que Flávio perdeu? O que os números mostram (data/derrota.json, gerado por analise/derrota.py). */
(function () {
  "use strict";
  var A = "13", B = "22", d = null, mapa = null;
  var $ = function (id) { return document.getElementById(id); };
  var nf = new Intl.NumberFormat("pt-BR");
  var n = function (x) { return x == null ? "—" : nf.format(Math.round(x)); };
  var p1 = function (x) { return x == null ? "—" : x.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%"; };
  var pp = function (x) { return x == null ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " p.p."; };
  var mi = function (x, s) { if (x == null) return "—"; var a = Math.abs(x), r = a >= 1e6 ? (a / 1e6).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: a >= 1e7 ? 1 : 2 }) + " mi" : a >= 1e3 ? Math.round(a / 1e3) + " mil" : nf.format(a); return (x < 0 ? "−" : s && x > 0 ? "+" : "") + r; };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var COR = { "13": "var(--c13, #e5484d)", "22": "var(--c22, #5fb3f0)", L: "var(--c13, #e5484d)", F: "var(--c22, #5fb3f0)", O: "var(--mut, #a3a3ae)", M: "var(--ouro, #FACC15)", bn: "var(--branco, #d6d6dc)", nv: "var(--abst, #5a5a66)" };
  var REG = { N: "Norte", NE: "Nordeste", CO: "Centro-Oeste", SE: "Sudeste", S: "Sul" };

  function bonito(s) { s = String(s || ""); return s.charAt(0) + s.slice(1).toLowerCase().replace(/([ .'-])(\S)/g, function (m, sep, w) { return sep + w.toUpperCase(); }).replace(/ (De|Da|Do|Das|Dos|E) /g, function (m, w) { return " " + w.toLowerCase() + " "; }); }
  function hora(iso) { return iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + " " + iso.slice(11, 16) : "—"; }
  function ufn(uf) { return (d.ufs[uf] && d.ufs[uf].nome) || uf.toUpperCase(); }
  function lista(ufs) { var x = ufs.map(function (u) { return u.toUpperCase(); }); return x.length > 1 ? x.slice(0, -1).join(", ") + " e " + x[x.length - 1] : x.join(""); }
  var CAMPO = { L: "campo de Lula", F: "campo de Flávio", O: "outros", M: "PT e PL juntos" };
  function tagCampo(c) { return '<i class="an-ponto" style="background:' + COR[c || "O"] + '" aria-hidden="true"></i>'; }
  function tag(t) { return '<span class="an-tag ' + t + '">' + { fato: "FATO", est: "ESTIMATIVA", hip: "HIPÓTESE" }[t] + "</span>"; }

  // ---------- achados ----------
  function achados() {
    var p = d.placar, gv = p.votos_gov_1t.pct, sv = p.votos_sen_1t.pct, c = d.conta, b = c.brasil, ex = c.exercicio || {}, g = c.estimativa.grupos || {}, dv = d.divisao;
    $("dr-perg-sub").textContent = "O campo de Flávio elegeu mais governadores e senadores que o de Lula. Flávio também teve mais votos no 1º turno. Mesmo assim, Lula venceu o 2º turno com " + p1(d.tse.pct_validos[A]) + " dos votos válidos. O que os números do TSE mostram sobre isso:";
    var t = g.terceiros || {}, nb = (g["Brancos e nulos"] || {}), nv = (g["Não votou"] || {});
    var itens = [
      ["fato", "O campo de Flávio elegeu <b>" + p.governadores.F.n + " governadores</b> (campo de Lula: " + p.governadores.L.n + "; outros: " + p.governadores.O.n + ") e <b>" + p.senadores.F.n + " dos 54 senadores</b> (campo de Lula: " + p.senadores.L.n + "; outros: " + p.senadores.O.n + ")."],
      ["fato", "Mas os aliados de cada lado tiveram <b>menos votos que o próprio presidenciável</b>. Para governador, o campo de Flávio teve " + p1(gv.F) + " dos válidos e Flávio, " + p1(p.pres_1t.pct_flavio) + ". O campo de Lula teve " + p1(gv.L) + " e Lula, " + p1(p.pres_1t.pct_lula) + ". Lula teve " + p1(p.pres_1t.pct_lula - gv.L).replace("%", "") + " pontos a mais que os aliados dele; Flávio, " + p1(p.pres_1t.pct_flavio - gv.F).replace("%", "") + "."],
      ["fato", "<b>" + p1(gv.O) + " dos votos para governador</b> foram para candidatos sem PT nem PL na coligação. Esses votos não entram no placar de nenhum dos dois campos."],
      ["fato", "Em <b>" + dv.estados_F_lula.length + " estados</b> (" + lista(dv.estados_F_lula) + ") o governador eleito é do campo de Flávio e Lula venceu. Cidade a cidade, isso aconteceu em <b>" + n(dv.cidades.F_lula.cidades) + " cidades</b> com " + mi(dv.cidades.F_lula.eleitores) + " de eleitores. O contrário (governador do campo de Lula e Flávio vencendo) ocorreu em " + n(dv.cidades.L_flavio.cidades) + " cidades, com " + mi(dv.cidades.L_flavio.eleitores) + "."],
      ["fato", "Flávio terminou o 1º turno <b>" + mi(-b.margem_1t) + "</b> votos à frente. No 2º turno, Lula ganhou " + mi(b.ganho_lula, 1) + " e Flávio, " + mi(b.ganho_flavio, 1) + ". Do saldo de " + mi(ex.bolo) + " de votos a mais para os dois, Flávio ficou com " + p1(ex.parte_flavio) + "; para vencer, precisaria de " + p1(ex.flavio_precisava_pct) + "."],
      ["est", "Pelo modelo, os eleitores de Cury, Renan Santos, Caiado e dos outros candidatos <b>se dividiram quase ao meio</b> (≈" + mi(t[A]) + " para Lula e ≈" + mi(t[B]) + " para Flávio). A diferença aparece em quem votou branco ou nulo ou não votou no 1º turno: ≈" + mi((nb[A] || 0) + (nv[A] || 0)) + " para Lula e ≈" + mi((nb[B] || 0) + (nv[B] || 0)) + " para Flávio."],
      ["fato", "<b>" + n(d.virada.para_lula) + " cidades</b> passaram a ter Lula como mais votado no 2º turno e " + n(d.virada.para_flavio) + " passaram para Flávio. " + (d.virada.estados_mudaram.length ? "Só " + (d.virada.estados_mudaram.length === 1 ? "um estado trocou" : d.virada.estados_mudaram.length + " estados trocaram") + " de líder: " + d.virada.estados_mudaram.map(ufn).join(", ") + "." : "Nenhum estado trocou de líder.") + " Flávio venceu em " + p.estados_presidente.flavio.n + " estados e Lula em " + p.estados_presidente.lula.n + "; quem decide é a soma dos votos do país."]
    ];
    $("dr-achados").innerHTML = itens.map(function (i) { return '<div class="dr-ach">' + tag(i[0]) + "<p>" + i[1] + "</p></div>"; }).join("");
  }

  // ---------- 1. placar ----------
  function pilha(el, tot, partes, unidade) {
    el.innerHTML = '<div class="dr-pilha" role="img" aria-label="' + esc(partes.map(function (x) { return x.nm + ": " + x.v + " " + unidade; }).join("; ")) + '">' + partes.filter(function (x) { return x.v > 0; }).map(function (x) {
      return '<span style="flex:' + x.v + " 1 0;background:" + x.cor + '">' + x.v + "</span>";
    }).join("") + '</div><div class="dr-pilha-leg">' + partes.map(function (x) { return "<span><i style=\"background:" + x.cor + '"></i><b>' + x.v + " " + unidade + "</b> · " + esc(x.nm) + (x.extra ? " · " + x.extra : "") + "</span>"; }).join("") + "</div>";
  }
  function placar() {
    var p = d.placar, G = p.governadores, S = p.senadores, et = p.eleitores_total;
    $("dr-campo-def").innerHTML = "<b>Como cada candidato foi classificado.</b> Campo de Lula = candidato de coligação com o PT (ou da federação dele). Campo de Flávio = candidato de coligação com o PL. Os demais ficam em “outros”. É um critério formal, do registro no TSE, e pode surpreender: Ciro Gomes (PSDB, CE) e JHC (PSDB, AL) estão no campo de Flávio porque a coligação deles incluía o PL; Renan Filho (MDB, AL) e Omar Aziz (PSD, AM) estão no campo de Lula porque a deles incluía o PT. Estar na coligação não quer dizer que o candidato fez campanha para o presidenciável.";
    pilha($("dr-gov-barra"), 27, [
      { nm: CAMPO.F, v: G.F.n, cor: COR.F, extra: mi(G.F.eleitores) + " de eleitores (" + p1(100 * G.F.eleitores / et) + ")" },
      { nm: CAMPO.L, v: G.L.n, cor: COR.L, extra: mi(G.L.eleitores) + " de eleitores (" + p1(100 * G.L.eleitores / et) + ")" },
      { nm: CAMPO.O, v: G.O.n, cor: COR.O, extra: mi(G.O.eleitores) + " de eleitores (" + p1(100 * G.O.eleitores / et) + ")" }
    ], "");
    var lid = Object.keys(d.ufs).filter(function (uf) { return d.ufs[uf].governador.status !== "eleito"; });
    if (lid.length) $("dr-gov-barra").insertAdjacentHTML("beforeend", '<p class="pj-nota">Em ' + lid.map(ufn).join(", ") + " a apuração do 2º turno para governador ainda não terminou; vale o mais votado até agora (" + lid.map(function (uf) { return esc(bonito(d.ufs[uf].governador.nome)); }).join(", ") + ").</p>");
    pilha($("dr-sen-barra"), 54, [
      { nm: CAMPO.F, v: S.F.n, cor: COR.F }, { nm: CAMPO.L, v: S.L.n, cor: COR.L }, { nm: CAMPO.O, v: S.O.n, cor: COR.O }
    ], "");
    var gv = p.votos_gov_1t, sv = p.votos_sen_1t, p1t = p.pres_1t, p2t = p.pres_2t;
    $("dr-cmp-leg").innerHTML = ["L", "F", "O"].map(function (c) { return '<span><i style="background:' + COR[c] + '"></i>' + (c === "L" ? "Lula / campo de Lula" : c === "F" ? "Flávio / campo de Flávio" : "Outros candidatos") + "</span>"; }).join("");
    var grupos = [
      { nm: "Governador", sub: "1º turno · " + mi(gv.validos) + " de votos válidos", v: [["L", gv.pct.L, gv.L], ["F", gv.pct.F, gv.F], ["O", gv.pct.O, gv.O]] },
      { nm: "Senador", sub: "1º turno · cada eleitor votou em 2", v: [["L", sv.pct.L, sv.L / 2], ["F", sv.pct.F, sv.F / 2], ["O", sv.pct.O, sv.O / 2]] },
      { nm: "Presidente, 1º turno", sub: mi(p1t.validos) + " de votos válidos", v: [["L", p1t.pct_lula, p1t.lula], ["F", p1t.pct_flavio, p1t.flavio], ["O", 100 - p1t.pct_lula - p1t.pct_flavio, p1t.validos - p1t.lula - p1t.flavio]] },
      { nm: "Presidente, 2º turno", sub: "só os dois", v: [["L", p2t.pct_lula, p2t.lula], ["F", p2t.pct_flavio, p2t.flavio]] }
    ];
    $("dr-cmp").innerHTML = grupos.map(function (gr) {
      return '<div class="dr-cg"><div class="nm">' + esc(gr.nm) + "<small>" + esc(gr.sub) + '</small></div><div class="dr-cb">' + gr.v.map(function (x) {
        return '<div class="dr-cr" title="' + esc((x[0] === "O" ? "Outros" : CAMPO[x[0]]) + ": " + p1(x[1]) + " ≈ " + mi(x[2]) + " votos") + '"><div class="tr"><span style="width:' + Math.max(0.5, x[1]).toFixed(2) + "%;background:" + COR[x[0]] + '"></span></div><div class="vl num">' + p1(x[1]) + "</div></div>";
      }).join("") + "</div></div>";
    }).join("");
    $("dr-cmp-nota").innerHTML = "Votos absolutos no Brasil (sem exterior): governadores do campo de Flávio <b>" + mi(gv.F) + "</b> x Flávio no 1º turno <b>" + mi(p1t.flavio) + "</b>; campo de Lula <b>" + mi(gv.L) + "</b> x Lula <b>" + mi(p1t.lula) + "</b>. " +
      "Senado: cada eleitor votou em 2 senadores, então os votos somam o dobro. Dividindo por 2 só para comparar a escala: campo de Flávio ≈" + mi(sv.F / 2) + ", campo de Lula ≈" + mi(sv.L / 2) + ". Por isso a comparação justa é em % dos válidos. Um campo com dois candidatos fortes no mesmo estado (por exemplo DF e SP) soma mais votos que um campo com um só.";
  }

  // ---------- 2. divisão ----------
  function divisao() {
    var dv = d.divisao, U = d.ufs, c = dv.cidades;
    var card = function (tit, val, sub, cor) { return '<div class="an-card"' + (cor ? ' style="--cor:' + cor + '"' : "") + '><div class="t">' + tit + '</div><div class="v num">' + val + '</div><div class="s">' + sub + "</div></div>"; };
    $("dr-div-cards").innerHTML =
      card("Estados com governador do campo de Flávio e vitória de Lula", n(dv.estados_F_lula.length), lista(dv.estados_F_lula) + " · " + mi(dv.eleitores_estados_F_lula) + " de eleitores", "var(--ouro)") +
      card("Cidades com governador do campo de Flávio e vitória de Lula", n(c.F_lula.cidades), mi(c.F_lula.eleitores) + " de eleitores", COR.L) +
      card("Cidades com governador do campo de Lula e vitória de Flávio", n(c.L_flavio.cidades), mi(c.L_flavio.eleitores) + " de eleitores · " + n(dv.estados_L_flavio.length) + " estados", COR.F) +
      card("Estados em que o senado do campo de Flávio teve mais que ele", n(dv.sen_F_acima_flavio_1t.length) + " de 27", "maiores diferenças: " + dv.sen_F_acima_flavio_1t.slice(0, 5).map(function (u) { return u.toUpperCase() + " " + pp(U[u].dif_sen_F).replace(" p.p.", ""); }).join(", ") + " p.p.");
    // halteres
    var cor = COR.F;
    $("dr-hal-leg").innerHTML = '<span><i class="an-mk o" style="border-color:' + cor + '"></i>Flávio no 1º turno</span>' +
      '<span><i class="an-mk" style="background:' + cor + '"></i>Flávio no 2º turno (só os dois)</span>' +
      '<span><i class="an-mk q"></i>Senado do campo de Flávio</span><span><i class="an-mk s"></i>Governador do campo de Flávio</span>';
    var ks = Object.keys(U).sort(function (a, b) { return (U[b].dif_sen_F || -99) - (U[a].dif_sen_F || -99); });
    $("dr-hal").innerHTML = '<div class="an-hl an-eixo"><div></div><div class="tr">' + [0, 25, 50, 75, 100].map(function (x) { return '<span style="left:' + x + '%">' + x + "%</span>"; }).join("") + "</div><div></div></div>" +
      ks.map(function (uf) {
        var u = U[uf], v = [u.flavio_1t, u.flavio_2t, u.senado_F].concat(u.gov1_F ? [u.gov1_F] : []), mn = Math.min.apply(null, v), mx = Math.max.apply(null, v), dif = u.dif_sen_F;
        var tit = "Flávio 1º turno " + p1(u.flavio_1t) + " · 2º turno " + p1(u.flavio_2t) + " · senado do campo " + p1(u.senado_F) + " · governador do campo " + (u.gov1_F ? p1(u.gov1_F) : "sem candidato");
        return '<div class="an-hl' + (u.regiao === "NE" ? " ne" : "") + '" title="' + esc(tit) + '"><div class="nm">' + esc(u.nome) + " <small>" + (REG[u.regiao] || "") + '</small></div><div class="tr"><b class="ln" style="left:' + mn + "%;width:" + (mx - mn) + '%"></b>' +
          '<i class="an-mk o" style="left:' + u.flavio_1t + "%;border-color:" + cor + '"></i>' +
          '<i class="an-mk" style="left:' + u.flavio_2t + "%;background:" + cor + '"></i>' +
          (u.gov1_F ? '<i class="an-mk s" style="left:' + u.gov1_F + '%;transform:translateX(-50%)"></i>' : "") +
          '<i class="an-mk q" style="left:' + u.senado_F + '%"></i></div><div class="vl num">' + pp(dif) + "</div></div>";
      }).join("") + (function () { var sem = ks.filter(function (uf) { return !U[uf].gov1_F; }); return sem.length ? '<p class="pj-nota">Sem quadrado branco: o campo de Flávio não teve candidato a governador (' + sem.map(ufn).join(", ") + ").</p>" : ""; })();
    // mapa
    var cat = function (u) {
      var gc = u.governador.campo, pv = u.lider_2t;
      if (gc === "F") return pv === A ? "FL" : "FF";
      if (gc === "L") return pv === B ? "LF" : "LL";
      return "O";
    };
    var CAT = { FF: ["Governador do campo de Flávio · Flávio venceu", COR.F, ".85"], LL: ["Governador do campo de Lula · Lula venceu", COR.L, ".85"],
      FL: ["Governador do campo de Flávio · Lula venceu", "var(--ouro)", "1"], LF: ["Governador do campo de Lula · Flávio venceu", "var(--ouro2)", "1"], O: ["Governador de outro campo", "var(--pend)", "1"] };
    if (mapa) {
      $("dr-div-mapa").innerHTML = '<svg viewBox="' + mapa.viewBox + '" role="img" aria-label="Mapa: campo do governador eleito e presidente que venceu em cada estado">' + Object.keys(mapa.ufs).map(function (uf) {
        var u = U[uf], k = u ? cat(u) : null;
        return '<path d="' + mapa.ufs[uf].d + '" fill="' + (k ? CAT[k][1] : "var(--pend)") + '" fill-opacity="' + (k ? CAT[k][2] : "1") + '" stroke="var(--bg)" stroke-width="1"><title>' + esc(ufn(uf)) + (u ? ": governador " + esc(bonito(u.governador.nome)) + " (" + esc(u.governador.partido) + ", " + CAMPO[u.governador.campo] + (u.governador.status !== "eleito" ? ", liderando a apuração" : "") + "); " + (u.lider_2t === A ? "Lula" : "Flávio") + " venceu" : "") + "</title></path>";
      }).join("") + "</svg>";
    }
    var grupos = {};
    Object.keys(U).forEach(function (uf) { var k = cat(U[uf]); (grupos[k] = grupos[k] || []).push(uf); });
    $("dr-div-leg").innerHTML = ["FL", "FF", "LL", "LF", "O"].map(function (k) { var g = grupos[k] || []; return '<span><i style="background:' + CAT[k][1] + '"></i>' + CAT[k][0] + ": " + (g.length ? lista(g.sort()) : "nenhum") + "</span>"; }).join("");
    $("dr-div-tab").querySelector("thead").innerHTML = "<tr><th>Cidade</th><th>Eleitores</th><th>Governador eleito</th><th>Lula 2º</th><th>Flávio 2º</th></tr>";
    $("dr-div-tab").querySelector("tbody").innerHTML = dv.maiores.slice(0, 25).map(function (c) {
      var gov = U[c.uf].governador;
      return "<tr><td>" + esc(bonito(c.nm)) + " <small>" + c.uf.toUpperCase() + "</small></td><td>" + n(c.te) + "</td><td>" + tagCampo(gov.campo) + esc(bonito(gov.nome)) + " <small>" + esc(gov.partido) + (gov.status !== "eleito" ? " · liderando" : "") + "</small></td><td>" + (c.pl2 > c.pf2 ? "<b>" + p1(c.pl2) + "</b>" : p1(c.pl2)) + "</td><td>" + (c.pf2 > c.pl2 ? "<b>" + p1(c.pf2) + "</b>" : p1(c.pf2)) + "</td></tr>";
    }).join("");
  }

  // ---------- 3. conta ----------
  function conta() {
    var c = d.conta, b = c.brasil, ci = c.cidades, ex = c.exercicio || {};
    var card = function (tit, val, sub, cor) { return '<div class="an-card"' + (cor ? ' style="--cor:' + cor + '"' : "") + '><div class="t">' + tit + '</div><div class="v num">' + val + '</div><div class="s">' + sub + "</div></div>"; };
    $("dr-conta-cards").innerHTML =
      card("Vantagem de Flávio no 1º turno", mi(-b.margem_1t), mi(b.flavio_1t) + " x " + mi(b.lula_1t) + " votos", COR.F) +
      card("Vantagem de Lula no 2º turno", mi(b.margem_2t), mi(b.lula_2t) + " x " + mi(b.flavio_2t) + " votos", COR.L) +
      card("Lula ganhou do 1º para o 2º turno", mi(b.ganho_lula, 1), "votos a mais (Brasil e exterior)", COR.L) +
      card("Flávio ganhou do 1º para o 2º turno", mi(b.ganho_flavio, 1), "votos a mais (Brasil e exterior)", COR.F) +
      card("Votos de outros candidatos no 1º turno", mi(ex.livres_br), "ficaram livres para o 2º turno") +
      card("Comparecimento", mi(ci.comp, 1), "eleitores a mais votaram no 2º turno *") +
      card("Brancos e nulos", mi(ci.bn, 1), "variação do 1º para o 2º turno *") +
      card("Saldo em jogo", mi(ex.bolo), "soma do que os dois ganharam");
    var pf = ex.parte_flavio || 0, pl = ex.parte_lula || 0, need = ex.flavio_precisava_pct;
    $("dr-bolo").innerHTML = '<h3 class="an-h3">Como o saldo de ' + mi(ex.bolo) + " se dividiu</h3>" +
      '<div class="bx" role="img" aria-label="Flávio ficou com ' + p1(pf) + " do saldo e Lula com " + p1(pl) + "; Flávio precisava de " + p1(need) + '">' +
      '<span style="flex:' + pf + " 1 0;background:" + COR.F + '">Flávio ' + p1(pf).replace(",0%", "%") + "</span>" +
      '<span style="flex:' + pl + " 1 0;background:" + COR.L + '">Lula ' + p1(pl).replace(",0%", "%") + "</span>" +
      (need != null ? '<i class="mk" style="left:' + need + '%"><em>Flávio venceria a partir de ' + p1(need) + "</em></i>" : "") + "</div>" +
      '<div class="rot"><span>Flávio: ' + mi(b.ganho_flavio, 1) + "</span><span>Lula: " + mi(b.ganho_lula, 1) + "</span></div>";
    $("dr-bolo-nota").innerHTML = "* Comparecimento e brancos/nulos: só nas " + n(ci.comparadas) + " de " + n(ci.total) + " cidades já finalizadas nos dois turnos (" + mi(ci.eleitores) + " de eleitores). Nessas cidades Lula ganhou " + mi(ci.ganho_lula, 1) + " e Flávio " + mi(ci.ganho_flavio, 1) + ". Os demais números deste bloco são do Brasil todo, com o exterior. O “saldo” é líquido: mostra o resultado final da troca, não quantas pessoas mudaram de voto.";
    // origens (estimativa)
    var g = c.estimativa.grupos || {}, orig = [["terceiros", "Eleitores dos outros candidatos", "Cury, Renan Santos, Caiado e mais 7"], ["Brancos e nulos", "Quem votou branco ou nulo", "no 1º turno"], ["Não votou", "Quem não votou", "no 1º turno"]];
    var mx = 1;
    orig.forEach(function (o) { var x = g[o[0]] || {}; mx = Math.max(mx, x[A] || 0, x[B] || 0); });
    $("dr-orig-leg").innerHTML = '<span><i style="background:' + COR.L + '"></i>Foi para Lula</span><span><i style="background:' + COR.F + '"></i>Foi para Flávio</span>';
    $("dr-orig").innerHTML = orig.map(function (o) {
      var x = g[o[0]] || {};
      return '<div class="dr-og"><div class="nm">' + esc(o[1]) + "<small>" + esc(o[2]) + '</small></div><div class="dr-cb">' + [A, B].map(function (k) {
        return '<div class="dr-cr"><div class="tr"><span style="width:' + Math.max(0.4, 100 * (x[k] || 0) / mx).toFixed(2) + "%;background:" + COR[k] + '"></span></div><div class="vl num">≈' + mi(x[k] || 0) + "</div></div>";
      }).join("") + "</div></div>";
    }).join("");
    var tb = (d.hipoteses.terceiros || []);
    $("dr-terc").querySelector("thead").innerHTML = "<tr><th>Votou no 1º turno em</th><th>Votos</th><th>Lula</th><th>Flávio</th><th>Branco/nulo</th><th>Não votou</th></tr>";
    $("dr-terc").querySelector("tbody").innerHTML = tb.map(function (o) {
      var nm = o.origem === "Não votou" ? "Não votou" : o.origem === "Brancos e nulos" ? "Branco ou nulo" : bonito(o.origem);
      return "<tr><td>" + esc(nm) + "</td><td>" + mi(o.votos_1t) + "</td><td>" + p1(o.lula) + "</td><td>" + p1(o.flavio) + "</td><td>" + p1(o.bn) + "</td><td>" + p1(o.nv) + "</td></tr>";
    }).join("");
    // exercício
    $("dr-exerc").innerHTML =
      '<div><b class="g num">' + mi(ex.virar_meia_margem) + "</b>de eleitores que escolheram Lula, se tivessem escolhido Flávio, empatariam a eleição. Cada voto trocado tira um de um lado e põe no outro, por isso basta metade da diferença. É " + p1(100 * ex.virar_meia_margem / ex.livres_br) + " dos " + mi(ex.livres_br) + " de votos dos outros candidatos no 1º turno.</div>" +
      '<div><b class="g num">' + mi(ex.virar_margem) + "</b>de votos novos só para Flávio (de quem anulou, votou branco ou não votou) também empatariam, sem tirar nenhum voto de Lula.</div>" +
      '<div><b class="g num">' + mi(ex.flavio_precisava_ganhar) + "</b>é o que Flávio precisaria ter ganhado do saldo de " + mi(ex.bolo) + " (" + p1(ex.flavio_precisava_pct) + "), em vez de " + mi(d.conta.brasil.ganho_flavio) + " (" + p1(ex.parte_flavio) + "). A diferença é de " + mi(ex.faltou) + " de votos.</div>";
  }

  // ---------- 4. virada ----------
  function virada() {
    var v = d.virada, pu = v.por_uf, U = d.ufs;
    var mud = v.estados_mudaram.map(function (uf) { var u = U[uf]; return u.nome + " (1º turno: Flávio " + p1(u.flavio_1t) + " x Lula " + p1(u.lula_1t) + "; 2º turno: Lula " + p1(u.lula_2t) + ")"; });
    var empate = Object.keys(U).filter(function (uf) { var u = U[uf]; return Math.abs(u.margem_1t) < 5000 && !u.mudou; });
    $("dr-vir-sub").textContent = n(v.para_lula) + " cidades passaram a ter Lula como mais votado e " + n(v.para_flavio) + " passaram para Flávio. Estado que trocou de líder: " + (mud.length ? mud.join("; ") : "nenhum") + "." +
      (empate.length ? " " + empate.map(function (uf) { return U[uf].nome + " teve quase empate no 1º turno (diferença de " + n(Math.abs(U[uf].margem_1t)) + " votos)"; }).join("; ") + "." : "") + " No mapa: quantas cidades de cada estado viraram.";
    var max = 1;
    Object.keys(pu).forEach(function (k) { max = Math.max(max, pu[k].viradas_lula + pu[k].viradas_flavio); });
    if (mapa) {
      $("dr-vir-mapa").innerHTML = '<svg viewBox="' + mapa.viewBox + '" role="img" aria-label="Mapa: cidades que viraram em cada estado">' + Object.keys(mapa.ufs).map(function (uf) {
        var u = pu[uf], x = u ? u.viradas_lula + u.viradas_flavio : 0, op = u ? (x ? 0.15 + 0.85 * x / max : 0.05) : 0;
        var mudou = U[uf] && U[uf].mudou;
        return '<path d="' + mapa.ufs[uf].d + '" fill="' + (u ? "rgba(250,204,21," + op.toFixed(2) + ")" : "var(--pend)") + '" stroke="' + (mudou ? "var(--c13)" : "var(--bg)") + '" stroke-width="' + (mudou ? 4 : 1) + '"><title>' + esc(ufn(uf)) + ": " + n(x) + " cidades viraram (de " + n(u ? u.cidades : 0) + " comparadas)" + (mudou ? " · o estado trocou de líder" : "") + "</title></path>";
      }).join("") + "</svg>";
      $("dr-vir-escala").innerHTML = "<span>0</span><i></i><span>" + n(max) + " cidades</span>" + (v.estados_mudaram.length ? '<span>· contorno vermelho = estado que trocou de líder</span>' : "");
    }
    var rg = v.regioes, ks = Object.keys(rg).sort(function (a, b) { return rg[b].saldo - rg[a].saldo; }), mx = 1, tot = 0;
    ks.forEach(function (k) { mx = Math.max(mx, Math.abs(rg[k].saldo)); tot += rg[k].saldo; });
    $("dr-reg").innerHTML = ks.map(function (k) {
      var r = rg[k];
      return '<div class="dr-rg" title="Lula ' + mi(r.dl, 1) + " · Flávio " + mi(r.df, 1) + " · " + n(r.viradas) + ' cidades viraram"><div>' + esc(r.nome) + '</div><div class="tr"><span style="width:' + Math.max(0.5, 100 * Math.max(0, r.saldo) / mx).toFixed(1) + '%"></span></div><div class="vl num">' + mi(r.saldo, 1) + "</div></div>";
    }).join("") + '<p class="pj-nota">Soma das ' + n(d.conta.cidades.comparadas) + " cidades finalizadas nos dois turnos: saldo de " + mi(tot, 1) + ". " + ks.slice(0, 2).map(function (k) { return rg[k].nome + " " + p1(100 * rg[k].saldo / tot); }).join(" e ") + " do saldo.</p>";
    $("dr-vir-tab").querySelector("thead").innerHTML = "<tr><th>Cidade</th><th>Eleitores</th><th>1º turno</th><th>2º turno</th></tr>";
    $("dr-vir-tab").querySelector("tbody").innerHTML = v.lista.slice(0, 15).map(function (c) {
      return "<tr><td>" + esc(bonito(c.nm)) + " <small>" + c.uf.toUpperCase() + "</small></td><td>" + n(c.te) + "</td><td>Flávio " + p1(c.pf1) + " · Lula " + p1(c.pl1) + "</td><td>Lula " + p1(c.pl2) + " · Flávio " + p1(c.pf2) + "</td></tr>";
    }).join("");
  }

  // ---------- 5. hipóteses ----------
  function hipoteses() {
    var U = d.ufs, h = d.hipoteses, hg = h.governador, q = h.comparecimento_quartis || [], ne = d.divisao.sen_F_acima_flavio_1t.filter(function (u) { return U[u].regiao === "NE"; });
    var dShare = function (u) { var s1 = 100 * u.flavio_1t_votos / (u.flavio_1t_votos + u.lula_1t_votos); return u.flavio_2t - s1; };
    var t = (d.conta.estimativa.grupos || {}).terceiros || {}, terc = (h.terceiros || []).filter(function (o) { return o.origem !== "Brancos e nulos" && o.origem !== "Não votou" && !/^Outros/.test(o.origem); });
    var gvO = d.placar.votos_gov_1t.pct.O;
    var H = [
      { t: "Voto pessoal em lideranças locais",
        dados: "No Nordeste, os candidatos a senador do campo de Flávio tiveram bem mais votos que ele no 1º turno: " + ne.map(function (u) { return U[u].nome + " " + pp(U[u].dif_sen_F); }).join(", ") + ". Nesses estados, a parte de Flávio entre os dois mudou assim do 1º para o 2º turno: " + ne.map(function (u) { return u.toUpperCase() + " " + pp(dShare(U[u])); }).join(", ") + ". Nesses estados, o resultado para senador e o resultado para presidente foram bem diferentes.",
        sim: "Pesquisa com o mesmo eleitor mostrando que muitos votaram no senador aliado e em Lula; ou o mesmo padrão em eleições anteriores com esses nomes.",
        nao: "Se os votos a mais dos senadores vierem de eleitores de outros presidenciáveis (Cury, Renan Santos, Caiado), e não de eleitores de Lula." },
      { t: "O eleitor de centro se dividiu",
        dados: "Pelo modelo " + tag("est") + ", os eleitores de " + terc.map(function (o) { return bonito(o.origem) + " (" + p1(o.lula) + " Lula, " + p1(o.flavio) + " Flávio)"; }).join("; ") + " se repartiram. Somando todos os outros candidatos: ≈" + mi(t[A]) + " para Lula e ≈" + mi(t[B]) + " para Flávio. Se isso estiver certo, esses votos quase se anularam e não explicam sozinhos a virada.",
        sim: "Pesquisas depois da eleição com eleitores desses candidatos chegando a uma divisão parecida.",
        nao: "Pesquisas mostrando uma divisão muito diferente, por exemplo a maioria para um dos lados." },
      { t: "Quem não votou ou anulou no 1º turno decidiu",
        dados: "Fato: o comparecimento subiu " + mi(d.conta.cidades.comp) + " e brancos e nulos caíram " + mi(-d.conta.cidades.bn) + " nas cidades comparadas. Pelo modelo " + tag("est") + ", quase todos esses votos foram para Lula. Mas cidade a cidade a ligação é fraca: dividindo as cidades em 4 grupos pelo quanto o comparecimento subiu, a parte de Lula entre os dois subiu " + q.map(function (x) { return pp(x.lula_pp); }).join(", ") + " (do grupo que menos subiu para o que mais subiu).",
        sim: "Dados por seção eleitoral ou por perfil de eleitor (o TSE publica depois) mostrando que quem voltou a votar escolheu Lula.",
        nao: "Se a mudança tiver vindo de eleitores que votaram nos dois turnos e trocaram de candidato." },
      { t: "Governador aliado não levou votos para o presidenciável",
        dados: "Nos " + hg.F.ufs + " estados com governador do campo de Flávio, a parte de Lula entre os dois foi de " + p1(hg.F.lula_entre_dois_1t) + " no 1º turno para " + p1(hg.F.lula_entre_dois_2t) + " no 2º (" + pp(hg.F.lula_entre_dois_2t - hg.F.lula_entre_dois_1t) + "). Nos " + hg.L.ufs + " com governador do campo de Lula: " + pp(hg.L.lula_entre_dois_2t - hg.L.lula_entre_dois_1t) + ". Nos " + hg.O.ufs + " de outros campos: " + pp(hg.O.lula_entre_dois_2t - hg.O.lula_entre_dois_1t) + ". Ou seja, Lula cresceu em todos os grupos, inclusive onde o governador é aliado de Flávio.",
        sim: "Saber quais governadores fizeram campanha no 2º turno e comparar o crescimento de Lula onde houve campanha e onde não houve.",
        nao: "Se, comparando estados parecidos, onde o governador aliado se engajou Flávio tiver crescido mais. Atenção: onde Lula já tinha muitos votos sobra menos espaço para subir." },
      { t: "O voto local segue critérios locais",
        dados: p1(gvO) + " dos votos para governador foram para candidatos sem PT nem PL na coligação (por exemplo " + ["mg", "pe", "ma", "go"].filter(function (u) { return U[u]; }).map(function (u) { return bonito(U[u].governador.nome) + " em " + u.toUpperCase(); }).join(", ") + "). Nesses " + hg.O.ufs + " estados, Lula tinha " + p1(hg.O.lula_entre_dois_1t) + " entre os dois no 1º turno e chegou a " + p1(hg.O.lula_entre_dois_2t) + ". A vantagem dos aliados de Flávio em cadeiras não se converteu em votos para presidente de forma automática.",
        sim: "Pesquisas sobre o motivo do voto para governador e senador (gestão, nome conhecido, região) separadas do motivo do voto para presidente.",
        nao: "Se o voto para governador e para presidente andarem juntos cidade a cidade, o que os gráficos desta página não mostram." }
    ];
    $("dr-hips").innerHTML = H.map(function (x) {
      return '<div class="dr-hp"><h3>' + tag("hip") + esc(x.t) + '</h3><p class="dados"><b>O que os dados mostram:</b> ' + x.dados.replace(/p\.p\.\./g, "p.p.") + "</p><p><b>Confirmaria:</b> " + esc(x.sim) + "</p><p><b>Descartaria:</b> " + esc(x.nao) + "</p></div>";
    }).join("");
    var nao = [
      "Em quem cada pessoa votou. O voto é secreto; as estimativas valem para o conjunto, não para indivíduos.",
      "Por que o eleitor escolheu o que escolheu. Campanha, debates, propaganda, pesquisas e acontecimentos não estão nestes dados.",
      "Se o resultado seria outro com outros candidatos ou outras alianças.",
      "Se um candidato de coligação com o PL ou com o PT pediu voto para o presidenciável. A classificação por coligação é formal.",
      "O exterior. Lá só se vota para presidente, então ele fica fora das comparações com governador e senador.",
      d.tse.final ? "" : "O resultado final oficial. O TSE ainda não declarou a totalização como final; os números podem mudar pouco."
    ].filter(Boolean);
    $("dr-nao-lista").innerHTML = nao.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("");
  }

  function desenha() {
    $("dr-hora").textContent = hora(d.tse.totalizado_tse);
    $("dr-sub").textContent = "Presidente 2026 · apuração " + d.tse.pct_secoes.toLocaleString("pt-BR", { minimumFractionDigits: 2 }) + "%" + " das seções · Lula " + p1(d.tse.pct_validos[A]) + " x Flávio " + p1(d.tse.pct_validos[B]);
    achados(); placar(); divisao(); conta(); virada(); hipoteses();
  }

  function vivo(estado, txt) { var el = $("vivo"); el.dataset.estado = estado; el.querySelector("span").textContent = txt; }

  function carrega() {
    var pm = mapa ? Promise.resolve() : fetch("assets/mapa-br.json", { cache: "force-cache" }).then(function (r) { return r.json(); }).then(function (m) { mapa = m; }).catch(function () {});
    var pd = fetch("data/derrota.json?t=" + Date.now(), { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); });
    Promise.all([pd, pm]).then(function (x) {
      d = x[0];
      if (d.schema !== 1 || d.tipo !== "derrota") throw new Error("formato novo, atualize a página");
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
