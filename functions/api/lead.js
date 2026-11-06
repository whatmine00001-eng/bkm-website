// Cloudflare Pages Function: POST /api/lead
// All secrets are Cloudflare encrypted bindings. Never commit a webhook.
// Production can submit only when owner-enabled Cloudflare runtime bindings are configured.
const ALLOWED_HOSTS = new Set(["24bkm.com", "www.24bkm.com"]);
const SERVICES = new Set([
  "Международные перевозки", "Таможенное оформление", "Экспедирование",
  "Логистика и склад", "Сборные грузы", "Финансовое сопровождение", "Другое"
]);
const EXTRA_HEADERS = {
  "content-type":"application/json; charset=utf-8",
  "cache-control":"no-store, private",
  "x-content-type-options":"nosniff",
  "referrer-policy":"same-origin"
};
function reply(status, code, extra={}) {
  return new Response(JSON.stringify({ok:status===200 && code==="lead_created",code,...extra}), {
    status, headers:EXTRA_HEADERS
  });
}
function field(data,key,max) {
  return typeof data[key]==="string"
    ? data[key].replace(/[\x00-\x1f\x7f]/g," ").trim().slice(0,max)
    : "";
}
function webhookEndpoint(secret) {
  if(typeof secret!=="string") return null;
  try {
    const parsed=new URL(secret.trim());
    if(parsed.protocol!=="https:" || parsed.hostname!=="bitrix.24bkm.com"
       || parsed.port || parsed.username || parsed.password || parsed.search || parsed.hash
       || !/^\/rest\/\d+\/[A-Za-z0-9_-]+\/?$/.test(parsed.pathname)) return null;
    return parsed.href.replace(/\/$/,"")+"/crm.lead.add.json";
  } catch { return null; }
}
async function verifyTurnstile(token, secret, ip, expectedHost, fetcher) {
  if(!token || !secret || token.length>2500) return false;
  const body=new URLSearchParams({secret,response:token});
  if(ip) body.set("remoteip",ip);
  try {
    const result=await fetcher("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},
      body,signal:AbortSignal.timeout(8000)
    });
    if(!result.ok) return false;
    const json=await result.json();
    return json.success===true && json.hostname===expectedHost;
  } catch { return false; }
}
export async function onRequestPost({request,env}) {
  // Fail closed: a published preview must never start collecting contact data.
  // Owner approved the uploaded legal texts. One runtime deployment switch
  // prevents partial activation before Cloudflare secrets are configured.
  if(env.BKM_CRM_ENABLED!=="true")
    return reply(503,"not_enabled");
  const url=new URL(request.url);
  const previewHost=typeof env.BKM_PREVIEW_HOST==="string" ? env.BKM_PREVIEW_HOST : "";
  const approvedPreview=/^[a-z0-9-]+\.pages\.dev$/.test(previewHost) && url.hostname===previewHost;
  if((!ALLOWED_HOSTS.has(url.hostname) && !approvedPreview) || url.protocol!=="https:")
    return reply(403,"host_rejected");
  if(request.headers.get("origin")!==url.origin)
    return reply(403,"origin_rejected");
  if(!(request.headers.get("content-type")||"").toLowerCase().startsWith("application/json"))
    return reply(415,"json_required");
  const endpoint=webhookEndpoint(env.BKM_BITRIX_WEBHOOK_URL);
  if(!endpoint || !env.BKM_TURNSTILE_SECRET || !env.BKM_CONSENT_VERSION)
    return reply(503,"server_not_configured");
  const raw=await request.text();
  if(!raw || raw.length>14000) return reply(413,"invalid_payload_size");
  let data;
  try {data=JSON.parse(raw);} catch {return reply(400,"invalid_json");}
  if(!data || typeof data!=="object" || Array.isArray(data))
    return reply(400,"invalid_json");
  if(field(data,"website",40)) return reply(202,"accepted");
  if(data.consent!==true) return reply(422,"consent_required");
  const name=field(data,"name",120);
  const phone=field(data,"phone",36);
  const email=field(data,"email",160);
  const service=field(data,"service",100);
  if(name.length<2 || !/^[+0-9 ()-]{7,36}$/.test(phone)
    || (phone.match(/\d/g)||[]).length<7
    || (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
    || !SERVICES.has(service)) return reply(422,"invalid_fields");
  // Cloudflare Turnstile is mandatory: honeypot alone is insufficient.
  const ip=request.headers.get("cf-connecting-ip") || "";
  const fetcher=globalThis.fetch;
  if(!await verifyTurnstile(field(data,"turnstile_token",2500),
                            env.BKM_TURNSTILE_SECRET,ip,url.hostname,fetcher))
    return reply(422,"verification_required");
  const comments=[
    "Услуга: "+service,
    "Маршрут: "+field(data,"origin",150)+" → "+field(data,"destination",150),
    "Груз: "+field(data,"cargo",180),
    "Пожелания: "+field(data,"details",1600),
    "Страница: "+field(data,"page",200),
    "Согласие: "+new Date().toISOString(),
    "Редакция согласия: "+String(env.BKM_CONSENT_VERSION).slice(0,80),
    "Политика: https://24bkm.com/privacy.html"
  ].join("\n");
  const fields={
    TITLE:"Сайт БКМ — "+service,
    NAME:name,
    COMPANY_TITLE:field(data,"company",160),
    PHONE:[{VALUE:phone,VALUE_TYPE:"WORK"}],
    STATUS_ID:"NEW",SOURCE_ID:"WEB",
    SOURCE_DESCRIPTION:"24bkm.com / Cloudflare Pages",
    OPENED:"N",ASSIGNED_BY_ID:7,COMMENTS:comments
  };
  if(email) fields.EMAIL=[{VALUE:email,VALUE_TYPE:"WORK"}];
  for(const key of ["source","medium","campaign","term","content"]) {
    const value=field(data,"utm_"+key,150);
    if(value) fields["UTM_"+key.toUpperCase()]=value;
  }
  try {
    const crm=await fetcher(endpoint, {
      method:"POST",headers:{"content-type":"application/json","accept":"application/json"},
      body:JSON.stringify({fields,params:{REGISTER_SONET_EVENT:"Y"}}),
      signal:AbortSignal.timeout(15000),
      redirect:"error"
    });
    if(!crm.ok) return reply(502,"crm_unavailable");
    const result=await crm.json();
    const id=Number(result?.result);
    if(result?.error || !Number.isSafeInteger(id) || id<=0)
      return reply(502,"crm_invalid_response");
    return reply(200,"lead_created",{lead_id:id});
  } catch {
    // Never auto-retry: a timed-out request may have created a CRM lead.
    return reply(502,"crm_unconfirmed");
  }
}
export async function onRequestGet(){return reply(405,"method_not_allowed");}
