#!/usr/bin/env python3
"""Build BKM Cloudflare Pages in review_only or approved active CRM mode.

The owner approved the supplied policy and consent. The active build includes a
Turnstile-protected form and nonsecret config; private webhook and Turnstile
secrets are runtime-only Cloudflare bindings. The Pages /functions directory
is outside static output and is deployed automatically by Pages Git integration.
"""
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
import os
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"dist"
LEGAL=ROOT/"cloudflare"/"legal"
MODE=os.environ.get("BKM_PAGES_MODE","review_only")
if MODE not in {"review_only","active"}:
    raise SystemExit("Invalid BKM_PAGES_MODE")
if MODE=="active":
    # The owner has expressly approved both documents; require that technical
    # approval marker without changing their substantive wording.
    for filename in ("privacy.html","consent.html"):
        legal=(LEGAL/filename).read_text(encoding="utf-8")
        if ('name="bkm-policy-status" content="approved"' not in legal
            or 'name="bkm-policy-review" content="pending"' in legal):
            raise SystemExit("CRM release blocked: legal review not approved for "+filename)
    if not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',os.environ.get("BKM_TURNSTILE_SITE_KEY","")):
        raise SystemExit("CRM release blocked: Cloudflare Turnstile site key required")
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
paths=[
    p for p in sorted(ROOT.glob("*.html"))
    if p.name not in ("privacy.html","consent.html")
]
if not any(p.name=="index.html" for p in paths):
    raise SystemExit("Homepage missing")

SAFE_CONTACT="""<div class="form" id="bkm-mail-contact">
<h3>Обсудить поставку</h3>
<p>На новой площадке мы пока не принимаем персональные данные через веб-форму. Для расчёта поставки напишите нам или позвоните.</p>
<p><a class="btn" href="mailto:info@24bkm.com?subject=%D0%97%D0%B0%D0%BF%D1%80%D0%BE%D1%81%20%D0%91%D0%9A%D0%9C">Написать в БКМ ↗</a></p>
<p><a href="tel:+78007077902">8 800 707-79-02</a></p>
</div>"""
for path in paths:
    s=path.read_text(encoding="utf-8")
    if "<html" not in s.lower() or "</head>" not in s.lower():
        raise SystemExit("Invalid HTML: "+path.name)
    if path.name=="index.html":
        if MODE=="review_only":
            s,n=re.subn(r'<form\b[^>]*\bid="bkm-lead-form"[^>]*>.*?</form>',
                         lambda _: SAFE_CONTACT,s,count=1,flags=re.S|re.I)
            if n!=1:
                raise SystemExit("Contact form not found exactly once")
            s=re.sub(r'<script\b[^>]*src="assets/lead-form\.js"[^>]*></script>','',s,flags=re.I)
        else:
            s=s.replace('На этапе тестирования автоматическая отправка в CRM выключена. '
                        'Для отправки обращения откроется ваша почтовая программа.',
                        'Отправка заявки по защищённому соединению в БКМ.')
            # Use only a public site key, never expose the Turnstile secret.
            key=os.environ["BKM_TURNSTILE_SITE_KEY"]
            widget=f'<div class="cf-turnstile" data-sitekey="{key}"></div>'
            s=s.replace('<div class="form__actions">',widget+'<div class="form__actions">',1)
            s=s.replace('</body>','<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script></body>',1)
            s=s.replace('Подготовить письмо по заявке','Отправить заявку в БКМ')
        if 'class="bkm-cloudflare-legal"' not in s:
            links=('<nav class="bkm-cloudflare-legal" aria-label="Документы о персональных данных" '
                   'style="display:flex;gap:18px;flex-wrap:wrap;padding:12px 5%;font-size:13px">'
                   '<a href="/privacy.html">Политика обработки персональных данных</a>'
                   '<a href="/consent.html">Согласие на обработку персональных данных</a>'
                   '<a href="/lite.html">Облегчённая версия сайта</a></nav>')
            s=s.replace('</footer>',links+'</footer>',1)
    # No pages.dev version should accidentally enter a search index.
    s=re.sub(r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*["\']\s*/?>',
             '',s,flags=re.I)
    s=s.replace('</head>','<meta name="robots" content="noindex,nofollow"></head>',1)
    (OUT/path.name).write_text(s,encoding="utf-8")
for name in ("privacy.html","consent.html"):
    shutil.copy2(LEGAL/name, OUT/name)

shutil.copytree(ROOT/"assets",OUT/"assets",
    ignore=lambda directory,names:[
        n for n in names if not(
            Path(directory,n).is_dir() or Path(n).suffix.lower() in
            {".css",".svg",".js",".png",".jpg",".jpeg",".webp"}
        )
    ])
config=OUT/"assets"/"site-config.js"
src=config.read_text(encoding="utf-8")
if src.count("formsEnabled: false")!=1 or src.count("analyticsEnabled: false")!=1:
    raise SystemExit("Unsafe public site feature flags")
if MODE=="active":
    src=src.replace("formsEnabled: false","formsEnabled: true",1)
config.write_text(src,encoding="utf-8")
if MODE=="active":
    js=OUT/"assets"/"lead-form.js"
    text=js.read_text(encoding="utf-8")
    if text.count('"/api/lead.php"')!=1:
        raise SystemExit("Expected only one legacy PHP endpoint")
    text=text.replace('"/api/lead.php"','"/api/lead"',1)
    if 'turnstile_token:' not in text:
        text=text.replace('consent: data.get("consent") === "on",',
            'consent: data.get("consent") === "on",\n'
            '      turnstile_token: String(data.get("cf-turnstile-response") || ""),',1)
    js.write_text(text,encoding="utf-8")
(OUT/"_headers").write_text(
    "/*\n  X-Robots-Tag: noindex, nofollow\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n",
    encoding="utf-8")
(OUT/"robots.txt").write_text("User-agent: *\nDisallow: /\n",encoding="utf-8")
(OUT/"sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+
    ''.join('<url><loc>'+xml_escape('https://24bkm.com/' + ("" if p.name=="index.html" else p.name))+'</loc></url>' for p in paths)
    +'</urlset>\n',encoding="utf-8")
assert not (OUT/"api"/"lead.php").exists()
assert not (OUT/"index.php").exists()
homepage=(OUT/"index.html").read_text(encoding="utf-8")
if MODE=="review_only":
    assert 'id="bkm-lead-form"' not in homepage
    assert 'formsEnabled: false' in config.read_text()
else:
    assert 'id="bkm-lead-form"' in homepage
    assert 'formsEnabled: true' in config.read_text()
print(f"BKM_CLOUDFLARE_BUILD_OK: mode={MODE}; HTML pages={len(paths)+2}; no secrets; no PHP")
