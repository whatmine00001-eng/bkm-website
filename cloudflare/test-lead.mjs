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
  name:"ТЕСТ БКМ",phone:"+70000000000",company:"Тест",
  email:"example@example.test",service:"Сборные грузы",
  origin:"Санкт-Петербург",destination:"Минск",
  cargo:"Тестовый груз",details:"Проверка без реальной отправки",
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
  for(const [field,value] of [["consent",false],["phone","123"],["service","outside whitelist"]]){
    const res=await api.onRequestPost({request:request({...data,[field]:value}),env});
    assert.equal(res.status,422);
  }
});
test("valid synthetic lead is sent to Bitrix24 after Turnstile and assigned to ID 7",async()=>{
  const old=globalThis.fetch;let calls=[];
  globalThis.fetch=async(url,options)=>{
    calls.push({url:String(url),options});
    if(String(url).includes("siteverify"))return new Response('{"success":true}',{status:200});
    if(String(url).endsWith("crm.lead.add.json")){
      let payload=JSON.parse(options.body);
      assert.equal(payload.fields.ASSIGNED_BY_ID,7);
      assert.equal(payload.fields.SOURCE_ID,"WEB");
      assert.equal(payload.fields.NAME,data.name);
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
    ? new Response('{"success":true}',{status:200})
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
