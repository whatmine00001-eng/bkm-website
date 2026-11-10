// Cloudflare Pages Function: POST /api/lead
// All secrets are Cloudflare encrypted bindings. Never commit a webhook.
// Production can submit only when owner-enabled Cloudflare runtime bindings are configured.
const ALLOWED_HOSTS = new Set(["24bkm.com", "www.24bkm.com", "bkm-website-7kj.pages.dev"]);
const PHONE_RULES = {"RU":["7",10,10],"KZ":["7",10,10],"BY":["375",9,9],"CN":["86",11,11],"IN":["91",10,10],"KR":["82",9,10],"AE":["971",9,9],"US":["1",10,10],"CA":["1",10,10],"DE":["49",7,13],"GB":["44",9,10],"FR":["33",9,9],"IT":["39",8,12],"TR":["90",10,10],"PL":["48",9,9],"KG":["996",9,9],"UZ":["998",9,9],"AM":["374",8,8],"GE":["995",9,9],"AZ":["994",9,9],"TJ":["992",9,9],"MD":["373",8,8],"NL":["31",9,9],"ES":["34",9,9],"PT":["351",9,9],"CH":["41",9,9],"BE":["32",8,9],"LT":["370",8,8],"LV":["371",8,8],"EE":["372",7,8],"JP":["81",9,10],"SG":["65",8,8],"TH":["66",9,9],"VN":["84",9,10]};
const SERVICES = new Set(["Международная перевозка","Таможенное оформление","Логистика и склад","Агентские услуги","Другое"]);
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
  // Only the actual deployed project plus its eventual custom domains.
  if(!ALLOWED_HOSTS.has(url.hostname) || url.protocol!=="https:")
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
  if(name.length<2) return reply(422,"invalid_fields");
  const country=field(data,"country",2);
  const national=field(data,"phone",20);
  const rule=PHONE_RULES[country];
  if(!rule || !/^[0-9]+$/.test(national)
     || national.length<rule[1] || national.length>rule[2]
     || (rule[0]+national).length>15) return reply(422,"invalid_phone");
  const phone="+"+rule[0]+national;
  const email=field(data,"email",160);
  const parts=email.split("@");
  if(parts.length!==2 || !/^[A-Za-z0-9._%+-]+$/.test(parts[0])
     || parts[0].startsWith(".") || parts[0].endsWith(".") || parts[0].includes("..")
     || !/^[A-Za-z]{2,24}$/.test(parts[1].split(".").at(-1))
     || parts[1].split(".").length<2
     || !parts[1].split(".").every(x=>/^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/.test(x)))
    return reply(422,"invalid_email");
  const service=field(data,"service",100);
  if(!SERVICES.has(service)) return reply(422,"invalid_fields");
  // Cloudflare Turnstile is mandatory: honeypot alone is insufficient.
  const ip=request.headers.get("cf-connecting-ip") || "";
  const fetcher=globalThis.fetch;
  if(!await verifyTurnstile(field(data,"turnstile_token",2500),
                            env.BKM_TURNSTILE_SECRET,ip,url.hostname,fetcher))
    return reply(422,"verification_required");
  const comments=[
    "Вид услуги: "+service,
    "Страна телефона: "+country,
    "Комментарии: "+field(data,"details",1600),
    "Страница: "+field(data,"page",200),
    "Согласие: "+new Date().toISOString(),
    "Редакция согласия: "+String(env.BKM_CONSENT_VERSION).slice(0,80),
    "Политика: https://24bkm.com/privacy.html"
  ].join("\n");
  const fields={
    TITLE:"Сайт БКМ — "+service,
    NAME:name,
    PHONE:[{VALUE:phone,VALUE_TYPE:"WORK"}],
    EMAIL:[{VALUE:email,VALUE_TYPE:"WORK"}],
    STATUS_ID:"NEW",SOURCE_ID:"WEB",
    SOURCE_DESCRIPTION:"24bkm.com / Cloudflare Pages",
    OPENED:"N",ASSIGNED_BY_ID:7,COMMENTS:comments
  };
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
    let result;
    try { result=await crm.json(); }
    catch { return reply(502,"crm_response_not_json"); }
    if(result?.error){
      const failure=String(result.error).toUpperCase();
      // These codes reveal a category only, never raw CRM messages or secrets.
      if(/INVALID_CREDENTIALS|INVALID_TOKEN|EXPIRED_TOKEN|NO_AUTH_FOUND/.test(failure))
        return reply(502,"crm_auth_rejected");
      if(/ACCESS_DENIED|INSUFFICIENT_SCOPE|USER_ACCESS_ERROR|ACCESS_ERROR/.test(failure))
        return reply(502,"crm_access_denied");
      if(/METHOD_NOT_FOUND|REST_MODULE_NOT_INSTALLED/.test(failure))
        return reply(502,"crm_method_unavailable");
      return reply(502,"crm_rejected");
    }
    const id=Number(result?.result);
    if(!Number.isSafeInteger(id) || id<=0)
      return reply(502,"crm_invalid_response");
    return reply(200,"lead_created",{lead_id:id});
  } catch (error) {
    // Never auto-retry: a timed-out request may have created a CRM lead.
    return reply(502,["TimeoutError","AbortError"].includes(error?.name)
      ? "crm_timeout" : "crm_connection_failed");
  }
}
export async function onRequestGet(){return reply(405,"method_not_allowed");}
