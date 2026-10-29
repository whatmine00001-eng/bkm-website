#!/usr/bin/env python3
"""Add BKM procurement support to two existing HTML pages, not forms or CRM."""
from pathlib import Path
import argparse
import re

VERSION = '20261029-financial-support'
TITLE = 'Финансовое сопровождение'
DESCRIPTION = ('Услуги БКМ (BKM): международная логистика, таможенное оформление, '
               'финансовое сопровождение, поиск поставщика и выкуп товара по агентскому договору.')
CARD = '''<article class="card" id="financial-support-card" data-bkm-service="financial-support">
<h2>Финансовое сопровождение</h2>
<p>Помощь в поиске поставщика, выкупе товара и организации импортной закупки через БКМ. Прямые поставки и закупки с участием третьих стран с проверкой применимых ограничений. Работа по агентским договорам.</p>
<p class="muted"><b>Для расчёта сообщите:</b> Наименование и количество товара, страну закупки, данные поставщика (если известен) и желаемые сроки.</p>
<a class="cta" href="#financial-support">Подробнее об услуге ↗</a>
</article>'''
DETAIL = '''<section class="wrap bkm-financial-detail" id="financial-support" aria-labelledby="financial-support-title">
<div class="bkm-financial-heading"><p class="bkm-financial-kicker">Закупка и импорт для бизнеса</p>
<h2 id="financial-support-title">Финансовое сопровождение импортных закупок</h2>
<p>Помогаем найти поставщика, согласовать условия закупки, выкупить товар и организовать его поставку. Состав работ и ответственность сторон закрепляем в договоре.</p></div>
<div class="bkm-financial-grid">
<article><h3>Поиск поставщика</h3><p>Подбираем поставщиков под вашу задачу, запрашиваем коммерческие предложения, уточняем характеристики товара и условия закупки.</p></article>
<article><h3>Выкуп и прямой импорт</h3><p>Организуем закупку непосредственно у производителя или поставщика и импортную поставку через БКМ. Порядок оплаты, состав расходов и документы согласуем до выкупа.</p></article>
<article><h3>Закупки через третьи страны</h3><p>Рассматриваем закупку и поставку с участием третьих стран после проверки товара, контрагентов, конечного использования и применимых санкционных и экспортных ограничений. Работаем только с допустимыми сделками.</p></article>
<article><h3>Агентское сопровождение</h3><p>Работаем по агентским договорам: заранее согласуем поручение, вознаграждение, порядок расчётов, возмещаемые расходы и отчётность по выполненной закупке.</p></article>
</div>
<p class="bkm-financial-note">Возможность поставки, условия оплаты, стоимость и сроки определяются по результатам проверки конкретного товара и сделки. Поставка через третью страну не отменяет применимые ограничения.</p>
<div class="bkm-financial-actions"><a class="cta" href="mailto:info@24bkm.com?subject=%D0%A4%D0%B8%D0%BD%D0%B0%D0%BD%D1%81%D0%BE%D0%B2%D0%BE%D0%B5%20%D1%81%D0%BE%D0%BF%D1%80%D0%BE%D0%B2%D0%BE%D0%B6%D0%B4%D0%B5%D0%BD%D0%B8%D0%B5%20%D0%91%D0%9A%D0%9C">Обсудить закупку ↗</a><a href="tel:+78007077902">8 800 707-79-02</a></div>
</section>'''
HOME_CARD = '''<article class="service-card" id="financial-support-home" data-bkm-service="financial-support"><div class="service-card__media"><span class="service-card__num">06</span><img src="https://images.unsplash.com/photo-1494412519320-aa613dfb7738?auto=format&amp;fit=crop&amp;w=800&amp;q=82" alt="Организация импортной закупки и поставки" loading="lazy" decoding="async"></div><div class="service-card__body"><h3>Финансовое сопровождение</h3><p>Поиск поставщика, выкуп товара и сопровождение импортной закупки. Работа по агентским договорам с проверкой применимых ограничений.</p><a class="service-card__link" href="services.html#financial-support">Подробнее <span class="round-arrow"><svg class="icon" aria-hidden="true"><use href="#i-arrow"></use></svg></span></a></div></article>'''
STYLE = '''<style id="bkm-financial-style">
#financial-support{padding-top:36px;padding-bottom:64px;scroll-margin-top:110px}
#financial-support .bkm-financial-heading{max-width:820px}
#financial-support .bkm-financial-kicker{font-size:12px;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:#9b4400}
#financial-support h2{font-size:clamp(28px,3vw,40px);line-height:1.2;margin:12px 0 20px;overflow-wrap:anywhere}
#financial-support h3{font-size:22px;line-height:1.35;margin:0 0 12px}
#financial-support p{line-height:1.75}
#financial-support .bkm-financial-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px;margin:28px 0}
#financial-support .bkm-financial-grid article{padding:26px;border:1px solid #dce7e1;border-radius:12px;background:#f4f8f6;min-width:0}
#financial-support .bkm-financial-grid article p{margin:0}
#financial-support .bkm-financial-note{font-size:14px;max-width:900px;color:#475f56}
#financial-support .bkm-financial-actions{display:flex;gap:20px;align-items:center;flex-wrap:wrap;margin-top:24px}
#financial-support .bkm-financial-actions a{overflow-wrap:anywhere;font-weight:700}
body #services .service-grid[data-bkm-service-count="6"]{grid-template-columns:repeat(3,minmax(0,1fr))!important}
@media(max-width:720px){#financial-support .bkm-financial-grid{grid-template-columns:1fr}body #services .service-grid[data-bkm-service-count="6"]{grid-template-columns:repeat(2,minmax(0,1fr))!important}}
@media(max-width:480px){body #services .service-grid[data-bkm-service-count="6"]{grid-template-columns:1fr!important}#financial-support .bkm-financial-grid article{padding:22px}#financial-support .bkm-financial-actions .cta{width:100%;text-align:center}}
</style>'''

def service_section(text):
    match = re.search(r'<section\b(?=[^>]*\bid=["\']services["\'])[^>]*>.*?</section>', text, re.I|re.S)
    if not match:
        raise ValueError('Expected services section missing')
    return match

def transform(text, name):
    if name not in ('index.html','services.html'):
        raise ValueError('Only homepage and services catalogue are allowed')
    marker = 'id="financial-support-home"' if name=='index.html' else 'id="financial-support-card"'
    if marker in text:
        validate(text, name)
        return text
    original = text
    forms = re.findall(r'<form\b.*?</form>', text, re.I|re.S)
    headers = re.findall(r'<header\b.*?</header>', text, re.I|re.S)
    scripts = re.findall(r'<script\b.*?</script>', text, re.I|re.S)
    section = service_section(text)
    body = section.group()
    klass = 'service-card' if name=='index.html' else 'card'
    cards = list(re.finditer(r'<article\b(?=[^>]*class=["\']'+klass+r'["\'])[^>]*>.*?</article>', body, re.I|re.S))
    if len(cards) != 5:
        raise ValueError('Expected exactly five existing service cards')
    pos = cards[-1].end()
    body = body[:pos]+'\n'+(HOME_CARD if name=='index.html' else CARD)+body[pos:]
    if name=='index.html':
        body,n = re.subn(r'class=["\']service-grid["\']', 'class="service-grid" data-bkm-service-count="6"', body, count=1)
        if n != 1: raise ValueError('Expected homepage service grid')
    text = text[:section.start()]+body+text[section.end():]
    if name=='services.html':
        end=service_section(text).end()
        text=text[:end]+'\n'+DETAIL+'\n'+text[end:]
        def meta(m):
            tag=m.group()
            if re.search(r'(?:name|property)=["\'](?:description|og:description|twitter:description)["\']',tag,re.I):
                return re.sub(r'content=(["\']).*?\1',lambda _: 'content="'+DESCRIPTION+'"',tag,flags=re.I|re.S)
            return tag
        text=re.sub(r'<meta\b[^>]*>',meta,text,flags=re.I)
    else:
        text,n=re.subn(r'(<strong\s+class=["\']stat__number["\']>\s*)5(\s*</strong>\s*<span\s+class=["\']stat__label["\']>Направлений услуг)',r'\g<1>6\2',text,count=1)
        if n!=1: raise ValueError('Expected service count 5 on homepage')
    if 'id="bkm-financial-style"' in text: raise ValueError('Unexpected existing financial styles')
    text,n=re.subn(r'</head\s*>',lambda _: '\n'+STYLE+'\n</head>',text,count=1,flags=re.I)
    if n!=1: raise ValueError('HTML head missing')
    if forms!=re.findall(r'<form\b.*?</form>',text,re.I|re.S): raise ValueError('Form changed')
    if headers!=re.findall(r'<header\b.*?</header>',text,re.I|re.S): raise ValueError('Header changed')
    if scripts!=re.findall(r'<script\b.*?</script>',text,re.I|re.S): raise ValueError('Scripts changed')
    if 'обход санкций' in text.lower() and 'обход санкций' not in original.lower(): raise ValueError('Prohibited circumvention promise')
    validate(text,name)
    return text

def validate(text,name):
    section=service_section(text).group()
    klass='service-card' if name=='index.html' else 'card'
    assert len(re.findall(r'<article\b(?=[^>]*class=["\']'+klass+r'["\'])',section))==6
    assert text.count('data-bkm-service="financial-support"')==1
    assert text.count('id="bkm-financial-style"')==1
    if name=='services.html':
        assert text.count('id="financial-support"')==1
        assert all(x in text for x in ['Поиск поставщика','Выкуп и прямой импорт','Закупки через третьи страны','Агентское сопровождение'])
    else:
        assert 'href="services.html#financial-support"' in text
        assert re.search(r'stat__number["\']>6</strong>\s*<span\s+class=["\']stat__label["\']>Направлений услуг',text)

def self_test():
    for name,klass in [('index.html','service-card'),('services.html','card')]:
        cards=''.join('<article class="'+klass+'"><h2>Услуга '+str(i)+'</h2></article>' for i in range(5))
        fixture='<html><head><title>БКМ</title></head><body><header>keep</header><strong class="stat__number">5</strong><span class="stat__label">Направлений услуг</span><section id="services"><div class="service-grid">'+cards+'</div></section><form id="keep">keep</form><script>/*keep*/</script></body></html>'
        patched=transform(fixture,name)
        assert transform(patched,name)==patched
    print('FINANCIAL_SUPPORT_SELF_TEST_PASS: six cards, agency copy, preserved forms/scripts/header, idempotent')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path,nargs='?');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test: self_test()
    elif a.directory:
        for n in ('index.html','services.html'):
            path=a.directory/n;path.write_text(transform(path.read_text(encoding='utf-8'),n),encoding='utf-8')
        print('FINANCIAL_SUPPORT_PAGES_READY: index.html and services.html only')
    else:p.error('Specify directory or --self-test')
