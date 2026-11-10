// TEMPORARY diagnostic: tests CRM webhook permission without creating a lead,
// storing contact details, returning secrets, or changing Bitrix24 data.
// Delete this function from the branch immediately after the investigation.
const HEADERS={"content-type":"application/json; charset=utf-8","cache-control":"no-store, private","x-content-type-options":"nosniff"};
let cached=null, cachedAt=0;
function answer(code, status=200){
  return new Response(JSON.stringify({code}),{status,headers:HEADERS});
}
export async function onRequestGet({request,env}){
  const u=new URL(request.url);
  if(u.protocol!=="https:" || u.hostname!=="bkm-website-7kj.pages.dev")return answer("unavailable",404);
  if(cached && Date.now()-cachedAt<45000)return answer(cached.code,cached.status);
  const raw=env.BKM_BITRIX_WEBHOOK_URL;
  if(typeof raw!=="string")return answer("not_configured",503);
  let base;
  try{
    const parsed=new URL(raw.trim());
    if(parsed.protocol!=="https:" || parsed.hostname!=="bitrix.24bkm.com" ||
      parsed.port || parsed.username || parsed.password || parsed.search || parsed.hash ||
      !/^\/rest\/\d+\/[A-Za-z0-9_-]+\/?$/.test(parsed.pathname))
        return answer("not_configured",503);
    base=parsed.href.replace(/\/$/,"");
  }catch{return answer("not_configured",503);}
  let result, status;
  try{
    const response=await fetch(base+"/crm.lead.fields.json",{
      method:"POST",
      headers:{"content-type":"application/json","accept":"application/json"},
      body:"{}",redirect:"error",signal:AbortSignal.timeout(9000)
    });
    status=response.status;
    try{result=await response.json();}
    catch{return answer("non_json_http_"+String(status),502);}
  }catch(e){
    return answer(["TimeoutError","AbortError"].includes(e?.name)?"crm_timeout":"crm_connect_failure",502);
  }
  let code;
  if(result?.error) {
    const error=String(result.error).toUpperCase();
    code=/INVALID_CREDENTIALS|INVALID_TOKEN|EXPIRED_TOKEN/.test(error)?"crm_auth_rejected":
      /ACCESS_DENIED|INSUFFICIENT_SCOPE|USER_ACCESS_ERROR/.test(error)?"crm_access_denied":
      /METHOD_NOT_FOUND/.test(error)?"crm_method_unavailable":"crm_api_rejected";
  }else if(status!==200)code="crm_http_"+String(status);
  else if(result?.result && typeof result.result==="object" && result.result.NAME)
    code="crm_fields_ok";
  else code="crm_unexpected_response";
  cached={code,status:code==="crm_fields_ok"?200:502};
  cachedAt=Date.now();
  return answer(cached.code,cached.status);
}
