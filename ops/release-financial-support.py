#!/usr/bin/env python3
"""Publish only index.html/services.html. No CRM, private settings, DNS or policy changes."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import subprocess
import urllib.request
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
patch=runpy.run_path(str(ROOT/'scripts/financial_support.py'))
BASE='https://24bkm.com'
FILES=('index.html','services.html')
OUT=Path('financial-support-review');OUT.mkdir(exist_ok=True)

def read(url):
    req=urllib.request.Request(url,headers={'Cache-Control':'no-cache','User-Agent':'BKM-owner-service-release/1.0'})
    with urllib.request.urlopen(req,timeout=25) as r:
        if r.status!=200 or urlsplit(r.url).hostname not in ('24bkm.com','www.24bkm.com'):
            raise RuntimeError('Unexpected public response')
        return r.read(3000000)

def sha(data):return hashlib.sha256(data).hexdigest()

REMOTE=r'''
import base64,hashlib,json,os,re,sys
from pathlib import Path
p=json.load(sys.stdin);run=p['run']
assert re.fullmatch(r'[0-9]+-[0-9]+',run)
root=Path('/home/h/help24pw/24bkm.com/public_html')
backup=Path('/home/h/help24pw/.bkm_backups/financial-support-'+run)
def digest(b):return hashlib.sha256(b).hexdigest()
if p['mode']=='apply':
    rows=p['files'];assert set(rows)=={'index.html','services.html'}
    for name,row in rows.items():
        target=root/name
        assert target.is_file() and not target.is_symlink()
        assert digest(target.read_bytes())==row['before'],'Concurrent change detected'
        content=base64.b64decode(row['content'],validate=True)
        assert b'<?php' not in content and b'</html>' in content.lower()
        assert b'data-bkm-service="financial-support"' in content
    backup.mkdir(mode=0o700,parents=True,exist_ok=False);os.chmod(str(backup),0o700)
    manifest={}
    for name,row in rows.items():
        old=(root/name).read_bytes();(backup/name).write_bytes(old);os.chmod(str(backup/name),0o600)
        manifest[name]={'before':digest(old),'after':digest(base64.b64decode(row['content'])),'mode':(root/name).stat().st_mode&0o777}
    (backup/'manifest.json').write_text(json.dumps(manifest));os.chmod(str(backup/'manifest.json'),0o600)
    for name,row in rows.items():
        assert digest((root/name).read_bytes())==row['before'],'Concurrent change during publication'
        temp=backup/(name+'.next')
        with temp.open('xb') as f:f.write(base64.b64decode(row['content']))
        os.chmod(str(temp),manifest[name]['mode']);os.replace(str(temp),str(root/name))
    print('FINANCIAL_HTML_APPLIED: two files; private backup financial-support-'+run)
elif p['mode']=='rollback':
    if not (backup/'manifest.json').is_file():
        print('NO_TRANSACTION_TO_ROLL_BACK');sys.exit(0)
    manifest=json.loads((backup/'manifest.json').read_text())
    assert set(manifest)=={'index.html','services.html'}
    for name,row in manifest.items():
        assert digest((root/name).read_bytes()) in (row['before'],row['after']),'Concurrent edit: manual review required'
    for name,row in manifest.items():
        temp=backup/(name+'.restore')
        with temp.open('xb') as f:f.write((backup/name).read_bytes())
        os.chmod(str(temp),row['mode']);os.replace(str(temp),str(root/name))
    print('FINANCIAL_HTML_ROLLBACK_COMPLETE')
else:raise ValueError('Unsupported mode')
'''

def browser_check(candidate,label):
    from playwright.sync_api import sync_playwright
    results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in (320,390,768,1440,1920):
            context=browser.new_context(viewport={'width':width,'height':950})
            def intercept(route):
                req=route.request
                if req.method!='GET':route.abort();return
                u=urlsplit(req.url);name='index.html' if u.path=='/' else u.path.lstrip('/')
                if candidate is not None and u.hostname=='24bkm.com' and name in candidate:
                    route.fulfill(status=200,content_type='text/html; charset=utf-8',body=candidate[name])
                else:route.continue_()
            context.route('**/*',intercept)
            page=context.new_page()
            for name in FILES:
                response=page.goto(BASE+'/'+name,wait_until='domcontentloaded',timeout=40000)
                assert response.status==200
                page.wait_for_timeout(900)
                if name=='index.html':
                    assert page.locator('#services .service-card').count()==6
                    expect=page.locator('#financial-support-home')
                    assert expect.locator('a').get_attribute('href')=='services.html#financial-support'
                    assert page.locator('.stat__number').nth(1).inner_text().strip()=='6'
                else:
                    assert page.locator('#services .card').count()==6
                    assert page.locator('#financial-support .bkm-financial-grid article').count()==4
                    expect=page.locator('#financial-support')
                    assert 'только с допустимыми сделками' in expect.inner_text()
                    assert page.locator('#financial-support .cta').get_attribute('href').startswith('mailto:info@24bkm.com')
                assert page.locator('#bkm-header .bkm-header-action').count()==1
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+2'),'Horizontal overflow'
                if width<=1050:
                    page.locator('#menu-toggle').click()
                    assert page.locator('#site-nav .bkm-header-action').is_visible()
                    page.keyboard.press('Escape')
                else:assert page.locator('#site-nav .bkm-header-action').is_visible()
                expect.scroll_into_view_if_needed();page.wait_for_timeout(200)
                if width in (390,1440):
                    page.screenshot(path=str(OUT/(label+'-'+name[:-5]+'-'+str(width)+'.png')))
                results.append({'page':name,'width':width,'six_services':True,'single_header_action':True,'overflow':False})
            context.close()
        browser.close()
    (OUT/(label+'.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(label.upper()+'_FINANCIAL_BROWSER_PASS: 10 page/width checks; menu, cards and layout')

def main():
    patch['self_test']()
    # Test the same transformation on the repository's source pages, without changing them.
    for name in FILES:
        source=(ROOT/name).read_text(encoding='utf-8')
        result=patch['transform'](source,name)
        assert patch['transform'](result,name)==result
    before={name:read(BASE+'/'+name) for name in FILES}
    after={name:patch['transform'](body.decode('utf-8'),name).encode('utf-8') for name,body in before.items()}
    for name,body in after.items():
        assert patch['transform'](body.decode('utf-8'),name).encode('utf-8')==body
        assert not re.search(r'<meta[^>]+noindex',body.decode('utf-8'),re.I)
        (OUT/name).write_bytes(body)
    stable_paths=('/assets/site-config.js','/assets/lead-form.js','/assets/bkm-header.svg','/assets/home.js','/sitemap.xml','/robots.txt','/news.html')
    stable={path:sha(read(BASE+path)) for path in stable_paths}
    browser_check(after,'candidate')
    if after==before:
        browser_check(None,'live');print('ALREADY_PUBLISHED: content validated, no write');return
    run=os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
    remote=os.environ['USER']+'@'+os.environ['HOST']
    options=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=20']
    def invoke(payload):
        subprocess.run(['ssh',*options,remote,'python3 -c '+shlex.quote(REMOTE)],input=json.dumps(payload),text=True,check=True,timeout=65)
    payload={name:{'before':sha(before[name]),'content':base64.b64encode(body).decode('ascii')} for name,body in after.items()}
    attempted=False
    try:
        attempted=True;invoke({'mode':'apply','run':run,'files':payload})
        for name,body in after.items():assert read(BASE+'/'+name)==body,'Public HTML mismatch'
        assert read(BASE+'/')==after['index.html'],'Root differs from index.html'
        for path,expected in stable.items():assert sha(read(BASE+path))==expected,'Protected file changed'
        browser_check(None,'live')
        print('FINANCIAL_SUPPORT_LIVE_PASS: two existing pages; six services; procurement, third-country compliance and agency support.')
        print('UNCHANGED: public form markup, all scripts, CRM settings, policies, original logo, header, news, sitemap, robots, DNS and .htaccess.')
    except BaseException:
        if attempted:invoke({'mode':'rollback','run':run})
        raise

if __name__=='__main__':main()
