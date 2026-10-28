#!/usr/bin/env python3
"""Remove only the owner-selected paragraph above news search; no CRM changes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path('/home/h/help24pw/24bkm.com/public_html')
BACKUPS = Path('/home/h/help24pw/.bkm_backups')
NOTICE = ('Материалы сверены с указанными первоисточниками; '
          'дата изменения правил может отличаться от даты редакционного обновления.')
BLOCK = re.compile(r'(<div class="filters">\s*<h2\b[^>]*>Актуальные материалы</h2>)(?P<note>.*?)(?=<div class="search-row">)', re.S)

def clean(raw):
    text = raw.decode('utf-8')
    matches = list(BLOCK.finditer(text))
    if len(matches) != 1:
        raise ValueError('Expected one news filter heading')
    match = matches[0]
    note = match['note']
    if not note.strip():
        return raw
    if not re.fullmatch(r'\s*<p class="muted" style="color:#64766b">[0-9]+ материалов · Проверено [^<]+</p>\s*', note) or NOTICE not in note:
        raise ValueError('Unexpected paragraph; stop rather than remove other content')
    updated = text[:match.start('note')] + text[match.end('note'):]
    return updated.encode('utf-8')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def atomic(path, data, mode, run):
    temporary = path.parent / ('.bkm-news-note-' + run + '.tmp')
    try:
        with temporary.open('xb') as handle:
            os.chmod(temporary, mode)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['self-test', 'apply', 'rollback'])
    parser.add_argument('--run', default='')
    parser.add_argument('--before', default='')
    args = parser.parse_args()
    if args.mode == 'self-test':
        prefix = '<div class="filters"><h2 style="font-size:29px">Актуальные материалы</h2>'
        suffix = '<div class="search-row">KEEP SEARCH</div><article><time>KEEP DATE</time>KEEP ARTICLE</article>'
        for count in (6, 8):
            note = '<p class="muted" style="color:#64766b">'+str(count)+' материалов · Проверено 22 октября 2026. '+NOTICE+'</p>'
            original = (prefix+note+suffix).encode()
            expected = (prefix+suffix).encode()
            assert clean(original) == expected
            assert clean(expected) == expected
        try:
            clean((prefix+'<p>KEEP OTHER TEXT</p>'+suffix).encode())
        except ValueError:
            pass
        else:
            raise AssertionError('Unexpected content must be rejected')
        print('PASS: one selected paragraph removed; other text preserved; idempotent')
        return
    if not re.fullmatch(r'[0-9]+-[0-9]+', args.run):
        raise ValueError('Invalid run identifier')
    target = ROOT / 'news.html'
    if not target.is_file() or target.is_symlink():
        raise ValueError('Expected regular news.html file')
    backup = BACKUPS / ('news-note-' + args.run)
    before = target.read_bytes()
    if args.mode == 'apply':
        if not re.fullmatch(r'[0-9a-f]{64}', args.before) or digest(before) != args.before:
            raise ValueError('Live file changed; refusing to overwrite')
        after = clean(before)
        if after == before:
            print('ALREADY_CLEAN: no file changed')
            return
        backup.mkdir(mode=0o700, parents=False, exist_ok=False)
        os.chmod(backup, 0o700)
        mode = target.stat().st_mode & 0o777
        for name, data in [('news.html', before), ('manifest.json', json.dumps({'before': digest(before), 'after': digest(after), 'mode': mode}).encode())]:
            with (backup/name).open('xb') as handle:
                os.chmod(backup/name, 0o600)
                handle.write(data)
        if digest(target.read_bytes()) != args.before:
            raise ValueError('Concurrent change; no public write performed')
        atomic(target, after, mode, args.run)
        print('APPLIED: news.html only; backup news-note-' + args.run)
    else:
        if not (backup/'manifest.json').is_file():
            print('NO_TRANSACTION: nothing to roll back')
            return
        manifest = json.loads((backup/'manifest.json').read_text())
        if digest(before) not in (manifest['before'], manifest['after']):
            raise ValueError('Concurrent change; manual review required')
        restored = (backup/'news.html').read_bytes()
        if digest(restored) != manifest['before']:
            raise ValueError('Backup checksum mismatch')
        atomic(target, restored, manifest['mode'], args.run)
        print('ROLLED_BACK: original news.html restored')

if __name__ == '__main__':
    main()
