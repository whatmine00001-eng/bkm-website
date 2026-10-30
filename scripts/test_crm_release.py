#!/usr/bin/env python3
"""Offline release checks: default safe mode, rejected incomplete CRM, approved CRM."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

BUILD = Path(__file__).with_name("build-production.py")
PAGES = [
    "index.html", "services.html", "customs-clearance.html",
    "international-freight.html", "freight-forwarding.html",
    "warehousing-logistics.html", "consolidated-cargo.html", "news.html"
]
INDEX = """<!doctype html><html lang="ru"><head><meta name="robots" content="noindex,nofollow"></head>
<body><form class="form" id="bkm-lead-form"><label class="field full bkm-consent"><span><input name="consent" required><a href="privacy.html">Privacy</a></span></label>
<input name="name"></form><footer class="footer"><p>BKM</p></footer><script src="assets/lead-form.js" defer></script></body></html>"""
OTHER = '<!doctype html><html lang="ru"><head><meta name="robots" content="noindex,nofollow"></head><body></body></html>'
APPROVED = ('<!doctype html><html lang="ru"><head>'
            '<meta name="bkm-policy-status" content="approved"></head>'
            '<body><h1>Политика обработки персональных данных</h1>'
            '<p>Демонстрационный оператор для автоматического теста.</p></body></html>')


def setup(root: Path):
    for name in PAGES:
        (root / name).write_text(INDEX if name == "index.html" else OTHER, encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets" / "site-config.js").write_text(
        "window.BKM_SITE_CONFIG = {formsEnabled: false, metrikaId: null};", encoding="utf-8")
    (root / "assets" / "lead-form.js").write_text("/* fixture */", encoding="utf-8")
    (root / "api").mkdir()
    (root / "api" / "lead.php").write_text("<?php // fixture", encoding="utf-8")


def run(root: Path, mode: str):
    env = {**os.environ, "BKM_CRM_RELEASE": mode}
    return subprocess.run([sys.executable, str(BUILD)], cwd=root, env=env,
                          text=True, capture_output=True)


def main():
    with tempfile.TemporaryDirectory(prefix="bkm-crm-test-") as dirname:
        root = Path(dirname)
        setup(root)
        result = run(root, "off")
        assert result.returncode == 0, result.stderr or result.stdout
        dest = root / "_production_release"
        assert (dest / "index.html").exists()
        assert not (dest / "privacy.html").exists()
        assert not (dest / "api").exists()
        assert 'mailto:info@24bkm.com' in (dest / "index.html").read_text()
        assert 'formsEnabled: false' in (dest / "assets" / "site-config.js").read_text()
        assert "noindex,nofollow" not in (dest / "index.html").read_text()

        result = run(root, "on")
        assert result.returncode != 0 and "approved/privacy.html is missing" in (
            result.stderr + result.stdout)

        (root / "approved").mkdir()
        (root / "approved" / "consent.html").write_text(
            '<html><head><meta name="bkm-consent-version" content="test-v1"></head><body>Consent</body></html>', encoding="utf-8")
        (root / "approved" / "privacy.html").write_text(
            APPROVED.replace('content="approved"', 'content="draft"'), encoding="utf-8")
        consent_fixture = '<!doctype html><html><head><meta name="bkm-consent-version" content="test-v1"></head><body>Consent test</body></html>'
        (root / "approved" / "consent.html").write_text(consent_fixture, encoding="utf-8")
        result = run(root, "on")
        assert result.returncode != 0 and "approval marker" in (result.stderr + result.stdout)

        (root / "approved" / "privacy.html").write_text(APPROVED, encoding="utf-8")
        (root / "approved" / "consent.html").unlink()
        result = run(root, "on")
        assert result.returncode != 0 and "approved/consent.html is missing" in (result.stderr+result.stdout)
        (root / "approved" / "consent.html").write_text(consent_fixture, encoding="utf-8")

        result = run(root, "on")
        assert result.returncode == 0, result.stderr or result.stdout
        assert (dest / "api" / "lead.php").is_file()
        assert (dest / "privacy.html").is_file()
        assert (dest / "consent.html").is_file()
        assert (dest / "consent.html").is_file()
        assert 'href="consent.html"' in (dest / "index.html").read_text()
        assert (dest / "index.html").read_text().count('class="bkm-legal-links"') == 1
        assert 'formsEnabled: true' in (dest / "assets" / "site-config.js").read_text()
        assert '<form class="form" id="bkm-lead-form">' in (dest / "index.html").read_text()
        assert 'href="privacy.html"' in (dest / "index.html").read_text()
        assert "noindex,nofollow" not in (dest / "index.html").read_text()
        assert not (dest / "index.php").exists()
    print("BKM CRM release checks passed: off safe / policy missing denied / draft denied / approved prepared")


if __name__ == "__main__":
    main()
