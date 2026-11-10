<?php
declare(strict_types=1);
/**
 * Timeweb-only public site key endpoint. NEVER disclose webhook/secret.
 * For ordinary Beget hosting this file is not included in production.
 */
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, private');
header('X-Content-Type-Options: nosniff');
function fail(): void {
    http_response_code(503);
    echo '{"ready":false}';
    exit;
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
    http_response_code(405);
    echo '{"ready":false}';
    exit;
}
if (getenv('BKM_HOSTING_TARGET') !== 'timeweb') fail();
$host = strtolower(preg_replace('/:\d+$/', '', (string) ($_SERVER['HTTP_HOST'] ?? '')));
$allowed = array_values(array_unique(array_filter(array_map('trim',
    explode(',', strtolower((string) (getenv('BKM_ALLOWED_HOSTS') ?: '24bkm.com,www.24bkm.com')))
))));
if (!in_array($host, $allowed, true)) fail();
$key = (string) (getenv('BKM_TURNSTILE_SITE_KEY') ?: '');
$secret = (string) (getenv('BKM_TURNSTILE_SECRET') ?: '');
$webhook = (string) (getenv('BKM_BITRIX_WEBHOOK_URL') ?: '');
$salt = (string) (getenv('BKM_RATE_SALT') ?: '');
$u = parse_url($webhook);
if (getenv('BKM_CRM_ENABLED') !== 'true' ||
    strlen($secret) < 8 ||
    strlen($salt) < 24 ||
    !preg_match('/^[A-Za-z0-9_-]{8,100}$/D', $key) ||
    !is_array($u) ||
    strtolower((string) ($u['scheme'] ?? '')) !== 'https' ||
    strtolower((string) ($u['host'] ?? '')) !== 'bitrix.24bkm.com' ||
    !preg_match('~^/rest/[0-9]+/[A-Za-z0-9_-]+/?$~', (string) ($u['path'] ?? '')) ||
    !empty($u['query']) || !empty($u['fragment'])) fail();
echo json_encode(['ready' => true, 'sitekey' => $key], JSON_UNESCAPED_UNICODE);
