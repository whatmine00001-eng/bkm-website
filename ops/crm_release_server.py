#!/usr/bin/env python3
"""Beget-only transactional deployment of BKM form and policy.

No API tokens or private configuration are printed. No .htaccess, DNS, other
pages, or existing Bitrix24 records are modified by this deployment script.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path('/home/h/help24pw/24bkm.com/public_html')
PRIVATE = Path('/home/h/help24pw/.bkm_private')
RELEASES = Path('/home/h/help24pw/.bkm_releases')
BACKUPS = Path('/home/h/help24pw/.bkm_backups')
FILES = ['index.html', 'privacy.html', 'consent.html', 'assets/site-config.js',
         'assets/lead-form.js', 'api/lead.php']
CONFIG = PRIVATE / 'config.php'

def stop(message):
    raise SystemExit('CRM RELEASE BLOCKED: ' + message)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def config():
    if not CONFIG.is_file() or not CONFIG.is_relative_to(PRIVATE):
        stop('private config not found')
    data = CONFIG.read_text(encoding='utf-8')
    if not re.search(r"['\"]assigned_by_id['\"]\s*=>\s*7\s*,", data):
        stop('assignment must be ID 7 in private config')
    for key in ('enabled', 'privacy_approved'):
        if len(re.findall(r"['\"]"+key+r"['\"]\s*=>\s*(?:true|false)\s*,",data))!=1:
            stop('config switch missing or duplicated: '+key)
    return data

def toggled(s, enabled):
    value = 'true' if enabled else 'false'
    for key in ('enabled','privacy_approved'):
        pattern=r"(['\"]"+key+r"['\"]\s*=>\s*)(?:true|false)(\s*,)"
        s,n=re.subn(pattern,lambda m:m[1]+value+m[2],s,count=1)
        if n!=1: stop('missing private switch '+key)
    return s

def php_lint(path):
    proc=subprocess.run(['/usr/bin/env','php8.2','-l',str(path)],
                        capture_output=True,text=True,timeout=15)
    if proc.returncode!=0: stop('PHP syntax validation failed')

def atomic(path, data, mode=0o644):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name('.bkm-crm-pending-'+path.name)
    with tmp.open('xb') as file:
        file.write(data);file.flush();os.fsync(file.fileno())
    os.chmod(tmp,mode)
    os.replace(tmp,path)

def read_manifest(stage):
    mf=stage/'manifest.json'
    if not mf.is_file(): stop('staging manifest missing')
    m=json.loads(mf.read_text())
    if sorted(m.get('files',{}))!=sorted(FILES): stop('file allowlist mismatch')
    return m

def matches(root, mapping, key):
    for filename,entry in mapping.items():
        p=root/filename
        have=sha(p.read_bytes()) if p.is_file() else None
        if have!=entry[key]: stop('concurrent file change: '+filename)

def main(mode,run):
    if not re.fullmatch(r'\d+-\d+',run): stop('invalid run ID')
    stage=RELEASES/('crm-web-'+run)
    backup=BACKUPS/('crm-web-'+run)
    if mode=='prepare':
        m=read_manifest(stage)
        data=config()
        if toggled(data,False)!=data: stop('enabled flags are already on; refusing simultaneous activation')
        matches(ROOT,m['files'],'before')
        for f,info in m['files'].items():
            source=stage/f
            if not source.is_file() or sha(source.read_bytes())!=info['after']:
                stop('staged file checksum mismatch: '+f)
        php_lint(stage/'api/lead.php')
        backup.mkdir(mode=0o700,parents=True,exist_ok=False)
        os.chmod(backup,0o700)
        for f in FILES:
            p=ROOT/f
            if p.is_file():
                dest=backup/f;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(p,dest)
                os.chmod(dest,0o600)
        shutil.copy2(CONFIG,backup/'config.php')
        os.chmod(backup/'config.php',0o600)
        (backup/'manifest.json').write_text(json.dumps(m))
        os.chmod(backup/'manifest.json',0o600)
        for f,info in m['files'].items():
            p=ROOT/f
            have=sha(p.read_bytes()) if p.is_file() else None
            if have!=info['before']:stop('concurrent edit during copy: '+f)
            atomic(p,(stage/f).read_bytes())
        print('CRM_FILES_STAGED: six allowlisted files and private backup, intake still OFF')
    elif mode=='activate':
        m=json.loads((backup/'manifest.json').read_text())
        matches(ROOT,m['files'],'after')
        orig=config()
        if toggled(orig,False)!=orig: stop('flags changed externally')
        new=toggled(orig,True)
        staging=stage/'config-validation.php'
        staging.write_text(new)
        os.chmod(staging,0o600)
        try:php_lint(staging)
        finally:staging.unlink(missing_ok=True)
        atomic(CONFIG,new.encode('utf-8'),0o600)
        print('CRM_SERVER_FLAGS_ON: HTTPS form receiving enabled with owner-assigned lead ID 7')
    elif mode=='rollback':
        if not (backup/'manifest.json').is_file():
            print('NO_RELEASE_TO_ROLLBACK');return
        m=json.loads((backup/'manifest.json').read_text())
        # Do not overwrite work made concurrently after release.
        for f,info in m['files'].items():
            p=ROOT/f
            current=sha(p.read_bytes()) if p.is_file() else None
            if current not in (info['before'],info['after']):
                stop('manual review needed before restoring concurrently changed file: '+f)
        for f,info in m['files'].items():
            p=ROOT/f; copy=backup/f
            if copy.exists(): atomic(p,copy.read_bytes())
            elif p.exists():p.unlink()
        atomic(CONFIG,(backup/'config.php').read_bytes(),0o600)
        print('CRM_ROLLBACK_COMPLETE: previous homepage, config and API restored')
    else:
        stop('unknown mode')

if __name__=='__main__':
    if len(sys.argv)!=3:stop('usage: <mode> <run-id>')
    main(sys.argv[1],sys.argv[2])
