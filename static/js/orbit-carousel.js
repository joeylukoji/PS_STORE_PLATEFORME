// Carrousel orbital de l'accueil — portage en JavaScript du composant Dish Orbit Carousel.
// Le visuel courant sort par le haut sur une large orbite pendant que le suivant arrive de l'autre côté ;
// le titre s'efface puis réapparaît, la carte se fond, et la bande pastel tourne en prenant la couleur de l'univers.
// Le défilement de la page pilote le carrousel (section épinglée) ; flèches, vignettes, pastilles,
// touches fléchées et balayage permettent aussi de changer d'univers.
(function () {
  "use strict";

  var track = document.querySelector("[data-orbit]");
  var dataEl = document.getElementById("orbit-data");
  if (!track || !dataEl || !window.gsap || !window.ScrollTrigger) return;
  gsap.registerPlugin(ScrollTrigger);

  var items = JSON.parse(dataEl.textContent);
  var n = items.length;
  var root = track.querySelector(".dsh-root");
  // Pas de boucle : après le dernier univers, le défilement reprend normalement vers la suite de la page.
  var loop = false;

  // --- utilitaires (identiques au composant) ---
  function wrapIndex(i, len) { return len <= 0 ? 0 : ((Math.round(i) % len) + len) % len; }
  function stepDirection(from, to, len) {
    if (len <= 0) return 1;
    var fwd = (((to - from) % len) + len) % len;
    return fwd <= len - fwd ? 1 : -1;
  }
  function scrollSteps(len, lp) { return Math.max(0, lp ? len : len - 1); }
  function segmentFor(i, current, len, lp) { return lp && i === 0 && current > len / 2 ? len : i; }
  function stripStart(index, len, visible) {
    if (len <= visible) return 0;
    return Math.max(0, Math.min(index - 1, len - visible));
  }
  function fitSize(chars, max, width, em) { return Math.min(max, width / (Math.max(1, chars) * em)); }
  function arcPath(a0, a1, cx, cy, r, w, steps) {
    steps = steps || 48;
    var outer = [], inner = [];
    for (var i = 0; i <= steps; i++) {
      var t = i / steps;
      var a = ((a0 + (a1 - a0) * t) * Math.PI) / 180;
      var h = (w / 2) * Math.pow(Math.sin(Math.PI * t), 0.45);
      var c = Math.cos(a), s = Math.sin(a);
      outer.push((cx + c * (r + h)).toFixed(1) + " " + (cy + s * (r + h)).toFixed(1));
      inner.push((cx + c * (r - h)).toFixed(1) + " " + (cy + s * (r - h)).toFixed(1));
    }
    return "M" + outer.join("L") + "L" + inner.reverse().join("L") + "Z";
  }
  var ARC_REST = [[50, 98], [46, 124], [60, 126], [40, 100]];
  function arcRest(i) { return ARC_REST[((i % ARC_REST.length) + ARC_REST.length) % ARC_REST.length]; }
  var ARC_SWEEP = [38, 146];

  var ORBIT_X = 299, ORBIT_Y = -450, ORBIT_R = 650;
  var SCROLL_PER_ITEM = 0.7, SWING = 50, ITEM = 118, VISIBLE = 4;
  var HIDE_1 = "inset(0% 0% 0% 100%)", HIDE_2 = "inset(0% 100% 0% 0%)", SHOW = "inset(0% 0% 0% 0%)";

  // --- éléments ---
  var orbits = root.querySelectorAll(".dsh-orbit");
  var heads = root.querySelectorAll(".dsh-hd");
  var bodies = root.querySelectorAll(".dsh-body");
  var dots = root.querySelectorAll(".dsh-dot");
  var thumbs = root.querySelectorAll(".dsh-th .dsh-btn");
  var stripTrack = root.querySelector(".dsh-track");
  var arcEl = root.querySelector(".dsh-arc path");
  var card = root.querySelector(".dsh-card");
  var actUrl = root.querySelector('[data-act="url"]');
  var srEl = root.querySelector(".dsh-sr");

  // Tailles de titre ajustées à la largeur de la colonne.
  root.querySelectorAll("[data-fit]").forEach(function (el) {
    var p = el.dataset.fit.split(",").map(Number);
    el.style.fontSize = fitSize(el.textContent.trim().length, p[0], p[1], p[2]) + "px";
  });

  // Hauteur de la piste : une portion de défilement par univers.
  var steps = scrollSteps(n, loop);
  track.style.height = "calc((100svh - var(--hdr)) * " + (1 + steps * SCROLL_PER_ITEM) + ")";

  // Ajuste le canevas 960 x 520 à la zone visible.
  function fit() {
    var w = root.clientWidth, h = root.clientHeight;
    root.style.setProperty("--dsh-s", String(Math.min(w / 960, h / 520, 1.6)));
  }
  fit();
  new ResizeObserver(fit).observe(root);

  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  var index = 0, shown = -1, dir = 1, tl = null, seg = 0, st = null;
  var arc = { a0: 0, a1: 0 };

  function parts(i) {
    var head = heads[i];
    return {
      orbit: orbits[i], head: head, body: bodies[i],
      eye: head && head.querySelector(".dsh-eye"),
      t1: head && head.querySelector(".dsh-t1"),
      t2: head && head.querySelector(".dsh-t2"),
    };
  }
  function drawArc() { arcEl.setAttribute("d", arcPath(arc.a0, arc.a1, ORBIT_X, ORBIT_Y, ORBIT_R, 118)); }

  function syncChrome(to) {
    dots.forEach(function (d, i) {
      d.setAttribute("aria-selected", i === to);
      if (i === to) d.setAttribute("aria-current", "true"); else d.removeAttribute("aria-current");
    });
    thumbs.forEach(function (b, i) {
      if (i === to) b.setAttribute("aria-current", "true"); else b.removeAttribute("aria-current");
    });
    stripTrack.style.transform = "translateX(" + -stripStart(to, n, VISIBLE) * ITEM + "px)";
    orbits.forEach(function (o, i) { o.setAttribute("aria-hidden", i !== to); });
    heads.forEach(function (h, i) { h.setAttribute("aria-hidden", i !== to); });
    bodies.forEach(function (b, i) {
      b.setAttribute("aria-hidden", i !== to);
      b.querySelectorAll("a").forEach(function (a) { a.tabIndex = i === to ? 0 : -1; });
    });
    actUrl.href = items[to].url;
    srEl.textContent = "Univers " + (to + 1) + " sur " + n + " : " + items[to].title + " " + items[to].subtitle;
  }

  // Le changement : tout est dans le DOM, GSAP n'anime que le sortant et l'entrant.
  function swap() {
    var from = shown, to = index;
    var rest = arcRest(to);
    var tint = items[to] ? items[to].accent : "transparent";
    if (tl) tl.progress(1).kill();
    syncChrome(to);
    var b = parts(to);
    if (from === -1 || from === to || reduced.matches) {
      for (var i = 0; i < n; i++) if (i !== to) {
        var p = parts(i);
        gsap.set([p.orbit, p.head, p.body], { autoAlpha: 0 });
      }
      gsap.set([b.orbit, b.head, b.body, b.eye], { autoAlpha: 1, rotation: 0, y: 0 });
      gsap.set(b.t1, { clipPath: SHOW });
      gsap.set(b.t2, { clipPath: SHOW });
      arc.a0 = rest[0]; arc.a1 = rest[1];
      drawArc();
      gsap.set(arcEl, { fill: tint });
      shown = to;
      return;
    }
    var a = parts(from), d = dir;
    tl = gsap.timeline({ onComplete: function () { tl = null; } });
    // visuel : sort par le haut sur l'orbite, le suivant arrive de l'autre côté
    tl.to(a.orbit, { rotation: SWING * d, duration: 0.62, ease: "power2.in" }, 0)
      .set(a.orbit, { autoAlpha: 0, rotation: 0 }, 0.62)
      .fromTo(b.orbit, { autoAlpha: 1, rotation: -SWING * d }, { rotation: 0, duration: 0.95, ease: "power3.out" }, 0.3);
    // titre : la ligne fine part à droite, la ligne grasse à gauche, puis le suivant apparaît
    tl.to(a.t1, { clipPath: HIDE_1, duration: 0.42, ease: "power2.in" }, 0)
      .to(a.t2, { clipPath: HIDE_2, duration: 0.42, ease: "power2.in" }, 0.06)
      .to(a.eye, { autoAlpha: 0, duration: 0.25 }, 0)
      .set(a.head, { autoAlpha: 0 }, 0.5)
      .set(b.head, { autoAlpha: 1 }, 0.5)
      .fromTo(b.eye, { autoAlpha: 0, y: 6 }, { autoAlpha: 1, y: 0, duration: 0.4, ease: "power2.out" }, 0.55)
      .fromTo(b.t1, { clipPath: HIDE_1 }, { clipPath: SHOW, duration: 0.7, ease: "power3.out" }, 0.55)
      .fromTo(b.t2, { clipPath: HIDE_2 }, { clipPath: SHOW, duration: 0.7, ease: "power3.out" }, 0.62);
    // carte : fondu enchaîné, les lignes entrantes montent tour à tour
    tl.to(a.body, { autoAlpha: 0, y: -6, duration: 0.3, ease: "power1.in" }, 0.05)
      .set(b.body, { autoAlpha: 1, y: 0 }, 0.4)
      .fromTo(b.body.children, { autoAlpha: 0, y: 10 }, { autoAlpha: 1, y: 0, duration: 0.5, stagger: 0.06, ease: "power2.out" }, 0.4);
    // la bande s'étire le long de l'orbite puis se pose sur la portion suivante en changeant de couleur
    tl.to(arc, { a0: ARC_SWEEP[0], a1: ARC_SWEEP[1], duration: 0.6, ease: "power2.inOut", onUpdate: drawArc }, 0)
      .to(arc, { a0: rest[0], a1: rest[1], duration: 0.85, ease: "power3.out", onUpdate: drawArc }, 0.6)
      .to(arcEl, { fill: tint, duration: 1.1, ease: "power1.inOut" }, 0.1);
    shown = to;
  }

  function select(next, d) {
    if (next === index) return;
    dir = d;
    index = next;
    swap();
  }

  // Le défilement pilote l'univers : la section s'épingle, une portion de défilement par univers, avec aimantation.
  if (steps >= 1) {
    st = ScrollTrigger.create({
      trigger: track,
      start: "top top+=" + parseInt(getComputedStyle(track).getPropertyValue("--hdr"), 10),
      end: "bottom bottom",
      snap: { snapTo: 1 / steps, duration: { min: 0.3, max: 0.8 }, delay: 0.08, ease: "power2.inOut" },
      onUpdate: function (self) {
        // En boucle : la dernière portion montre le premier univers, on revient en haut sans que ça se voie.
        if (loop && self.progress >= 1 && self.direction > 0) {
          seg = 0;
          self.scroll(self.start + 1);
          select(0, 1);
          return;
        }
        var s = Math.round(self.progress * steps);
        if (s === seg) return;
        var d = s > seg ? 1 : -1;
        seg = s;
        select(wrapIndex(s, n), d);
      },
    });
    // Tout en haut, remonter fait boucler vers le dernier univers.
    var raf = 0;
    window.addEventListener("wheel", function (e) {
      var y = st.scroll();
      if (!loop || e.deltaY >= 0 || y < st.start - 1 || y > st.start + 1) return;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(function () {
        seg = n - 1;
        st.scroll(st.start + ((st.end - st.start) * (n - 1)) / steps);
        select(n - 1, -1);
      });
    }, { passive: true });
  }

  // Boutons, touches et balayages sautent à un univers et déplacent le défilement en conséquence.
  function go(to, d) {
    if (n < 2) return;
    var next = wrapIndex(to, n);
    if (next === index) return;
    if (st) {
      var y = st.scroll();
      if (y >= st.start - 1 && y <= st.end + 1) {
        seg = segmentFor(next, seg, n, loop);
        st.scroll(st.start + ((st.end - st.start) * seg) / steps);
      }
    }
    select(next, d || stepDirection(index, next, n));
  }
  function step(d) { go(index + d, d); }

  root.querySelectorAll("[data-go]").forEach(function (b) {
    b.addEventListener("click", function () { go(Number(b.dataset.go)); });
  });
  root.querySelectorAll("[data-step]").forEach(function (b) {
    b.addEventListener("click", function () { step(Number(b.dataset.step)); });
  });
  root.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight") { e.preventDefault(); step(1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); step(-1); }
  });
  var swipe = null, plates = root.querySelector(".dsh-plates");
  plates.addEventListener("pointerdown", function (e) { swipe = { x: e.clientX, y: e.clientY }; });
  plates.addEventListener("pointercancel", function () { swipe = null; });
  plates.addEventListener("pointerup", function (e) {
    var s = swipe; swipe = null;
    if (!s) return;
    var dx = e.clientX - s.x;
    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(e.clientY - s.y) * 1.4) step(dx < 0 ? 1 : -1);
  });

  // Onglets de la carte : Aperçu / Points clés.
  root.querySelectorAll(".dsh-tab").forEach(function (t) {
    t.addEventListener("click", function () {
      root.querySelectorAll(".dsh-tab").forEach(function (x) { x.setAttribute("aria-selected", x === t); });
      card.classList.toggle("is-ingredients", t.dataset.tab === "ingredients");
    });
  });

  root.classList.add("is-ready");
  swap();
})();
