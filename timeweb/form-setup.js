/* Timeweb PHP form startup; no reliance on Cloudflare scripts or widgets. */
(function(){
"use strict";
const form=document.getElementById("bkm-lead-form");
if(!form)return;
const button=form.querySelector('button[type="submit"]');
const token=form.elements.form_token;
const status=document.getElementById("bkm-form-status");
if(!button||!token)return;
function message(text,type){
 if(!status)return;
 status.textContent=text;
 status.dataset.type=type||"info";
}
function unavailable(){
 button.disabled=true;
 token.value="";
 message("Форма временно недоступна. Напишите на info@24bkm.com или позвоните 8 800 707-79-02.","error");
}
async function prepare(){
 const keepSuccess=status && status.dataset.type==="success";
 button.disabled=true;token.value="";
 if(!keepSuccess)message("Проверяем готовность формы…");
 try{
   const controller=new AbortController();
   const timeout=setTimeout(()=>controller.abort(),10000);
   let response;
   try{
     response=await fetch("/api/form-config.php",{
       credentials:"same-origin",cache:"no-store",
       headers:{"Accept":"application/json"},signal:controller.signal
     });
   }finally{clearTimeout(timeout);}
   if(!response.ok)throw Error("not_ready");
   const data=await response.json();
   if(data.ready!==true || typeof data.form_token!=="string" ||
     !/^[0-9]{10}\.[a-f0-9]{64}$/.test(data.form_token))throw Error("not_ready");
   token.value=data.form_token;
   // Prevent instant bot form submissions; backend also enforces minimum age.
   await new Promise(resolve=>setTimeout(resolve,3100));
   if(form.dataset.deliveryUnconfirmed==="true")return;
   button.disabled=false;
   if(!keepSuccess)message("Заполните поля и отправьте заявку — она поступит менеджеру БКМ.","info");
 }catch(_){if(!keepSuccess)unavailable();}
}
window.BKMRefreshFormToken=function(){
 if(form.dataset.deliveryUnconfirmed==="true")return;
 prepare();
};
prepare();
})();
