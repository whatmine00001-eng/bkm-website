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
if os.environ.get("BKM_SHARED_PRODUCTION","true").lower()!="true":
    # Do not accidentally index the temporary test domain.
    (DEST/"robots.txt").write_text("User-agent: *\nDisallow: /\n",encoding="utf-8")
    for page in DEST.glob("*.html"):
        value=page.read_text(encoding="utf-8")
        if 'name="robots"' not in value:
            value=re.sub(r'</head>', '<meta name="robots" content="noindex,nofollow"></head>',value,count=1,flags=re.I)
        page.write_text(value,encoding="utf-8")
else:
    (DEST/"robots.txt").write_text("User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /.bkm_private/\nSitemap: https://24bkm.com/sitemap.xml\n",encoding="utf-8")
    for page in DEST.glob("*.html"):
        value=page.read_text(encoding="utf-8").replace('<meta name="robots" content="noindex,nofollow">','')
        page.write_text(value,encoding="utf-8")
privacy=DEST/"privacy.html"
privacy.write_text(re.sub(r'<p>Для размещения сайта применяется .*?</p>', '<p>Для размещения сайта применяется хостинг Timeweb: АО «ТаймВэб», ИНН 7810353960, ОГРН 1247800127112; 196006, г. Санкт-Петербург, ул. Заставская, д. 22, корп. 2, лит. А. В части обработки по поручению Оператора допускаются техническое размещение и хранение передаваемых через сайт данных, обеспечение доступности и безопасности инфраструктуры. Обработка должна быть оформлена договором или поручением с требованиями части 3 статьи 6 Закона № 152-ФЗ.</p>', privacy.read_text(encoding="utf-8")),encoding="utf-8")
assert (DEST/"assets"/"form-setup.js").exists()
assert (DEST/"api"/"form-config.php").exists()
assert 'bkm-form-token' in (DEST/"index.html").read_text(encoding="utf-8")
assert "cn705088.tw1.ru" in endpoint.read_text(encoding="utf-8")
assert not (DEST/".bkm_private"/"config.php").exists()
print("TIMEWEB_SHARED_RELEASE_OK: PHP 8.2 files ready; no secrets; technical host allowed")

