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
s=endpoint.read_text(encoding="utf-8")
old="$timewebMode = (getenv('BKM_HOSTING_TARGET') === 'timeweb');"
assert s.count(old)==1
s=s.replace(old, "$timewebMode = true; // Timeweb shared hosting, fixed server-side",1)
hosts="getenv('BKM_ALLOWED_HOSTS') ?: '24bkm.com,www.24bkm.com'"
assert s.count(hosts)==1
s=s.replace(hosts,"'24bkm.com,www.24bkm.com,cn705088.tw1.ru'",1)
start=s.index('if ($timewebMode) {\n    // App Platform runs ephemeral containers.')
end=s.index('if (!is_array($config)',start)
s=s[:start]+"""$configFile = dirname(__DIR__, 2) . '/.bkm_private/config.php';
if (!is_file($configFile) || !is_readable($configFile)) {
    reply(503, 'not_configured');
}
$config = require $configFile;
"""+s[end:]
rate="""$rateDirectory = $timewebMode
    ? sys_get_temp_dir() . '/bkm_rate'
    : dirname($configFile) . '/rate';"""
assert s.count(rate)==1
s=s.replace(rate,"$rateDirectory = dirname($configFile) . '/rate';",1)
endpoint.write_text(s,encoding="utf-8")
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
assert not (DEST/".bkm_private").exists()
print("TIMEWEB_SHARED_RELEASE_OK: PHP 8.2 files ready; no secrets; technical host allowed")
