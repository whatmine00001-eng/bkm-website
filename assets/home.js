(function () {
  "use strict";
  const toggle = document.getElementById("menu-toggle");
  const nav = document.getElementById("site-nav");
  if (!toggle || !nav) return;

  function closeMenu(restoreFocus) {
    nav.dataset.open = "false";
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-label", "Открыть меню");
    document.body.classList.remove("menu-open");
    if (restoreFocus) toggle.focus();
  }

  toggle.addEventListener("click", function () {
    const open = nav.dataset.open !== "true";
    nav.dataset.open = String(open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Закрыть меню" : "Открыть меню");
    document.body.classList.toggle("menu-open", open);
  });

  nav.querySelectorAll("a").forEach(function (a) {
    a.addEventListener("click", function () { closeMenu(false); });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && nav.dataset.open === "true") closeMenu(true);
  });
  document.addEventListener("click", function (event) {
    if (nav.dataset.open === "true" && !nav.contains(event.target) && !toggle.contains(event.target)) {
      closeMenu(false);
    }
  });
  const mq = window.matchMedia("(min-width: 1051px)");
  const sync = function () { if (mq.matches) closeMenu(false); };
  if (mq.addEventListener) mq.addEventListener("change", sync);
  else if (mq.addListener) mq.addListener(sync);
  sync();
})();
