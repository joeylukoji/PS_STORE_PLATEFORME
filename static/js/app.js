// PS STORE — interactions côté client (amélioration progressive : tout fonctionne sans JS).
(function () {
  "use strict";

  // Menu mobile
  document.querySelectorAll(".menu-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var nav = document.getElementById(btn.getAttribute("aria-controls"));
      var open = nav.classList.toggle("open");
      btn.setAttribute("aria-expanded", open);
    });
  });

  // Barre de recherche
  document.querySelectorAll("[data-toggle-search]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var bar = document.getElementById(btn.getAttribute("aria-controls"));
      var open = bar.classList.toggle("open");
      btn.setAttribute("aria-expanded", open);
      if (open) bar.querySelector("input").focus();
    });
  });

  // Fermeture des messages
  document.querySelectorAll(".alert-close").forEach(function (btn) {
    btn.addEventListener("click", function () { btn.parentElement.remove(); });
  });

  // Sélecteurs de quantité +/-
  document.querySelectorAll("[data-qty]").forEach(function (box) {
    var input = box.querySelector("input[type=number]");
    box.querySelectorAll("[data-step]").forEach(function (b) {
      b.addEventListener("click", function () {
        var min = parseInt(input.min || "0", 10);
        var max = input.max ? parseInt(input.max, 10) : Infinity;
        var v = (parseInt(input.value, 10) || 0) + parseInt(b.dataset.step, 10);
        input.value = Math.max(min, Math.min(max, v));
        input.dispatchEvent(new Event("change", { bubbles: true }));
      });
    });
  });

  // Soumission automatique des filtres et quantités du panier
  document.querySelectorAll("form[data-autosubmit]").forEach(function (form) {
    var timer;
    form.addEventListener("change", function () {
      clearTimeout(timer);
      timer = setTimeout(function () { form.requestSubmit ? form.requestSubmit() : form.submit(); }, 350);
    });
  });

  // Chips de plateforme : état visuel immédiat
  document.querySelectorAll(".chips input[type=radio]").forEach(function (r) {
    r.addEventListener("change", function () {
      r.closest(".chips").querySelectorAll(".chip").forEach(function (c) { c.classList.remove("active"); });
      r.parentElement.classList.add("active");
    });
  });

  // Galerie produit
  var main = document.getElementById("main-img");
  document.querySelectorAll(".thumb[data-src]").forEach(function (t) {
    t.addEventListener("click", function () {
      if (main) main.src = t.dataset.src;
      document.querySelectorAll(".thumb").forEach(function (x) { x.classList.remove("active"); });
      t.classList.add("active");
    });
  });

  // Champs adresse visibles seulement pour la livraison
  var delivery = document.getElementById("delivery-fields");
  if (delivery) {
    var radios = document.querySelectorAll("input[name=delivery_mode]");
    var sync = function () {
      var checked = document.querySelector("input[name=delivery_mode]:checked");
      delivery.hidden = !checked || checked.value !== "livraison";
    };
    radios.forEach(function (r) { r.addEventListener("change", sync); });
    sync();
  }

  // Confirmations
  document.querySelectorAll("form[data-confirm]").forEach(function (f) {
    f.addEventListener("submit", function (e) { if (!confirm(f.dataset.confirm)) e.preventDefault(); });
  });
  document.querySelectorAll("form[data-confirm-cancel]").forEach(function (f) {
    f.addEventListener("submit", function (e) {
      if (f.status.value === "annulee" && !confirm("Annuler cette commande ? Les articles seront remis en stock.")) e.preventDefault();
    });
  });

  // Copier la référence de commande
  document.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var text = document.querySelector(b.dataset.copy).textContent.trim();
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(function () { b.textContent = "Copié !"; });
    });
  });
})();
