import assert from "node:assert/strict";
import fs from "node:fs/promises";
import test from "node:test";

const source=await fs.readFile(new URL("../functions/api/form-config.js",import.meta.url),"utf8");
const api=await import("data:text/javascript;base64,"+Buffer.from(source).toString("base64"));
const env={
  BKM_CRM_ENABLED:"true",
  BKM_CONSENT_VERSION:"bkm-consent-uploaded-2026-11-06-v1",
  BKM_BITRIX_WEBHOOK_URL:"https://bitrix.24bkm.com/rest/7/TEST_TOKEN_123456789/",
  BKM_TURNSTILE_SECRET:"ONLY_FAKE_SECRET_123",
  BKM_TURNSTILE_SITE_KEY:"FAKE_PUBLIC_SITE_KEY_123456"
};
const request=(host="bkm-website-7kj.pages.dev")=>
  new Request("https://"+host+"/api/form-config");

test("unconfigured project remains closed and never leaks token",async()=>{
  const r=await api.onRequestGet({request:request(),env:{...env,BKM_BITRIX_WEBHOOK_URL:""}});
  assert.equal(r.status,503);
  const body=await r.text();
  assert.equal(body,'{"ready":false}');
  assert.ok(!body.includes("TEST_TOKEN"));
});
test("enabled project serves only public sitekey",async()=>{
  const r=await api.onRequestGet({request:request(),env});
  assert.equal(r.status,200);
  assert.deepEqual(await r.json(),{ready:true,sitekey:env.BKM_TURNSTILE_SITE_KEY});
});
test("must not return sitekey for disallowed host",async()=>{
  const r=await api.onRequestGet({request:request("another-project.pages.dev"),env});
  assert.equal(r.status,403);
  assert.deepEqual(await r.json(),{ready:false});
});
test("disabled runtime flag fails closed",async()=>{
  const r=await api.onRequestGet({request:request(),env:{...env,BKM_CRM_ENABLED:"false"}});
  assert.equal(r.status,503);
});
test("non-get methods not accepted",async()=>{
  const r=await api.onRequestPost();
  assert.equal(r.status,405);
});
