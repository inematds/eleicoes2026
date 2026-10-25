/* Botão Compartilhar (25/10): só no navegador, sem servidor e sem custo.
   Celular → menu de compartilhar do aparelho; computador → copia o link.
   Compartilha a página atual (com o estado aberto no #), sem o ?sim=1. */
(function () {
  "use strict";
  var TITULO = "INEMA Eleições 2026 — 2º Turno ao vivo";
  var TEXTO = "Apuração do 2º turno com dados oficiais do TSE, em tempo real:";

  function link() {
    var u = new URL(location.href);
    u.searchParams.delete("sim");
    return u.toString();
  }

  function aviso(btn, txt) {
    var s = btn.querySelector("span");
    var antes = s.textContent;
    s.textContent = txt;
    setTimeout(function () { s.textContent = antes; }, 2200);
  }

  function copiar(btn, url) {
    var ok = function () { aviso(btn, "Link copiado"); };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(url).then(ok, function () { prompt("Copie o link:", url); });
    } else {
      prompt("Copie o link:", url);
    }
  }

  document.querySelectorAll("[data-compartilhar]").forEach(function (btn) {
    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      var url = link();
      if (navigator.share) {
        navigator.share({ title: TITULO, text: TEXTO, url: url }).catch(function (e) {
          if (e && e.name !== "AbortError") copiar(btn, url);
        });
      } else {
        copiar(btn, url);
      }
    });
  });
})();
