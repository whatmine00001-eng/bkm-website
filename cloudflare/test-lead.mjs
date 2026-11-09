import assert from "node:assert/strict";
import fs from "node:fs/promises";
import test from "node:test";

const source=await fs.readFile(new URL("../functions/api/lead.js", import.meta.url),"utf8");
const api=await import("data:text/javascript;base64,"+Buffer.from(source).toString("base64"));
const origin="https://24bkm.com";
const env={
  BKM_CRM_ENABLED:"true",
  BKM_LEGAL_APPROVED:"true",
  BKM_BITRIX_WEBHOOK_URL:"https://bitrix.24bkm.com/rest/7/FAKE_TEST_SECRET/",
  BKM_TURNSTILE_SECRET:"TEST_ONLY_TURNSTILE_SECRET",
  BKM_CONSENT_VERSION:"test-fixture-v1"
};
const data={
  country:"RU",phone:"9991234567",
  email:"example@company.ru",service:"Агентские услуги",
  details:"Тестовый комментарий без реальных данных",
  consent:true,website:"",turnstile_token:"TEST_ONLY",
  page:"/index.html",utm_source:"test"
};
function request(body=data,headers={},url=origin+"/api/lead"){
  return new Request(url,{
    method:"POST",headers:{"origin":new URL(url).origin,"content-type":"application/json",...headers},
    body:JSON.stringify(body)
  });
}
test("closed configuration refuses request before any network activity",async()=>{
  let calls=0;const old=globalThis.fetch;
  globalThis.fetch=async()=>{calls++;throw Error("no network expected")};
  try{
    const res=await api.onRequestPost({request:request(),env:{...env,BKM_CRM_ENABLED:"false"}});
    assert.equal(res.status,503);assert.equal((await res.json()).code,"not_enabled");assert.equal(calls,0);
  } finally {globalThis.fetch=old;}
});
test("origin and host enforced",async()=>{
  const a=await api.onRequestPost({request:request(data,{"origin":"https://evil.example"}),env});
  const b=await api.onRequestPost({request:request(data,{}, "https://preview.pages.dev/api/lead"),env});
  assert.equal(a.status,403);assert.equal(b.status,403);
});
test("consent, phone and service validated",async()=>{
  for(const [field,value] of [["consent",false],["phone","123"],["email","wrong-address"],["country","XX"],["service","outside whitelist"]]){
    const res=await api.onRequestPost({request:request({...data,[field]:value}),env});
    assert.equal(res.status,422);
  }
});
test("valid synthetic lead is sent to Bitrix24 after Turnstile and assigned to ID 7",async()=>{
  const old=globalThis.fetch;let calls=[];
  globalThis.fetch=async(url,options)=>{
    calls.push({url:String(url),options});
    if(String(url).includes("siteverify"))return new Response('{"success":true,"hostname":"24bkm.com"}',{status:200});
    if(String(url).endsWith("crm.lead.add.json")){
      let payload=JSON.parse(options.body);
      assert.equal(payload.fields.ASSIGNED_BY_ID,7);
      assert.equal(payload.fields.SOURCE_ID,"WEB");
      assert.equal(payload.fields.PHONE[0].VALUE,"+79991234567");
      assert.equal(payload.fields.EMAIL[0].VALUE,data.email);
      assert.equal(payload.fields.ASSIGNED_BY_ID,7);
      assert.ok(payload.fields.COMMENTS.includes("Вид услуги: Агентские услуги"));
      assert.equal(payload.fields.UTM_SOURCE,"test");
      return new Response('{"result":123}',{status:200});
    }
    throw Error("unexpected remote URL");
  };
  try{
    const res=await api.onRequestPost({request:request(),env});
    assert.equal(res.status,200);
    const result=await res.json();
    assert.deepEqual(result,{ok:true,code:"lead_created",lead_id:123});
    assert.equal(calls.length,2);
  }finally{globalThis.fetch=old}
});
test("failed CRM response never claims a confirmed lead",async()=>{
  const old=globalThis.fetch;
  globalThis.fetch=async url=>String(url).includes("siteverify")
    ? new Response('{"success":true,"hostname":"24bkm.com"}',{status:200})
    : new Response('{"error":"FORBIDDEN"}',{status:200});
  try{
    const res=await api.onRequestPost({request:request(),env});
    assert.equal(res.status,502);
    assert.notEqual((await res.json()).code,"lead_created");
  }finally{globalThis.fetch=old}
});
test("GET is not a submit",async()=>{
  assert.equal((await api.onRequestGet()).status,405);
});

test("Turnstile token issued for another hostname is rejected",async()=>{
  const old=globalThis.fetch;
  let crmCalls=0;
  globalThis.fetch=async url=>{
    if(String(url).includes("siteverify"))
      return new Response('{"success":true,"hostname":"other-site.test"}',{status:200});
    crmCalls++;throw Error("CRM must not be called");
  };
  try {
    const result=await api.onRequestPost({request:request(),env});
    assert.equal(result.status,422);
    assert.equal((await result.json()).code,"verification_required");
    assert.equal(crmCalls,0);
  }finally{globalThis.fetch=old;}
});
test("the actual BKM Pages host is accepted for staging test only",async()=>{
  const req=request(data,{}, "https://bkm-website-7kj.pages.dev/api/lead");
  const original=globalThis.fetch;
  globalThis.fetch=async url=>String(url).includes("siteverify")
    ? new Response('{"success":true,"hostname":"bkm-website-7kj.pages.dev"}',{status:200})
    : new Response('{"result":777}',{status:200});
  try {
    const r=await api.onRequestPost({request:req,env});
    assert.equal(r.status,200);
    assert.equal((await r.json()).lead_id,777);
  }finally{globalThis.fetch=original;}
});

test("other pages.dev hosts remain forbidden",async()=>{
  const res=await api.onRequestPost({request:request(data,{}, "https://other-project.pages.dev/api/lead"),env});
  assert.equal(res.status,403);
});

test("validation rejects excessive phone digits and invalid email before CAPTCHA",async()=>{
 for(const change of [{phone:"99912345679999"},{email:"anything@@foo.ru"},{email:"foo@bar"},{email:"foo@bar.c"}]){
   const res=await api.onRequestPost({request:request({...data,...change}),env});
   assert.equal(res.status,422);
 }
});
test("Kazakhstan code produces normalized +7 CRM phone",async()=>{
 const original=globalThis.fetch;
 globalThis.fetch=async(url,options)=>{
   if(String(url).includes("siteverify"))
     return new Response('{"success":true,"hostname":"24bkm.com"}',{status:200});
   const fields=JSON.parse(options.body).fields;
   assert.equal(fields.PHONE[0].VALUE,"+77011234567");
   assert.equal(fields.ASSIGNED_BY_ID,7);
   return new Response('{"result":900}',{status:200});
 };
 try{
   const res=await api.onRequestPost({request:request({...data,country:"KZ",phone:"7011234567"}),env});
   assert.equal(res.status,200);
 }finally{globalThis.fetch=original;}
});
