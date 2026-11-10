<?php
declare(strict_types=1);
// Timeweb site isolation: PHP-only private configuration, denied by Apache.
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, private');
header('X-Content-Type-Options: nosniff');
function fail(int $status = 503): void {
    http_response_code($status);
    echo '{"ready":false}';
    exit;
}
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') fail(405);
$host = strtolower(preg_replace('/:\d+$/', '', (string) ($_SERVER['HTTP_HOST'] ?? '')));
if (!in_array($host, ['cn705088.tw1.ru','24bkm.com','www.24bkm.com'], true)) fail();
$configFile = dirname(__DIR__) . '/.bkm_private/config.php';
if (!is_readable($configFile)) fail();
$config = require $configFile;
if (!is_array($config) || ($config['enabled'] ?? false) !== true ||
    ($config['privacy_approved'] ?? false) !== true) fail();
$salt = (string) ($config['rate_salt'] ?? '');
$webhook = (string) ($config['bitrix_webhook_url'] ?? '');
$u = parse_url($webhook);
if (strlen($salt) < 24 || stripos($salt, 'REPLACE') !== false ||
    !is_array($u) ||
    strtolower((string) ($u['scheme'] ?? '')) !== 'https' ||
    strtolower((string) ($u['host'] ?? '')) !== 'bitrix.24bkm.com' ||
    !preg_match('~^/rest/[0-9]+/[A-Za-z0-9_-]+/?$~',
       (string) ($u['path'] ?? '')) ||
    !empty($u['query']) || !empty($u['fragment'])) fail();
$now = (string) time();
$mac = hash_hmac('sha256', $now . '|' . $host, $salt);
echo json_encode(['ready' => true, 'form_token' => $now . '.' . $mac], JSON_UNESCAPED_UNICODE);
