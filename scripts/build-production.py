#!/usr/bin/env python3
"""Prepare static BKM production release, separate from noindex HTTP staging.

- Removes preview-only noindex on approved static pages
- Replaces unconfigured contact form with honest mail/phone contact
- Generates canonical, sitemap and robots for 24bkm.com
- Excludes unapproved privacy draft and inactive PHP endpoint
"""
from pathlib import Path
from urllib.parse import urljoin
from xml.sax.saxutils import escape as xml_escape
import re
import shutil
import os

ROOT = Path.cwd()
DEST = ROOT / "_production_release"
DOMAIN = "https://24bkm.com/"
CRM_RELEASE = os.environ.get("BKM_CRM_RELEASE", "off").strip().lower()
if CRM_RELEASE not in ("off", "on"):
    raise SystemExit("BKM_CRM_RELEASE must be 'off' or 'on'")
# This file must be replaced by the actual policy approved by the company.
APPROVED_POLICY = ROOT / "approved" / "privacy.html"
if CRM_RELEASE == "on":
    if not APPROVED_POLICY.is_file():
        raise SystemExit("CRM release blocked: approved/privacy.html is missing")
    policy_source = APPROVED_POLICY.read_text(encoding="utf-8")
    if not re.search(r'<meta\s+name=["\']bkm-policy-status["\']\s+content=["\']approved["\']', policy_source, re.I):
        raise SystemExit("CRM release blocked: policy approval marker is missing")
    if not re.search(r'<html\b', policy_source, re.I) or not re.search(r'</html\s*>', policy_source, re.I):
        raise SystemExit("CRM release blocked: invalid approved privacy HTML")
    if any(token in policy_source.lower() for token in
           ("[указать", "[вписать", "название организации]", "не утверждённая политика",
            "документ для согласования", "bkm_policy_placeholder")):
        raise SystemExit("CRM release blocked: policy contains placeholders")
SERVICE_FILES = [
    "index.html", "services.html", "customs-clearance.html",
    "international-freight.html", "freight-forwarding.html",
    "warehousing-logistics.html", "consolidated-cargo.html", "news.html"
]
ARTICLES = sorted(p.name for p in ROOT.glob("news-*.html"))
PAGES = SERVICE_FILES + ARTICLES

if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir()

REPLACEMENT_CONTACT = """
<div class="form" id="bkm-mail-contact">
  <h3>Связаться с БКМ</h3>
  <p>Для расчёта перевозки или импортной поставки направьте описание груза, маршрут и контакты на нашу корпоративную почту либо позвоните нам.</p>
  <p><a class="btn" href="mailto:info@24bkm.com?subject=%D0%97%D0%B0%D0%BF%D1%80%D0%BE%D1%81%20%D0%BD%D0%B0%20%D1%80%D0%B0%D1%81%D1%87%D1%91%D1%82%20%D0%91%D0%9A%D0%9C">Запросить расчёт по email ↗</a></p>
  <p><a href="tel:+78007077902">8 800 707-79-02</a></p>
  <p class="note">Автоматическая форма временно отключена до утверждения политики обработки данных и успешного теста Bitrix24.</p>
</div>"""

for name in PAGES:
    path = ROOT / name
    if not path.exists():
        raise SystemExit("Missing content page: " + name)
    html = path.read_text(encoding="utf-8")
    if "<html" not in html.lower() or "</head>" not in html.lower():
        raise SystemExit("Invalid page: " + name)
    html = re.sub(
        r'<meta\s+name=["\']robots["\']\s+content=["\']noindex\s*,\s*nofollow["\']\s*/?>',
        "", html, flags=re.I
    )
    if name == "index.html" and CRM_RELEASE == "off":
        html, count = re.subn(
            r'<form\s+class="form"\s+id="bkm-lead-form"[^>]*>[\s\S]*?</form>',
            lambda _: REPLACEMENT_CONTACT, html, count=1, flags=re.I
        )
        if count != 1:
            raise SystemExit("Expected CRM-ready form on homepage; found " + str(count))
        html = html.replace('<script src="assets/lead-form.js" defer></script>', "")
    elif name == "index.html" and CRM_RELEASE == "on":
        if ('<form class="form" id="bkm-lead-form">' not in html or
                'href="privacy.html"' not in html):
            raise SystemExit("CRM release blocked: expected lead form / privacy link missing")
        html = html.replace(
            'На этапе тестирования автоматическая отправка в CRM выключена. '
            'Для отправки обращения откроется ваша почтовая программа.',
            'Передача заявки защищена HTTPS. Мы используем контакты '
            'только для ответа на обращение.'
        )
    canonical = DOMAIN if name == "index.html" else urljoin(DOMAIN, name)
    html = re.sub(
        r'</head>', '<link rel="canonical" href="' + canonical + '"></head>',
        html, count=1, flags=re.I
    )
    if re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']noindex', html, flags=re.I):
        raise SystemExit("Preview noindex still on " + name)
    (DEST / name).write_text(html, encoding="utf-8")

assets = ROOT / "assets"
if not assets.is_dir():
    raise SystemExit("Missing assets directory")
shutil.copytree(
    assets, DEST / "assets",
    ignore=lambda directory, names: [
        n for n in names if not (Path(directory, n).is_dir() or Path(n).suffix in
            {".css", ".svg", ".js", ".png", ".webp", ".jpg", ".jpeg"})
    ]
)

# The default production build has NO personal-data handler.
# The opt-in CRM build is deliberately impossible without company-approved policy.
if CRM_RELEASE == "on":
    (DEST / "privacy.html").write_text(
        re.sub(r'</head>', '<link rel="canonical" href="https://24bkm.com/privacy.html"></head>',
               policy_source, count=1, flags=re.I), encoding="utf-8"
    )
    (DEST / "api").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "api" / "lead.php", DEST / "api" / "lead.php")
    cfg_path = DEST / "assets" / "site-config.js"
    cfg = cfg_path.read_text(encoding="utf-8")
    if cfg.count("formsEnabled: false") != 1:
        raise SystemExit("CRM release blocked: unsafe public configuration")
    cfg_path.write_text(cfg.replace("formsEnabled: false", "formsEnabled: true", 1),
                        encoding="utf-8")

# Explicitly do not ship the draft privacy.html or any private credentials.
(DEST / "robots.txt").write_text(
    "User-agent: *\nAllow: /\nSitemap: https://24bkm.com/sitemap.xml\n",
    encoding="utf-8"
)
links = "".join("<url><loc>" + xml_escape(DOMAIN if name == "index.html" else DOMAIN + name) +
                "</loc></url>" for name in PAGES)
(DEST / "sitemap.xml").write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
    links + "</urlset>\n", encoding="utf-8"
)

# Validate links and media references.
bad = []
for path in DEST.glob("*.html"):
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r'(?:href|src)=["\']([^"\']+)["\']', text):
        rel = target.split("#")[0].split("?")[0]
        if not rel or rel.startswith(("mailto:", "tel:", "https:", "http:", "#", "/", "//", "javascript:")):
            continue
        if not (DEST / rel).exists():
            bad.append(f"{path.name}: {rel}")
if bad:
    raise SystemExit("Broken local links:\n" + "\n".join(bad))
if CRM_RELEASE == "off":
    if (DEST / "privacy.html").exists() or (DEST / "api").exists():
        raise SystemExit("Unapproved privacy draft or API accidentally included")
    if "formsEnabled: true" in (DEST / "assets" / "site-config.js").read_text(encoding="utf-8"):
        raise SystemExit("CRM unexpectedly enabled in default release")
else:
    if not (DEST / "api" / "lead.php").is_file() or not (DEST / "privacy.html").is_file():
        raise SystemExit("CRM release missing backend or approved privacy policy")
    if "formsEnabled: true" not in (DEST / "assets" / "site-config.js").read_text(encoding="utf-8"):
        raise SystemExit("CRM feature flag remains off")
assert not (DEST / "index.php").exists()
print(f"Production candidate validated: {len(PAGES)} HTML files; CRM={CRM_RELEASE}; sitemap present.")
