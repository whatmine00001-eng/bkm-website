// Public (nonsecret) status and Turnstile site key for the BKM contact form.
// Secrets are never returned. The form stays disabled until Bitrix24, consent,
// and Turnstile bindings are configured in Cloudflare.
const ALLOWED_HOSTS = new Set([
  "bkm-website-7kj.pages.dev", "24bkm.com", "www.24bkm.com"
]);
const HEADERS = {
  "content-type":"application/json; charset=utf-8",
  "cache-control":"no-store, private, max-age=0",
  "x-content-type-options":"nosniff",
  "access-control-allow-origin":"null"
};
function result(status, data) {
  return new Response(JSON.stringify(data), {status, headers:HEADERS});
}
function webhookIsValid(secret) {
  if(typeof secret!=="string") return false;
  try {
    const u=new URL(secret.trim());
    return u.protocol==="https:" && u.hostname==="bitrix.24bkm.com"
      && !u.port && !u.search && !u.hash && !u.username && !u.password
      && /^\/rest\/\d+\/[A-Za-z0-9_-]+\/?$/.test(u.pathname);
  } catch { return false; }
}
export async function onRequestGet({request,env}) {
  const u=new URL(request.url);
  if(u.protocol!=="https:" || !ALLOWED_HOSTS.has(u.hostname))
    return result(403,{ready:false});
  // Explicitly require every server-side dependency; never leak status
  // of individual secrets, webhook, CRM response, or private values.
  const sitekey=typeof env.BKM_TURNSTILE_SITE_KEY==="string"
    ? env.BKM_TURNSTILE_SITE_KEY.trim() : "";
  if(env.BKM_CRM_ENABLED!=="true"
    || typeof env.BKM_TURNSTILE_SECRET!=="string"
    || env.BKM_TURNSTILE_SECRET.length<8
    || !/^[A-Za-z0-9_-]{8,100}$/.test(sitekey)
    || !env.BKM_CONSENT_VERSION
    || !webhookIsValid(env.BKM_BITRIX_WEBHOOK_URL)) {
    return result(503,{ready:false});
  }
  // sitekey is deliberately public, unlike its matching secret.
  return result(200,{ready:true,sitekey});
}
export async function onRequestPost() {
  return result(405,{ready:false});
}
