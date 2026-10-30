#!/usr/bin/env python3
"""BKM style-only safe release. Deploy ONE CSS file with rollback.

No change to HTML, forms, personal data, Bitrix24, secrets, DNS or other styles.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import urllib.request
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'assets/home-brand-final.css'
OUT=Path('cinematic-style-review')
OUT.mkdir(exist_ok=True)
URL='https://24bkm.com'
RUN=os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
HOST=os.environ['BEGET_HOST']
USER=os.environ['BEGET_USER']
SSH=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=20']
REMOTE=USER+'@'+HOST
STAGE='/home/h/help24pw/.bkm_releases/cinematic-style-'+RUN
TARGET='/home/h/help24pw/24bkm.com/public_html/assets/home-brand-final.css'
BACKUP='/home/h/help24pw/.bkm_backups/cinematic-style-'+RUN
NEW=SRC.read_bytes()
assert b'BKM_CINEMATIC_RESTORE_20261030' in NEW
assert b'bitrix_webhook_url' not in NEW and b'<?php' not in NEW
assert len(NEW)<45000 and b'@import url(' in NEW

def sha(b):return hashlib.sha256(b).hexdigest()
def get(path):
    req=urllib.request.Request(URL+path,headers={'Cache-Control':'no-cache','User-Agent':'BKM-owner-cinematic-style-check'})
    with urllib.request.urlopen(req,timeout=25) as r:
        assert r.status==200 and urlsplit(r.url).hostname in ('24bkm.com','www.24bkm.com')
        return r.read(3000000)
def ssh(s):
    subprocess.run(['ssh',*SSH,REMOTE,s],check=True,timeout=35)
def remote_py(script):
    ssh('python3 -c '+shlex.quote(script))
def preview(styles=None, label='candidate'):
    with sync_playwright() as p:
        browser=p.chromium.launch()
        checks=[]
        for w in (390,768,1440):
            ctx=browser.new_context(viewport={'width':w,'height':950},device_scale_factor=1)
            if styles is not None:
                def serve(route):
                    route.fulfill(status=200,body=styles,content_type='text/css; charset=utf-8',
                                  headers={'Cache-Control':'no-store'})
                ctx.route('**/assets/home-brand-final.css*',serve)
            page=ctx.new_page()
            response=page.goto(URL+'/index.html',wait_until='domcontentloaded',timeout=45000)
            assert response.status==200
            page.wait_for_timeout(600)
            hero=page.locator('.hero')
            assert hero.count()==1
            bg=hero.evaluate('(e)=>getComputedStyle(e).backgroundColor')
            assert bg=='rgb(5, 31, 37)', ('hero dark background not loaded: '+bg)
            text_color=page.locator('.hero h1').evaluate('(e)=>getComputedStyle(e).color')
            assert text_color=='rgb(249, 251, 255)',('hero text not light: '+text_color)
            panel=page.locator('#bkm-mail-contact')
            assert panel.count()==1, 'existing form missing'
            form_bg=panel.evaluate('(e)=>getComputedStyle(e).backgroundImage')
            assert 'gradient' in form_bg and 'rgba(9, 56, 55' in form_bg,('form glass background missing: '+form_bg)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'), 'horizontal overflow'
            assert page.locator('#bkm-header').count()==1, 'shared navigation changed'
            page.screenshot(path=str(OUT/(label+'-'+str(w)+'.png')),full_page=True)
            checks.append({'width':w,'hero_dark':bg,'text_color':text_color,
                           'form_glass':True,'overflow':False,'navigation_intact':True})
            ctx.close()
        browser.close()
        (OUT/(label+'.json')).write_text(json.dumps(checks,ensure_ascii=False,indent=2))
        print('CINEMATIC_BROWSER_'+label.upper()+'_PASS at 390, 768 and 1440 px',flush=True)

def main():
    BEFORE=get('/assets/home-brand-final.css')
    if sha(BEFORE)==sha(NEW):
        print('CINEMATIC_CSS_ALREADY_LIVE')
        preview(None,'live')
        return
    assert b'.hero{background:#f7f8f7' in BEFORE or b'BKM_CINEMATIC_RESTORE_20261030' in BEFORE
    before_html=get('/index.html')
    private_config_sha=None
    preview(NEW,'candidate')
    ssh('mkdir -p '+shlex.quote(STAGE)+' && chmod 700 '+shlex.quote(STAGE))
    subprocess.run(['scp',*SSH,str(SRC),REMOTE+':'+STAGE+'/home-brand-final.css'],
                   check=True,timeout=30)
    script=r'''
import hashlib,os,pathlib,sys
src=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);backup=pathlib.Path(sys.argv[3])
expected=sys.argv[4];new=sys.argv[5]
def sha(b):return hashlib.sha256(b).hexdigest()
assert src.is_file() and dest.is_file() and not dest.is_symlink()
old=dest.read_bytes();content=src.read_bytes()
assert sha(old)==expected,'Live file changed while preparing'
assert sha(content)==new and b'BKM_CINEMATIC_RESTORE_20261030' in content
assert not backup.exists()
backup.mkdir(parents=True,mode=0o700)
(backup/'home-brand-final.css').write_bytes(old)
os.chmod(backup/'home-brand-final.css',0o600)
tmp=dest.with_name('.bkm-cinematic-'+sys.argv[6]+'.css')
with tmp.open('xb') as file: file.write(content)
os.chmod(tmp,0o644);os.replace(tmp,dest)
assert sha(dest.read_bytes())==new
print('ONE_CSS_DEPLOYED with backup; no HTML, JS, PHP or CRM modified')
'''
    from subprocess import run
    remote_py(script+'\n') if False else None
    command='python3 -c '+shlex.quote(script)+' '+' '.join(shlex.quote(arg) for arg in
     [STAGE+'/home-brand-final.css',TARGET,BACKUP,sha(BEFORE),sha(NEW),RUN])
    deployed=False
    try:
        deployed=True
        ssh(command)
        assert sha(get('/assets/home-brand-final.css'))==sha(NEW), 'Live CSS bytes are not current'
        assert get('/index.html')==before_html, 'Homepage HTML changed unexpectedly'
        preview(None,'live')
        print('CINEMATIC_STYLE_LIVE_PASS: only assets/home-brand-final.css changed',flush=True)
    except BaseException:
        if deployed:
            restore=r'''
import hashlib,os,pathlib,sys
dest=pathlib.Path(sys.argv[1]);backup=pathlib.Path(sys.argv[2])
expected=sys.argv[3]
def sha(b):return hashlib.sha256(b).hexdigest()
orig=backup/'home-brand-final.css'
if orig.is_file() and dest.is_file() and sha(dest.read_bytes())==expected:
 tmp=dest.with_name('.bkm-cinematic-restore-'+sys.argv[4]+'.css')
 with tmp.open('xb') as f:f.write(orig.read_bytes())
 os.chmod(tmp,0o644);os.replace(tmp,dest)
 print('CINEMATIC_ROLLBACK_COMPLETE')
else:
 print('CINEMATIC_MANUAL_REVIEW_REQUIRED')
'''
            ssh('python3 -c '+shlex.quote(restore)+' '+' '.join(shlex.quote(a) for a in
                [TARGET,BACKUP,sha(NEW),RUN]))
        raise

if __name__=='__main__':main()
