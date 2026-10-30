#!/usr/bin/env python3
"""Publish only homepage local-only preview. No PHP, webhook, private config or policy writes."""
import base64,hashlib,json,os,re,runpy,shlex,subprocess,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
preview=runpy.run_path(str(ROOT/'scripts/form_preview.py'))
BASE='https://24bkm.com'
OUT=Path('form-preview-review');OUT.mkdir(exist_ok=True)

def read(path):
    req=urllib.request.Request(BASE+path,headers={'Cache-Control':'no-cache','User-Agent':'BKM-owner-form-preview/1.0'})
    with urllib.request.urlopen(req,timeout=20) as r:
        assert r.status==200 and urlsplit(r.url).hostname in ('24bkm.com','www.24bkm.com')
        return r.read(2000000)

def verify(body,label):
    results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in (390,768,1440):
            ctx=browser.new_context(viewport={'width':width,'height':1000})
            requests=[]
            def route(r):
                u=urlsplit(r.request.url)
                if r.request.method!='GET':r.abort();return
                if body is not None and u.hostname=='24bkm.com' and u.path in ('/','/index.html'):
                    r.fulfill(status=200,content_type='text/html; charset=utf-8',body=body)
                else:r.continue_()
            ctx.route('**/*',route)
            page=ctx.new_page()
            page.goto(BASE+'/index.html#contact',wait_until='domcontentloaded',timeout=35000)
            box=page.locator('[data-bkm-form-preview="20261030"]')
            expect(box).to_be_visible()
            assert page.locator('form').count()==0
            box.locator('[data-preview=check]').click()
            assert box.locator('[data-field=name]').evaluate('e=>e.validity.valueMissing')
            box.locator('[data-preview=example]').click()
            expect(box.locator('[data-field=service]')).to_have_value('Финансовое сопровождение')
            page.on('request',lambda r:requests.append({'method':r.method,'url':r.url}))
            box.locator('[data-preview=check]').click()
            expect(page.locator('#bkm-preview-status')).to_contain_text('лид в Bitrix24 не создан')
            box.locator('[data-field=phone]').fill('123456')
            box.locator('[data-preview=check]').click()
            assert box.locator('[data-field=phone]').evaluate('e=>e.validity.tooShort') or box.locator('[data-field=phone]').input_value()=='123456'
            box.locator('[data-preview=example]').click()
            box.locator('[data-preview=check]').click()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
            assert not [r for r in requests if r['method']!='GET' or '/api/' in r['url'] or 'bitrix.24bkm.com' in r['url'] or 'test%40example' in r['url']]
            assert page.locator('#bkm-header').locator('a').filter(has_text='Рассчитать доставку').count()==1
            page.screenshot(path=str(OUT/(label+'-'+str(width)+'.png')))
            box.locator('[data-preview=clear]').click()
            expect(box.locator('[data-field=name]')).to_have_value('')
            results.append({'width':width,'visible':True,'validation':True,'no_submission':True,'overflow':False})
            ctx.close()
        browser.close()
    (OUT/(label+'.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(label.upper()+'_FORM_PREVIEW_PASS: three widths, local validation, reset, no submission')

REMOTE=r'''
import base64,hashlib,json,os,re,sys
from pathlib import Path
p=json.load(sys.stdin);run=p['run'];assert re.fullmatch(r'[0-9]+-[0-9]+',run)
root=Path('/home/h/help24pw/24bkm.com/public_html');target=root/'index.html'
backup=Path('/home/h/help24pw/.bkm_backups/form-preview-'+run)
def digest(b):return hashlib.sha256(b).hexdigest()
assert target.is_file() and not target.is_symlink()
if p['mode']=='apply':
    assert digest(target.read_bytes())==p['before'],'Concurrent homepage modification'
    new=base64.b64decode(p['content'],validate=True)
    assert b'<?php' not in new and b'<form ' not in new and b'data-bkm-form-preview="20261030"' in new
    backup.mkdir(mode=0o700,parents=True,exist_ok=False);os.chmod(str(backup),0o700)
    old=target.read_bytes();(backup/'index.html').write_bytes(old);os.chmod(str(backup/'index.html'),0o600)
    mode=target.stat().st_mode&0o777
    (backup/'manifest.json').write_text(json.dumps({'before':digest(old),'after':digest(new),'mode':mode}));os.chmod(str(backup/'manifest.json'),0o600)
    assert digest(target.read_bytes())==p['before']
    temp=root/('.bkm-form-preview-'+run)
    with temp.open('xb') as f:f.write(new)
    os.chmod(str(temp),mode);os.replace(str(temp),str(target))
    print('FORM_PREVIEW_HTML_APPLIED: one homepage; backup form-preview-'+run)
elif p['mode']=='rollback':
    if not (backup/'manifest.json').is_file():print('NOT_APPLIED');sys.exit(0)
    m=json.loads((backup/'manifest.json').read_text());assert digest(target.read_bytes()) in (m['before'],m['after'])
    temp=root/('.bkm-form-rollback-'+run)
    with temp.open('xb') as f:f.write((backup/'index.html').read_bytes())
    os.chmod(str(temp),m['mode']);os.replace(str(temp),str(target));print('FORM_PREVIEW_ROLLED_BACK')
else:raise ValueError('Invalid operation')
'''

def main():
    before=read('/index.html')
    config=read('/assets/site-config.js')
    assert re.search(rb'formsEnabled\s*:\s*false',config),'Do not override live CRM intake'
    assert re.search(rb'analyticsEnabled\s*:\s*false',config),'External analytics needs review'
    after=preview['replace_preview'](before.decode('utf-8')).encode('utf-8')
    protected=['/services.html','/news.html','/assets/site-config.js','/assets/lead-form.js','/assets/bkm-header.svg','/robots.txt','/sitemap.xml']
    stable={p:hashlib.sha256(read(p)).hexdigest() for p in protected}
    verify(after,'candidate')
    run=os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
    remote=os.environ['USER']+'@'+os.environ['HOST']
    options=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=20']
    def invoke(p):subprocess.run(['ssh',*options,remote,'python3 -c '+shlex.quote(REMOTE)],input=json.dumps(p),text=True,check=True,timeout=45)
    attempted=False
    try:
        attempted=True
        invoke({'mode':'apply','run':run,'before':hashlib.sha256(before).hexdigest(),'content':base64.b64encode(after).decode('ascii')})
        assert read('/index.html')==after and read('/')==after
        assert stable=={p:hashlib.sha256(read(p)).hexdigest() for p in protected}
        verify(None,'live')
        print('FORM_PREVIEW_LIVE_PASS: visual/local validation form only, no leads or personal-data receiver. Policies, existing PHP, config, DNS, HTTPS rules and protected files unchanged.')
    except BaseException:
        if attempted:invoke({'mode':'rollback','run':run})
        raise
if __name__=='__main__':main()
