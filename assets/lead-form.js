(function () {
"use strict";
const form = document.getElementById("bkm-lead-form");
if (!form) return;
const country = form.elements.country;
const phone = form.elements.phone;
const emailInput = form.elements.email;
const emailHint = document.getElementById("bkm-email-hint");
const button = form.querySelector('button[type="submit"]');
const status = document.getElementById("bkm-form-status");
const hint = document.getElementById("bkm-phone-hint");
const cfg = window.BKM_SITE_CONFIG || {};
const live = cfg.formsEnabled === true && location.protocol === "https:";
const endpoint = cfg.leadEndpoint || "/api/lead.php";
const rules = {"RU":["7",10,10],"KZ":["7",10,10],"BY":["375",9,9],"CN":["86",11,11],"IN":["91",10,10],"KR":["82",9,10],"AE":["971",9,9],"US":["1",10,10],"CA":["1",10,10],"DE":["49",7,13],"GB":["44",9,10],"FR":["33",9,9],"IT":["39",8,12],"TR":["90",10,10],"PL":["48",9,9],"KG":["996",9,9],"UZ":["998",9,9],"AM":["374",8,8],"GE":["995",9,9],"AZ":["994",9,9],"TJ":["992",9,9],"MD":["373",8,8],"NL":["31",9,9],"ES":["34",9,9],"PT":["351",9,9],"CH":["41",9,9],"BE":["32",8,9],"LT":["370",8,8],"LV":["371",8,8],"EE":["372",7,8],"JP":["81",9,10],"SG":["65",8,8],"TH":["66",9,9],"VN":["84",9,10]};
let submitting = false;
function message(text, type) {
 if (!status) return;
 status.textContent = text;
 status.dataset.type = type || "info";
}
function syncPhone() {
 const rule = rules[country.value] || rules.RU;
 const [dial, min, max] = rule;
 const rawDigits=phone.value.replace(/[^0-9]/g,"");
 const truncated=rawDigits.length>max;
 phone.value=rawDigits.slice(0,max);
 phone.minLength = min;
 phone.maxLength = max;
 phone.setAttribute("pattern", "[0-9]{" + min + (min === max ? "" : "," + max) + "}");
 phone.setCustomValidity("");
 phone.placeholder = min === 10 ? "9991234567" : "Номер без кода страны";
 hint.textContent = (min === max ? String(min) : min + "–" + max) +
    " цифр без +" + dial + " · введено " + phone.value.length + "/" + max +
    (truncated ? " (лишние цифры удалены)" : "");
}
country.addEventListener("change", function () { phone.value = ""; syncPhone(); });
phone.addEventListener("input", syncPhone);
syncPhone();
if (!live) message("Для отправки откроется почтовая программа.", "info");
else message("Завершите проверку безопасности и заполните поля.", "info");
function emailValid(email) {
 if (email.length > 160 || !/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}$/.test(email)) return false;
 const [local, domain] = email.split("@");
 if (!local || local.startsWith(".") || local.endsWith(".") ||
    local.includes("..") || domain.includes("..")) return false;
 return domain.split(".").every(function (part) {
   return /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/.test(part);
 });
}
function updateEmailStatus() {
 const email=emailInput.value.trim();
 const good=email.length===0 || emailValid(email);
 emailInput.setCustomValidity(good ? "" : "Введите email в формате name@company.ru");
 emailInput.setAttribute("aria-invalid", good ? "false" : "true");
 if(emailHint){
  emailHint.textContent=!email ? "Пример: name@company.ru" :
    good ? "Адрес указан корректно" : "Нужен адрес вида name@company.ru";
  emailHint.dataset.type=!email ? "info" : good ? "success" : "error";
 }
}
emailInput.addEventListener("input",updateEmailStatus);
emailInput.addEventListener("blur",updateEmailStatus);
const query = new URLSearchParams(location.search);
const utmKeys = ["source","medium","campaign","term","content"];
let utm = {};
try {
 utm = JSON.parse(sessionStorage.getItem("bkm_utms") || "{}");
 if (!utm || typeof utm !== "object" || Array.isArray(utm)) utm = {};
} catch (_) { utm = {}; }
for (const key of utmKeys) {
 const value = query.get("utm_" + key);
 if (value && value.length < 160) utm[key] = value;
}
try { sessionStorage.setItem("bkm_utms", JSON.stringify(utm)); } catch (_) {}
form.addEventListener("submit", async function(event) {
 event.preventDefault();
 if (submitting) return;
 syncPhone();
 const rule = rules[country.value];
 if (!rule || phone.value.length < rule[1] || phone.value.length > rule[2]) {
   phone.setCustomValidity("Проверьте количество цифр номера для выбранной страны.");
   phone.reportValidity();
   return;
 }
 const email = emailInput.value.trim();
 if (!emailValid(email)) {
   emailInput.setCustomValidity("Введите email в формате name@company.ru");
   emailInput.reportValidity();
   return;
 }
 if (!form.reportValidity()) return;
 const data = new FormData(form);
 const payload = {
   country:country.value, phone:phone.value, email,
   service:String(data.get("service")||"").trim(),
   details:String(data.get("details")||"").trim(),
   website:String(data.get("website")||""),
   consent:data.get("consent")==="on",
   turnstile_token:String(data.get("cf-turnstile-response")||""),
   page:location.pathname
 };
 for(const key of utmKeys) payload["utm_"+key]=String(utm[key]||"").slice(0,150);
 const intl = "+" + rule[0] + payload.phone;
 if(!live) {
   const body=["Телефон: "+intl,"Email: "+payload.email,"Вид услуги: "+payload.service,
     "Комментарии: "+payload.details].join("\n");
   location.href="mailto:info@24bkm.com?subject="+encodeURIComponent("Запрос с сайта БКМ")+
     "&body="+encodeURIComponent(body);
   message("Откроется почтовая программа. Подтвердите отправку письма в ней.", "info");
   return;
 }
 if(!payload.turnstile_token) {
   message("Сначала завершите проверку безопасности Cloudflare.", "error");
   return;
 }
 submitting=true;
 form.setAttribute("aria-busy","true");
 if(button){button.disabled=true;button.textContent="Отправляем заявку…";}
 message("Передаём заявку в БКМ.", "info");
 const controller=new AbortController();
 const timeout=setTimeout(function(){controller.abort();},25000);
 try {
   const response=await fetch(endpoint,{
     method:"POST",credentials:"same-origin",cache:"no-store",
     headers:{"Content-Type":"application/json","Accept":"application/json"},
     body:JSON.stringify(payload),signal:controller.signal
   });
   const result=await response.json();
   const codes=["lead_created","not_enabled","server_not_configured","host_rejected",
     "origin_rejected","invalid_payload_size","consent_required","invalid_fields",
     "invalid_phone","invalid_email","verification_required","crm_unavailable",
     "crm_invalid_response","crm_unconfirmed"];
   if(status) {
     status.dataset.responseCode=codes.includes(result.code)?result.code:"unknown";
     status.dataset.httpStatus=String(response.status);
   }
   if(!response.ok || result.ok!==true || result.code!=="lead_created")
     throw new Error("lead_unconfirmed");
   message("Заявка отправлена в БКМ. Спасибо! Мы свяжемся с вами.", "success");
   form.reset();syncPhone();
   if(typeof window.BKMTrackGoal==="function")window.BKMTrackGoal("bkm_lead_success");
 } catch (_) {
   message("Не удалось подтвердить получение заявки. Не отправляйте повторно сразу; позвоните нам или напишите на info@24bkm.com.", "error");
 } finally {
   clearTimeout(timeout);
   submitting=false;
   form.removeAttribute("aria-busy");
   if(button){
     button.textContent="Отправить заявку ↗";
     if(typeof window.BKMResetTurnstile==="function"){
       window.BKMResetTurnstile();
     } else button.disabled=false;
   }
 }
});
})();
