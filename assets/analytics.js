(function () {
  "use strict";
  const cfg = window.BKM_SITE_CONFIG || {};
  const id = Number(cfg.metrikaId);
  const enabled = cfg.analyticsEnabled === true &&
    window.location.protocol === "https:" &&
    Number.isSafeInteger(id) && id > 0;

  function goal(name) {
    if (!enabled || typeof window.ym !== "function") return;
    window.ym(id, "reachGoal", name);
  }
  window.BKMTrackGoal = goal;

  if (!enabled) return;

  // Yandex Metrika's official JS API, without placeholders masquerading as a real counter.
  (function (m, e, t, r, i, k, a) {
    m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
    m[i].l = Date.now();
    for (let j = 0; j < e.scripts.length; j++) {
      if (e.scripts[j].src === r) return;
    }
    k = e.createElement(t);
    a = e.getElementsByTagName(t)[0];
    k.async = 1;
    k.src = r;
    a.parentNode.insertBefore(k, a);
  })(window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");

  window.ym(id, "init", {
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    webvisor: false
  });

  document.addEventListener("click", function (event) {
    const target = event.target.closest("a[href]");
    if (!target) return;
    const href = target.getAttribute("href") || "";
    if (href.startsWith("tel:")) goal("bkm_phone_click");
    if (href.startsWith("mailto:")) goal("bkm_email_click");
  }, true);
})();
