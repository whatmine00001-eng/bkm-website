/* BKM Cloudflare contact form: obtain only public Turnstile sitekey at runtime.
 * Contact data is never sent until the server confirms dependencies are ready.
 * Keep this file separate from shared Beget PHP form logic.
 */
(function () {
  "use strict";
  const form = document.getElementById("bkm-lead-form");
  if (!form) return;
  const submit = form.querySelector('button[type="submit"]');
  const status = document.getElementById("bkm-form-status");
  const target = document.getElementById("bkm-turnstile");
  if (!submit || !target) return;
  let widgetId = null;
  submit.disabled = true;
  function message(text, type) {
    if (!status) return;
    status.textContent = text;
    status.dataset.type = type || "info";
  }
  message("Проверяем готовность защищённой формы…");
  function unavailable() {
    submit.disabled = true;
    message("Форма временно недоступна. Напишите на info@24bkm.com или позвоните 8 800 707-79-02.", "error");
  }
  async function initialize() {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(function () { controller.abort(); }, 12000);
      let response;
      try {
        response = await fetch("/api/form-config", {
          credentials: "same-origin", cache: "no-store",
          headers: { "Accept": "application/json" },
          signal: controller.signal
        });
      } finally {
        clearTimeout(timeout);
      }
      if (!response.ok) throw new Error("not_ready");
      const cfg = await response.json();
      if (cfg.ready !== true || typeof cfg.sitekey !== "string" ||
          !/^[A-Za-z0-9_-]{8,100}$/.test(cfg.sitekey)) {
        throw new Error("not_ready");
      }
      // The widget script is loaded only after runtime configuration is ready.
      await new Promise(function (resolve, reject) {
        const script = document.createElement("script");
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
        script.async = true;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
      if (!window.turnstile || typeof window.turnstile.render !== "function") {
        throw new Error("turnstile_unavailable");
      }
      widgetId = window.turnstile.render(target, {
        sitekey: cfg.sitekey,
        theme: "auto",
        callback: function (token) {
          if (token && form.dataset.deliveryUnconfirmed !== "true") {
            submit.disabled = false;
            // Never overwrite a server error or an ambiguous CRM response.
            if (!status || status.dataset.type !== "error")
              message("Заполните поля и отправьте заявку — она поступит менеджеру БКМ.");
          }
        },
        "expired-callback": function () {
          submit.disabled = true;
          message("Срок проверки истёк. Пройдите проверку ещё раз.", "info");
        },
        "error-callback": function () {
          submit.disabled = true;
          message("Проверка безопасности не завершилась. Обновите страницу или напишите на info@24bkm.com.", "error");
        }
      });
      window.BKMResetTurnstile = function () {
        submit.disabled = true;
        if (window.turnstile && widgetId !== null) {
          window.turnstile.reset(widgetId);
        }
      };
      message("Завершите проверку безопасности, чтобы отправить заявку.");
    } catch (_) {
      unavailable();
    }
  }
  initialize();
})();
