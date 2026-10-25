/* Exterior país a país (data/exterior.json, gerado por exterior/coletor_ext.py). */
(function () {
  "use strict";
  var CA = "13", CB = "22", dados = null, filtro = "apurados", ordem = "votos", abertos = {};
  var $ = function (id) { return document.getElementById(id); };
  var nf = new Intl.NumberFormat("pt-BR");
  var p1 = function (x) { return x == null ? "—" : x.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%"; };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };

  function nome(n) {
    var c = (dados.candidatos || []).filter(function (x) { return x.numero === n; })[0];
    var s = c ? c.nome_urna : n;
    return s.charAt(0) + s.slice(1).toLowerCase().replace(/ (\w)/g, function (m, l) { return " " + l.toUpperCase(); });
  }
  function hora(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: "America/Sao_Paulo" });
  }
  // parte de Lula entre Lula e Flávio no 1º turno (comparável com o 2º turno)
  function parte1(t) { return t && (t[CA] + t[CB]) ? 100 * t[CA] / (t[CA] + t[CB]) : null; }
  function mudou(p) { var a = parte1(p.primeiro_turno); return p.pct && a != null ? p.pct[CA] - a : null; }

  function barra(pct) {
    return pct ? '<div class="ex-mini"><span class="ba" style="width:' + pct[CA] + '%"></span><span class="bb" style="width:' + pct[CB] + '%"></span></div>' : "";
  }

  function total() {
    var t = dados.total;
    $("ex-total").hidden = false;
    if (!t.pct) {
      $("ex-cands").innerHTML = "";
      $("ex-barra").innerHTML = "";
      $("ex-base").innerHTML = "Nenhum boletim do exterior publicado ainda.";
      return;
    }
    var lid = t.pct[CA] >= t.pct[CB] ? CA : CB;
    $("ex-cands").innerHTML = [CA, CB].map(function (n) {
      var um = t.primeiro_turno ? " · 1º turno " + p1(t.primeiro_turno[n]) : "";
      return '<div class="pj-cand c' + n + (n === lid ? " lid" : "") + '"><div class="pj-nome">' + esc(nome(n)) + "<small>" + n + "</small></div>" +
        '<div class="pj-pct">' + p1(t.pct[n]) + '</div><div class="pj-votos">' + nf.format(t.votos[n] || 0) + " votos" + um + "</div></div>";
    }).join("");
    $("ex-barra").innerHTML = '<div class="pj-b"><span class="ba" style="width:' + t.pct[CA] + '%"></span><span class="bb" style="width:' + t.pct[CB] + '%"></span><span class="pj-meio"></span></div>';
    var pctSec = 100 * t.recebidas / t.secoes;
    $("ex-base").innerHTML = "<b>" + nf.format(t.recebidas) + "</b> de " + nf.format(t.secoes) + " seções (" + p1(pctSec) + ") · " +
      "<b>" + nf.format(t.comparecimento) + "</b> votantes · brancos " + nf.format(t.brancos) + " · nulos " + nf.format(t.nulos) +
      " · último boletim " + esc(t.ultimo || "—");
  }

  function comparacao() {
    var pv = dados.previsto || {}, m = pv.mesmas_cidades, t = dados.total;
    if (!m || !t.pct) { $("ex-comp").hidden = true; return; }
    $("ex-comp").hidden = false;
    $("ex-comp-sub").textContent = "Só nas " + m.cidades + " cidades que já mandaram boletim, para a comparação ser justa";
    var linhas = [];
    if (m.regra_inicial) linhas.push(["Previsto pela regra inicial da projeção", m.regra_inicial, ""]);
    if (m.projecao) linhas.push(["Previsto com as taxas medidas no Brasil", m.projecao, ""]);
    linhas.push(["Apurado nos boletins", t.pct, "ex-real"]);
    $("ex-comp-tab").querySelector("thead").innerHTML = "<tr><th></th><th>" + esc(nome(CA)) + "</th><th>" + esc(nome(CB)) + "</th><th>Diferença de " + esc(nome(CA)) + "</th></tr>";
    $("ex-comp-tab").querySelector("tbody").innerHTML = linhas.map(function (l) {
      var d = l[2] ? "" : (t.pct[CA] - l[1][CA]);
      var dtxt = d === "" ? "" : (d > 0 ? "+" : "") + d.toLocaleString("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 }) + " p.p.";
      return '<tr class="' + l[2] + '"><td>' + l[0] + '</td><td class="ex-c13">' + p1(l[1][CA]) + '</td><td class="ex-c22">' + p1(l[1][CB]) + "</td><td>" + (l[2] ? "" : "apurado " + dtxt) + "</td></tr>";
    }).join("");
  }

  function linha(p, cid) {
    var t1 = p.primeiro_turno, mud = mudou(p), pv = p.previsto && (p.previsto.projecao || p.previsto.regra_inicial);
    var nomeTxt = cid ? esc(p.cidade.charAt(0) + p.cidade.slice(1).toLowerCase())
      : '<span class="ex-seta">▸</span> <b>' + esc(p.pais) + "</b><small>" + esc(p.continente) + "</small>";
    var mudTxt = mud == null ? "—" : '<span class="ex-dif ' + (mud >= 0 ? "mais" : "menos") + '">' + (mud > 0 ? "+" : "") + mud.toLocaleString("pt-BR", { maximumFractionDigits: 1, minimumFractionDigits: 1 }) + "</span>";
    return "<td class=\"ex-nome\">" + nomeTxt + "</td>" +
      "<td>" + nf.format(p.recebidas) + "/" + nf.format(p.secoes) + "</td>" +
      '<td class="ex-c13">' + (p.pct ? p1(p.pct[CA]) : "—") + "</td>" +
      '<td class="ex-c22">' + (p.pct ? p1(p.pct[CB]) : "—") + "</td>" +
      "<td>" + barra(p.pct) + "</td>" +
      "<td>" + (p.validos ? nf.format(p.validos) : "—") + "</td>" +
      "<td>" + (t1 ? p1(t1[CA]) + " · " + p1(t1[CB]) : "—") + "</td>" +
      "<td>" + mudTxt + "</td>" +
      "<td>" + (pv ? p1(pv[CA]) : "—") + "</td>" +
      "<td>" + esc(p.ultimo ? p.ultimo.slice(-8, -3) : "—") + "</td>";
  }

  function ordenar(l) {
    var f = {
      votos: function (a, b) { return (b.validos || 0) - (a.validos || 0) || a.pais.localeCompare(b.pais); },
      lula: function (a, b) { return ((b.pct || {})[CA] || -1) - ((a.pct || {})[CA] || -1); },
      flavio: function (a, b) { return ((b.pct || {})[CB] || -1) - ((a.pct || {})[CB] || -1); },
      mudou: function (a, b) { return Math.abs(mudou(b) || 0) - Math.abs(mudou(a) || 0); },
      az: function (a, b) { return a.pais.localeCompare(b.pais, "pt-BR"); }
    }[ordem];
    return l.slice().sort(f);
  }

  function paises() {
    var l = dados.paises.filter(function (p) { return filtro === "todos" || p.recebidas > 0; });
    $("ex-paises").hidden = false;
    var com = dados.paises.filter(function (p) { return p.recebidas > 0; }).length;
    $("ex-paises-sub").textContent = com + " de " + dados.paises.length + " países já com boletim. 2º turno apurado, com o 1º turno ao lado. Clique num país para ver as cidades.";
    $("ex-tab").querySelector("thead").innerHTML = "<tr><th>País</th><th>Seções</th><th>" + esc(nome(CA).split(" ")[0]) + "</th><th>" + esc(nome(CB).split(" ")[0]) +
      "</th><th></th><th>Válidos</th><th>1º turno (" + esc(nome(CA).split(" ")[0]) + " · " + esc(nome(CB).split(" ")[0]) + ")</th><th>Mudou</th><th>Previsto " + esc(nome(CA).split(" ")[0]) + "</th><th>Boletim</th></tr>";
    var h = [];
    ordenar(l).forEach(function (p) {
      var ab = !!abertos[p.pais];
      h.push('<tr class="ex-pais' + (ab ? " ex-aberto" : "") + (p.recebidas ? "" : " ex-sem") + '" data-p="' + esc(p.pais) + '">' + linha(p) + "</tr>");
      if (ab) (p.cidades || []).forEach(function (c) { h.push('<tr class="ex-cid' + (c.recebidas ? "" : " ex-sem") + '">' + linha(c, true) + "</tr>"); });
    });
    $("ex-tab").querySelector("tbody").innerHTML = h.join("") || '<tr><td colspan="10">Nenhum país com boletim ainda.</td></tr>';
  }

  function desenha() {
    $("ex-hora").textContent = hora(dados.ultima_consulta_tse || dados.gerado_em);
    var v = $("vivo");
    v.dataset.estado = "vivo";
    v.querySelector("span").textContent = "parcial · consulta de hora em hora";
    total(); comparacao(); paises();
  }

  function carrega() {
    fetch("data/exterior.json?t=" + Date.now(), { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (d) { dados = d; $("faixa-erro").hidden = true; desenha(); }).catch(function () {
      if (!dados) { var e = $("faixa-erro"); e.hidden = false; e.textContent = "Os dados do exterior ainda não estão disponíveis. Tente de novo em alguns minutos."; }
    });
  }

  function grupo(id, attr, set) {
    $(id).addEventListener("click", function (ev) {
      var b = ev.target.closest("button"); if (!b) return;
      [].forEach.call($(id).querySelectorAll("button"), function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      set(b.dataset[attr]); if (dados) paises();
    });
  }
  grupo("ex-filtro", "f", function (v) { filtro = v; });
  grupo("ex-ord", "o", function (v) { ordem = v; });
  $("ex-tab").addEventListener("click", function (ev) {
    var tr = ev.target.closest("tr.ex-pais"); if (!tr) return;
    abertos[tr.dataset.p] = !abertos[tr.dataset.p]; paises();
  });
  carrega();
  setInterval(carrega, 120000);
})();
