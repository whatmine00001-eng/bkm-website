<?php
declare(strict_types=1);

/**
 * BKM lead receiver — Beget PHP 8+, same-origin POST only.
 * Secret configuration: /home/h/help24pw/.bkm_private/config.php (outside public_html).
 * Test HTTP website must NEVER accept customer information.
 */
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, private');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: same-origin');

function reply(int $status, string $code, bool $ok = false): void {
    http_response_code($status);
    echo json_encode(['ok' => $ok, 'code' => $code], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    reply(405, 'method_not_allowed');
}

$https = ($_SERVER['HTTPS'] ?? '') === 'on' || ($_SERVER['HTTPS'] ?? '') === '1';
if (!$https) {
    reply(426, 'https_required');
}

$host = strtolower((string) ($_SERVER['HTTP_HOST'] ?? ''));
$host = preg_replace('/:\d+$/', '', $host);
$origin = (string) ($_SERVER['HTTP_ORIGIN'] ?? '');
$referer = (string) ($_SERVER['HTTP_REFERER'] ?? '');
$source = $origin !== '' ? $origin : $referer;
$parsed = $source ? parse_url($source) : false;
if (!is_array($parsed) || strtolower((string) ($parsed['scheme'] ?? '')) !== 'https' ||
    strtolower((string) ($parsed['host'] ?? '')) !== $host) {
    reply(403, 'origin_rejected');
}

if (stripos((string) ($_SERVER['CONTENT_TYPE'] ?? ''), 'application/json') !== 0) {
    reply(415, 'json_required');
}
$length = (int) ($_SERVER['CONTENT_LENGTH'] ?? 0);
if ($length <= 0 || $length > 14000) {
    reply(413, 'invalid_payload_size');
}
$raw = file_get_contents('php://input', false, null, 0, 14001);
if (!is_string($raw) || strlen($raw) > 14000) {
    reply(413, 'invalid_payload_size');
}
$data = json_decode($raw, true);
if (!is_array($data)) {
    reply(400, 'invalid_json');
}

$configFile = '/home/h/help24pw/.bkm_private/config.php';
if (!is_file($configFile) || !is_readable($configFile)) {
    reply(503, 'not_configured');
}
$config = require $configFile;
if (!is_array($config) || ($config['enabled'] ?? false) !== true ||
    ($config['privacy_approved'] ?? false) !== true) {
    reply(503, 'not_enabled');
}

function input(array $data, string $key, int $max = 250): string {
    $value = $data[$key] ?? '';
    if (!is_string($value)) {
        return '';
    }
    $value = trim(preg_replace('/[\x00-\x1F\x7F]/u', ' ', $value) ?? '');
    return mb_substr($value, 0, $max);
}

if (input($data, 'website', 40) !== '') {
    // Honeypot. Bots get an uninformative successful reply; no lead is created.
    reply(200, 'accepted', true);
}
if (($data['consent'] ?? false) !== true) {
    reply(422, 'consent_required');
}
$name = input($data, 'name', 120);
$company = input($data, 'company', 160);
$phone = input($data, 'phone', 36);
$email = input($data, 'email', 160);
$service = input($data, 'service', 100);
$from = input($data, 'origin', 150);
$to = input($data, 'destination', 150);
$cargo = input($data, 'cargo', 180);
$details = input($data, 'details', 1600);
if (mb_strlen($name) < 2 || mb_strlen($phone) < 7 ||
    preg_match('/^[+0-9 ()\-]{7,36}$/', $phone) !== 1 ||
    strlen(preg_replace('/\D/', '', $phone)) < 7 ||
    ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL))) {
    reply(422, 'invalid_fields');
}
if (!in_array($service, [
    'Международные перевозки', 'Таможенное оформление',
    'Экспедирование', 'Логистика и склад', 'Сборные грузы', 'Другое'
], true)) {
    reply(422, 'invalid_service');
}

$rateDirectory = '/home/h/help24pw/.bkm_private/rate';
if (!is_dir($rateDirectory) && !@mkdir($rateDirectory, 0700, true) && !is_dir($rateDirectory)) {
    reply(503, 'server_unavailable');
}
$ip = (string) ($_SERVER['REMOTE_ADDR'] ?? 'unknown');
$rateId = hash('sha256', $ip . (string) ($config['rate_salt'] ?? 'bkm'));
$file = @fopen($rateDirectory . '/' . $rateId . '.json', 'c+');
if (!$file || !flock($file, LOCK_EX)) {
    reply(503, 'server_unavailable');
}
@chmod($rateDirectory . '/' . $rateId . '.json', 0600);
$record = stream_get_contents($file);
$times = json_decode((string) $record, true);
if (!is_array($times)) { $times = []; }
$now = time();
$times = array_values(array_filter($times, static fn($t): bool => is_int($t) && $t > $now - 3600));
if (count($times) >= 5) {
    flock($file, LOCK_UN);
    fclose($file);
    reply(429, 'rate_limited');
}
$times[] = $now;
rewind($file);
ftruncate($file, 0);
fwrite($file, json_encode($times));
fflush($file);
flock($file, LOCK_UN);
fclose($file);

$webhook = trim((string) ($config['bitrix_webhook_url'] ?? ''));
$parsedWebhook = parse_url($webhook);
if (!is_array($parsedWebhook) ||
    strtolower((string) ($parsedWebhook['scheme'] ?? '')) !== 'https' ||
    strtolower((string) ($parsedWebhook['host'] ?? '')) !== 'bitrix.24bkm.com' ||
    !preg_match('~^/rest/[0-9]+/[A-Za-z0-9_-]+/?$~', (string) ($parsedWebhook['path'] ?? '')) ||
    !empty($parsedWebhook['query']) || !empty($parsedWebhook['fragment']) ||
    !empty($parsedWebhook['user']) || !empty($parsedWebhook['pass'])) {
    reply(503, 'crm_not_configured');
}

$utms = [];
foreach (['source','medium','campaign','term','content'] as $key) {
    $value = input($data, 'utm_' . $key, 150);
    if ($value !== '') {
        $utms['UTM_' . strtoupper($key)] = $value;
    }
}
$path = input($data, 'page', 200);
$comments = implode("\n", [
    'Услуга: ' . $service,
    'Маршрут: ' . $from . ' → ' . $to,
    'Груз: ' . $cargo,
    'Пожелания: ' . $details,
    'Страница сайта: ' . $path,
    'Согласие с обработкой данных предоставлено на сайте: ' . gmdate('c')
]);
$fields = [
    'TITLE' => 'Сайт БКМ — ' . $service,
    'NAME' => $name,
    'COMPANY_TITLE' => $company,
    'SOURCE_ID' => 'WEB',
    'SOURCE_DESCRIPTION' => 'Сайт БКМ (Beget)',
    'OPENED' => 'N',
    'STATUS_ID' => 'NEW',
    'PHONE' => [['VALUE' => $phone, 'VALUE_TYPE' => 'WORK']],
    'COMMENTS' => $comments
] + $utms;
if ($email !== '') {
    $fields['EMAIL'] = [['VALUE' => $email, 'VALUE_TYPE' => 'WORK']];
}

$payload = json_encode(['fields' => $fields, 'params' => ['REGISTER_SONET_EVENT' => 'Y']],
    JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
if (!$payload || !function_exists('curl_init')) {
    reply(503, 'server_unavailable');
}
$endpoint = rtrim($webhook, '/') . '/crm.lead.add.json';
$curl = curl_init($endpoint);
curl_setopt_array($curl, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => $payload,
    CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Accept: application/json'],
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CONNECTTIMEOUT => 5,
    CURLOPT_TIMEOUT => 15,
    CURLOPT_FOLLOWLOCATION => false,
    CURLOPT_SSL_VERIFYPEER => true,
    CURLOPT_SSL_VERIFYHOST => 2
]);
$response = curl_exec($curl);
$status = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
$errorCode = curl_errno($curl);
curl_close($curl);
$json = is_string($response) ? json_decode($response, true) : null;
if ($errorCode !== 0 || $status !== 200 || !is_array($json) ||
    isset($json['error']) || empty($json['result'])) {
    error_log('BKM CRM submission failed: transport=' . $errorCode . ' status=' . $status .
        ' code=' . (is_array($json) ? preg_replace('/[^a-zA-Z0-9_]/', '', (string) ($json['error'] ?? 'response')) : 'response'));
    reply(502, 'crm_unavailable');
}
reply(200, 'lead_created', true);
