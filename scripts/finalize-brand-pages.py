#!/usr/bin/env python3
"""Finalize static HTML only; preserve form state, secrets, routes and page content.
Safe to run on a private copy of LIVE HTML or on a generated production build.
"""
from pathlib import Path
from html import escape, unescape
import argparse
import json
import re

BASE = 'https://24bkm.com/'
VERSION = 'bkm-20261028-b'
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
DESCRIPTION = ('БКМ (BKM) — работаем с 2011 года. Международная логистика, таможенное оформление '
               'и импортные поставки в одном окне. 8 800 707-79-02, info@24bkm.com.')

def attrs(tag):
    return {k.lower(): unescape(v) for k, _, v in re.findall(r'([\w:-]+)\s*=\s*([\"\'])(.*?)\2', tag, re.S)}

def finalize(text, name):
    original_forms = re.findall(r'<form\b.*?</form>', text, flags=re.S | re.I)
    end = re.search(r'</head\s*>', text, re.I)
    if not end:
        raise ValueError('Missing HTML head: ' + name)
    head, tail = text[:end.start()], text[end.start():]
    title_match = re.search(r'<title\b[^>]*>(.*?)</title>', head, re.I | re.S)
    title = TITLES.get(name, unescape(title_match[1]) if title_match else 'БКМ (BKM)')
    description = DESCRIPTION
    for m in re.finditer(r'<meta\b[^>]*>', head, re.I):
        a = attrs(m.group())
        if a.get('name', '').lower() == 'description' and name != 'index.html':
            description = a.get('content') or DESCRIPTION
    meta_keys = {'description', 'og:title', 'og:description', 'og:site_name', 'og:url', 'og:type', 'og:locale', 'referrer'}
    head = re.sub(r'<meta\b[^>]*>', lambda m: '' if attrs(m.group()).get('name', attrs(m.group()).get('property', '')).lower() in meta_keys else m.group(), head, flags=re.I)
    head = re.sub(r'<link\b[^>]*>', lambda m: '' if attrs(m.group()).get('rel', '').lower() == 'canonical' or attrs(m.group()).get('href', '').split('?')[0] == 'assets/bkm-ui-polish.css' else m.group(), head, flags=re.I)
    head = re.sub(r'<script\b[^>]*id=[\"\']bkm-brand-schema[\"\'][^>]*>.*?</script>', '', head, flags=re.I | re.S)
    head = re.sub(r'<style\b[^>]*id=[\"\']bkm-header-critical[\"\'][^>]*>.*?</style>', '', head, flags=re.I | re.S)
    if title_match:
        head = re.sub(r'<title\b[^>]*>.*?</title>', '<title>' + escape(title) + '</title>', head, count=1, flags=re.I | re.S)
    else:
        head += '\n<title>' + escape(title) + '</title>'
    canonical = BASE if name == 'index.html' else BASE + name
    tags = [f'<meta name="description" content="{escape(description, quote=True)}">',
            '<meta name="referrer" content="strict-origin-when-cross-origin">',
            f'<link rel="canonical" href="{canonical}">']
    for prop, value in {'og:site_name': 'БКМ', 'og:title': title, 'og:description': description, 'og:url': canonical, 'og:type': 'article' if name.startswith('news-') else 'website', 'og:locale': 'ru_RU'}.items():
        tags.append(f'<meta property="{prop}" content="{escape(value, quote=True)}">')
    tags.append(f'<link rel="stylesheet" href="assets/bkm-ui-polish.css?v={VERSION}">')
    if name == 'index.html':
        # Keep ONE action in the nav, remove the redundant sibling action.
        header = re.search(r'<header\b[^>]*class=[\"\']site-header[\"\'][^>]*>.*?</header>', tail, re.I | re.S)
        if header:
            h = header.group()
            h = re.sub(r'<a\b[^>]*class=[\"\'][^\"\']*\bheader-cta\b[^\"\']*[\"\'][^>]*>.*?</a>', '', h, flags=re.I | re.S)
            h = re.sub(r'<a\b([^>]*class=[\"\']btn[\"\'][^>]*)>', lambda m: '<a' + m[1].replace('class="btn"', 'class="btn bkm-header-action"').replace("class='btn'", 'class="btn bkm-header-action"') + ' style="display:inline-flex!important">', h, flags=re.I)
            tail = tail[:header.start()] + h + tail[header.end():]
        # Year of business operation selected by the owner; not a fabricated incorporation date.
        tail = tail.replace('2011*', '2011')
        tail = re.sub(r'<p>\s*\*Год начала работы требует подтверждения\.\s*</p>', '<p>Работаем с 2011 года</p>', tail)
        tags.append('<style id="bkm-header-critical">.site-header .nav>.bkm-header-action{display:inline-flex!important}.site-header .header-cta{display:none!important}</style>')
        graph = {'@context': 'https://schema.org', '@graph': [
            {'@type': 'Organization', '@id': BASE+'#organization', 'name': 'БКМ', 'alternateName': ['BKM', '24BKM', 'BKM Customs & Service'], 'url': BASE, 'logo': BASE+'assets/bkm-header.svg', 'telephone': '+78007077902', 'email': 'info@24bkm.com'},
            {'@type': 'WebSite', '@id': BASE+'#website', 'name': 'БКМ', 'alternateName': ['BKM', '24BKM', '24bkm.com'], 'url': BASE, 'inLanguage': 'ru-RU', 'publisher': {'@id': BASE+'#organization'}}]}
        tags.append('<script type="application/ld+json" id="bkm-brand-schema">'+json.dumps(graph, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')+'</script>')
    tail = tail.replace('© BKM Customs & Service. Предварительная версия сайта.', '© БКМ (BKM). Работаем с 2011 года.')
    result = head + '\n' + '\n'.join(tags) + '\n' + tail
    # Fresh URLs also bypass old parent CSS / JS caches. Never touch API or secrets.
    assets = 'home-redesign.css|home-brand-final.css|interior-redesign.css|news.css|home.js'
    result = re.sub(r'((?:href|src)=[\"\']assets/(?:' + assets + r'))(?:\?[^\"\']*)?([\"\'])', lambda m: m[1]+'?v='+VERSION+m[2], result)
    if original_forms != re.findall(r'<form\b.*?</form>', result, flags=re.S | re.I):
        raise ValueError('Form unexpectedly changed')
    if len(re.findall(r'<link\b[^>]*rel=[\"\']canonical[\"\']', result, re.I)) != 1:
        raise ValueError('Canonical count is not one')
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        sample = '<html><head><title>Old</title></head><body><header class="site-header"><nav class="nav"><a class="btn" href="#contact">Рассчитать доставку</a></nav><a class="btn header-cta" href="#contact">Рассчитать доставку</a></header><b>2011*</b><p>*Год начала работы требует подтверждения.</p></body></html>'
        result = finalize(sample, 'index.html')
        assert result.count('Рассчитать доставку') == 1
        assert '2011*' not in result and 'требует подтверждения' not in result
        assert finalize(result, 'index.html') == result, 'Transformation must be idempotent'
        print('FINALIZER_SELF_TEST_PASS')
        return
    pages = sorted(args.directory.glob('*.html'))
    if not pages:
        raise SystemExit('No HTML pages')
    for page in pages:
        if page.name == 'privacy.html':
            continue
        page.write_text(finalize(page.read_text(encoding='utf-8'), page.name), encoding='utf-8')
    print(f'BRAND_HTML_READY: {len(pages)} pages; one header action; owner year 2011; fresh assets; SEO; forms unchanged')

if __name__ == '__main__':
    main()
