#!/usr/bin/env python3
"""Create a separate SEO review candidate; never modify sources, deployment, CRM or DNS.
Run build-production.py with BKM_CRM_RELEASE=off first. The final deploy remains separate.
"""
from pathlib import Path
from html import escape, unescape
from html.parser import HTMLParser
import json
import re
import shutil
import xml.etree.ElementTree as ET

BASE = 'https://24bkm.com/'
SOURCE = Path('_production_release')
DEST = Path('_seo_candidate')
TITLES = {
    'index.html': 'БКМ (BKM) — импортные поставки, логистика и таможенное оформление',
    'services.html': 'Услуги БКМ (BKM) — международная логистика и таможня',
    'international-freight.html': 'Международные грузоперевозки — БКМ (BKM)',
    'customs-clearance.html': 'Таможенное оформление импортных грузов — БКМ (BKM)',
    'freight-forwarding.html': 'Экспедирование грузов — БКМ (BKM)',
    'warehousing-logistics.html': 'Складская логистика и обработка грузов — БКМ (BKM)',
    'consolidated-cargo.html': 'Доставка сборных грузов — БКМ (BKM)',
    'news.html': 'Новости импорта и международной логистики — БКМ (BKM)',
}
HOME_DESCRIPTION = ('БКМ (BKM): международная логистика, таможенное оформление и сопровождение '
                    'импортных поставок в одном окне. 8 800 707-79-02, info@24bkm.com.')
class Head(HTMLParser):
    def __init__(self):
        super().__init__(); self.meta={}; self.title=''; self.read_title=False; self.canonical=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='title': self.read_title=True
        if tag=='meta': self.meta[a.get('name',a.get('property',''))]=a.get('content','')
        if tag=='link' and a.get('rel')=='canonical': self.canonical.append(a.get('href',''))
    def handle_endtag(self,tag):
        if tag=='title': self.read_title=False
    def handle_data(self,data):
        if self.read_title: self.title+=data

def attrs(tag):
    return {k.lower():unescape(v) for k,_,v in re.findall(r'([\w:-]+)\s*=\s*([\"\'])(.*?)\2', tag, re.S)}

def clean_head(s):
    keys={'description','referrer','og:title','og:description','og:site_name','og:url','og:type','og:locale',
          'twitter:card','twitter:title','twitter:description','yandex-verification','google-site-verification'}
    def meta(m):
        a=attrs(m.group()); return '' if a.get('name',a.get('property')) in keys else m.group()
    s=re.sub(r'<meta\b[^>]*>',meta,s,flags=re.I)
    s=re.sub(r'<link\b[^>]*>',lambda m: '' if attrs(m.group()).get('rel')=='canonical' else m.group(),s,flags=re.I)
    return re.sub(r'<script\b[^>]*id=[\"\']bkm-brand-schema[\"\'][^>]*>.*?</script>','',s,flags=re.I|re.S)

def main():
    if not (SOURCE/'index.html').is_file(): raise SystemExit('Build safe production candidate first')
    cfg=(SOURCE/'assets/site-config.js').read_text(encoding='utf-8')
    if not re.search(r'formsEnabled\s*:\s*false\b',cfg) or re.search(r'formsEnabled\s*:\s*true\b',cfg):
        raise SystemExit('SEO preparation requires CRM intake to remain OFF')
    if (SOURCE/'api').exists() or (SOURCE/'privacy.html').exists():
        raise SystemExit('SEO-only candidate must not include CRM endpoint or draft policy')
    if DEST.exists(): shutil.rmtree(DEST)
    shutil.copytree(SOURCE,DEST)
    verification={}
    vp=Path('seo/search-verification.json')
    if vp.exists():
        verification=json.loads(vp.read_text(encoding='utf-8'))
        if not isinstance(verification,dict) or set(verification)-{'google','yandex'}:
            raise SystemExit('Invalid search verification config keys')
        for k,v in verification.items():
            if not isinstance(v,str) or (v and not re.fullmatch(r'[A-Za-z0-9_-]{5,200}',v)):
                raise SystemExit('Invalid verification code; use only owner-supplied token')
    pages=sorted(DEST.glob('*.html'))
    for page in pages:
        text=page.read_text(encoding='utf-8'); p=Head(); p.feed(text)
        if 'noindex' in p.meta.get('robots','').lower(): raise SystemExit('Unexpected noindex in production candidate')
        if re.search(r'<form\b',text,re.I): raise SystemExit('SEO-only candidate must not collect data')
        title=TITLES.get(page.name,p.title)
        description=HOME_DESCRIPTION if page.name=='index.html' else p.meta.get('description','')
        if not title or not description: raise SystemExit('Missing page title or description: '+page.name)
        head_end=re.search(r'</head\s*>',text,re.I)
        if not head_end: raise SystemExit('Invalid HTML head: '+page.name)
        head=clean_head(text[:head_end.start()]); tail=text[head_end.start():]
        head,n=re.subn(r'<title\b[^>]*>.*?</title>','<title>'+escape(title)+'</title>',head,count=1,flags=re.I|re.S)
        if n!=1: raise SystemExit('Expected one title: '+page.name)
        canonical=BASE if page.name=='index.html' else BASE+page.name
        tags=[f'<meta name="description" content="{escape(description,quote=True)}">',
              '<meta name="referrer" content="strict-origin-when-cross-origin">',
              f'<link rel="canonical" href="{canonical}">']
        for prop,value in {'og:site_name':'БКМ','og:title':title,'og:description':description,
                           'og:url':canonical,'og:type':'article' if page.name.startswith('news-') else 'website',
                           'og:locale':'ru_RU'}.items():
            tags.append(f'<meta property="{prop}" content="{escape(value,quote=True)}">')
        tags.append('<meta name="twitter:card" content="summary">')
        if page.name=='index.html':
            for key,tagname in [('google','google-site-verification'),('yandex','yandex-verification')]:
                if verification.get(key): tags.append(f'<meta name="{tagname}" content="{verification[key]}">')
                elif p.meta.get(tagname): tags.append(f'<meta name="{tagname}" content="{escape(p.meta[tagname],quote=True)}">')
            schema={'@context':'https://schema.org','@graph':[
                {'@type':'Organization','@id':BASE+'#organization','name':'БКМ',
                 'alternateName':['BKM','24BKM'],'url':BASE,'logo':BASE+'assets/bkm-header.svg',
                 'telephone':'+78007077902','email':'info@24bkm.com'},
                {'@type':'WebSite','@id':BASE+'#website','name':'БКМ','alternateName':['BKM','24BKM','24bkm.com'],
                 'url':BASE,'inLanguage':'ru-RU','publisher':{'@id':BASE+'#organization'}}]}
            tags.append('<script type="application/ld+json" id="bkm-brand-schema">'+
                        json.dumps(schema,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+'</script>')
        page.write_text(head+'\n'+'\n'.join(tags)+'\n'+tail,encoding='utf-8')
    root=ET.parse(DEST/'sitemap.xml').getroot()
    for n in root.findall('.//{*}loc'):
        if not n.text or not n.text.startswith(BASE): raise SystemExit('Unexpected sitemap host')
        rel=n.text[len(BASE):] or 'index.html'
        if not (DEST/rel).is_file(): raise SystemExit('Sitemap points to missing file')
    assert (DEST/'assets/site-config.js').read_text(encoding='utf-8')==cfg
    assert not (DEST/'api').exists()
    for page in pages:
        p=Head(); p.feed(page.read_text(encoding='utf-8'))
        assert len(p.canonical)==1, page
        assert p.meta.get('og:site_name')=='БКМ', page
    print(f'SEO_CANDIDATE_PASS: {len(pages)} pages; БКМ/BKM metadata, one canonical per page; CRM OFF; no deployment.')

if __name__=='__main__': main()
