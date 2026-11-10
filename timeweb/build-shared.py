#!/usr/bin/env python3
"""Build BKM for Timeweb shared hosting. Only public files enter the ZIP."""
from pathlib import Path
import os
import re
import subprocess
import sys
import shutil

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
env=os.environ.copy()
env["BKM_CRM_RELEASE"]="on"
env["BKM_RUNTIME_TARGET"]="timeweb"
subprocess.run([sys.executable,str(ROOT/"scripts"/"build-production.py")],env=env,check=True)
DEST=ROOT/"_production_release"
endpoint=DEST/"api"/"lead.php"
shutil.copy2(ROOT/"timeweb"/"shared-lead.php",endpoint)
shutil.copy2(ROOT/"timeweb"/"shared-lead-form.js",DEST/"assets"/"lead-form.js")
home=DEST/"index.html"
markup=home.read_text(encoding="utf-8")
markup=re.sub(r'\s*aria-describedby="bkm-phone-hint"','',markup)
markup=re.sub(r'<span class="bkm-field-hint" id="bkm-phone-hint">.*?</span>','',markup)
markup=markup.replace('assets/lead-form.js','assets/lead-form.js?v=20261110b')
markup=markup.replace('assets/form-setup.js','assets/form-setup.js?v=20261110b')
home.write_text(markup,encoding="utf-8")
private=DEST/".bkm_private"
private.mkdir(exist_ok=True)
(private/".htaccess").write_text("Require all denied\nDeny from all\n",encoding="utf-8")
shutil.copy2(ROOT/"timeweb"/"shared-form-config.php",DEST/"api"/"form-config.php")
if os.environ.get("BKM_SHARED_PRODUCTION","false").lower()!="true":
    # Do not accidentally index the temporary test domain.
    (DEST/"robots.txt").write_text("User-agent: *\nDisallow: /\n",encoding="utf-8")
    for page in DEST.glob("*.html"):
        value=page.read_text(encoding="utf-8")
        if 'name="robots"' not in value:
            value=re.sub(r'</head>', '<meta name="robots" content="noindex,nofollow"></head>',value,count=1,flags=re.I)
        page.write_text(value,encoding="utf-8")
assert (DEST/"assets"/"form-setup.js").exists()
assert (DEST/"api"/"form-config.php").exists()
assert 'bkm-form-token' in (DEST/"index.html").read_text(encoding="utf-8")
assert "cn705088.tw1.ru" in endpoint.read_text(encoding="utf-8")
assert not (DEST/".bkm_private"/"config.php").exists()
print("TIMEWEB_SHARED_RELEASE_OK: PHP 8.2 files ready; no secrets; technical host allowed")
