#!/usr/bin/env python3
"""Build a non-collecting, noindex design preview for isolated Beget test space.

NEVER copy the live API handler or the unapproved privacy draft to staging.
Leave the design and form layout visible, but make all form fields and the
submit button inert. Does not change the main website or source HTML.
"""
from pathlib import Path
import re
import shutil

ROOT = Path.cwd()
DEST = ROOT / "_preview_release"
PAGES = sorted(p for p in ROOT.glob("*.html")
               if p.name not in {"privacy.html"})
if not (ROOT / "index.html").is_file() or len(PAGES) < 8:
    raise SystemExit("Preview build blocked: source website pages not found")

if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir()

form_pat = re.compile(
    r'<form\s+class=["\']form["\']\s+id=["\']bkm-lead-form["\'][^>]*>([\s\S]*?)</form>',
    re.I
)
for path in PAGES:
    source = path.read_text(encoding="utf-8")
    if not re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']noindex\s*,\s*nofollow["\']',
                     source, flags=re.I):
        raise SystemExit(f"Preview build blocked: noindex missing on {path.name}")
    if path.name == "index.html":
        match = form_pat.search(source)
        if not match:
            raise SystemExit("Preview build blocked: expected designed lead form not found")
        body = match.group(1)
        body = re.sub(r'<(input|select|textarea)\b', r'<\1 disabled', body, flags=re.I)
        body = re.sub(r'<button\b', r'<button disabled', body, flags=re.I)
        body = re.sub(
            r'<a\s+href=["\']privacy\.html["\'][^>]*>([\s\S]*?)</a>',
            r'\1 (документ в подготовке)', body, flags=re.I
        )
        body = body.replace(
            'На этапе тестирования автоматическая отправка в CRM выключена. '
            'Для отправки обращения откроется ваша почтовая программа.',
            'Демонстрационная форма. Приём и отправка заявок выключены.'
        )
        body = body.replace(
            'Согласен на обработку переданных сведений для ответа на обращение.',
            'Обработка персональных данных на тестовом сайте отключена.'
        )
        source = source[:match.start()] + (
            '<div class="form" id="bkm-preview-contact" role="group" '
            'aria-label="Демонстрационная форма без отправки">'
            + body + '</div>'
        ) + source[match.end():]
        source = re.sub(
            r'<script\s+src=["\']assets/lead-form\.js["\'][^>]*></script>',
            '', source, flags=re.I
        )

    if re.search(r'href=["\']privacy\.html["\']', source, flags=re.I):
        raise SystemExit(f"Preview build blocked: draft privacy link on {path.name}")
    (DEST / path.name).write_text(source, encoding="utf-8")

ALLOWED = {".css", ".svg", ".js", ".png", ".webp", ".jpg", ".jpeg"}
def ignore(directory: str, names: list[str]) -> list[str]:
    excluded = []
    for name in names:
        p = Path(directory) / name
        if name == "lead-form.js":
            excluded.append(name)
        elif not p.is_dir() and p.suffix.lower() not in ALLOWED:
            excluded.append(name)
    return excluded

shutil.copytree(ROOT / "assets", DEST / "assets", ignore=ignore)
(DEST / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")

config = (DEST / "assets" / "site-config.js").read_text(encoding="utf-8")
if "formsEnabled: false" not in config or "formsEnabled: true" in config:
    raise SystemExit("Preview build blocked: forms unexpectedly enabled")

broken = []
for path in DEST.glob("*.html"):
    html = path.read_text(encoding="utf-8")
    for value in re.findall(r'(?:href|src)=["\']([^"\']+)["\']', html):
        relative = value.split("#")[0].split("?")[0]
        if not relative or relative.startswith(("#", "//", "/")) or ":" in relative:
            continue
        if not (path.parent / relative).is_file():
            broken.append(f"{path.name}: missing {relative}")
if broken:
    raise SystemExit("Preview build has broken local links:\n" + "\n".join(broken))

if (DEST / "privacy.html").exists() or (DEST / "api").exists() or (
    DEST / "assets" / "lead-form.js"
).exists():
    raise SystemExit("Preview build contains unapproved privacy page, API or active form JS")
if re.search(r'<form\b', (DEST / "index.html").read_text(), flags=re.I):
    raise SystemExit("Preview build unexpectedly still has an HTML form")
print(f"Non-collecting noindex preview validated: {len(PAGES)} HTML pages, no CRM endpoint.")
