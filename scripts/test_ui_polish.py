#!/usr/bin/env python3
"""Read public pages, render UI candidate (or live), never submit a form.
Playwright/Chromium required. Writes screenshots and a JSON report locally.
"""
import argparse
import hashlib
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

BASE = 'https://24bkm.com'
ASSETS = ['bkm-ui-polish.css', 'home-brand-final.css', 'interior-redesign.css', 'home.js']
ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
args = parser.parse_args()
OUT = ROOT / 'ui-review' / ('live' if args.live else 'candidate')
OUT.mkdir(parents=True, exist_ok=True)

def read(url):
    req = urllib.request.Request(url, headers={'User-Agent':'BKM-owner-UI-review/1.0', 'Cache-Control':'no-cache'})
    with urllib.request.urlopen(req, timeout=20) as r:
        if urlsplit(r.url).hostname not in ('24bkm.com','www.24bkm.com'):
            raise RuntimeError('Unexpected redirect host')
        return r.read(3000000)

sitemap = ET.fromstring(read(BASE + '/sitemap.xml'))
urls = list(dict.fromkeys(n.text for n in sitemap.findall('.//{*}loc')))
if not 8 <= len(urls) <= 40 or any(urlsplit(u).hostname != '24bkm.com' for u in urls):
    raise SystemExit('Unexpected sitemap scope')
if BASE + '/' not in urls:
    raise SystemExit('Homepage missing from sitemap')
pages = {urlsplit(u).path or '/': read(u) for u in urls}
patches = {'/assets/'+name:(ROOT/'assets'/name).read_bytes() for name in ASSETS}
rows = []
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width':1440,'height':1000}, reduced_motion='reduce', device_scale_factor=1)
    page = context.new_page()
    page.set_default_timeout(10000)
    def route(r):
        req = r.request
        parts = urlsplit(req.url)
        if req.method not in ('GET','HEAD'):
            r.abort(); return
        if parts.hostname in ('24bkm.com','www.24bkm.com'):
            if not args.live and parts.path in patches:
                typ = 'text/javascript' if parts.path.endswith('.js') else 'text/css'
                r.fulfill(status=200,content_type=typ,body=patches[parts.path]); return
            if not args.live and parts.path in pages:
                r.fulfill(status=200,content_type='text/html; charset=utf-8',body=pages[parts.path]); return
        r.continue_()
    page.route('**/*',route)
    for url in urls:
        widths = [320,390,768,1024,1280,1440,1920] if url == BASE+'/' else [390,1024,1440]
        for width in widths:
            page.set_viewport_size({'width':width,'height':1000 if width>=1000 else 844})
            response = page.goto(url,wait_until='domcontentloaded',timeout=30000)
            if response is None or response.status != 200:
                errors.append(f'{url} {width}: HTTP status'); continue
            page.evaluate("() => Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,5000))])")
            page.wait_for_timeout(120)
            report = page.evaluate('''() => {
              const w=innerWidth;
              const visible=e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0;};
              const selectors='h1,h2,h3,.hero__lead,.service-card p,.step p,.story p,.contact__methods a';
              const clipped=[];
              for(const e of document.querySelectorAll(selectors)){
                if(!visible(e))continue;
                const range=document.createRange();range.selectNodeContents(e);
                const r=range.getBoundingClientRect();
                if(r.left < -2 || r.right>w+2)clipped.push({tag:e.tagName,text:e.textContent.trim().slice(0,90),left:Math.round(r.left),right:Math.round(r.right)});
              }
              return {width:w,scrollWidth:document.documentElement.scrollWidth,clipped,
                bodyFont:getComputedStyle(document.body).fontFamily,
                bodySize:getComputedStyle(document.body).fontSize,
                headingFont:document.querySelector('h1')?getComputedStyle(document.querySelector('h1')).fontFamily:null,
                headerCTAs:[...document.querySelectorAll('.site-header a.btn')].filter(visible).length,
                activeForms:document.querySelectorAll('form#bkm-lead-form').length,
                fontExo:document.fonts.check('800 32px "Exo 2"'),fontManrope:document.fonts.check('400 16px Manrope')};
            }''')
            report.update(url=url)
            rows.append(report)
            if report['scrollWidth']>width+2 or report['clipped']:
                errors.append(f'{url} {width}: overflow '+json.dumps(report['clipped'],ensure_ascii=False))
            if 'Manrope' not in report['bodyFont'] or report['headingFont'] and 'Exo 2' not in report['headingFont']:
                errors.append(f'{url} {width}: inconsistent font stack')
            if url==BASE+'/':
                if report['activeForms']:
                    errors.append('Public CRM form unexpectedly enabled')
                if width>1050:
                    if report['headerCTAs']!=1: errors.append(f'{width}: expected exactly one desktop CTA')
                else:
                    if report['headerCTAs']!=0: errors.append(f'{width}: CTA visible while menu closed')
                    page.locator('#menu-toggle').click()
                    if page.locator('#menu-toggle').get_attribute('aria-expanded')!='true':
                        errors.append(f'{width}: menu did not open')
                    if page.locator('#site-nav .btn:visible').count()!=1:
                        errors.append(f'{width}: menu CTA missing/duplicated')
                    page.keyboard.press('Escape')
                    if page.locator('#menu-toggle').get_attribute('aria-expanded')!='false':
                        errors.append(f'{width}: Escape did not close menu')
                    page.locator('#menu-toggle').click()
                    page.locator('#site-nav a[href="#contact"]:not(.btn)').click()
                    if page.locator('#menu-toggle').get_attribute('aria-expanded')!='false':
                        errors.append(f'{width}: anchor click left menu open')
                    page.evaluate('scrollTo(0,0)')
            if width in (390,1440) and url in [BASE+'/',BASE+'/services.html',BASE+'/news.html',BASE+'/customs-clearance.html']:
                name=(urlsplit(url).path.strip('/') or 'home').replace('.html','')
                page.screenshot(path=str(OUT/f'{name}-{width}.png'),full_page=True,timeout=20000)
            print('UI_CHECK',width,url,'overflow='+str(len(report['clipped'])),flush=True)
    browser.close()
(OUT/'report.json').write_text(json.dumps({'mode':'live' if args.live else 'candidate','pages':len(urls),'checks':len(rows),'results':rows,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'UI_BROWSER_PASS: {len(urls)} public pages, {len(rows)} viewport checks, single CTA, menu behavior, typography and no clipped headings. No forms submitted.')
