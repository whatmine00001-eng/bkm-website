#!/usr/bin/env python3
"""Owner-authorized static HTML repair. Never deploy API/PHP or change CRM/DNS."""
import base64
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

BASE = 'https://24bkm.com'
REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('brand', REPO/'scripts/finalize-brand-pages.py')
brand = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brand)
OUT = Path('brand-release-review')
OUT.mkdir(exist_ok=True)

# This script runs via existing secured SSH, not as a public web endpoint.
REMOTE = r'''
import base64, hashlib, json, os, re, sys
from pathlib import Path
p=json.load(sys.stdin)
run=p['run']
assert re.fullmatch(r'[0-9]+-[0-9]+',run)
root=Path('/home/h/help24pw/24bkm.com/public_html')
backup=Path('/home/h/help24pw/.bkm_backups/brand-html-'+run)
def digest(b): return hashlib.sha256(b).hexdigest()
if p['mode']=='apply':
    rows=p['files']
    assert 8<=len(rows)<=40
    for name,row in rows.items():
        assert re.fullmatch(r'[a-z0-9-]+\.html',name) and name!='privacy.html'
        path=root/name
        assert path.is_file() and not path.is_symlink()
        assert digest(path.read_bytes())==row['before'], 'Concurrent modification: '+name
        content=base64.b64decode(row['content'],validate=True)
        assert b'<?php' not in content and b'</html>' in content.lower()
    backup.mkdir(mode=0o700,parents=True,exist_ok=False)
    os.chmod(str(backup),0o700)
    manifest={}
    for name,row in rows.items():
        old=(root/name).read_bytes()
        (backup/name).write_bytes(old)
        os.chmod(str(backup/name),0o600)
        manifest[name]={'before':digest(old),'after':digest(base64.b64decode(row['content'])),'mode':(root/name).stat().st_mode&0o777}
    (backup/'manifest.json').write_text(json.dumps(manifest))
    os.chmod(str(backup/'manifest.json'),0o600)
    try:
        for name,row in rows.items():
            path=root/name
            assert digest(path.read_bytes())==row['before'], 'Concurrent modification during apply'
            tmp=root/('.bkm-html-'+run+'-'+name)
            with tmp.open('xb') as f: f.write(base64.b64decode(row['content']))
            os.chmod(str(tmp),manifest[name]['mode'])
            os.replace(str(tmp),str(path))
    except BaseException:
        for name,row in manifest.items():
            path=root/name
            if digest(path.read_bytes())==row['after']:
                path.write_bytes((backup/name).read_bytes())
                os.chmod(str(path),row['mode'])
        raise
    print('STATIC_HTML_APPLIED: '+str(len(rows))+' pages; private backup brand-html-'+run)
elif p['mode']=='rollback':
    if not (backup/'manifest.json').is_file():
        print('NO_TRANSACTION_TO_ROLL_BACK'); sys.exit(0)
    rows=json.loads((backup/'manifest.json').read_text())
    for name,row in rows.items():
        path=root/name
        assert digest(path.read_bytes()) in (row['before'],row['after']), 'Concurrent edit; manual review required'
    for name,row in rows.items():
        path=root/name
        tmp=root/('.bkm-restore-'+run+'-'+name)
        with tmp.open('xb') as f: f.write((backup/name).read_bytes())
        os.chmod(str(tmp),row['mode']); os.replace(str(tmp),str(path))
    print('STATIC_HTML_ROLLBACK_COMPLETE')
else: raise ValueError('Unsupported mode')
'''

def read(url):
    req=urllib.request.Request(url,headers={'Cache-Control':'no-cache','User-Agent':'BKM-owner-static-HTML-repair/1.0'})
    with urllib.request.urlopen(req,timeout=20) as r:
        if r.status!=200 or urlsplit(r.url).hostname not in ('24bkm.com','www.24bkm.com'):
            raise RuntimeError('Unexpected response: '+url)
        return r.read(3000000)

def browser_check(candidate, label):
    from playwright.sync_api import sync_playwright
    checks=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        for width in (390,1024,1440,1920):
            context=browser.new_context(viewport={'width':width,'height':950})
            def intercept(route):
                request=route.request
                if request.method!='GET':
                    route.abort(); return
                u=urlsplit(request.url)
                name='index.html' if u.path=='/' else u.path.lstrip('/')
                if candidate is not None and u.hostname=='24bkm.com' and name in candidate:
                    route.fulfill(status=200,content_type='text/html; charset=utf-8',body=candidate[name])
                else: route.continue_()
            context.route('**/*',intercept)
            page=context.new_page()
            for path in ('/','/index.html'):
                response=page.goto(BASE+path,wait_until='domcontentloaded',timeout=35000)
                assert response.status==200
                page.wait_for_timeout(700)
                header=page.locator('.site-header')
                assert header.locator('a').filter(has_text='Рассчитать доставку').count()==1, 'Duplicate remains in HTML'
                if width<=1050:
                    page.locator('#menu-toggle').click()
                    assert page.locator('#site-nav .bkm-header-action').is_visible()
                    page.keyboard.press('Escape')
                else:
                    assert page.locator('#site-nav .bkm-header-action').is_visible()
                assert page.locator('body').inner_text().find('Год начала работы требует подтверждения')==-1
                assert page.locator('.stat__number').first.inner_text().strip()=='2011'
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), 'Horizontal overflow'
                assert page.locator('link[rel=canonical]').count()==1
                assert page.title().startswith('БКМ (BKM)')
                checks.append({'path':path,'width':width,'single_cta':True,'year':2011})
            page.screenshot(path=str(OUT/(label+'-home-'+str(width)+'.png')))
            context.close()
        browser.close()
    (OUT/(label+'.json')).write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    print(label.upper()+'_BROWSER_PASS: root and index.html at four widths; one action; year and SEO')

def main():
    sitemap=ET.fromstring(read(BASE+'/sitemap.xml'))
    urls=list(dict.fromkeys(n.text for n in sitemap.findall('.//{*}loc')))
    assert 8<=len(urls)<=40
    mapping={}
    for url in urls:
        u=urlsplit(url)
        assert u.scheme=='https' and u.netloc=='24bkm.com' and not u.query
        name='index.html' if u.path=='/' else u.path.lstrip('/')
        assert re.fullmatch(r'[a-z0-9-]+\.html',name) and name!='privacy.html'
        mapping[name]=BASE+'/'+name
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        before=dict(zip(mapping,pool.map(read,mapping.values())))
    after={name:brand.finalize(b.decode('utf-8'),name).encode('utf-8') for name,b in before.items()}
    for name,b in after.items():
        assert brand.finalize(b.decode('utf-8'),name).encode('utf-8')==b
        assert b'noindex' not in b.lower()
    protected=['/assets/site-config.js','/assets/bkm-header.svg','/robots.txt','/sitemap.xml']
    stable={p:hashlib.sha256(read(BASE+p)).hexdigest() for p in protected}
    browser_check(after,'candidate')
    run=os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
    remote=os.environ['USER']+'@'+os.environ['HOST']
    options=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=20']
    import shlex
    def invoke(payload):
        subprocess.run(['ssh',*options,remote,'python3 -c '+shlex.quote(REMOTE)],input=json.dumps(payload),text=True,check=True,timeout=60)
    files={name:{'before':hashlib.sha256(before[name]).hexdigest(),'content':base64.b64encode(b).decode('ascii')} for name,b in after.items()}
    attempted=False
    try:
        attempted=True
        invoke({'mode':'apply','run':run,'files':files})
        for name,content in after.items():
            assert read(BASE+'/'+name)==content, 'Published HTML differs: '+name
        assert read(BASE+'/')==after['index.html'], 'Root not serving index.html'
        for p,sha in stable.items():
            assert hashlib.sha256(read(BASE+p)).hexdigest()==sha, 'Protected file changed: '+p
        browser_check(None,'live')
        print('BRAND_HTML_LIVE_PASS: '+str(len(after))+' pages published; one actual header link, 2011, bilingual SEO, versioned styles.')
        print('CRM_UNCHANGED: no API deployment, lead creation, private config, DNS or .htaccess edits.')
    except BaseException:
        if attempted: invoke({'mode':'rollback','run':run})
        raise

if __name__=='__main__': main()
