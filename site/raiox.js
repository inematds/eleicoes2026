/* Raio-X do 2º turno (data/raiox.json, gerado por analise/raiox.py). Tudo é conta direta sobre números do TSE. */
(function () {
  "use strict";
  var A = "13", B = "22", d = null, mapa = null, modoSaldo = "uf", modoCid = "votos", candCr = B;
  var $ = function (id) { return document.getElementById(id); };
  var nf = new Intl.NumberFormat("pt-BR");
  var n = function (x) { return x == null ? "—" : nf.format(Math.round(x)); };
  var p1 = function (x) { return x == null ? "—" : x.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%"; };
  var p2 = function (x) { return x == null ? "—" : x.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + "%"; };
  var pp = function (x) { return x == null ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " p.p."; };
  var sn = function (x) { return (x > 0 ? "+" : x < 0 ? "−" : "") + nf.format(Math.abs(Math.round(x))); };
  var mi = function (x, nd) { var a = Math.abs(x); return (x < 0 ? "−" : "") + (a >= 1e6 ? (a / 1e6).toLocaleString("pt-BR", { minimumFractionDigits: nd == null ? 1 : nd, maximumFractionDigits: nd == null ? 1 : nd }) + " mi" : a >= 1e3 ? Math.round(a / 1e3) + " mil" : nf.format(a)); };
  var smi = function (x, nd) { return (x > 0 ? "+" : "") + mi(x, nd); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var COR = { "13": "var(--c13, #e5484d)", "22": "var(--c22, #5fb3f0)" };
  var UF = { ac: "Acre", al: "Alagoas", am: "Amazonas", ap: "Amapá", ba: "Bahia", ce: "Ceará", df: "Distrito Federal", es: "Espírito Santo", go: "Goiás", ma: "Maranhão", mg: "Minas Gerais", ms: "Mato Grosso do Sul", mt: "Mato Grosso", pa: "Pará", pb: "Paraíba", pe: "Pernambuco", pi: "Piauí", pr: "Paraná", rj: "Rio de Janeiro", rn: "Rio Grande do Norte", ro: "Rondônia", rr: "Roraima", rs: "Rio Grande do Sul", sc: "Santa Catarina", se: "Sergipe", sp: "São Paulo", to: "Tocantins", zz: "Exterior" };

  function bonito(s) { s = String(s || ""); return s.charAt(0) + s.slice(1).toLowerCase().replace(/ (\S+)/g, function (m, w) { return " " + (/^(de|da|do|das|dos|e|d')$/.test(w) ? w : w.charAt(0).toUpperCase() + w.slice(1)); }); }
  function nome(num) { var c = (d.candidatos || []).filter(function (x) { return x.numero === num; })[0]; return bonito(c ? c.nome_urna : num); }
  function curto(num) { return nome(num).split(" ")[0]; }
  function hora(iso) { return iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + " " + iso.slice(11, 16) : "—"; }
  function sigla(uf) { return uf === "zz" ? "EX" : uf.toUpperCase(); }
  function cid(c) { return esc(bonito(c.nm)) + " <small>" + sigla(c.uf) + "</small>"; }
  function botoes(el, itens, atual, cb) {
    el.innerHTML = itens.map(function (i) { return '<button type="button" data-v="' + i[0] + '" aria-pressed="' + (i[0] === atual) + '">' + esc(i[1]) + "</button>"; }).join("");
    el.onclick = function (e) { var b = e.target.closest("button"); if (b) cb(b.dataset.v); };
  }
  function card(tit, val, sub, cor) { return '<div class="rx-card"' + (cor ? ' style="--cor:' + cor + '"' : "") + '><div class="t">' + tit + '</div><div class="v">' + val + '</div><div class="s">' + sub + "</div></div>"; }
  function tabela(id, cab, linhas) { $(id).querySelector("thead").innerHTML = "<tr>" + cab.map(function (c) { return "<th>" + c + "</th>"; }).join("") + "</tr>"; $(id).querySelector("tbody").innerHTML = linhas.join(""); }
  function lado(s) { return s >= 0 ? A : B; }

  // ---------- 1. de onde veio a diferença ----------
  function saldo() {
    var S = d.saldo, lider = lado(S.margem_br);
    botoes($("rx-saldo-modo"), [["uf", "Estados"], ["reg", "Regiões"]], modoSaldo, function (v) { modoSaldo = v; saldo(); });
    var ufs = S.ufs.filter(function (r) { return r.uf !== "zz"; });
    var topA = ufs[0], topB = ufs[ufs.length - 1];
    $("rx-saldo-sub").textContent = "Saldo = votos de " + curto(A) + " menos votos de " + curto(B) + ". Cada barra empurra a diferença para um lado; a soma de todos é a margem nacional.";
    $("rx-saldo-cards").innerHTML =
      card("Margem nacional", mi(Math.abs(S.margem_br), 2), "votos a favor de " + esc(curto(lider)) + " · " + n(Math.abs(S.margem_br)), COR[lider]) +
      card("Estados com saldo para cada um", S.estados_lula + " x " + S.estados_flavio, esc(curto(A)) + " x " + esc(curto(B)) + " (contando o exterior)") +
      card("Maior saldo para " + esc(curto(A)), esc(UF[topA.uf]), smi(topA.s, 2) + " votos", COR[A]) +
      card("Maior saldo para " + esc(curto(B)), esc(UF[topB.uf]), smi(-topB.s, 2) + " votos", COR[B]);
    $("rx-saldo-leg").innerHTML = '<span><i style="background:' + COR[A] + '"></i>somou para ' + esc(curto(A)) + '</span><span><i style="background:' + COR[B] + '"></i>somou para ' + esc(curto(B)) + '</span><span><i style="background:var(--ouro)"></i>margem oficial do Brasil</span>';
    var itens = modoSaldo === "uf"
      ? S.ufs.map(function (r) { return { nm: UF[r.uf], sg: sigla(r.uf), s: r.s, tit: UF[r.uf] + ": " + curto(A) + " " + p1(r.pl) + " x " + curto(B) + " " + p1(r.pf) }; })
      : S.regioes.map(function (r) { return { nm: r.nome, sg: r.ufs > 1 ? r.ufs + " UFs" : "", s: r.s, tit: r.nome + ": " + curto(A) + " " + p1(r.pl) }; });
    var cum = 0, mn = 0, mx = 0, rows = [];
    itens.forEach(function (it) { var de = cum; cum += it.s; mn = Math.min(mn, cum); mx = Math.max(mx, cum); rows.push({ it: it, de: de, ate: cum }); });
    mx = Math.max(mx, S.margem_br); mn = Math.min(mn, S.margem_br);
    var span = mx - mn || 1, X = function (v) { return (100 * (v - mn) / span).toFixed(3) + "%"; }, W = function (a, b) { return (100 * Math.max(Math.abs(b - a), span * 0.002) / span).toFixed(3) + "%"; };
    var z = '<i class="z" style="left:' + X(0) + '"></i>';
    var val = function (s) { return '<span class="' + (s >= 0 ? "rx-cor-a" : "rx-cor-b") + '">' + (s >= 0 ? "+" : "−") + mi(Math.abs(s), 2).replace(/^−/, "") + "</span>"; };
    var html = rows.map(function (r, i) {
      var lig = i > 0 ? '<b class="lig" style="left:' + X(Math.min(rows[i - 1].de, r.de)) + ";width:" + W(rows[i - 1].de, r.de) + '"></b>' : "";
      return '<div class="rx-cl' + (modoSaldo === "reg" ? " reg" : "") + '" title="' + esc(r.it.tit + " · saldo " + sn(r.it.s)) + '"><div class="nm">' + esc(r.it.nm) + (r.it.sg && modoSaldo === "reg" ? "<small>" + esc(r.it.sg) + "</small>" : "") + '</div><div class="tr">' + z +
        '<span style="--cor:' + COR[lado(r.it.s)] + ";left:" + X(Math.min(r.de, r.ate)) + ";width:" + W(r.de, r.ate) + '"></span></div><div class="vl num">' + val(r.it.s) + "</div></div>";
    }).join("");
    html += '<div class="rx-cl tot"><div class="nm">Soma</div><div class="tr">' + z + '<span style="--cor:' + COR[lado(cum)] + ";left:" + X(Math.min(0, cum)) + ";width:" + W(0, cum) + '"></span></div><div class="vl num">' + val(cum) + "</div></div>";
    html += '<div class="rx-cl real"><div class="nm">Brasil (oficial)</div><div class="tr">' + z + '<span style="left:' + X(Math.min(0, S.margem_br)) + ";width:" + W(0, S.margem_br) + '"></span></div><div class="vl num">' + val(S.margem_br) + "</div></div>";
    $("rx-casc").innerHTML = html;
    var dif = S.margem_br - S.soma_ufs;
    $("rx-saldo-fonte").textContent = "Fonte: " + S.fonte + ". Dado do TSE: " + hora(S.totalizado_tse) + ". Cobertura: " + S.cobertura.finalizadas + " de " + S.cobertura.abrangencias + " (27 estados + exterior) finalizados." +
      (dif ? " A soma dos estados difere da margem do Brasil em " + n(Math.abs(dif)) + " votos porque os arquivos são atualizados em horários um pouco diferentes." : "");
  }

  // ---------- 2. concentração ----------
  function concentracao() {
    var C = d.concentracao, a = C.por[A], b = C.por[B];
    $("rx-conc-sub").textContent = "Somamos, em cada cidade, a diferença a favor de quem venceu ali (o “saldo bruto”). Quantas cidades, das maiores para as menores em saldo, bastam para chegar à metade desse total?";
    var cc = function (num, x) {
      return card(esc(curto(num)) + ": metade do saldo vem de", n(x.cidades_metade) + " cidades", "de " + n(x.cidades_venceu) + " em que venceu (" + p1(x.pct_cidades_metade) + ") · " + mi(x.eleitores_metade) + " de eleitores", COR[num]);
    };
    $("rx-conc-cards").innerHTML = cc(A, a) + cc(B, b) +
      card("Saldo bruto de " + esc(curto(A)), mi(a.saldo_bruto, 2), "só as 10 maiores somam " + mi(a.top10_saldo, 2) + " (" + p1(100 * a.top10_saldo / a.saldo_bruto) + ")", COR[A]) +
      card("Saldo bruto de " + esc(curto(B)), mi(b.saldo_bruto, 2), "só as 10 maiores somam " + mi(b.top10_saldo, 2) + " (" + p1(100 * b.top10_saldo / b.saldo_bruto) + ")", COR[B]);
    var lin = function (num) { return function (c, i) { return "<tr><td>" + (i + 1) + ". " + cid(c) + "</td><td>" + n(c.te) + "</td><td>" + p1(c.pl) + "</td><td>" + p1(c.pf) + '</td><td class="' + (num === A ? "rx-cor-a" : "rx-cor-b") + '">+' + n(c.s) + "</td></tr>"; }; };
    var cab = ["Cidade", "Eleitores", esc(curto(A)), esc(curto(B)), "Saldo"];
    $("rx-top-a-tit").textContent = "As 10 cidades que mais deram saldo a " + curto(A);
    $("rx-top-b-tit").textContent = "As 10 cidades que mais deram saldo a " + curto(B);
    tabela("rx-top-a", cab, a.top.map(lin(A)));
    tabela("rx-top-b", cab, b.top.map(lin(B)));
    $("rx-conc-nota").textContent = "Atenção: uma cidade não vale o mesmo que outra. Uma capital com milhões de eleitores pesa mais que centenas de cidades pequenas juntas; por isso poucas cidades grandes concentram boa parte do saldo. A soma dos saldos brutos dos dois (" + mi(a.saldo_bruto - b.saldo_bruto, 2) + " de diferença) só bate com a margem nacional quando todas as cidades e o exterior estiverem finalizados.";
    $("rx-conc-fonte").textContent = "Fonte: " + C.fonte + ". Dado das cidades: " + hora(C.totalizado) + ". Cobertura: " + n(C.cobertura.fin) + " de " + n(C.cobertura.total) + " cidades finalizadas (" + mi(C.cobertura.eleitores_fin) + " de eleitores)." + (C.empates ? " " + n(C.empates) + " cidade(s) empatada(s) ficaram fora." : "");
  }

  // ---------- 3. cenário aritmético ----------
  function cenario() {
    var E = d.cenario, L = E.lider, O = L === A ? B : A;
    $("rx-cen-cards").innerHTML =
      card("Margem final", mi(E.margem, 2), n(E.margem) + " votos · " + pp(E.pp_validos).replace("+", "") + " dos válidos", COR[L]) +
      card("Votos que teriam que trocar de lado", mi(E.troca_virar, 2), "metade da margem (+1 para virar): " + p2(E.troca_pct_eleitorado) + " do eleitorado, " + p2(E.troca_pct_comparecimento) + " de quem votou · cerca de " + E.troca_por_secao.toLocaleString("pt-BR") + " por seção") +
      card("Abstenções a mais de um lado", mi(E.abst_virar, 2), "eleitores de " + esc(curto(L)) + " que teriam que ficar em casa (ou faltosos que teriam que votar em " + esc(curto(O)) + "): " + p1(E.abst_pct_abstencao) + " dos " + mi(E.abstencao) + " que não votaram") +
      card("Brancos e nulos", mi(E.brancos_nulos, 2), E.bn_pct_bn > 100 ? "mesmo se todos tivessem votado em " + esc(curto(O)) + ", não bastaria: cobririam " + p1(100 * E.brancos_nulos / E.margem) + " da margem" : "teriam que ir " + p1(E.bn_pct_bn) + " para " + esc(curto(O)));
    var vL = 100 * (E.validos / 2 + E.margem / 2) / E.validos, vO = 100 - vL;
    var barra = function (rot, a, b) { return '<div class="rx-cb"><div>' + rot + '</div><div class="bx"><span style="flex-basis:' + a + "%;background:" + COR[L] + '">' + esc(curto(L)) + " " + p2(a) + '</span><span style="flex-basis:' + b + "%;background:" + COR[O] + '">' + esc(curto(O)) + " " + p2(b) + '</span><i class="meio"></i></div></div>'; };
    $("rx-cen-barra").innerHTML = barra("Resultado real (válidos)", vL, vO) + barra("Se " + mi(E.troca_virar, 2) + " trocassem", 100 * (E.validos / 2 - 0.5) / E.validos, 100 * (E.validos / 2 + 0.5) / E.validos);
    $("rx-cen-fonte").textContent = "Fonte: " + E.fonte + ". Dado do TSE: " + hora(E.totalizado_tse) + " (" + p2(E.pct_secoes) + " das seções). Cada voto que troca de lado tira 1 de um e dá 1 ao outro, por isso basta metade da margem. Uma abstenção a mais só tira 1 de um lado, por isso precisa da margem inteira. A linha amarela marca 50%.";
  }

  // ---------- 4. comparecimento ----------
  function comparecimento() {
    var K = d.comparecimento, N = K.nacional, cv = K.cobertura;
    $("rx-comp-sub").textContent = "Mais gente votou no 2º turno: o comparecimento passou de " + p2(N.pc1) + " para " + p2(N.pc2) + " dos eleitores aptos.";
    $("rx-comp-cards").innerHTML =
      card("Comparecimento", pp(N.dpp), p2(N.pc1) + " → " + p2(N.pc2) + " · " + smi(N.dcomp, 2) + " eleitores", "var(--ouro)") +
      card("Abstenção", mi(N.abst2, 1), "eram " + mi(N.abst1, 1) + " no 1º turno (" + smi(N.abst2 - N.abst1, 2) + ")") +
      card("Brancos e nulos", mi(N.bn2, 2), "eram " + mi(N.bn1, 2) + " no 1º turno (" + smi(N.dbn, 2) + ")") +
      card("Cidades com mais votantes", n(K.cidades.subiu), "e " + n(K.cidades.caiu) + " com menos, de " + n(cv.cidades_comparadas) + " comparadas");
    var U = {}; K.ufs.forEach(function (r) { U[r.uf] = r; });
    var est = K.ufs.filter(function (r) { return r.uf !== "zz"; }), amp = Math.max.apply(null, est.map(function (r) { return Math.abs(r.dpp || 0); }).concat([0.5]));
    if (mapa) {
      $("rx-mapa").innerHTML = '<svg viewBox="' + mapa.viewBox + '" role="img" aria-label="Mapa: variação do comparecimento em pontos percentuais">' + Object.keys(mapa.ufs).map(function (uf) {
        var r = U[uf], v = r ? r.dpp : null, op = v == null ? 0 : 0.1 + 0.9 * Math.min(1, Math.abs(v) / amp);
        var fill = v == null ? "var(--pend)" : v >= 0 ? "rgba(250,204,21," + op.toFixed(2) + ")" : "rgba(214,214,220," + op.toFixed(2) + ")";
        return '<path d="' + mapa.ufs[uf].d + '" fill="' + fill + '" stroke="var(--bg)" stroke-width="1"><title>' + UF[uf] + ": " + (r ? pp(v) + " (" + p1(r.pc1) + " → " + p1(r.pc2) + "), " + sn(r.dcomp) + " votantes" : "sem dados") + "</title></path>";
      }).join("") + "</svg>";
      $("rx-escala").innerHTML = "<span>caiu " + pp(-amp).replace("−", "") + "</span><i></i><span>subiu " + pp(amp) + "</span>";
    }
    tabela("rx-comp-uf", ["Estado", "1º turno", "2º turno", "Variação", "Votantes", "Brancos e nulos"], K.ufs.map(function (r) {
      return "<tr><td>" + UF[r.uf] + "</td><td>" + p1(r.pc1) + "</td><td>" + p1(r.pc2) + '</td><td class="' + (r.dpp >= 0 ? "rx-pos" : "rx-neg") + '">' + pp(r.dpp) + "</td><td>" + sn(r.dcomp) + "</td><td>" + p1(r.pbn1) + " → " + p1(r.pbn2) + "</td></tr>";
    }));
    botoes($("rx-comp-modo"), [["votos", "Em votos"], ["pp", "Em pontos percentuais"]], modoCid, function (v) { modoCid = v; comparecimento(); });
    var vt = modoCid === "votos", ca = vt ? K.cidades.mais_votos : K.cidades.mais_pp, cb = vt ? K.cidades.menos_votos : K.cidades.menos_pp;
    $("rx-comp-cid-nota").textContent = vt
      ? "Diferença no número de pessoas que votaram, em " + n(cv.cidades_comparadas) + " cidades finalizadas nos dois turnos. Cidades grandes aparecem mais aqui."
      : "Diferença na porcentagem de eleitores que votaram, só nas " + n(cv.cidades_10mil) + " cidades finalizadas nos dois turnos e com 10 mil eleitores ou mais (em cidades muito pequenas a porcentagem oscila demais).";
    $("rx-cid-a-tit").textContent = "Maior aumento";
    $("rx-cid-b-tit").textContent = "Maior queda";
    var lin = function (c, i) { return "<tr><td>" + (i + 1) + ". " + cid(c) + "</td><td>" + n(c.te) + "</td><td>" + p1(c.pc1) + " → " + p1(c.pc2) + '</td><td class="' + ((vt ? c.dcomp : c.dpp) >= 0 ? "rx-pos" : "rx-neg") + '">' + (vt ? sn(c.dcomp) : pp(c.dpp)) + "</td></tr>"; };
    var cab = ["Cidade", "Eleitores", "Comparecimento", vt ? "Votantes" : "Variação"];
    tabela("rx-cid-a", cab, ca.map(lin));
    tabela("rx-cid-b", cab, cb.map(lin));
    var mx = Math.max(N.b1, N.n1, N.b2, N.n2) || 1;
    var bl = function (rot, v, base, cor) { return '<div class="rx-bnl"><div class="nm">' + rot + '</div><div class="tr"><span style="width:' + (100 * v / mx).toFixed(2) + "%;background:" + cor + '"></span></div><div class="vl num">' + n(v) + " <small>(" + p2(100 * v / base) + ")</small></div></div>"; };
    $("rx-bn").innerHTML = bl("Brancos · 1º turno", N.b1, N.comp1, "var(--branco)") + bl("Brancos · 2º turno", N.b2, N.comp2, "var(--branco)") +
      bl("Nulos · 1º turno", N.n1, N.comp1, "var(--nulo)") + bl("Nulos · 2º turno", N.n2, N.comp2, "var(--nulo)");
    $("rx-comp-fonte").textContent = "Fonte: " + K.fonte + ". Dado do TSE: " + hora(K.totalizado_tse) + "; cidades: " + hora(K.totalizado_cidades) + ". Cobertura: 27 estados + exterior; " + n(cv.cidades_comparadas) + " de " + n(cv.cidades_total) + " cidades finalizadas nos dois turnos. % entre parênteses = sobre quem votou.";
  }

  // ---------- 5. crescimento em votos x em % ----------
  var QN = { vs_pd: "mais votos, % menor", vd_ps: "menos votos, % maior", ambos_s: "cresceu nos dois", ambos_d: "caiu nos dois", outro: "sem mudança" };
  function crescimento() {
    var R = d.crescimento, c = candCr, k = R.contagem[c] || {};
    botoes($("rx-cresc-cand"), [[A, curto(A)], [B, curto(B)]], c, function (v) { candCr = v; crescimento(); });
    $("rx-cresc-cards").innerHTML =
      card("Cidades: mais votos, % menor", n(k.vs_pd || 0), esc(curto(c)) + " ganhou votos mas caiu na porcentagem", COR[c]) +
      card("Cidades: menos votos, % maior", n(k.vd_ps || 0), esc(curto(c)) + " perdeu votos mas subiu na porcentagem", COR[c]) +
      card("Cidades: cresceu nos dois", n(k.ambos_s || 0), "mais votos e % maior") +
      card("Cidades: caiu nos dois", n(k.ambos_d || 0), "menos votos e % menor");
    var est = R.estados.slice().sort(function (x, y) { return (y[c].dp || 0) - (x[c].dp || 0); });
    tabela("rx-cresc-uf", ["Estado", "Votos 1º → 2º", "Variação", "% válidos 1º → 2º", "Variação", "Resultado", "Cidades: + votos − %", "Cidades: − votos + %"], est.map(function (r) {
      var x = r[c], dif = x.q === "vs_pd" || x.q === "vd_ps";
      return "<tr><td>" + UF[r.uf] + "</td><td>" + mi(x.v1, 2) + " → " + mi(x.v2, 2) + '</td><td class="' + (x.dv >= 0 ? "rx-pos" : "rx-neg") + '">' + sn(x.dv) + "</td><td>" + p1(x.p1) + " → " + p1(x.p2) + '</td><td class="' + (x.dp >= 0 ? "rx-pos" : "rx-neg") + '">' + pp(x.dp) + "</td><td>" + (dif ? "<b>" + QN[x.q] + "</b>" : QN[x.q]) + "</td><td>" + (r.cid_q ? n(r.cid_q[c].vs_pd) : "—") + "</td><td>" + (r.cid_q ? n(r.cid_q[c].vd_ps) : "—") + "</td></tr>";
    }));
    var ex = R.exemplos[c];
    var lin = function (e, i) { return "<tr><td>" + (i + 1) + ". " + cid(e) + "</td><td>" + n(e.v1) + " → " + n(e.v2) + "</td><td>" + p1(e.p1) + " → " + p1(e.p2) + "</td></tr>"; };
    var vazio = function (cols) { return ['<tr><td colspan="' + cols + '">Nenhuma cidade</td></tr>']; };
    $("rx-ex-a-tit").textContent = curto(c) + ": mais votos, % menor (maiores cidades)";
    $("rx-ex-b-tit").textContent = curto(c) + ": menos votos, % maior (maiores cidades)";
    tabela("rx-ex-a", ["Cidade", "Votos 1º → 2º", "% 1º → 2º"], ex.vs_pd.length ? ex.vs_pd.map(lin) : vazio(3));
    tabela("rx-ex-b", ["Cidade", "Votos 1º → 2º", "% 1º → 2º"], ex.vd_ps.length ? ex.vd_ps.map(lin) : vazio(3));
    $("rx-cresc-fonte").textContent = "Fonte: " + R.fonte + ". Dado das cidades: " + hora(R.totalizado) + ". Cobertura: " + n(R.cobertura.cidades) + " de " + n(R.cobertura.cidades_total) + " cidades finalizadas nos dois turnos. % = sobre os votos válidos de cada turno; no 1º turno os válidos incluem os outros 10 candidatos.";
  }

  function desenha() {
    $("rx-hora").textContent = hora(d.tse.totalizado_tse);
    $("rx-sub").textContent = "Presidente 2026 · apuração " + p2(d.tse.pct_secoes) + " das seções · " + curto(A) + " " + p2(d.tse.pct_validos[A]) + " x " + curto(B) + " " + p2(d.tse.pct_validos[B]);
    [saldo, concentracao, cenario, comparecimento, crescimento].forEach(function (f) {
      try { f(); } catch (e) { if (window.console) console.error(f.name, e); }
    });
  }

  function vivo(estado, txt) { var el = $("vivo"); el.dataset.estado = estado; el.querySelector("span").textContent = txt; }

  function carrega() {
    var pm = mapa ? Promise.resolve() : fetch("assets/mapa-br.json", { cache: "force-cache" }).then(function (r) { return r.json(); }).then(function (m) { mapa = m; }).catch(function () {});
    var pd = fetch("data/raiox.json?t=" + Date.now(), { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); });
    Promise.all([pd, pm]).then(function (x) {
      d = x[0];
      if (d.schema !== 1 || d.tipo !== "raiox") throw new Error("formato novo, atualize a página");
      $("faixa-erro").hidden = true;
      desenha();
      vivo(d.tse.final ? "final" : "vivo", d.tse.final ? "resultado final" : "atualizado " + hora(d.gerado_em).slice(6));
    }).catch(function (e) {
      $("faixa-erro").hidden = false;
      $("faixa-erro").textContent = "Não consegui carregar o Raio-X agora (" + e.message + "). Tento de novo em 2 min.";
      vivo("erro", "sem conexão");
    });
  }
  carrega();
  setInterval(carrega, 120000);
})();
