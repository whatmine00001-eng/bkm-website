<?php
declare(strict_types=1);
/**
 * Local Timeweb HMAC ticket: no dependency on Cloudflare JS, no client secrets.
 * This endpoint intentionally returns only a short-lived public form ticket.
 */
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, private');
header('X-Content-Type-Options: nosniff');
function fail(int $status = 503): void {
    http_response_code($status);
    echo '{"ready":false}';
    exit;
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') fail(405);
if (getenv('BKM_HOSTING_TARGET') !== 'timeweb') fail();
$host = strtolower(preg_replace('/:\d+$/', '', (string) ($_SERVER['HTTP_HOST'] ?? '')));
$hosts = array_values(array_unique(array_filter(array_map('trim',
    explode(',', strtolower((string) (getenv('BKM_ALLOWED_HOSTS') ?: '24bkm.com,www.24bkm.com')))
))));
if (!in_array($host, $hosts, true)) fail();
$salt = (string) (getenv('BKM_RATE_SALT') ?: '');
$webhook = (string) (getenv('BKM_BITRIX_WEBHOOK_URL') ?: '');
$u = parse_url($webhook);
if (getenv('BKM_CRM_ENABLED') !== 'true' ||
    strlen($salt) < 24 || stripos($salt, 'REPLACE') !== false ||
    !is_array($u) ||
    strtolower((string) ($u['scheme'] ?? '')) !== 'https' ||
    strtolower((string) ($u['host'] ?? '')) !== 'bitrix.24bkm.com' ||
    !preg_match('~^/rest/[0-9]+/[A-Za-z0-9_-]+/?$~',
       (string) ($u['path'] ?? '')) ||
    !empty($u['query']) || !empty($u['fragment'])) fail();
$now = (string) time();
$mac = hash_hmac('sha256', $now . '|' . $host, $salt);
echo json_encode(['ready' => true, 'form_token' => $now . '.' . $mac], JSON_UNESCAPED_UNICODE);
