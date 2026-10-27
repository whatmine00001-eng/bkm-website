#!/usr/bin/env python3
"""Offline PHP ingress smoke tests. Never reach Bitrix24 or read actual leads."""
from pathlib import Path
import base64
import json
import subprocess

ROOT = Path(__file__).resolve().parent.parent
HANDLER = ROOT / "api" / "lead.php"
if not HANDLER.is_file():
    raise SystemExit("Missing PHP lead handler")


def case(label: str, server: dict[str, str], expected: str) -> None:
    encoded = base64.b64encode(json.dumps(server).encode("utf-8")).decode("ascii")
    code = (
        f'$_SERVER=json_decode(base64_decode("{encoded}"),true);'
        f'require "{HANDLER.as_posix()}";'
    )
    result = subprocess.run(["php", "-d", "display_errors=0", "-r", code],
                            text=True, capture_output=True, timeout=15)
    if result.returncode != 0:
        raise SystemExit(f"{label}: PHP failed with exit code {result.returncode}")
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"{label}: PHP output is not a JSON response")
    if response.get("code") != expected or response.get("ok") is not False:
        raise SystemExit(
            f"{label}: expected failure {expected}, got {response.get('code')}"
        )
    print(f"{label}: expected rejection ({expected})")


valid_site = {
    "REQUEST_METHOD": "POST",
    "HTTPS": "on",
    "HTTP_HOST": "24bkm.com",
    "HTTP_ORIGIN": "https://24bkm.com",
    "CONTENT_TYPE": "application/json",
    "CONTENT_LENGTH": "0",
}
case("GET does not create a lead", {"REQUEST_METHOD": "GET"}, "method_not_allowed")
case("Plain HTTP refused", {**valid_site, "HTTPS": "off"}, "https_required")
case("Foreign host refused", {**valid_site, "HTTP_HOST": "evil.invalid"}, "host_rejected")
case("Cross-site origin refused", {**valid_site, "HTTP_ORIGIN": "https://evil.invalid"}, "origin_rejected")
case("Non-JSON payload refused", {**valid_site, "CONTENT_TYPE": "text/plain"}, "json_required")
case("Empty payload refused", valid_site, "invalid_payload_size")
print("Offline BKM lead handler safety checks passed. No CRM or external service contacted.")
