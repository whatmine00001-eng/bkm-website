#!/usr/bin/env python3
"""Prepare one scoped BKM CRM activation bundle, preserving the LIVE site layout.

Input: snapshots of six public live files (missing files may be absent),
and a CRM=on production candidate. No network, private config or deployment.
Output: six allowlisted files and a SHA-256 manifest for crm_release_server.py.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys

FILES = ('index.html', 'privacy.html', 'consent.html', 'assets/site-config.js',
         'assets/lead-form.js', 'api/lead.php')
SECTION = re.compile(r'<section\b[^>]*\bclass="contact"[^>]*\bid="contact"[^>]*>.*?</section>', re.I | re.S)
PREVIEW_STYLE = re.compile(r'\s*<style\s+id="bkm-form-preview-style"[^>]*>.*?</style>', re.I | re.S)
PREVIEW_SCRIPT = re.compile(r'\s*<script\s+id="bkm-form-preview-script"[^>]*>.*?</script>', re.I | re.S)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def prepare(live, candidate, dest):
    current = (live / 'index.html').read_text(encoding='utf-8')
    proposal = (candidate / 'index.html').read_text(encoding='utf-8')
    if 'data-bkm-form-preview="20261030"' not in current:
        raise ValueError('Live homepage is not the expected test-only form: refusing overwrite')
    if re.search(r'<form\b', current, re.I):
        raise ValueError('Existing live form detected: refusing an unreviewed replacement')
    original_section = SECTION.findall(current)
    replacement_section = SECTION.findall(proposal)
    if len(original_section) != 1 or len(replacement_section) != 1:
        raise ValueError('Expected one contact section in both live and proposed pages')
    if proposal.count('id="bkm-lead-form"') != 1 or '<form class="form"' not in replacement_section[0]:
        raise ValueError('Approved candidate does not contain the real lead form')
    if 'href="consent.html"' not in replacement_section[0] or 'href="privacy.html"' not in replacement_section[0]:
        raise ValueError('Approved candidate is missing legal links')
    result = current.replace(original_section[0], replacement_section[0], 1)
    result, a = PREVIEW_STYLE.subn('', result)
    result, b = PREVIEW_SCRIPT.subn('', result)
    if a != 1 or b != 1:
        raise ValueError('Unexpected preview CSS or script layout; refusing overwrite')
    if result.count('id="bkm-lead-form"') != 1 or 'data-bkm-form-preview' in result:
        raise ValueError('Incorrect HTML form replacement')
    for tag in ('header', 'footer'):
        rx = re.compile(r'<'+tag+r'\b.*?</'+tag+r'>', re.I | re.S)
        if rx.findall(current) != rx.findall(result):
            raise ValueError(tag + ' unexpectedly changed')
    for asset in ('assets/site-config.js', 'assets/lead-form.js', 'api/lead.php',
                  'privacy.html', 'consent.html'):
        if not (candidate / asset).is_file():
            raise ValueError('Required release file missing: ' + asset)
    flags = (candidate / 'assets/site-config.js').read_text(encoding='utf-8')
    if 'formsEnabled: true' not in flags or 'analyticsEnabled: false' not in flags:
        raise ValueError('CRM form or unrelated analytics flags incorrect')
    policy = (candidate / 'privacy.html').read_text(encoding='utf-8')
    consent = (candidate / 'consent.html').read_text(encoding='utf-8')
    if '<meta name="bkm-policy-status" content="approved">' not in policy:
        raise ValueError('Approved policy marker missing')
    if '<meta name="bkm-consent-version"' not in consent:
        raise ValueError('Approved consent version missing')

    dest.mkdir(parents=True, exist_ok=False)
    mapping = {}
    for filename in FILES:
        old = live / filename
        after = dest / filename
        after.parent.mkdir(parents=True, exist_ok=True)
        if filename == 'index.html':
            after.write_text(result, encoding='utf-8')
        else:
            shutil.copy2(candidate / filename, after)
        mapping[filename] = {'before': sha(old.read_bytes()) if old.is_file() else None,
                             'after': sha(after.read_bytes())}
    (dest / 'manifest.json').write_text(
        json.dumps({'files': mapping, 'purpose': 'BKM CRM activation; live homepage form only'},
                   ensure_ascii=False, indent=2), encoding='utf-8')
    print('CRM_SCOPED_BUNDLE_PASS: six allowed public files; original header/footer and all other pages retained')

if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('Usage: prepare-live-crm.py LIVE_SNAPSHOT PRODUCTION_BUILD STAGING_DEST')
    prepare(*(Path(a) for a in sys.argv[1:]))
