<?php
declare(strict_types=1);

/**
 * BKM lead receiver — Beget or Timeweb Cloud PHP 8.2+, same-origin POST only.
 * Secret configuration (outside public_html): BKM_PRIVATE_CONFIG_PATH env,
 * defaulting to /home/h/help24pw/.bkm_private/config.php on Beget.
 * Test HTTP website must NEVER accept customer information.
 */
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store, private');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: same-origin');

function reply(int $status, string $code, bool $ok = false, ?int $leadId = null): void {
    http_response_code($status);
    $out = ['ok' => $ok, 'code' => $code];
    if ($leadId !== null && $ok) { $out['lead_id'] = $leadId; }
    echo json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    reply(405, 'method_not_allowed');
}

$timewebMode = (getenv('BKM_HOSTING_TARGET') === 'timeweb');
$https = ($_SERVER['HTTPS'] ?? '') === 'on' || ($_SERVER['HTTPS'] ?? '') === '1';
// Timeweb App Platform terminates HTTPS at its Caddy reverse proxy.
// Trust this header only for deployments explicitly built for Timeweb Cloud.
if ($timewebMode && strtolower(trim((string) ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? ''))) === 'https') {
    $https = true;
}
if (!$https) {
    reply(426, 'https_required');
}

$host = strtolower((string) ($_SERVER['HTTP_HOST'] ?? ''));
$host = preg_replace('/:\d+$/', '', $host);
$hosts = ['24bkm.com', 'www.24bkm.com'];
if ($timewebMode) {
    $hosts = array_values(array_unique(array_filter(array_map(
        'trim', explode(',', strtolower((string) (getenv('BKM_ALLOWED_HOSTS') ?: '24bkm.com,www.24bkm.com')))
    ))));
}
if (!in_array($host, $hosts, true)) {
    reply(403, 'host_rejected');
}
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

if ($timewebMode) {
    // App Platform runs ephemeral containers. Use runtime environment secrets;
    // never include them in Docker layers or the public repository.
    $configFile = '';
    $config = [
        'enabled' => getenv('BKM_CRM_ENABLED') === 'true',
        'privacy_approved' => true,
        'rate_salt' => (string) (getenv('BKM_RATE_SALT') ?: ''),
        'bitrix_webhook_url' => (string) (getenv('BKM_BITRIX_WEBHOOK_URL') ?: '')
    ];
} else {
    $configFile = getenv('BKM_PRIVATE_CONFIG_PATH') ?: '/home/h/help24pw/.bkm_private/config.php';
    if (!is_file($configFile) || !is_readable($configFile)) {
        reply(503, 'not_configured');
    }
    $config = require $configFile;
}
if (!is_array($config) || ($config['enabled'] ?? false) !== true ||
    ($config['privacy_approved'] ?? false) !== true) {
    reply(503, 'not_enabled');
}
if (!is_file(dirname(__DIR__) . '/privacy.html') || !is_file(dirname(__DIR__) . '/consent.html')) {
    reply(503, 'policy_not_available');
}
$salt = (string) ($config['rate_salt'] ?? '');
if (strlen($salt) < 24 || stripos($salt, 'REPLACE') !== false) {
    reply(503, 'anti_spam_not_configured');
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
if (mb_strlen($name) < 2) {
    reply(422, 'invalid_fields');
}
$country = strtoupper(input($data, 'country', 2));
$phoneRaw = input($data, 'phone', 20);
$email = input($data, 'email', 160);
$service = input($data, 'service', 100);
$details = input($data, 'details', 1600);
$phoneRules = [
    'RU' => ['7', 10, 10],
    'KZ' => ['7', 10, 10],
    'BY' => ['375', 9, 9],
    'CN' => ['86', 11, 11],
    'IN' => ['91', 10, 10],
    'KR' => ['82', 9, 10],
    'AE' => ['971', 9, 9],
    'US' => ['1', 10, 10],
    'CA' => ['1', 10, 10],
    'DE' => ['49', 7, 13],
    'GB' => ['44', 9, 10],
    'FR' => ['33', 9, 9],
    'IT' => ['39', 8, 12],
    'TR' => ['90', 10, 10],
    'PL' => ['48', 9, 9],
    'KG' => ['996', 9, 9],
    'UZ' => ['998', 9, 9],
    'AM' => ['374', 8, 8],
    'GE' => ['995', 9, 9],
    'AZ' => ['994', 9, 9],
    'TJ' => ['992', 9, 9],
    'MD' => ['373', 8, 8],
    'NL' => ['31', 9, 9],
    'ES' => ['34', 9, 9],
    'PT' => ['351', 9, 9],
    'CH' => ['41', 9, 9],
    'BE' => ['32', 8, 9],
    'LT' => ['370', 8, 8],
    'LV' => ['371', 8, 8],
    'EE' => ['372', 7, 8],
    'JP' => ['81', 9, 10],
    'SG' => ['65', 8, 8],
    'TH' => ['66', 9, 9],
    'VN' => ['84', 9, 10]
];
$rule = $phoneRules[$country] ?? null;
if ($rule === null || preg_match('/^[0-9]+$/D', $phoneRaw) !== 1 ||
    strlen($phoneRaw) < $rule[1] || strlen($phoneRaw) > $rule[2] ||
    strlen($rule[0] . $phoneRaw) > 15) {
    reply(422, 'invalid_phone');
}
$phone = '+' . $rule[0] . $phoneRaw;
$emailParts = explode('@', $email);
$validEmail = count($emailParts) === 2 &&
    preg_match('/^[A-Za-z0-9._%+\\-]+$/D', $emailParts[0]) === 1 &&
    $emailParts[0][0] !== '.' &&
    substr($emailParts[0], -1) !== '.' &&
    strpos($emailParts[0], '..') === false &&
    filter_var($email, FILTER_VALIDATE_EMAIL) !== false;
if ($validEmail) {
    $labels = explode('.', $emailParts[1]);
    $validEmail = count($labels) >= 2 &&
        preg_match('/^[A-Za-z]{2,24}$/D', end($labels)) === 1;
    foreach ($labels as $label) {
        if (preg_match('/^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$/D', $label) !== 1) {
            $validEmail = false;
            break;
        }
    }
}
if (!$validEmail) {
    reply(422, 'invalid_email');
}
if (!in_array($service, [
    'Международная перевозка',
    'Таможенное оформление',
    'Логистика и склад',
    'Агентские услуги',
    'Другое'
], true)) {
    reply(422, 'invalid_service');
}

// Timeweb App Platform container filesystem is not persistent between deploys.
// This is a supplementary throttle; Turnstile remains the main bot protection.
$rateDirectory = $timewebMode
    ? sys_get_temp_dir() . '/bkm_rate'
    : dirname($configFile) . '/rate';
if (!is_dir($rateDirectory) && !@mkdir($rateDirectory, 0700, true) && !is_dir($rateDirectory)) {
    reply(503, 'server_unavailable');
}
$ip = (string) ($_SERVER['REMOTE_ADDR'] ?? 'unknown');
if ($timewebMode) {
    // Timeweb Caddy supplies the original client IP via reverse proxy.
    $forwarded = trim(explode(',', (string) ($_SERVER['HTTP_X_FORWARDED_FOR'] ?? ''))[0]);
    if (filter_var($forwarded, FILTER_VALIDATE_IP)) {
        $ip = $forwarded;
    }
}
$rateId = hash('sha256', $ip . $salt);
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

if ($timewebMode) {
    // A local HMAC form ticket replaces Cloudflare Turnstile for Russian access.
    // The public ticket never contains a webhook, password or private salt.
    $ticket = input($data, 'form_token', 100);
    $parts = explode('.', $ticket);
    if (count($parts) !== 2 ||
        preg_match('/^[0-9]{10}$/D', $parts[0]) !== 1 ||
        preg_match('/^[a-f0-9]{64}$/D', $parts[1]) !== 1) {
        reply(422, 'verification_required');
    }
    $age = time() - (int) $parts[0];
    if ($age < 3 || $age > 3600 ||
        !hash_equals(hash_hmac('sha256', $parts[0] . '|' . $host, $salt), $parts[1])) {
        reply(422, 'verification_required');
    }
}
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
    'Вид услуги: ' . $service,
    'Страна телефона: ' . $country,
    'Комментарии: ' . $details,
    'Страница сайта: ' . $path,
    'Согласие на обработку данных на сайте: ' . gmdate('c'),
    'Редакция согласия: bkm-consent-uploaded-2026-11-06-v1',
    'Политика: https://24bkm.com/privacy.html'
]);
$fields = [
    'TITLE' => 'Сайт БКМ — ' . $service,
    'NAME' => $name,
    'SOURCE_ID' => 'WEB',
    'SOURCE_DESCRIPTION' => $timewebMode ? 'Сайт БКМ (Timeweb)' : 'Сайт БКМ (Beget)',
    'OPENED' => 'N',
    'STATUS_ID' => 'NEW',
    'ASSIGNED_BY_ID' => 7,
    'PHONE' => [['VALUE' => $phone, 'VALUE_TYPE' => 'WORK']],
    'EMAIL' => [['VALUE' => $email, 'VALUE_TYPE' => 'WORK']],
    'COMMENTS' => $comments
] + $utms;
// Optional routing by the company's Bitrix24 administrator.
// Values come only from server-side config; site visitors cannot change them.
if (isset($config['lead_status_id'])) {
    $statusId = (string) $config['lead_status_id'];
    if (!preg_match('/^[A-Za-z0-9_:-]{1,60}$/D', $statusId)) {
        reply(503, 'crm_status_not_configured');
    }
    $fields['STATUS_ID'] = $statusId;
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
$leadId = filter_var($json['result'] ?? null, FILTER_VALIDATE_INT);
if ($leadId === false || (int) $leadId <= 0) {
    reply(502, 'crm_invalid_response');
}
reply(200, 'lead_created', true, (int) $leadId);
