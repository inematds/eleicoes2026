/* Contador de acessos: soma 1 na primeira visita da sessão do navegador (POST) e só lê nas outras (GET).
   Sem polling. Se /api/acessos não responder (ex.: servidor local), o contador fica escondido. */
(function () {
  "use strict";
  var CHAVE = "inema-acesso-contado", ja = false;
  try { ja = sessionStorage.getItem(CHAVE) === "1"; } catch (e) {}
  fetch("/api/acessos", { method: ja ? "GET" : "POST", cache: "no-store" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (j) {
      if (typeof j.acessos !== "number") return;
      try { sessionStorage.setItem(CHAVE, "1"); } catch (e) {}
      var t = new Intl.NumberFormat("pt-BR").format(j.acessos);
      document.querySelectorAll("[data-acessos]").forEach(function (el) { el.querySelector("b").textContent = t; el.hidden = false; });
    })
    .catch(function () {});
})();
