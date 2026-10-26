/* Conferência dos resultados (data/conferencia.json, gerado por analise/conferencia.py). */
(function () {
  "use strict";
  var A = "13", B = "22", d = null, eixo = "hora";
  var $ = function (id) { return document.getElementById(id); };
  var nf = new Intl.NumberFormat("pt-BR");
  var n = function (x) { return x == null ? "—" : nf.format(x); };
  var p2 = function (x) { return x == null ? "—" : x.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + "%"; };
  var pp = function (x) { return x == null ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " p.p."; };
  var sn = function (x) { return x == null ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + nf.format(Math.abs(x)); };
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var ST = { conferido: "✓ Conferido", pendente: "… Pendente", divergencia: "! Divergência reproduzida", insuficiente: "? Dados insuficientes" };
  var NOME = { "13": "Lula", "22": "Flávio" };

  function hora(iso) { return iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + " " + iso.slice(11, 16) : "—"; }
  function hm(iso) { return iso ? iso.slice(11, 16) : "—"; }
  function chip(st) { return '<b class="cf-st ' + esc(st) + '">' + esc(ST[st] || st) + "</b>"; }
  function frac(a, b) { return n(a) + " de " + n(b); }
  function card(tit, val, sub, st) { return '<div class="cf-card' + (st ? " " + st : "") + '"><div class="t">' + tit + '</div><div class="v num">' + val + '</div><div class="s">' + sub + "</div></div>"; }
  function tabela(id, cab, linhas) {
    $(id).querySelector("thead").innerHTML = "<tr>" + cab.map(function (c) { return "<th>" + c + "</th>"; }).join("") + "</tr>";
    $(id).querySelector("tbody").innerHTML = linhas.join("");
  }
  function difcel(x) { return '<td class="' + (x ? "cf-dif" : "cf-ok") + '">' + (x ? sn(x) : "0") + "</td>"; }

  // ---------- resumo ----------
  function resumo() {
    var r = d.resumo, tot = d.itens.length;
    $("cf-resumo-sub").textContent = tot + " conferências nesta fase · refeitas em " + hora(d.gerado_em) + " com os arquivos do TSE de " + hora(d.tse.totalizado_tse) + ".";
    $("cf-cards").innerHTML =
      card("Conferido", n(r.conferido), "de " + tot + " itens", "conferido") +
      card("Pendente", n(r.pendente), "aguardando arquivo ou fim da apuração", "pendente") +
      card("Divergência reproduzida", n(r.divergencia), r.divergencia ? "ver detalhes abaixo" : "nenhuma até agora", "divergencia") +
      card("Dados insuficientes", n(r.insuficiente), "sem informação para classificar", "insuficiente");
    tabela("cf-itens", ["Item", "Situação", "Conferidos / total", "Horário", "Critério"], d.itens.map(function (i) {
      return "<tr><td>" + esc(i.titulo) + "</td><td>" + chip(i.status) + '</td><td class="num">' + (i.num == null ? "—" : frac(i.num, i.den)) + "</td><td>" + hora(i.horario) + '</td><td class="cf-crit">' + esc(i.criterio) + "</td></tr>";
    }));
  }

  // ---------- somas ----------
  function somas() {
    var b = d.brasil, a = b.atual, m = b.momentos;
    if (a) {
      $("cf-br-st").innerHTML = chip(a.status);
      $("cf-br-motivo").textContent = a.motivo + " Arquivo do Brasil: TSE " + hora(a.br_totalizado) + "; estados e exterior: de " + hora(a.ufs_totalizado_de) + " a " + hora(a.ufs_totalizado_ate) + ".";
      tabela("cf-br", ["Campo", "Arquivo do Brasil", "Soma UFs + exterior", "Diferença"], a.campos.map(function (c) {
        return "<tr><td>" + esc(c.campo) + '</td><td class="num">' + n(c.oficial) + '</td><td class="num">' + n(c.soma) + "</td>" + difcel(c.dif) + "</tr>";
      }));
    }
    if (m) {
      var t = "Momentos guardados da noite: " + n(m.arquivos_br) + " arquivos do Brasil baixados. Em " + n(m.comparaveis) + " deles todos os 28 arquivos (27 UFs + exterior) estavam na mesma atualização (mesma soma de seções) e " +
        (m.n_divergentes ? n(m.n_divergentes) + " NÃO bateram campo a campo; " : "") + n(m.conferidos) + " bateram em todos os campos";
      if (m.ultimo_conferido) t += " — o último às " + hm(m.ultimo_conferido.t) + ", com " + n(m.ultimo_conferido.secoes) + " seções (" + p2(m.ultimo_conferido.pct_secoes) + ")";
      t += ". Os outros " + n(m.sem_par) + " eram de horários diferentes e não dá para comparar.";
      if (m.bloqueados.length) t += " " + n(m.bloqueados.length) + " arquivos do Brasil ficaram de fora por terem sido bloqueados pelo próprio INEMA (veja o item 2).";
      $("cf-br-mom").innerHTML = chip(m.status) + " " + esc(t);
    }
    var conf = d.ufs.filter(function (u) { return u.status === "conferido"; }), cad = d.ufs.filter(function (u) { return u.cadastro_ok; }).length;
    $("cf-uf-txt").textContent = n(conf.length) + " de " + d.ufs.length + " estados já conferidos (" + (conf.map(function (u) { return u.uf.toUpperCase(); }).join(", ") || "nenhum") + "). Em " + cad + " de " + d.ufs.length + " estados, o eleitorado e o número de seções previstas das cidades somam exatamente o do estado (isso não depende da apuração).";
    var ord = { divergencia: 0, conferido: 1, pendente: 2, insuficiente: 3 };
    var lista = d.ufs.slice().sort(function (x, y) { return (ord[x.status] - ord[y.status]) || x.nome.localeCompare(y.nome); });
    tabela("cf-uf", ["Estado", "Situação", "Cidades finais", "Seções do estado", "Dif. Lula", "Dif. Flávio", "Dif. brancos", "Dif. nulos", "Dif. total", "Motivo"], lista.map(function (u) {
      if (!u.campos) return "<tr><td>" + esc(u.nome) + "</td><td>" + chip(u.status) + '</td><td colspan="8">' + esc(u.motivo) + "</td></tr>";
      var dc = function (nm) { var c = u.campos.filter(function (x) { return x.campo === nm; })[0]; return c ? c.dif : null; };
      var comp = u.status === "conferido" || u.status === "divergencia";
      var cel = function (nm) { var v = dc(nm); return comp ? difcel(v) : '<td class="cf-mut num" title="soma parcial, ainda não comparável">' + sn(v) + "</td>"; };
      return "<tr><td>" + esc(u.nome) + (u.bloqueadas && u.bloqueadas.length ? ' <small title="cidades em que a coleta por cidade do INEMA bloqueou o arquivo">(' + u.bloqueadas.length + " bloq.)</small>" : "") + "</td><td>" + chip(u.status) + '</td><td class="num">' + frac(u.finalizadas, u.cidades) + '</td><td class="num">' + frac(u.uf_secoes, u.uf_secoes_total) + "</td>" +
        cel("Votos de Lula (13)") + cel("Votos de Flávio (22)") + cel("Brancos") + cel("Nulos") + cel("Total de votos") + '<td class="cf-crit">' + esc(u.motivo) + "</td></tr>";
    }));
  }

  // ---------- integridade ----------
  function integridade() {
    var g = d.integridade, mf = g.manifesto;
    var bl = g.bloqueios || [];
    $("cf-integ-cards").innerHTML =
      card("Arquivos do TSE guardados", n(g.arquivos), "sha256 confere em " + frac(g.sha_conferidos, g.arquivos), g.sha_errados.length ? "divergencia" : "conferido") +
      card("Downloads no registro", n(g.log_downloads), (g.log_faltando_em_disco.length ? n(g.log_faltando_em_disco.length) + " sem arquivo em disco" : "todos com o arquivo em disco"), g.log_faltando_em_disco.length ? "divergencia" : "conferido") +
      card("Versões publicadas", n(g.publicacoes), "a última, nº " + n(g.ultima_versao) + ", às " + hm(g.ultima_publicacao)) +
      card("Publicados agora com original", frac(mf.com_original, mf.arquivos), "arquivos do painel com o original do TSE guardado", mf.sem_original.length ? "divergencia" : "conferido") +
      card("Bloqueios automáticos", n(bl.length), bl.length ? "arquivos que não foram para o painel" : "nenhum") +
      card("Erros de coleta", n(g.n_erros), "falhas de rede registradas");
    var MOT = function (p) {
      return p.map(function (x) {
        return /seções totalizadas diminuíram/.test(x) ? "as seções apuradas diminuíram" : /total de votos diminuiu/.test(x) ? "o total de votos diminuiu" : /voltou no tempo/.test(x) ? "a hora do arquivo voltou no tempo" : /soma/.test(x) ? "a soma não fecha (" + x + ")" : x;
      }).join("; ");
    };
    tabela("cf-bloq", ["Horário", "Arquivo", "Motivo", "O que significa"], bl.length ? bl.map(function (x) {
      var velho = (x.problemas || []).some(function (p) { return /diminu|voltou/.test(p); });
      return "<tr><td>" + hora(x.t) + "</td><td>" + esc((x.abr || "").toUpperCase()) + ' <small class="cf-mono">' + esc(x.sha || "") + '</small></td><td class="cf-crit">' + esc(MOT(x.problemas || [])) + '</td><td class="cf-crit">' + (velho ? "Cópia mais antiga entregue pelo TSE; o painel manteve a versão mais nova." : "Arquivo segurado até a conta fechar.") + "</td></tr>";
    }) : ['<tr><td colspan="4">Nenhum bloqueio registrado.</td></tr>']);
    $("cf-integ-nota").textContent = "Também ficam no registro " + n(g.consultas_indice) + " consultas ao índice do TSE e " + n(g.avisos_br_soma) + " avisos de que o arquivo do Brasil ainda não batia com a soma dos estados (normal durante a apuração, quando os arquivos são de horários diferentes). sha256 recalculado em " + hora(d.gerado_em) + ".";
  }

  // ---------- exterior ----------
  function exterior() {
    var e = d.exterior;
    $("cf-ext-st").innerHTML = chip(e.status);
    if (!e.campos) { $("cf-ext-motivo").textContent = e.motivo; return; }
    $("cf-ext-sub").textContent = "Soma do INEMA, seção a seção (boletins até " + (e.bu_ultimo_boletim || "—") + ") x total oficial do TSE para o exterior (" + hora(e.oficial_totalizado) + ", " + frac(e.oficial_secoes, e.oficial_secoes_total) + " seções)";
    $("cf-ext-barra").style.width = Math.min(100, e.cobertura || 0) + "%";
    $("cf-ext-cob").innerHTML = "<b>" + p2(e.cobertura) + "</b> de cobertura · boletim lido em " + frac(e.recebidas, e.secoes) + " seções";
    $("cf-ext-motivo").textContent = e.motivo;
    tabela("cf-ext-tab", ["Campo", "Soma dos boletins", "Total oficial TSE", "Diferença", "Parcial ≤ oficial?"], e.campos.map(function (c) {
      var ok = c.boletins <= c.oficial;
      return "<tr><td>" + esc(c.campo) + '</td><td class="num">' + n(c.boletins) + '</td><td class="num">' + n(c.oficial) + '</td><td class="num">' + sn(c.dif) + "</td><td>" + (ok ? '<span class="cf-ok">✓ sim</span>' : '<span class="cf-dif">! não</span>') + "</td></tr>";
    }));
  }

  // ---------- projeção ----------
  function projecao() {
    var p = d.projecao;
    if (!p.serie) { $("cf-proj").hidden = true; return; }
    var nm = NOME[p.candidato] || p.candidato, venc = NOME[p.vencedor] || p.vencedor;
    var dz = p.desde, df = p.desde_faixa, dt = p.desde_tse;
    $("cf-proj-cards").innerHTML =
      card("Apontou " + esc(venc) + " desde", hm(dz && dz.t), dz ? "com " + p2(dz.tse_secoes) + " das seções apuradas, sem mudar mais" : "—", "conferido") +
      card("Faixa toda acima de 50% desde", hm(df && df.t), df ? "faixa de " + p2(df.lo) + " a " + p2(df.hi) : "—") +
      card("Apuração do TSE passou de 50% às", hm(dt && dt.t), dt ? "com " + p2(dt.tse_secoes) + " das seções" : "—") +
      card("Erro da 1ª projeção", pp(p.erro_primeira), "projetou " + p2(p.primeira.a) + " às " + hm(p.primeira.t)) +
      card("Erro da última projeção", pp(p.erro_ultima), "projetou " + p2(p.ultima.a) + " às " + hm(p.ultima.t)) +
      card("Resultado dentro da faixa", p2(p.faixa_pct), frac(p.faixa_dentro, p.faixa_n) + " cálculos", "conferido");
    botoes();
    grafico();
    $("cf-proj-txt").textContent = "Resultado usado na comparação: " + nm + " com " + p2(p.final) + " dos votos válidos (TSE " + hora(p.final_totalizado) + ", " + p2(p.final_secoes_pct) + " das seções). " +
      p.entradas + " cálculos guardados de " + hm(p.inicio) + " a " + hm(p.fim) + ", modelo versão " + p.versoes.join(", ") + ". Erro médio " + pp(p.erro_medio) + " (sinal = para que lado errou), erro médio sem sinal " + pp(p.erro_medio_abs).replace("+", "") + ", maior erro " + pp(p.erro_max_abs).replace("+", "") +
      "; na hora da 1ª projeção, a contagem do TSE mostrava " + p2(p.primeira.tse_a) + " (" + pp(p.erro_tse_primeira) + " do resultado).";
    var lista = p.ufs.slice().sort(function (x, y) { return x.nome.localeCompare(y.nome); });
    tabela("cf-puf", ["Estado", "Apurado TSE", "1ª projeção do estado", "Erro da 1ª", "Última projeção", "Erro da última"], lista.map(function (u) {
      return "<tr><td>" + esc(u.nome) + '</td><td class="num">' + p2(u.apurado) + " <small>" + p2(u.secoes_pct) + " seç.</small></td><td class=\"num\">" + p2(u.primeira) + " <small>" + hm(u.primeira_t) + " · TSE " + p2(u.primeira_tse_secoes) + '</small></td><td class="num">' + pp(u.erro_primeira) + '</td><td class="num">' + p2(u.ultima) + '</td><td class="num">' + pp(u.erro_ultima) + "</td></tr>";
    }));
    $("cf-proj-nota").textContent = "Erro = projeção menos apurado, em pontos percentuais dos votos válidos de " + nm + ". Erro médio sem sinal: " + pp(p.ufs_erro_medio_primeira).replace("+", "") + " na 1ª projeção de cada estado e " + pp(p.ufs_erro_medio_ultima).replace("+", "") + " na última (que já saiu com o estado quase todo apurado). “TSE x%” = parte do país apurada naquele momento. O resultado final ainda pode mudar algumas décimas até o TSE fechar a totalização.";
  }

  function botoes() {
    var el = $("cf-eixo");
    el.innerHTML = [["hora", "Por hora"], ["secoes", "Por % de seções"]].map(function (i) { return '<button type="button" data-v="' + i[0] + '" aria-pressed="' + (i[0] === eixo) + '">' + i[1] + "</button>"; }).join("");
    el.onclick = function (ev) { var b = ev.target.closest("button"); if (b) { eixo = b.dataset.v; botoes(); grafico(); } };
  }

  function grafico() {
    var p = d.projecao, e = p.serie.filter(function (x) { return eixo === "hora" || x.tse_secoes != null; });
    if (e.length < 2) { $("cf-graf").innerHTML = ""; return; }
    var cel = window.innerWidth < 640;
    var W = Math.max(320, Math.min(1100, $("cf-graf").clientWidth || 900)), H = cel ? 240 : 280, pl = 44, pr = cel ? 12 : 96, pt = 12, pb = 30;
    var xs = e.map(function (x) { return eixo === "hora" ? new Date(x.t).getTime() : x.tse_secoes; });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    var vals = [];
    e.forEach(function (x) { [x.lo, x.hi, x.tse_a, x.a].forEach(function (v) { if (v != null) vals.push(v); }); });
    vals.push(50, p.final);
    var y0 = Math.floor(Math.min.apply(null, vals) * 2 - 0.5) / 2, y1 = Math.ceil(Math.max.apply(null, vals) * 2 + 0.5) / 2;
    var X = function (v) { return pl + ((v - x0) / Math.max(1e-9, x1 - x0)) * (W - pl - pr); };
    var Y = function (v) { return pt + (1 - (v - y0) / (y1 - y0)) * (H - pt - pb); };
    var area = e.map(function (x, i) { return X(xs[i]) + "," + Y(x.hi); }).join(" ") + " " + e.map(function (x, i) { return X(xs[i]) + "," + Y(x.lo); }).reverse().join(" ");
    var linha = function (k) { return e.map(function (x, i) { return x[k] == null ? null : X(xs[i]).toFixed(1) + "," + Y(x[k]).toFixed(1); }).filter(Boolean).join(" "); };
    var g = "";
    for (var v = Math.ceil(y0); v <= y1; v += 1) g += '<line x1="' + pl + '" x2="' + (W - pr) + '" y1="' + Y(v) + '" y2="' + Y(v) + '" class="g"/><text x="' + (pl - 6) + '" y="' + (Y(v) + 4) + '" class="ty">' + v + "%</text>";
    var tx = function (v) { return eixo === "hora" ? new Date(v).toTimeString().slice(0, 5) : Math.round(v) + "%"; };
    var ticks = "";
    for (var k = 0; k <= 4; k++) { var tv = x0 + (x1 - x0) * k / 4; ticks += '<text x="' + X(tv) + '" y="' + (H - 10) + '" class="tx" text-anchor="' + (k === 0 ? "start" : k === 4 ? "end" : "middle") + '">' + tx(tv) + "</text>"; }
    var rot = function (y, txt, cls) { return cel ? "" : '<text x="' + (W - pr + 6) + '" y="' + (y + 4) + '" class="cf-rot ' + cls + '">' + txt + "</text>"; };
    var last = e[e.length - 1];
    $("cf-graf").innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Projeção INEMA ao longo da noite comparada com o resultado apurado">' + g +
      '<line x1="' + pl + '" x2="' + (W - pr) + '" y1="' + Y(50) + '" y2="' + Y(50) + '" class="m50"/>' +
      '<polygon points="' + area + '" class="ar"/>' +
      '<line x1="' + pl + '" x2="' + (W - pr) + '" y1="' + Y(p.final) + '" y2="' + Y(p.final) + '" class="cf-fin"/>' +
      '<polyline points="' + linha("tse_a") + '" class="lt"/><polyline points="' + linha("a") + '" class="lp"/>' +
      rot(Y(50), "50%", "m") + rot(Y(p.final) - 8, "resultado", "f") + rot(Y(last.a) + 10, "projeção", "p") +
      ticks + "</svg>";
    $("cf-graf-leg").innerHTML =
      '<span><i class="lp"></i>Projeção INEMA (% de ' + esc(NOME[p.candidato] || p.candidato) + ")</span>" +
      '<span><i class="ar"></i>Faixa da projeção</span>' +
      '<span><i class="lt"></i>Apurado pelo TSE naquele momento</span>' +
      '<span><i class="fin"></i>Resultado apurado agora (' + p2(p.final) + ")</span>" +
      '<span><i class="m50"></i>Linha de 50%</span>' +
      "<span>Eixo: " + (eixo === "hora" ? "hora da noite" : "% das seções apuradas pelo TSE") + "</span>";
  }

  function desenha() {
    $("cf-hora").textContent = hora(d.tse.totalizado_tse);
    $("cf-sub").textContent = "Presidente 2026 · fase inicial · apuração " + p2(d.tse.pct_secoes) + " das seções (" + n(d.tse.secoes) + " de " + n(d.tse.secoes_total) + ")";
    resumo(); somas(); integridade(); exterior(); projecao();
  }

  function vivo(estado, txt) { var el = $("vivo"); el.dataset.estado = estado; el.querySelector("span").textContent = txt; }

  function carrega() {
    fetch("data/conferencia.json?t=" + Date.now(), { cache: "no-store" }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(function (x) {
      if (x.schema !== 1 || x.tipo !== "conferencia") throw new Error("formato novo, atualize a página");
      d = x;
      $("faixa-erro").hidden = true;
      desenha();
      vivo(d.tse.final ? "final" : "vivo", d.tse.final ? "resultado final" : "conferido " + hora(d.gerado_em).slice(6));
    }).catch(function (e) {
      $("faixa-erro").hidden = false;
      $("faixa-erro").textContent = "Não consegui carregar a conferência agora (" + e.message + "). Tento de novo em 2 min.";
      vivo("erro", "sem conexão");
    });
  }
  var rt;
  window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(function () { if (d) grafico(); }, 200); });
  carrega();
  setInterval(carrega, 120000);
})();
