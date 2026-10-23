#!/usr/bin/env python3
"""Guard against stale public contact details in BKM production releases."""
from pathlib import Path

release = Path("_production_release")
pages = sorted(release.glob("*.html"))
if len(pages) < 8:
    raise SystemExit("Contact check: missing production pages")
old_variants = [
    "info@bkmcs.ru", "88007758812", "775-88-12",
    "8 (800) 775", "8 800 775"
]
required = [
    "info@24bkm.com", "mailto:info@24bkm.com",
    "8 800 707-79-02", "tel:+78007077902"
]
for page in pages:
    html = page.read_text(encoding="utf-8")
    if page.name != "privacy.html" and any(old in html for old in old_variants):
        raise SystemExit("Contact check: stale details in " + str(page))
    if page.name != "privacy.html":
        if "mailto:info@24bkm.com" not in html or "tel:+78007077902" not in html:
            raise SystemExit("Contact check: missing clickable contacts in " + str(page))
index = (release / "index.html").read_text(encoding="utf-8")
for value in required:
    if value not in index:
        raise SystemExit("Contact check: homepage missing " + value)
for asset in ["assets/lead-form.js", "assets/site-config.js"]:
    path = release / asset
    if path.exists() and any(old in path.read_text(encoding="utf-8") for old in old_variants):
        raise SystemExit("Contact check: stale JS details in " + asset)
print(f"BKM contact check passed on {len(pages)} pages: 8 800 707-79-02 and info@24bkm.com")
