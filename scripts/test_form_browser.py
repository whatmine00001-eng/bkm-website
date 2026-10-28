#!/usr/bin/env python3
"""Offline browser contract tests. Every request intercepted; NO hosting or CRM access.
These tests do NOT claim a real lead was created or a production form activated.
"""
import json
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT/'index.html').read_text(encoding='utf-8')
SCRIPT = (ROOT/'assets/lead-form.js').read_text(encoding='utf-8')
BASE = 'https://bkm-form.test'


def test(pw, code=200, body=None, enabled=True, success=False, label='case'):
    browser = pw.chromium.launch()
    context = browser.new_context(viewport={'width':1280,'height':900})
    posts = []
    def intercept(route):
        r = route.request
        u = urlsplit(r.url)
        if u.hostname != 'bkm-form.test':
            route.abort(); return
        if u.path == '/api/lead.php':
            assert r.method == 'POST'
            posts.append(r.post_data_json)
            route.fulfill(status=code, content_type='application/json', body=body)
        elif u.path == '/assets/site-config.js':
            route.fulfill(content_type='application/javascript', body='window.BKM_SITE_CONFIG='+json.dumps({'formsEnabled':enabled})+';')
        elif u.path == '/assets/lead-form.js':
            route.fulfill(content_type='application/javascript', body=SCRIPT)
        elif u.path == '/assets/analytics.js':
            route.fulfill(content_type='application/javascript', body='/* Analytics disabled for isolated test. */')
        elif u.path == '/index.html':
            route.fulfill(content_type='text/html; charset=utf-8', body=HTML)
        elif u.path.startswith('/assets/'):
            file=ROOT/u.path.lstrip('/')
            if file.is_file() and file.resolve().is_relative_to((ROOT/'assets').resolve()):
                kind='text/css' if file.suffix=='.css' else ('application/javascript' if file.suffix=='.js' else 'image/svg+xml')
                route.fulfill(content_type=kind,body=file.read_bytes())
            else: route.abort()
        else: route.abort()
    context.route('**/*',intercept)
    page=context.new_page()
    page.goto(BASE+'/index.html?utm_source=integration_test&utm_medium=qa#contact',wait_until='domcontentloaded')
    form=page.locator('#bkm-lead-form')
    button=form.locator('button[type=submit]')
    status=page.locator('#bkm-form-status')
    if not enabled:
        expect(button).to_contain_text('Подготовить письмо')
        assert not posts
        print('FORM_BROWSER_PASS: disabled mode does not claim CRM delivery')
        context.close(); browser.close(); return
    expect(button).to_contain_text('Отправить заявку')
    # Required fields and unchecked consent must stop submission in the browser.
    button.click()
    assert not posts
    form.locator('[name=name]').fill('ТЕСТ БКМ')
    form.locator('[name=phone]').fill('+70000000000')
    form.locator('[name=email]').fill('fixture@example.test')
    form.locator('[name=company]').fill('Синтетический тест — не клиент')
    form.locator('[name=service]').select_option(label='Таможенное оформление')
    form.locator('[name=origin]').fill('Тестовое отправление')
    form.locator('[name=destination]').fill('Тестовое назначение')
    form.locator('[name=details]').fill('Только локальная проверка, без сети и CRM')
    button.click()
    assert not posts, 'Unchecked consent must block submission'
    form.locator('[name=consent]').check()
    # Two events in one turn must produce only one in-flight request.
    form.evaluate("f=>{f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));}")
    expect(status).to_have_attribute('data-type','success' if success else 'error')
    assert len(posts)==1, 'Duplicate request sent'
    payload=posts[0]
    assert payload['name']=='ТЕСТ БКМ' and payload['consent'] is True
    assert payload['service']=='Таможенное оформление'
    assert payload['utm_source']=='integration_test' and payload['utm_medium']=='qa'
    assert payload['page']=='/index.html'
    assert 'bitrix_webhook_url' not in payload and 'assigned_by_id' not in payload
    assert payload['website']==''
    expect(button).to_be_enabled()
    if success:
        expect(form.locator('[name=name]')).to_have_value('')
    else:
        expect(form.locator('[name=name]')).to_have_value('ТЕСТ БКМ')
        expect(status).to_contain_text('Не удалось подтвердить')
    print('FORM_BROWSER_PASS: '+label+'; required fields, consent, UTM and duplicate-click guard')
    context.close(); browser.close()

with sync_playwright() as pw:
    test(pw,body=json.dumps({'ok':True,'code':'lead_created'}),success=True,label='synthetic success')
    test(pw,code=503,body=json.dumps({'ok':False,'code':'not_enabled'}),label='disabled backend')
    test(pw,code=502,body=json.dumps({'ok':False,'code':'crm_unavailable'}),label='CRM error response')
    test(pw,body='<html>Server error</html>',label='non-JSON response')
    test(pw,body=json.dumps({'ok':True,'code':'unknown'}),label='unrecognized success rejected')
    test(pw,enabled=False)
print('FORM_CONTRACT_SUITE_PASS: browser-only fixtures; no network escaped interception, no real CRM leads or production changes.')
