#!/usr/bin/env python3
"""Publish only identical site navigation across existing HTML; no article or CRM changes."""
import base64
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import urllib.request
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

BASE='https://24bkm.com'
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('shared_header',ROOT/'scripts/site_header.py')
shared=importlib.util.module_from_spec(spec); spec.loader.exec_module(shared)
OUT=Path('shared-header-review'); OUT.mkdir(exist_ok=True)
REMOTE=r'''
import base64,hashlib,json,os,re,sys
from pathlib import Path
p=json.load(sys.stdin); run=p['run']; assert re.fullmatch(r'[0-9]+-[0-9]+',run)
root=Path('/home/h/help24pw/24bkm.com/public_html')
backup=Path('/home/h/help24pw/.bkm_backups/shared-header-'+run)
def sha(b): return hashlib.sha256(b).hexdigest()
if p['mode']=='apply':
 rows=p['files']; assert 8<=len(rows)<=40
 for name,row in rows.items():
  assert re.fullmatch(r'[a-z0-9-]+\.html',name) and name!='privacy.html'
  path=root/name; assert path.is_file() and not path.is_symlink()
  assert sha(path.read_bytes())==row['before'], 'Concurrent change: '+name
  new=base64.b64decode(row['content'],validate=True)
  assert b'<?php' not in new and b'</html>' in new.lower() and b'id="bkm-header"' in new
 backup.mkdir(parents=True,mode=0o700,exist_ok=False); os.chmod(str(backup),0o700)
 manifest={}
 for name,row in rows.items():
  old=(root/name).read_bytes(); (backup/name).write_bytes(old); os.chmod(str(backup/name),0o600)
  manifest[name]={'before':sha(old),'after':sha(base64.b64decode(row['content'])),'mode':(root/name).stat().st_mode&0o777}
 (backup/'manifest.json').write_text(json.dumps(manifest)); os.chmod(str(backup/'manifest.json'),0o600)
 try:
  for name,row in rows.items():
   path=root/name; assert sha(path.read_bytes())==row['before']
   tmp=root/('.bkm-header-'+run+'-'+name)
   with tmp.open('xb') as f: f.write(base64.b64decode(row['content']))
   os.chmod(str(tmp),manifest[name]['mode']); os.replace(str(tmp),str(path))
 except BaseException:
  for name,row in manifest.items():
   path=root/name
   if sha(path.read_bytes())==row['after']:
    path.write_bytes((backup/name).read_bytes()); os.chmod(str(path),row['mode'])
  raise
 print('HEADER_HTML_APPLIED: '+str(len(rows))+' existing pages; backup shared-header-'+run)
elif p['mode']=='rollback':
 if not (backup/'manifest.json').is_file(): print('NO_TRANSACTION'); sys.exit(0)
 rows=json.loads((backup/'manifest.json').read_text())
 for name,row in rows.items():
  assert sha((root/name).read_bytes()) in (row['before'],row['after']), 'Concurrent edit; stop rollback'
 for name,row in rows.items():
  tmp=root/('.bkm-header-restore-'+run+'-'+name)
  with tmp.open('xb') as f: f.write((backup/name).read_bytes())
  os.chmod(str(tmp),row['mode']); os.replace(str(tmp),str(root/name))
 print('HEADER_ROLLBACK_PASS')
else: raise ValueError('Unsupported mode')
'''

def read(url):
 req=urllib.request.Request(url,headers={'Cache-Control':'no-cache','User-Agent':'BKM-owner-header-review/1.0'})
 with urllib.request.urlopen(req,timeout=20) as r:
  if r.status!=200 or urlsplit(r.url).hostname not in ('24bkm.com','www.24bkm.com'): raise RuntimeError('Unexpected HTTP response')
  return r.read(3000000)

def main_content(text):
 # Keep every main-content block and form byte-for-byte. No news edits.
 return re.findall(r'<main\b.*?</main>|<form\b.*?</form>',text,flags=re.I|re.S)

def browser_check(names,candidate,label):
 from playwright.sync_api import sync_playwright,expect
 results=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch()
  for width in (390,1440):
   context=browser.new_context(viewport={'width':width,'height':950})
   def intercept(route):
    r=route.request; u=urlsplit(r.url); name='index.html' if u.path=='/' else u.path.lstrip('/')
    if r.method!='GET': route.abort(); return
    if candidate is not None and u.hostname=='24bkm.com' and name in candidate:
     route.fulfill(status=200,content_type='text/html; charset=utf-8',body=candidate[name])
    else: route.continue_()
   context.route('**/*',intercept)
   page=context.new_page(); dimensions=None
   for name in names:
    resp=page.goto(BASE+'/'+name,wait_until='domcontentloaded',timeout=35000); assert resp.status==200
    page.wait_for_timeout(250)
    h=page.locator('#bkm-header'); expect(h).to_be_visible()
    links=h.locator('#site-nav>a').evaluate_all('(a)=>a.map(x=>[x.textContent.trim(),x.getAttribute("href")])')
    assert links==[list(v) for v in shared.LINKS]+[['Рассчитать доставку','index.html#contact']], (name,links)
    assert h.locator('.bkm-header-action').count()==1
    box=h.bounding_box(); logo=h.locator('.bkm-brand img').bounding_box()
    now=[round(box['height']),round(logo['width']),round(logo['x'])]
    if dimensions is None: dimensions=now
    assert now==dimensions, (name,width,'header geometry changed',now,dimensions)
    if width<=1050:
     page.locator('#menu-toggle').click(); expect(h.locator('.bkm-header-action')).to_be_visible()
     page.keyboard.press('Escape'); expect(page.locator('#menu-toggle')).to_have_attribute('aria-expanded','false')
     expect(h.locator('#site-nav')).to_be_hidden()
    else: expect(h.locator('.bkm-header-action')).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'), (name,width,'overflow')
    if name=='news.html' or name.startswith('news-'):
     assert h.locator('[aria-current=page]').get_attribute('href')=='news.html'
    if name in shared.SERVICE_NAMES:
     assert h.locator('[aria-current=page]').get_attribute('href')=='services.html'
    results.append({'page':name,'width':width,'header_geometry':now,'consistent_menu':True})
    if name in ('index.html','services.html','news.html'):
     page.screenshot(path=str(OUT/(label+'-'+name.replace('.html','')+'-'+str(width)+'.png')))
   context.close()
  browser.close()
 (OUT/(label+'.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2))
 print(label.upper()+'_HEADER_BROWSER_PASS: '+str(len(results))+' page/viewport checks; consistent links, geometry, logo, single CTA and mobile menu',flush=True)

def main():
 sitemap=ET.fromstring(read(BASE+'/sitemap.xml'))
 names=[]
 for node in sitemap.findall('.//{*}loc'):
  u=urlsplit(node.text); assert u.scheme=='https' and u.netloc=='24bkm.com' and not u.query
  name='index.html' if u.path=='/' else u.path.lstrip('/')
  assert re.fullmatch(r'[a-z0-9-]+\.html',name) and name!='privacy.html'
  if name not in names: names.append(name)
 assert 8<=len(names)<=40
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  before=dict(zip(names,pool.map(lambda name:read(BASE+'/'+name),names)))
 after={name:shared.unify_header(body.decode('utf-8'),name).encode('utf-8') for name,body in before.items()}
 for name,body in after.items():
  assert shared.unify_header(body.decode('utf-8'),name).encode('utf-8')==body, 'Not idempotent'
  assert main_content(body.decode('utf-8'))==main_content(before[name].decode('utf-8')), 'Main content changed'
 protected=['/assets/site-config.js','/assets/bkm-header.svg','/assets/home.js','/robots.txt','/sitemap.xml']
 stable={p:hashlib.sha256(read(BASE+p)).hexdigest() for p in protected}
 news=before.get('news.html',b'').decode('utf-8')
 print('PUBLIC_NEWS_ARTICLES_BEFORE: '+str(len(re.findall(r'<article\b',news))),flush=True)
 browser_check(names,after,'candidate')
 run=os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
 remote=os.environ['USER']+'@'+os.environ['HOST']
 options=['-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=20']
 def invoke(payload):
  subprocess.run(['ssh',*options,remote,'python3 -c '+shlex.quote(REMOTE)],input=json.dumps(payload),text=True,check=True,timeout=60)
 files={name:{'before':hashlib.sha256(before[name]).hexdigest(),'content':base64.b64encode(body).decode('ascii')} for name,body in after.items()}
 attempted=False
 try:
  attempted=True; invoke({'mode':'apply','run':run,'files':files})
  for name,body in after.items(): assert read(BASE+'/'+name)==body, 'Published bytes mismatch: '+name
  assert read(BASE+'/')==after['index.html']
  for p,sha in stable.items(): assert hashlib.sha256(read(BASE+p)).hexdigest()==sha, 'Protected file changed'
  browser_check(names,None,'live')
  print('SITE_HEADER_LIVE_PASS: '+str(len(names))+' pages. All article text, forms, SEO, original logo, CSS assets and sitemap preserved.',flush=True)
  print('SCOPE: no news publication, no CRM or personal-data activation, no DNS or .htaccess change.',flush=True)
 except BaseException:
  if attempted: invoke({'mode':'rollback','run':run})
  raise

if __name__=='__main__': main()
