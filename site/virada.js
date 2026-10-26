/* A virada de 10,4 milhões (data/virada.json, gerado por analise/virada.py). */
(function () {
  "use strict";
  var A = "13", B = "22", d = null, ufSel = "sc";
  var $ = function (id) { return document.getElementById(id); };
  var nf = new Intl.NumberFormat("pt-BR");
  var n = function (x) { return x == null ? "—" : nf.format(Math.round(x)); };
  var ns = function (x) { return x == null ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + nf.format(Math.abs(Math.round(x))); };
  var dec = function (x, k) { return x.toLocaleString("pt-BR", { minimumFractionDigits: k, maximumFractionDigits: k }); };
  var p1 = function (x) { return x == null ? "—" : dec(x, 1) + "%"; };
  var p2 = function (x) { return x == null ? "—" : dec(x, 2) + "%"; };
  var ps = function (x) { return x == null ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + dec(Math.abs(x), 1) + "%"; };
  var pp = function (x) { return x == null ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + dec(Math.abs(x), 1) + " p.p."; };
  var mi = function (x, s) { if (x == null) return "—"; var a = Math.abs(x), r = a >= 1e6 ? dec(a / 1e6, 2) + " mi" : a >= 1e3 ? Math.round(a / 1e3) + " mil" : nf.format(a); return (x < 0 ? "−" : s && x > 0 ? "+" : "") + r; };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var COR = { L: "var(--c13, #e5484d)", F: "var(--c22, #5fb3f0)", O: "var(--mut, #a3a3ae)", bn: "var(--branco, #d6d6dc)", nv: "var(--abst, #5a5a66)", ouro: "var(--ouro, #FACC15)" };
  var REGS = ["N", "NE", "CO", "SE", "S", "EX"];
  var CAT = { outros: "Votos dos outros 10 candidatos no 1º turno", comp: "Aumento do comparecimento (abstenção caiu)", brancos: "Queda dos votos brancos", nulos: "Queda dos votos nulos" };
  var CATC = { outros: "outros candidatos", comp: "comparecimento", brancos: "brancos", nulos: "nulos" };

  function bonito(s) { s = String(s || ""); return s.charAt(0) + s.slice(1).toLowerCase().replace(/([ .'-])(\S)/g, function (m, sep, w) { return sep + w.toUpperCase(); }).replace(/ (De|Da|Do|Das|Dos|E) /g, function (m, w) { return " " + w.toLowerCase() + " "; }); }
  function hora(iso) { return iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + " " + iso.slice(11, 16) : "—"; }
  function tag(t) { return '<span class="an-tag ' + t + '">' + { fato: "FATO", est: "ESTIMATIVA", exe: "CHECAGEM" }[t] + "</span>"; }
  function card(tit, val, sub, cor) { return '<div class="an-card"' + (cor ? ' style="--cor:' + cor + '"' : "") + '><div class="t">' + tit + '</div><div class="v num">' + val + '</div><div class="s">' + sub + "</div></div>"; }
  function tabela(id, cab, linhas) { var t = $(id); t.querySelector("thead").innerHTML = "<tr>" + cab.map(function (c) { return "<th>" + c + "</th>"; }).join("") + "</tr>"; t.querySelector("tbody").innerHTML = linhas.join(""); }
  function lista(ufs) { var x = ufs.map(function (u) { return u.toUpperCase(); }); return x.length > 1 ? x.slice(0, -1).join(", ") + " e " + x[x.length - 1] : x.join(""); }

  function trocaram() {
    var v1 = d.venceu_1t, v2 = d.venceu;
    return { para_lula: v2.lula.filter(function (u) { return v1.flavio.indexOf(u) >= 0; }), para_flavio: v2.flavio.filter(function (u) { return v1.lula.indexOf(u) >= 0; }) };
  }
  function regMenor(campo) { var r = d.regioes, ks = REGS.filter(function (k) { return k !== "EX" && r[k]; }); return ks.sort(function (a, b) { return r[a][campo] - r[b][campo]; }); }

  // ---------- a pergunta ----------
  function achados() {
    var b = d.brasil, t1 = b.t1, t2 = b.t2, al = d.alegacao, D = b.categorias, c = d.cidades, tr = trocaram(), ord = regMenor("dl_pct"), R = d.regioes, s0 = d.divisoes[0];
    $("vr-perg-sub").textContent = "Do 1º para o 2º turno Lula ganhou " + n(b.dl) + " votos e Flávio ganhou " + n(b.df) + ". Como isso foi possível? O que a conta explica, o que ela não prova e o que ainda dá para investigar:";
    var it = [
      ["fato", "Flávio terminou o 1º turno <b>" + mi(t1.flavio - t1.lula) + "</b> de votos à frente. No 2º turno Lula ganhou <b>" + mi(b.dl, 1) + "</b> (" + ps(b.dl_pct) + ") e Flávio <b>" + mi(b.df, 1) + "</b> (" + ps(b.df_pct) + "). Lula venceu por " + mi(t2.lula - t2.flavio) + " (" + p2(t2.pl) + " x " + p2(t2.pf) + ")."],
      ["fato", "Os dois juntos tiveram <b>" + mi(al.bolo) + "</b> de votos a mais. Saíram de três lugares: " + mi(D.outros) + " que foram para os outros 10 candidatos no 1º turno, " + mi(D.comp) + " de gente que não tinha votado e " + mi(D.brancos + D.nulos) + " a menos de brancos e nulos. Lula ficou com <b>" + p1(al.parte_lula) + "</b> desse saldo e Flávio com " + p1(al.parte_flavio) + "."],
      ["fato", "Qualquer forma de dividir essas categorias entre os dois deixa <b>a mesma sobra, com sinal trocado</b>, de cada lado. Com os números finais, a divisão do texto que circula dá " + n(s0.sobra_lula) + " (não 38.390, que vinha de uma parcial). É uma identidade da conta, não uma prova de transferência."],
      ["fato", "Lula cresceu mais que Flávio em <b>" + n(c.lula_cresceu_mais) + " das " + n(c.comparadas) + " cidades</b>, em todas as regiões. Em porcentagem, o crescimento de Lula foi menor no " + R[ord[0]].nome + " (" + ps(R[ord[0]].dl_pct) + "), onde ele já era forte, e maior no " + R[ord[ord.length - 1]].nome + " (" + ps(R[ord[ord.length - 1]].dl_pct) + ")."],
      ["fato", (tr.para_lula.length + tr.para_flavio.length ? "Só " + (tr.para_lula.length + tr.para_flavio.length === 1 ? "um estado trocou" : (tr.para_lula.length + tr.para_flavio.length) + " estados trocaram") + " de líder: " + tr.para_lula.concat(tr.para_flavio).map(function (u) { return d.ufs[u].nome; }).join(", ") + "." : "Nenhum estado trocou de líder.") + " Lula venceu em <b>" + d.venceu.lula.length + " estados</b> e Flávio em <b>" + d.venceu.flavio.length + "</b>; quem decide é a soma dos votos do país."],
      ["est", "Pelo modelo da Projeção, os eleitores de Cury, Renan Santos, Caiado e dos menores se dividiram entre os dois, e a maior diferença veio de quem votou branco, nulo ou não votou no 1º turno. Ver o bloco “Para onde foram”."]
    ];
    var cf = (d.conferencia || {}).resumo;
    if (cf) it.push(["fato", "Na conferência independente deste site, <b>" + cf.conferido + " itens conferidos</b> (somas Brasil = estados = cidades, integridade dos arquivos baixados, exterior seção a seção pelos boletins de urna), " + cf.divergencia + " divergência(s) e " + cf.pendente + " pendente(s). Falta conferir os boletins das seções do Brasil."]);
    $("vr-achados").innerHTML = it.map(function (i) { return '<div class="dr-ach">' + tag(i[0]) + "<p>" + i[1] + "</p></div>"; }).join("");
  }

  // ---------- nível 1 ----------
  function placar() {
    var b = d.brasil, t1 = b.t1, t2 = b.t2;
    $("vr-cards").innerHTML =
      card("Lula ganhou", mi(b.dl, 1), n(t1.lula) + " → " + n(t2.lula) + " · " + ps(b.dl_pct), COR.L) +
      card("Flávio ganhou", mi(b.df, 1), n(t1.flavio) + " → " + n(t2.flavio) + " · " + ps(b.df_pct), COR.F) +
      card("Comparecimento", mi(t2.comp - t1.comp, 1), "abstenção de " + p1(100 * t1.abst / t1.eleitores) + " para " + p1(100 * t2.abst / t2.eleitores), COR.ouro) +
      card("Brancos e nulos", mi(t2.brancos + t2.nulos - t1.brancos - t1.nulos, 1), n(t1.brancos + t1.nulos) + " → " + n(t2.brancos + t2.nulos), COR.bn);
    var L = function (nm, a, c, cor) { return "<tr><td>" + (cor ? '<i class="an-ponto" style="background:' + cor + '"></i>' : "") + nm + '</td><td class="num">' + n(a) + '</td><td class="num">' + n(c) + '</td><td class="num"><b>' + ns(c - a) + "</b></td></tr>"; };
    tabela("vr-tab-br", ["", "1º turno", "2º turno", "Variação"], [
      L("Lula", t1.lula, t2.lula, COR.L), L("Flávio", t1.flavio, t2.flavio, COR.F), L("Outros 10 candidatos", t1.outros, 0, COR.O),
      L("Votos válidos", t1.validos, t2.validos), L("Brancos", t1.brancos, t2.brancos), L("Nulos", t1.nulos, t2.nulos),
      L("Comparecimento", t1.comp, t2.comp), L("Abstenção", t1.abst, t2.abst), L("Eleitorado", t1.eleitores, t2.eleitores)
    ]);
  }

  // ---------- a conta ----------
  function conta() {
    var b = d.brasil, D = b.categorias, al = d.alegacao;
    $("vr-ident").innerHTML = '<div class="vr-eq"><span class="lado"><b>' + mi(b.dl, 1) + '</b><small>Lula</small></span><span class="op">+</span><span class="lado"><b>' + mi(b.df, 1) + '</b><small>Flávio</small></span><span class="op">=</span>' +
      ["outros", "comp", "brancos", "nulos"].map(function (k, i) { return (i ? '<span class="op">+</span>' : "") + '<span class="lado"><b>' + mi(D[k], 1) + "</b><small>" + CATC[k] + "</small></span>"; }).join("") + '<span class="op">=</span><span class="lado tot"><b>' + n(al.bolo) + "</b><small>votos</small></span></div>" +
      '<p class="pj-nota">Ganho de Lula + ganho de Flávio = votos dos outros candidatos no 1º turno + aumento do comparecimento + queda dos brancos + queda dos nulos. A conta fecha exatamente com os números oficiais; ela sempre fecha, porque cada voto do 2º turno tem de vir de algum lugar do 1º.</p>';
    var w = function (x) { return (100 * x / al.bolo).toFixed(2); };
    $("vr-bolo").innerHTML = '<div class="vr-bar-tit">De onde saiu o saldo</div><div class="dr-pilha">' + ["outros", "comp", "brancos", "nulos"].map(function (k, i) { return '<span style="flex:' + D[k] + ' 1 0;background:' + [COR.O, COR.ouro, COR.bn, COR.nv][i] + '" title="' + esc(CAT[k] + ": " + n(D[k])) + '">' + (D[k] / al.bolo >= 0.08 ? w(D[k]).replace(".", ",") + "%" : "") + "</span>"; }).join("") + "</div>" +
      '<div class="vr-bar-tit">Com quem ficou</div><div class="dr-pilha"><span style="flex:' + b.dl + ' 1 0;background:' + COR.L + '">Lula ' + p1(al.parte_lula) + '</span><span style="flex:' + b.df + ' 1 0;background:' + COR.F + '">Flávio ' + p1(al.parte_flavio) + "</span></div>";
    $("vr-bolo-nota").innerHTML = "A primeira barra é FATO. A ligação entre as duas barras (quem foi para quem) não aparece no total do país: um eleitor de Flávio pode ter votado em Lula no 2º turno enquanto um de Cury votou em Flávio, e essas trocas se anulam no total. Para chegar perto disso é preciso comparar cidades e seções (níveis 2 e 3 abaixo).";
  }

  // ---------- coincidência ----------
  function coincidencia() {
    var b = d.brasil, s0 = d.divisoes[0];
    $("vr-coinc-txt").innerHTML = "O texto que circula dá a Lula os votos dos outros candidatos e a queda dos nulos, e a Flávio o aumento do comparecimento e a queda dos brancos. Sobra a mesma diferença dos dois lados. A tabela faz a mesma conta com outras divisões: <b>em todas a sobra é igual e de sinal trocado</b>.";
    var nm = function (ks) { return ks.length ? ks.map(function (k) { return CATC[k]; }).join(" + ") : "nada"; };
    tabela("vr-tab-div", ["Divisão", "Para Lula", "Para Flávio", "Sobra de Lula", "Sobra de Flávio"], d.divisoes.map(function (x) {
      return "<tr><td>" + esc(x.nome) + '</td><td>' + esc(nm(x.lula_de)) + "<br><small>" + n(x.atrib_lula) + "</small></td><td>" + esc(nm(x.flavio_de)) + "<br><small>" + n(x.atrib_flavio) + '</small></td><td class="num"><b>' + ns(x.sobra_lula) + '</b></td><td class="num"><b>' + ns(x.sobra_flavio) + "</b></td></tr>";
    }));
    $("vr-coinc-conc").innerHTML = "<b>Conclusão.</b> Como os quatro números somados são iguais ao ganho dos dois somado (" + n(d.alegacao.bolo) + "), o que falta de um lado sobra do outro, sempre. Por isso a coincidência (" + ns(s0.sobra_lula) + " e " + ns(s0.sobra_flavio) + " com os números finais) não é evidência independente de que essa divisão aconteceu, nem de que não aconteceu. Ela também não aponta erro: é só a conta fechando.";
  }

  // ---------- alegação ----------
  function alegacao() {
    var al = d.alegacao, lst = d.brasil.outros_candidatos, mx = lst[0].votos, quatro = al.quatro.map(function (q) { return q.numero; });
    $("vr-cand").innerHTML = lst.map(function (c) {
      var q = quatro.indexOf(c.numero) >= 0;
      return '<div class="vr-cr' + (q ? " q" : "") + '"><span class="nm">' + esc(bonito(c.nome)) + (q ? " <small>no gráfico</small>" : "") + '</span><span class="tr"><span style="width:' + Math.max(0.4, 100 * c.votos / mx).toFixed(2) + '%"></span></span><span class="vl num">' + n(c.votos) + "</span></div>";
    }).join("");
    $("vr-cand-nota").innerHTML = "Os 4 do gráfico somam <b>" + n(al.soma_quatro) + "</b> (a soma está certa). Os outros 6 somam " + n(al.outros_seis) + ", total de <b>" + n(al.outros_todos) + "</b>. Lula ganhou " + n(d.brasil.dl) + ", ou seja " + n(al.lula_alem_dos_outros) + " a mais do que todos esses votos juntos. " +
      "Mas não precisou “pegar todas as abstenções”: a abstenção caiu " + n(al.abst_caiu) + " (de " + mi(al.abst_1t) + " para " + mi(al.abst_2t) + ") e brancos e nulos caíram " + n(d.brasil.categorias.brancos + d.brasil.categorias.nulos) + ". Havia " + n(al.bolo) + " votos novos para os dois, e Flávio ficou com " + n(d.brasil.df) + " deles.";
    var E = d.estimativa || [];
    $("vr-est-leg").innerHTML = [["L", "Lula"], ["F", "Flávio"], ["bn", "Branco ou nulo"], ["nv", "Não votou"]].map(function (x) { return '<span><i style="background:' + COR[x[0]] + '"></i>' + x[1] + "</span>"; }).join("");
    var sl = 0, sf = 0;
    $("vr-est").innerHTML = E.map(function (o) {
      sl += o.lula; sf += o.flavio;
      var p = o.para, seg = [["L", p[A] || 0], ["F", p[B] || 0], ["bn", p.brancos_nulos || 0], ["nv", p.nao_votou || 0]];
      return '<div class="vr-er"><div class="nm">' + esc(bonito(o.origem)) + "<small>" + mi(o.votos_1t) + ' no 1º turno · ≈' + mi(o.lula) + ' Lula · ≈' + mi(o.flavio) + ' Flávio</small></div><div class="dr-pilha fina">' + seg.filter(function (s) { return s[1] > 0; }).map(function (s) { return '<span style="flex:' + s[1] + ' 1 0;background:' + COR[s[0]] + '">' + (s[1] >= 8 ? dec(s[1], 0) + "%" : "") + "</span>"; }).join("") + "</div></div>";
    }).join("");
    $("vr-est-nota").innerHTML = E.length ? "Somando os grupos, o modelo atribui ≈" + mi(sl) + " a Lula e ≈" + mi(sf) + " a Flávio (o apurado foi " + mi(d.brasil.dl) + " e " + mi(d.brasil.df) + "; o modelo usa só as cidades e não fecha exato). O modelo não deixa voto sair de Lula ou de Flávio do 1º turno para o outro; trocas diretas entre os dois, se houve, aparecem misturadas nos outros grupos." : "Estimativa indisponível agora.";
  }

  // ---------- estados ----------
  function estados() {
    var U = d.ufs, ks = Object.keys(U).filter(function (u) { return u !== "zz"; }).sort(function (a, b) { return U[b].pl2 - U[a].pl2; }), tr = trocaram(), mud = tr.para_lula.concat(tr.para_flavio);
    var mx = Math.max.apply(null, ks.map(function (u) { return Math.abs(U[u].dif2); }));
    $("vr-est-sub").textContent = "% dos votos válidos no 2º turno e diferença em votos, resultado final. Lula venceu em " + d.venceu.lula.length + " estados, Flávio em " + d.venceu.flavio.length + ".";
    $("vr-uf-leg").innerHTML = '<span><i style="background:' + COR.L + '"></i>Lula</span><span><i style="background:' + COR.F + '"></i>Flávio</span>' + (mud.length ? '<span><b class="vr-troca">↺</b> trocou de líder do 1º para o 2º turno</span>' : "");
    var linha = function (u, ext) {
      var x = U[u], dif = x.dif2, w = (50 * Math.abs(dif) / mx).toFixed(2);
      return '<div class="vr-uf' + (ext ? " ext" : "") + '"><span class="nm">' + esc(x.nome) + (mud.indexOf(u) >= 0 ? ' <b class="vr-troca" title="trocou de líder">↺</b>' : "") + '</span><span class="br"><span class="l" style="width:' + x.pl2 + '%">' + p1(x.pl2) + '</span><span class="f">' + p1(x.pf2) + '</span><i></i></span><span class="df"><span class="' + (dif > 0 ? "l" : "f") + '" style="width:' + w + '%"></span><b class="' + (dif > 0 ? "l" : "f") + '">' + mi(Math.abs(dif), 1) + "</b></span></div>";
    };
    $("vr-ufs").innerHTML = '<div class="vr-uf cab"><span>Estado</span><span>% dos válidos</span><span>Diferença em votos</span></div>' + ks.map(function (u) { return linha(u); }).join("") + (U.zz ? linha("zz", true) : "") +
      '<p class="pj-nota">Brasil: Lula ' + p2(d.brasil.t2.pl) + " x Flávio " + p2(d.brasil.t2.pf) + ", diferença de " + n(d.brasil.t2.lula - d.brasil.t2.flavio) + " votos." + (mud.length ? " " + mud.map(function (u) { return U[u].nome; }).join(", ") + ": no 1º turno Lula " + p1(U[mud[0]].pl1) + " x Flávio " + p1(U[mud[0]].pf1) + " (% dos válidos com todos os candidatos)." : "") + "</p>";
  }

  // ---------- regiões ----------
  function regioes() {
    var R = d.regioes, U = d.ufs;
    $("vr-regs").innerHTML = REGS.filter(function (k) { return R[k]; }).map(function (k) {
      var r = R[k];
      return '<div class="vr-rg"><h3>' + esc(r.nome) + '</h3><div class="ln"><i style="background:' + COR.L + '"></i>Lula <b>' + mi(r.dl, 1) + "</b> <small>" + ps(r.dl_pct) + '</small></div><div class="ln"><i style="background:' + COR.F + '"></i>Flávio <b>' + mi(r.df, 1) + "</b> <small>" + ps(r.df_pct) + '</small></div><div class="s">' + p1(r.parte_do_ganho_lula) + " do ganho de Lula · outros candidatos tinham " + mi(r.o1) + "</div></div>";
    }).join("");
    var linhas = [];
    REGS.forEach(function (k) {
      var r = R[k]; if (!r) return;
      r.ufs.slice().sort().forEach(function (u) {
        var x = U[u];
        linhas.push("<tr><td>" + (u === "zz" ? "Exterior" : u.toUpperCase()) + ' <small>' + esc(u === "zz" ? "" : x.nome) + '</small></td><td class="num">' + n(x.l1) + '</td><td class="num">' + n(x.l2) + '</td><td class="num"><b>' + ns(x.dl) + '</b></td><td class="num">' + ps(x.dl_pct) + '</td><td class="num">' + n(x.f1) + '</td><td class="num">' + n(x.f2) + '</td><td class="num"><b>' + ns(x.df) + '</b></td><td class="num">' + ps(x.df_pct) + '</td><td class="num">' + n(x.o1) + "</td></tr>");
      });
      if (k !== "EX") linhas.push('<tr class="sub"><td>Total ' + esc(r.nome) + '</td><td class="num">' + n(r.l1) + '</td><td class="num">' + n(r.l2) + '</td><td class="num"><b>' + ns(r.dl) + '</b></td><td class="num">' + ps(r.dl_pct) + '</td><td class="num">' + n(r.f1) + '</td><td class="num">' + n(r.f2) + '</td><td class="num"><b>' + ns(r.df) + '</b></td><td class="num">' + ps(r.df_pct) + '</td><td class="num">' + n(r.o1) + "</td></tr>");
    });
    var b = d.brasil;
    linhas.push('<tr class="sub tot"><td>Brasil</td><td class="num">' + n(b.t1.lula) + '</td><td class="num">' + n(b.t2.lula) + '</td><td class="num"><b>' + ns(b.dl) + '</b></td><td class="num">' + ps(b.dl_pct) + '</td><td class="num">' + n(b.t1.flavio) + '</td><td class="num">' + n(b.t2.flavio) + '</td><td class="num"><b>' + ns(b.df) + '</b></td><td class="num">' + ps(b.df_pct) + '</td><td class="num">' + n(b.t1.outros) + "</td></tr>");
    tabela("vr-tab-uf", ["UF", "Lula 1º", "Lula 2º", "Lula +", "%", "Flávio 1º", "Flávio 2º", "Flávio +", "%", "Outros no 1º"], linhas);
    var ok = d.somas_conferidas;
    $("vr-reg-nota").innerHTML = (ok ? "Conferido: os 27 estados mais o exterior somam exatamente o total do Brasil nos dois turnos. " : "<b>Atenção:</b> a soma dos estados não bateu com o Brasil nesta rodada. ") +
      "Em todo estado e em toda região Lula cresceu mais que Flávio, em votos e em porcentagem. A coluna “Outros no 1º” mostra quantos votos estavam com os demais candidatos em cada estado: em vários, o ganho de Lula passa desse número, o que só fecha com o aumento do comparecimento e a queda de brancos e nulos naquele estado.";
  }

  // ---------- lupa ----------
  function lupa() {
    var U = d.ufs, sel = $("vr-uf-sel");
    if (!sel.options.length) {
      sel.innerHTML = Object.keys(U).sort(function (a, b) { return U[a].nome.localeCompare(U[b].nome, "pt-BR"); }).map(function (u) { return '<option value="' + u + '">' + esc(U[u].nome) + "</option>"; }).join("");
      sel.addEventListener("change", function () { ufSel = sel.value; lupaDesenha(); });
    }
    sel.value = U[ufSel] ? ufSel : "sc";
    lupaDesenha();
  }
  function lupaDesenha() {
    var x = d.ufs[$("vr-uf-sel").value];
    if (!x) return;
    var pl2t = 100 * x.l2 / x.vv2, pf2t = 100 * x.f2 / x.vv2;
    $("vr-lupa-box").innerHTML = '<table class="tab an-tab vr-lupa-t"><thead><tr><th>' + esc(x.nome) + '</th><th>% Flávio</th><th style="color:' + COR.F + '">Flávio</th><th style="color:' + COR.L + '">Lula</th><th>% Lula</th></tr></thead><tbody>' +
      '<tr><td>1º turno</td><td class="num">' + p2(x.pf1) + '</td><td class="num">' + n(x.f1) + '</td><td class="num">' + n(x.l1) + '</td><td class="num">' + p2(x.pl1) + "</td></tr>" +
      '<tr><td>2º turno</td><td class="num">' + p2(pf2t) + '</td><td class="num">' + n(x.f2) + '</td><td class="num">' + n(x.l2) + '</td><td class="num">' + p2(pl2t) + "</td></tr>" +
      '<tr class="sub"><td>Aumento</td><td class="num">' + pp(pf2t - x.pf1) + '</td><td class="num"><b>' + ns(x.df) + "</b><br><small>" + ps(x.df_pct) + '</small></td><td class="num"><b>' + ns(x.dl) + "</b><br><small>" + ps(x.dl_pct) + '</small></td><td class="num">' + pp(pl2t - x.pl1) + "</td></tr></tbody></table>" +
      '<p class="pj-nota">% dos votos válidos de cada turno (no 1º, com todos os candidatos). No 1º turno os outros candidatos tiveram ' + n(x.o1) + " votos no estado; o comparecimento foi de " + n(x.comp1) + " para " + n(x.comp2) + " (" + ns(x.comp2 - x.comp1) + ") e brancos e nulos de " + n(x.bn1) + " para " + n(x.bn2) + ". Resultado: " + (x.dif2 > 0 ? "Lula" : "Flávio") + " venceu por " + n(Math.abs(x.dif2)) + " votos.</p>";
  }

  // ---------- cidades ----------
  function cidades() {
    var c = d.cidades;
    $("vr-cid-sub").textContent = "As " + n(c.comparadas) + " cidades com resultado final nos dois turnos (sem exterior). Nível 2 da investigação: onde ocorreram as maiores mudanças.";
    $("vr-cid-cards").innerHTML =
      card("Cidades em que Lula cresceu mais que Flávio", n(c.lula_cresceu_mais), p1(100 * c.lula_cresceu_mais / c.comparadas) + " das cidades", COR.L) +
      card("Cidades em que Flávio cresceu mais que Lula", n(c.flavio_cresceu_mais), p1(100 * c.flavio_cresceu_mais / c.comparadas) + " das cidades", COR.F) +
      card("Cidades em que Lula ganhou mais do que os outros candidatos tinham", n(c.lula_ganhou_mais_que_outros), "o resto só fecha com comparecimento e brancos/nulos", COR.ouro) +
      (function () { var s15 = c.top_dl.reduce(function (s, x) { return s + x.dl; }, 0); return card("Parte do ganho de Lula nas 15 cidades que mais ganharam", p1(100 * s15 / d.brasil.dl), mi(s15) + " de " + mi(d.brasil.dl) + "; o resto veio das outras " + n(c.comparadas - 15) + " cidades e do exterior", COR.O); })();
    var nm = function (x) { return esc(bonito(x.nm)) + " <small>" + x.uf.toUpperCase() + "</small>"; };
    var tg = function (id, rows, k1, k2, dk) { tabela(id, ["Cidade", "1º turno", "2º turno", "Ganho"], rows.map(function (x) { return "<tr><td>" + nm(x) + '</td><td class="num">' + n(x[k1]) + '</td><td class="num">' + n(x[k2]) + '</td><td class="num"><b>' + ns(x[dk]) + "</b></td></tr>"; })); };
    tg("vr-tab-dl", c.top_dl, "l1", "l2", "dl");
    tg("vr-tab-df", c.top_df, "f1", "f2", "df");
    var tp = function (id, rows) { tabela(id, ["Cidade", "Lula entre os dois, 1º → 2º", "Mudança"], rows.map(function (x) { var s1 = 100 * x.l1 / (x.l1 + x.f1), s2 = 100 * x.l2 / (x.l2 + x.f2); return "<tr><td>" + nm(x) + '</td><td class="num">' + p1(s1) + " → " + p1(s2) + '</td><td class="num"><b>' + pp(x.pp) + "</b></td></tr>"; })); };
    tp("vr-tab-ppl", c.top_pp_lula);
    tp("vr-tab-ppf", c.top_pp_flavio);
  }

  // ---------- nível 3 ----------
  function boletins() {
    var cf = (d.conferencia || {}).resumo;
    $("vr-bu-box").innerHTML =
      '<div class="vr-bu-g"><div class="vr-bu-c ok"><h3>Já conferido aqui</h3><ul>' +
      "<li>Brasil = soma dos 27 estados + exterior, nos dois turnos (esta página e o menu Conferência).</li>" +
      "<li>Cada estado = soma das suas cidades, quando todas estão fechadas.</li>" +
      "<li>Integridade dos arquivos baixados do TSE durante a apuração (sha256 de cada arquivo guardado).</li>" +
      "<li>Exterior: soma dos boletins de urna seção a seção x total oficial.</li>" +
      (cf ? "<li>Situação agora: <b>" + cf.conferido + " conferidos</b>, " + cf.divergencia + " divergência(s), " + cf.pendente + " pendente(s).</li>" : "") +
      '</ul><a class="vr-link" href="conferencia.html">Abrir a Conferência →</a></div>' +
      '<div class="vr-bu-c"><h3>O que ainda dá para fazer</h3><ul>' +
      "<li>Baixar o boletim de urna de cada uma das ~499 mil seções do Brasil, que o TSE publica, e refazer a soma seção → cidade → estado → Brasil.</li>" +
      "<li>Comparar os boletins com as fotos dos boletins impressos que fiscais e partidos guardam das seções.</li>" +
      "<li>Procurar seções com padrão fora do comum (variação muito diferente das vizinhas) e verificar uma a uma. Padrão atípico não é prova; é o que se confere primeiro.</li>" +
      "<li>Usar os arquivos públicos do TSE (registro digital do voto, logs das urnas) e os resultados do teste de integridade do dia da eleição.</li>" +
      "</ul></div>" +
      '<div class="vr-bu-c"><h3>A pergunta certa</h3><p>Em vez de “houve fraude?” ou “está tudo provado?”, a pergunta que se responde com dados é: <b>os mecanismos disponíveis permitem que observadores independentes reproduzam a totalização, comparem os boletins das seções e encontrem inconsistências, se houver?</b></p><p>Esta página e a Conferência são esse trabalho feito em público: dados, código e somas abertos para qualquer um refazer, aceite ou questione o resultado.</p></div></div>';
  }

  // ---------- checagem ----------
  function checagem() {
    var cl = function (s) { return /confere/.test(s) && !/não/.test(s) ? "ok" : /parcial|arredond/.test(s) ? "par" : "nao"; };
    tabela("vr-tab-chk", ["Gráfico", "O que dizia", "Situação", "Número oficial final"], d.checagem.map(function (x) {
      return "<tr><td><small>" + esc(x.grafico) + "</small></td><td>" + esc(x.afirmacao) + '</td><td><span class="vr-st ' + cl(x.situacao) + '">' + esc(x.situacao) + "</span></td><td>" + esc(x.nota) + "</td></tr>";
    }));
  }

  function limites() {
    var it = [
      "Em quem cada pessoa votou. O voto é secreto. O total do país não mostra trocas que se anulam (um eleitor de Flávio indo para Lula e um de Cury indo para Flávio).",
      "Por que o eleitor mudou ou voltou a votar. Campanha, debates e acontecimentos entre os turnos não estão nestes dados.",
      "Se houve ou não irregularidade em alguma seção. Para isso é preciso o nível 3: boletim por boletim.",
      "Política econômica, juros e outros temas: são discussões importantes, mas não ajudam a testar a conta eleitoral, e ficam para outro texto.",
      d.tse.t2_final ? "" : "O resultado final. O TSE ainda não declarou a totalização do 2º turno como final; os números podem mudar pouco."
    ].filter(Boolean);
    $("vr-nao-lista").innerHTML = it.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("");
  }

  function desenha() {
    $("vr-hora").textContent = hora(d.tse.t2_totalizado);
    $("vr-sub").textContent = "Presidente 2026 · 1º turno x 2º turno · " + (d.tse.t2_final ? "resultado final" : dec(d.tse.t2_pct_secoes, 2) + "% das seções") + " · Lula " + p2(d.brasil.t2.pl) + " x Flávio " + p2(d.brasil.t2.pf);
    [achados, placar, conta, coincidencia, alegacao, estados, regioes, lupa, cidades, boletins, checagem, limites].forEach(function (f) {
      try { f(); } catch (e) { if (window.console) console.error(f.name, e); }
    });
  }

  function vivo(estado, txt) { var el = $("vivo"); el.dataset.estado = estado; el.querySelector("span").textContent = txt; }

  function carrega() {
    fetch("data/virada.json?t=" + Date.now(), { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(function (x) {
      if (x.schema !== 1 || x.tipo !== "virada") throw new Error("formato novo, atualize a página");
      d = x;
      $("faixa-erro").hidden = true;
      desenha();
      vivo(d.tse.t2_final ? "final" : "vivo", d.tse.t2_final ? "resultado final" : "atualizado " + hora(d.gerado_em).slice(6));
    }).catch(function (e) {
      $("faixa-erro").hidden = false;
      $("faixa-erro").textContent = "Não consegui carregar a análise agora (" + e.message + "). Tento de novo em 5 min.";
      vivo("erro", "sem conexão");
    });
  }
  carrega();
  setInterval(carrega, 300000);
})();
