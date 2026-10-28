"""One shared static header; no customer-data handling or content publication."""
from html import escape
import re

STYLE = r'''<style id="bkm-shared-header-style">
#bkm-topbar,#bkm-header{box-sizing:border-box;font-family:"Manrope",Arial,sans-serif}
#bkm-topbar *,#bkm-header *{box-sizing:border-box}
#bkm-topbar{position:relative;background:#062925;color:#edf6f2;font-size:12px;line-height:1.5}
#bkm-topbar .bkm-frame,#bkm-header .bkm-frame{width:min(1180px,calc(100% - 56px));max-width:1180px;margin:0 auto;padding:0}
#bkm-topbar .bkm-frame{display:flex;justify-content:space-between;align-items:center;gap:20px;min-height:36px}
#bkm-topbar .bkm-contacts{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
#bkm-topbar a{color:#edf6f2;text-decoration:none;white-space:nowrap;font:600 12px/1.5 "Manrope",Arial,sans-serif;margin:0}
#bkm-header.site-header{position:sticky!important;top:0;z-index:100;background:#fff!important;color:#172e27;border:0;border-bottom:1px solid #e4ece8;box-shadow:0 5px 22px #052c250b;padding:0;backdrop-filter:none}
#bkm-header .bkm-frame{height:84px;min-height:84px;display:flex;align-items:center;justify-content:space-between;gap:24px}
#bkm-header .bkm-brand{display:inline-flex;align-items:center;flex:0 0 220px;margin:0;padding:0;text-decoration:none}
#bkm-header .bkm-brand img{display:block;width:220px;max-width:100%;height:auto;margin:0}
#bkm-header #site-nav{display:flex!important;position:static;flex-direction:row;align-items:center;justify-content:flex-end;flex:1;gap:20px;margin:0;padding:0;background:transparent;border:0;box-shadow:none;max-height:none;overflow:visible}
#bkm-header #site-nav>a{display:inline-flex;align-items:center;justify-content:center;flex:none;white-space:nowrap;margin:0;padding:10px 0;border:0;text-decoration:none;color:#20382e;font:700 13px/1.5 "Manrope",Arial,sans-serif;letter-spacing:0;text-transform:none;transition:color .15s}
#bkm-header #site-nav>a:hover,#bkm-header #site-nav>a[aria-current="page"]{color:#a64800}
#bkm-header #site-nav>a[aria-current="page"]{text-decoration:underline;text-underline-offset:6px;text-decoration-thickness:2px}
#bkm-header #site-nav>.bkm-header-action{display:inline-flex!important;min-height:46px;padding:12px 20px;gap:12px;border:1px solid transparent;border-radius:6px;background:#ff7900;color:#132c22;font:800 14px/1.4 "Manrope",Arial,sans-serif;box-shadow:0 8px 18px #ff790020;transform:none}
#bkm-header #site-nav>.bkm-header-action:hover{background:#ff982f;color:#132c22}
#bkm-header .bkm-arrow{display:block;width:16px;height:16px;stroke:currentColor;stroke-width:1.8;fill:none;flex:none}
#bkm-header #menu-toggle{display:none!important;width:46px;height:46px;flex:none;border:1px solid #dce8e3;border-radius:6px;background:#fff;color:#063f30;padding:10px;align-items:center;justify-content:center;margin:0;box-shadow:none}
#bkm-header #menu-toggle svg{width:24px;height:24px;stroke:currentColor;fill:none;stroke-width:2}
#bkm-header a:focus-visible,#bkm-header button:focus-visible,#bkm-topbar a:focus-visible{outline:3px solid #ff7900;outline-offset:4px}
body.menu-open{overflow:hidden}
@media(max-width:1100px) and (min-width:1051px){#bkm-header #site-nav{gap:12px}#bkm-header .bkm-frame{gap:18px}#bkm-header #site-nav>.bkm-header-action{padding-inline:14px}}
@media(max-width:1050px){
 #bkm-header .bkm-frame{height:76px;min-height:76px;gap:16px}
 #bkm-header #menu-toggle{display:inline-flex!important;margin-left:auto}
 #bkm-header #site-nav{display:none!important;position:absolute;top:100%;left:0;right:0;flex-direction:column;align-items:stretch;gap:0;background:#fff;border-top:1px solid #e4ece8;box-shadow:0 18px 30px #052c2526;padding:16px max(20px,5vw) 24px;margin:0;max-height:calc(100dvh - 115px);overflow-y:auto;overscroll-behavior:contain}
 #bkm-header #site-nav[data-open="true"]{display:flex!important}
 #bkm-header #site-nav>a{justify-content:flex-start;font-size:16px;min-height:46px;white-space:normal;padding:12px 0;border-bottom:1px solid #e4ece8}
 #bkm-header #site-nav>.bkm-header-action{justify-content:center;margin-top:16px;padding:14px 18px;border:0}
}
@media(max-width:720px){
 #bkm-topbar .bkm-frame,#bkm-header .bkm-frame{width:calc(100% - 32px)}
 #bkm-topbar .bkm-description{display:none}
 #bkm-topbar .bkm-frame{justify-content:center;min-height:34px;padding:6px 0}
 #bkm-topbar .bkm-contacts{gap:8px 16px;justify-content:center}
 #bkm-topbar a{font-size:11px}
 #bkm-header .bkm-brand{flex-basis:190px;max-width:calc(100% - 70px)}
 #bkm-header .bkm-brand img{width:190px}
}
@media(prefers-reduced-motion:reduce){#bkm-header *{transition:none!important}}
</style>'''

LINKS = [('Услуги','services.html'),('Преимущества','index.html#advantages'),
         ('Как работаем','index.html#process'),('Новости импорта','news.html'),
         ('Контакты','index.html#contact')]
SERVICE_NAMES = {'services.html','international-freight.html','customs-clearance.html',
                 'freight-forwarding.html','warehousing-logistics.html','consolidated-cargo.html'}

def header(name):
    active = 'services.html' if name in SERVICE_NAMES else ('news.html' if name == 'news.html' or name.startswith('news-') else '')
    links = ''.join('<a href="'+href+'"'+(' aria-current="page"' if href == active else '')+'>'+escape(label)+'</a>' for label,href in LINKS)
    return '''<!-- BKM_SHARED_HEADER_BEGIN -->
<div id="bkm-topbar"><div class="bkm-frame"><span class="bkm-description">Международная логистика и таможенное сопровождение</span><div class="bkm-contacts"><a href="tel:+78007077902">8 800 707-79-02</a><a href="mailto:info@24bkm.com">info@24bkm.com</a></div></div></div>
<header class="site-header" id="bkm-header"><div class="bkm-frame">
<a class="bkm-brand" href="index.html" aria-label="БКМ — главная страница"><img src="assets/bkm-header.svg" alt="БКМ — Сложное делаем простым" width="220" height="70"></a>
<button class="menu-toggle" id="menu-toggle" type="button" aria-expanded="false" aria-controls="site-nav" aria-label="Открыть меню"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg></button>
<nav class="nav" id="site-nav" data-open="false" aria-label="Основная навигация">'''+links+'''<a class="btn bkm-header-action" href="index.html#contact">Рассчитать доставку<svg class="bkm-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg></a></nav>
</div></header>
<!-- BKM_SHARED_HEADER_END -->'''

def remove_old_topbar(prefix):
    match = re.search(r'<div\b[^>]*class=["\'](?:top|top-bar)["\'][^>]*>', prefix, re.I)
    if not match: return prefix
    depth = 0
    for token in re.finditer(r'</?div\b[^>]*>', prefix[match.start():], re.I):
        depth += -1 if token.group().startswith('</') else 1
        if depth == 0:
            return prefix[:match.start()] + prefix[match.start()+token.end():]
    raise ValueError('Unbalanced legacy topbar')

def unify_header(text, name):
    """Replace only the site header/topbar and load the existing menu JS once."""
    forms = re.findall(r'<form\b.*?</form>',text,re.I|re.S)
    body = re.search(r'<body\b[^>]*>', text, re.I)
    if not body: raise ValueError('Missing body')
    head, content = text[:body.end()], text[body.end():]
    head = re.sub(r'\s*<style id="bkm-shared-header-style">.*?</style>', '', head, flags=re.S)
    head = re.sub(r'<style\b[^>]*id=["\']bkm-header-critical["\'][^>]*>.*?</style>', '', head, flags=re.I|re.S)
    head = re.sub(r'\s*</head\s*>', lambda _: '\n'+STYLE+'</head>', head, count=1, flags=re.I)
    managed = re.search(r'<!-- BKM_SHARED_HEADER_BEGIN -->.*?<!-- BKM_SHARED_HEADER_END -->',content,re.S)
    if managed:
        content = content[:managed.start()]+header(name)+content[managed.end():]
    else:
        old = re.search(r'<header\b[^>]*>.*?</header>',content,re.I|re.S)
        if not old: raise ValueError('Missing site header: '+name)
        prefix = remove_old_topbar(content[:old.start()])
        content = prefix+header(name)+content[old.end():]
    js = '<script src="assets/home.js?v=bkm-navigation-20261028" defer></script>'
    existing = list(re.finditer(r'<script\b[^>]*src=["\']assets/home\.js(?:\?[^"\']*)?["\'][^>]*>\s*</script>', content, re.I))
    if len(existing)>1: raise ValueError('Unexpected duplicate home.js')
    if existing:
        m=existing[0]; content=content[:m.start()]+js+content[m.end():]
    else:
        content=content.replace('</body>',js+'</body>',1)
    result=head+content
    if re.findall(r'<form\b.*?</form>',result,re.I|re.S)!=forms:
        raise ValueError('Form changed during header-only operation')
    if result.count('id="bkm-header"')!=1 or result.count('id="menu-toggle"')!=1:
        raise ValueError('Duplicate navigation IDs')
    return result

if __name__ == '__main__':
    samples = [
        '<html><head><title>t</title></head><body><header><nav>old</nav></header><main>keep</main></body></html>',
        '<html><head><title>t</title>\n\n</head><body><div class="top"><div class="wrap"><span>old</span></div></div><header class="site-head">old</header><form>keep</form></body></html>',
        '<html><head>\n<!-- BKM_FINAL_BEGIN -->\n<style id="bkm-header-critical">.old{display:none}</style>\n<!-- BKM_FINAL_END -->\n</head><body><svg><defs></defs></svg><div class="top-bar"><div class="container"><div>old</div></div></div><header class="site-header">old</header><main>keep</main><script src="assets/home.js" defer></script></body></html>'
    ]
    for name in ('index.html','services.html','news.html','news-epd-2026.html'):
        for source in samples:
            result=unify_header(source,name)
            assert unify_header(result,name)==result, 'Header must be idempotent'
            assert result.count('Рассчитать доставку')==1
            assert result.count('assets/home.js?')==1
            assert all(label in result for label,_ in LINKS)
    print('SHARED_HEADER_SELF_TEST_PASS: legacy layouts and whitespace, idempotence, single action, form preservation')
