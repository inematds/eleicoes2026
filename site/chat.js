/* Chat "Tire suas dúvidas" (26/10): pergunta -> /api/chat (Worker chama o Claude com os números do site).
   A conversa fica na sessão do navegador e é gravada de forma anônima no servidor para análise. */
(function () {
  "use strict";
  var CHAVE = "inema_eleicoes_chat_v1";
  var SUGESTOES = [
    "Como Lula ganhou 10 milhões de votos do 1º para o 2º turno?",
    "A coincidência de 38 mil votos prova alguma coisa?",
    "Em quais estados Flávio perdeu votos?",
    "As somas do TSE foram conferidas?",
    "Por que Flávio perdeu mesmo elegendo mais governadores?"
  ];
  var st = carrega();
  var el = {};

  function carrega() {
    try { var x = JSON.parse(sessionStorage.getItem(CHAVE)); if (x && x.msgs) return x; } catch (e) { /* sem sessionStorage */ }
    return { sessao: Math.random().toString(36).slice(2) + Date.now().toString(36), msgs: [], aberto: false };
  }
  function salva() { try { sessionStorage.setItem(CHAVE, JSON.stringify(st)); } catch (e) { /* ignora */ } }

  function h(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }

  // texto do modelo -> nós DOM (nunca innerHTML): **negrito**, [rótulo](url), URLs soltas, quebras de linha
  function rico(alvo, txt) {
    var re = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(https?:\/\/[^\s)<>"']+[^\s)<>"'.,;:!?])|\*\*([^*]+)\*\*/g, ult = 0, m;
    function texto(s) { s.split("\n").forEach(function (p, i) { if (i) alvo.appendChild(document.createElement("br")); if (p) alvo.appendChild(document.createTextNode(p)); }); }
    while ((m = re.exec(txt))) {
      texto(txt.slice(ult, m.index));
      if (m[4]) alvo.appendChild(h("strong", null, m[4]));
      else { var a = h("a", null, m[1] || m[3]); a.href = m[2] || m[3]; a.target = /eleicoes\.inema\.club/.test(a.href) ? "_self" : "_blank"; a.rel = "noopener"; alvo.appendChild(a); }
      ult = re.lastIndex;
    }
    texto(txt.slice(ult));
  }

  function bolha(m) {
    var b = h("div", "ch-msg " + (m.role === "user" ? "eu" : "ia"));
    if (m.role === "user") b.textContent = m.content; else rico(b, m.content);
    el.lista.appendChild(b);
    return b;
  }

  function desenha() {
    el.lista.textContent = "";
    if (!st.msgs.length) {
      var ini = h("div", "ch-ini");
      ini.appendChild(h("p", null, "Pergunte sobre os números da eleição: votos, estados, cidades, a virada do 2º turno, a conferência das somas. As respostas usam só os dados oficiais do TSE deste site e dizem de qual página vêm."));
      var sg = h("div", "ch-sug");
      SUGESTOES.forEach(function (s) { var b = h("button", null, s); b.type = "button"; b.onclick = function () { envia(s); }; sg.appendChild(b); });
      ini.appendChild(sg);
      el.lista.appendChild(ini);
    } else st.msgs.forEach(bolha);
    el.lista.scrollTop = el.lista.scrollHeight;
  }

  function abre(sim) {
    st.aberto = sim; salva();
    el.painel.hidden = !sim; el.botao.hidden = sim;
    document.documentElement.classList.toggle("ch-aberto", sim);
    if (sim) { desenha(); setTimeout(function () { el.campo.focus(); }, 50); }
  }

  var ocupado = false;
  function envia(txt) {
    txt = (txt || el.campo.value).trim();
    if (!txt || ocupado) return;
    if (txt.length > 1500) txt = txt.slice(0, 1500);
    el.campo.value = ""; ajusta();
    if (!st.msgs.length) el.lista.textContent = "";
    st.msgs.push({ role: "user", content: txt }); salva(); bolha(st.msgs[st.msgs.length - 1]);
    var dig = h("div", "ch-msg ia dig"); dig.appendChild(h("i")); dig.appendChild(h("i")); dig.appendChild(h("i")); dig.appendChild(h("span", null, "consultando os números…"));
    el.lista.appendChild(dig); el.lista.scrollTop = el.lista.scrollHeight;
    ocupado = true; el.enviar.disabled = true;
    fetch("/api/chat", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ sessao: st.sessao, pagina: location.pathname + location.hash, historico: st.msgs.slice(-12) })
    }).then(function (r) { return r.json(); }).then(function (x) {
      return x.resposta || "Não consegui responder agora. Tente de novo em instantes.";
    }).catch(function () {
      return "Sem conexão com o chat agora. Tente de novo em instantes.";
    }).then(function (resp) {
      dig.remove();
      st.msgs.push({ role: "assistant", content: resp }); salva(); bolha(st.msgs[st.msgs.length - 1]);
      el.lista.scrollTop = el.lista.scrollHeight;
      ocupado = false; el.enviar.disabled = false; el.campo.focus();
    });
  }

  function ajusta() { el.campo.style.height = "auto"; el.campo.style.height = Math.min(el.campo.scrollHeight, 140) + "px"; }

  function monta() {
    el.botao = h("button", "ch-botao"); el.botao.type = "button";
    el.botao.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v11H10l-5 4v-4H4z"/><path d="M8 9.5h8M8 12.5h5"/></svg><span><b>Tire suas dúvidas</b><small>pergunte sobre os números</small></span>';
    el.botao.onclick = function () { abre(true); };

    el.painel = h("aside", "ch-painel"); el.painel.setAttribute("aria-label", "Chat Tire suas dúvidas"); el.painel.hidden = true;
    var cab = h("div", "ch-cab");
    var tit = h("div", "ch-tit"); tit.appendChild(h("b", null, "Tire suas dúvidas")); tit.appendChild(h("small", null, "IA (Claude) responde com os números do TSE deste site"));
    var novo = h("button", "ch-novo", "Nova conversa"); novo.type = "button"; novo.onclick = function () { st.msgs = []; st.sessao = Math.random().toString(36).slice(2) + Date.now().toString(36); salva(); desenha(); };
    var fecha = h("button", "ch-fecha", "×"); fecha.type = "button"; fecha.setAttribute("aria-label", "Fechar o chat"); fecha.onclick = function () { abre(false); };
    cab.appendChild(tit); cab.appendChild(novo); cab.appendChild(fecha);
    el.lista = h("div", "ch-lista"); el.lista.setAttribute("aria-live", "polite");
    var form = h("form", "ch-form");
    el.campo = h("textarea"); el.campo.rows = 1; el.campo.maxLength = 1500; el.campo.placeholder = "Escreva sua pergunta…";
    el.campo.addEventListener("input", ajusta);
    el.campo.addEventListener("keydown", function (e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); envia(); } });
    el.enviar = h("button", "ch-enviar", "Enviar"); el.enviar.type = "submit";
    form.onsubmit = function (e) { e.preventDefault(); envia(); };
    form.appendChild(el.campo); form.appendChild(el.enviar);
    var aviso = h("p", "ch-aviso", "As conversas são gravadas de forma anônima (sem nome nem endereço IP) para melhorar as análises. Não escreva dados pessoais. A IA pode errar: confira nas páginas citadas.");
    el.painel.appendChild(cab); el.painel.appendChild(el.lista); el.painel.appendChild(form); el.painel.appendChild(aviso);
    document.body.appendChild(el.botao); document.body.appendChild(el.painel);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && st.aberto) abre(false); });
    abre(!!st.aberto);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", monta); else monta();
})();
