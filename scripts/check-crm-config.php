<?php
declare(strict_types=1);

/**
 * Production release preflight. This file is uploaded to a PRIVATE Beget
 * staging directory, NEVER to 24bkm.com/public_html.
 * Prints no webhook secrets and creates no test CRM leads.
 * --connection-only: verify private config and CRM API without requiring
 * the website's approval switches to be enabled.
 */
function failCheck(string $message): void {
    fwrite(STDERR, "BKM CRM preflight failed: " . $message . PHP_EOL);
    exit(1);
}
if (PHP_SAPI !== 'cli') {
    exit(1);
}
if (!extension_loaded('curl') || !extension_loaded('mbstring')) {
    failCheck('required PHP extensions curl/mbstring are missing');
}
$file = '/home/h/help24pw/.bkm_private/config.php';
if (!is_readable($file)) {
    failCheck('private config file is not readable');
}
$config = require $file;
$connectionOnly = in_array('--connection-only', $argv ?? [], true);
if (!is_array($config)) {
    failCheck('private config is not a PHP array');
}
if (!$connectionOnly && (($config['enabled'] ?? false) !== true ||
    ($config['privacy_approved'] ?? false) !== true)) {
    failCheck('CRM or privacy approval is disabled');
}
$salt = (string) ($config['rate_salt'] ?? '');
if (strlen($salt) < 24 || stripos($salt, 'REPLACE') !== false) {
    failCheck('rate_salt must be a unique long secret');
}
$webhook = trim((string) ($config['bitrix_webhook_url'] ?? ''));
if ($webhook === '') {
    failCheck('bitrix_webhook_url missing in private config');
}
if (strpos($webhook, chr(92)) !== false) {
    failCheck('webhook URL contains a backslash; use https://, not https\\://');
}
$parts = parse_url($webhook);
if (!is_array($parts)) {
    failCheck('webhook URL cannot be parsed; check the quotation marks and protocol');
}
if (($parts['scheme'] ?? '') !== 'https') {
    failCheck('webhook URL must begin with https://');
}
if (strtolower((string) ($parts['host'] ?? '')) !== 'bitrix.24bkm.com') {
    failCheck('webhook URL hostname is not bitrix.24bkm.com');
}
$path = (string) ($parts['path'] ?? '');
if (preg_match('~\\.(?:json|php)$~i', $path)) {
    failCheck('webhook URL contains an API method; copy the UPPER webhook URL without crm.lead.add.json');
}
if (!preg_match('~^/rest/[0-9]+/[A-Za-z0-9_-]+/?$~', $path)) {
    failCheck('webhook URL path must be /rest/NUMERIC_ID/SECRET/ without anything after the last slash');
}
if (isset($parts['user']) || isset($parts['pass']) || isset($parts['query']) ||
    isset($parts['fragment']) || isset($parts['port'])) {
    failCheck('webhook URL must not contain user, password, port, question mark or fragment');
}
if (isset($config['assigned_by_id']) &&
    (!filter_var($config['assigned_by_id'], FILTER_VALIDATE_INT) ||
        (int) $config['assigned_by_id'] <= 0)) {
    failCheck('assigned_by_id must be a positive Bitrix24 user ID');
}
if (isset($config['lead_status_id']) &&
    !preg_match('/^[A-Za-z0-9_:-]{1,60}$/D', (string) $config['lead_status_id'])) {
    failCheck('invalid lead_status_id');
}

// Verify connection and CRM read permissions without transferring contact data.
$endpoint = rtrim($webhook, '/') . '/crm.lead.fields.json';
$curl = curl_init($endpoint);
if ($curl === false) {
    failCheck('cannot initialize CRM API connection');
}
curl_setopt_array($curl, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => '{}',
    CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Accept: application/json'],
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CONNECTTIMEOUT => 5,
    CURLOPT_TIMEOUT => 12,
    CURLOPT_FOLLOWLOCATION => false,
    CURLOPT_SSL_VERIFYPEER => true,
    CURLOPT_SSL_VERIFYHOST => 2,
]);
$response = curl_exec($curl);
$code = (int) curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
$curlError = curl_errno($curl);
curl_close($curl);
$json = is_string($response) ? json_decode($response, true) : null;
if ($curlError !== 0 || $code !== 200 || !is_array($json) ||
    isset($json['error']) || !isset($json['result']['TITLE']) ||
    !isset($json['result']['PHONE'])) {
    failCheck('CRM API check failed; verify webhook permissions and HTTPS');
}
fwrite(STDOUT, $connectionOnly
    ? "BKM CRM connection check PASSED: private config readable, webhook API available. Website form stays disabled." . PHP_EOL
    : "BKM CRM preflight PASSED: API available; private config enabled." . PHP_EOL);
