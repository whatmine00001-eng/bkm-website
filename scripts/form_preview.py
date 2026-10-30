#!/usr/bin/env python3
"""Local-only form preview; no network, policy publication or CRM activation.
A role=form container avoids default GET submission even without JavaScript.
"""
import re

FORM = '''<div class="form" id="bkm-mail-contact" data-bkm-form-preview="20261030" role="form" aria-labelledby="bkm-preview-title">
<h3 id="bkm-preview-title">Обсудить поставку</h3>
<p class="bkm-preview-banner"><strong>Тестовая форма.</strong> Данные остаются в этой вкладке и не отправляются в БКМ или Bitrix24. Для проверки используйте вымышленные данные.</p>
<div class="fields">
<label class="field">Имя *<input id="bkm-preview-name" data-field="name" required minlength="2" maxlength="120" autocomplete="off" placeholder="Как к вам обращаться"></label>
<label class="field">Телефон *<input id="bkm-preview-phone" data-field="phone" required type="tel" minlength="7" maxlength="36" autocomplete="off" placeholder="Контактный телефон"></label>
<label class="field">Компания<input data-field="company" maxlength="160" autocomplete="off" placeholder="Название организации"></label>
<label class="field">Email<input data-field="email" type="email" maxlength="160" autocomplete="off" placeholder="Электронная почта"></label>
<label class="field full">Услуга *<select data-field="service" required><option value="">Выберите направление</option><option>Международные перевозки</option><option>Таможенное оформление</option><option>Экспедирование</option><option>Логистика и склад</option><option>Сборные грузы</option><option>Финансовое сопровождение</option><option>Другое</option></select></label>
<label class="field">Откуда<input data-field="origin" maxlength="150" autocomplete="off" placeholder="Город, страна"></label>
<label class="field">Куда<input data-field="destination" maxlength="150" autocomplete="off" placeholder="Город, страна"></label>
<label class="field full">Груз<input data-field="cargo" maxlength="180" autocomplete="off" placeholder="Наименование, вес и объём"></label>
<label class="field full">Описание задачи<textarea data-field="details" maxlength="1600" rows="3" autocomplete="off" placeholder="Сроки и особенности поставки"></textarea></label>
</div>
<div class="form__actions bkm-preview-actions"><button class="btn" type="button" data-preview="check">Проверить заполнение</button><button class="bkm-preview-secondary" type="button" data-preview="example">Тестовый пример</button><button class="bkm-preview-secondary" type="button" data-preview="clear">Очистить</button></div>
<p id="bkm-preview-status" role="status" aria-live="polite">Это проверка интерфейса, а не отправка заявки.</p>
<p class="note">Для реального обращения: <a href="mailto:info@24bkm.com">info@24bkm.com</a> или <a href="tel:+78007077902">8 800 707-79-02</a>.</p>
<noscript><p>Проверка заполнения требует JavaScript. Эта форма ничего не отправляет.</p></noscript>
</div>'''
STYLE = '''<style id="bkm-form-preview-style">
#bkm-mail-contact[data-bkm-form-preview]{min-width:0;width:100%}
#bkm-mail-contact .bkm-preview-banner{padding:12px 14px;border-left:3px solid #ff7900;background:#fff6ec;font-size:13px;line-height:1.65;color:#183e32;margin:14px 0 20px}
#bkm-mail-contact .fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
#bkm-mail-contact .field{display:flex;flex-direction:column;gap:6px;min-width:0;font-size:14px;color:#173e32}
#bkm-mail-contact .field.full{grid-column:1/-1}
#bkm-mail-contact input,#bkm-mail-contact select,#bkm-mail-contact textarea{width:100%;min-width:0;box-sizing:border-box;border:1px solid #b9cec3;border-radius:6px;padding:12px;background:#fff;color:#173e32;font:16px/1.5 Manrope,Arial,sans-serif}
#bkm-mail-contact textarea{resize:vertical}
#bkm-mail-contact .bkm-preview-actions{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-top:20px}
#bkm-mail-contact .bkm-preview-actions .btn{cursor:pointer;white-space:normal;border:0}
#bkm-mail-contact .bkm-preview-secondary{background:transparent;color:#174e3b;border:0;text-decoration:underline;cursor:pointer;font:600 13px/1.4 Manrope,Arial,sans-serif;padding:8px 0;min-height:44px}
#bkm-preview-status{font-size:14px;line-height:1.65;color:#315b4b;margin:16px 0 0}
#bkm-mail-contact .note{font-size:13px;line-height:1.6}
#bkm-mail-contact .note a{overflow-wrap:anywhere;text-decoration:underline}
@media(max-width:480px){#bkm-mail-contact .fields{grid-template-columns:minmax(0,1fr)}#bkm-mail-contact .bkm-preview-actions .btn{width:100%}}
</style>'''
SCRIPT = '''<script id="bkm-form-preview-script">
(function(){
'use strict';
const box=document.querySelector('[data-bkm-form-preview]');if(!box)return;
const status=document.getElementById('bkm-preview-status');
const fields=Array.from(box.querySelectorAll('[data-field]'));
const say=function(text){status.textContent=text;};
box.addEventListener('input',function(){say('Данные изменены. Это только тест, не отправка заявки.');});
box.querySelector('[data-preview="check"]').addEventListener('click',function(){
for(const field of fields){if(!field.reportValidity()){say('Проверьте обязательные поля и формат данных. Ничего не отправлено.');return;}}
const phone=box.querySelector('[data-field="phone"]');
if(!/^[+0-9 ()-]{7,36}$/.test(phone.value)||phone.value.replace(/\\D/g,'').length<7){say('Проверьте телефон: нужно не менее семи цифр. Ничего не отправлено.');phone.focus();return;}
say('Поля заполнены корректно. Это только тест: заявка не отправлена, лид в Bitrix24 не создан.');
});
box.querySelector('[data-preview="example"]').addEventListener('click',function(){
const values={name:'Тестовая заявка',phone:'+70000000000',company:'Демонстрационный пример',email:'test@example.test',service:'Финансовое сопровождение',origin:'Тестовый пункт отправления',destination:'Тестовый пункт назначения',cargo:'Тестовый груз',details:'Проверка интерфейса без передачи данных'};
for(const field of fields){field.value=values[field.dataset.field]||'';}
say('Подставлены вымышленные данные. Ничего не отправлено.');
});
box.querySelector('[data-preview="clear"]').addEventListener('click',function(){for(const field of fields)field.value='';say('Поля очищены. Ничего не отправлено.');});
})();
</script>'''

def replace_preview(text):
    if 'data-bkm-form-preview="20261030"' in text:return text
    match=re.search(r'<div\s+class="form"\s+id="bkm-mail-contact"[^>]*>.*?</div>',text,re.S|re.I)
    if not match:raise ValueError('Expected inactive mail-contact placeholder missing; do not replace an active form')
    if re.search(r'<form\b',text,re.I):raise ValueError('Active HTML form present; explicit review needed')
    out=text[:match.start()]+FORM+text[match.end():]
    out,n=re.subn(r'</head\s*>',lambda _:STYLE+'\n</head>',out,count=1,flags=re.I)
    if n!=1:raise ValueError('Head missing')
    out,n=re.subn(r'</body\s*>',lambda _:SCRIPT+'\n</body>',out,count=1,flags=re.I)
    if n!=1:raise ValueError('Body missing')
    for block in ('header','footer'):
        if re.findall(r'<'+block+r'\b.*?</'+block+'>',text,re.S|re.I)!=re.findall(r'<'+block+r'\b.*?</'+block+'>',out,re.S|re.I):raise ValueError(block+' unexpectedly modified')
    assert not re.search(r'<form\b',out,re.I)
    return out

if __name__=='__main__':
    source='<html><head><title>t</title></head><body><header>keep</header><div class="form" id="bkm-mail-contact"><p>Email</p></div><footer>keep</footer></body></html>'
    result=replace_preview(source)
    assert replace_preview(result)==result
    assert 'Финансовое сопровождение' in result
    assert '<form' not in result and 'fetch(' not in SCRIPT and 'XMLHttpRequest' not in SCRIPT
    print('FORM_PREVIEW_SELF_TEST_PASS: no policy publication, no form action, no persistence or network code')
