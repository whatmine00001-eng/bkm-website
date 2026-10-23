(function () {
  "use strict";
  const form = document.getElementById("bkm-lead-form");
  if (!form) return;
  const status = document.getElementById("bkm-form-status");
  const button = form.querySelector('button[type="submit"]');
  const cfg = window.BKM_SITE_CONFIG || {};
  const live = cfg.formsEnabled === true && location.protocol === "https:";

  function feedback(message, type) {
    if (!status) return;
    status.textContent = message;
    status.dataset.type = type || "info";
  }

  // Preview HTTP cannot safely transmit client contacts to the backend.
  if (!live) {
    if (button) button.textContent = "Подготовить письмо по заявке ↗";
    feedback("Тестовая версия: автоматическая отправка пока отключена. Данные можно отправить через вашу почтовую программу.", "info");
  } else {
    if (button) button.textContent = "Отправить заявку в БКМ ↗";
    feedback("Передача заявки защищена HTTPS. После отправки вы увидите подтверждение.", "info");
  }

  const params = new URLSearchParams(location.search);
  const utmKeys = ["source", "medium", "campaign", "term", "content"];
  let utm = {};
  try {
    utm = JSON.parse(sessionStorage.getItem("bkm_utms") || "{}");
    if (!utm || typeof utm !== "object") utm = {};
  } catch (_) { utm = {}; }
  for (const key of utmKeys) {
    const value = params.get("utm_" + key);
    if (value && value.length < 160) utm[key] = value;
  }
  try { sessionStorage.setItem("bkm_utms", JSON.stringify(utm)); } catch (_) {}

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const data = new FormData(form);
    const payload = {
      name: String(data.get("name") || "").trim(),
      company: String(data.get("company") || "").trim(),
      phone: String(data.get("phone") || "").trim(),
      email: String(data.get("email") || "").trim(),
      service: String(data.get("service") || "").trim(),
      origin: String(data.get("origin") || "").trim(),
      destination: String(data.get("destination") || "").trim(),
      cargo: String(data.get("cargo") || "").trim(),
      details: String(data.get("details") || "").trim(),
      website: String(data.get("website") || ""),
      consent: data.get("consent") === "on",
      page: location.pathname
    };
    for (const key of utmKeys) payload["utm_" + key] = String(utm[key] || "").slice(0, 150);

    if (!live) {
      const body = [
        "Имя: " + payload.name,
        "Компания: " + payload.company,
        "Телефон: " + payload.phone,
        "Email: " + payload.email,
        "Услуга: " + payload.service,
        "Откуда: " + payload.origin,
        "Куда: " + payload.destination,
        "Груз: " + payload.cargo,
        "Комментарий: " + payload.details
      ].join("\n");
      location.href = "mailto:info@24bkm.com?subject=" +
        encodeURIComponent("Запрос с сайта БКМ") + "&body=" + encodeURIComponent(body);
      feedback("Откроется почтовая программа. Отправку письма нужно подтвердить там.", "info");
      return;
    }

    if (button) {
      button.disabled = true;
      button.textContent = "Отправляем заявку…";
    }
    feedback("Передаём заявку в БКМ.", "info");
    try {
      const response = await fetch("api/lead.php", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store"
      });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.code || "submission_failed");
      feedback("Заявка отправлена в БКМ. Спасибо! Мы свяжемся с вами.", "success");
      form.reset();
      if (typeof window.BKMTrackGoal === "function") window.BKMTrackGoal("bkm_lead_success");
    } catch (_) {
      feedback("Не удалось подтвердить получение заявки. Пожалуйста, позвоните нам или отправьте письмо на info@24bkm.com.", "error");
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = "Отправить заявку в БКМ ↗";
      }
    }
  });
})();
