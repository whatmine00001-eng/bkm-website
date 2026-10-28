<?php
declare(strict_types=1);
/* Private CLI diagnostic only. Never install in public_html or enable intake. */
if (PHP_SAPI !== 'cli') { http_response_code(404); exit(1); }
ini_set('display_errors', '0');
ini_set('log_errors', '0');
const TEST_REF = 'BKM-CLI-ONE-20261028';
const TEST_TITLE = 'ТЕСТ БКМ — интеграция сайта (служебный)';
const PRIVATE_DIR = '/home/h/help24pw/.bkm_private';

function stopTest(string $code): void {
    fwrite(STDERR, 'TEST_STOPPED: ' . $code . PHP_EOL);
    exit(1);
}
function testFields(): array {
    return [
        'TITLE' => TEST_TITLE,
        'ASSIGNED_BY_ID' => 7,
        'STATUS_ID' => 'NEW',
        'SOURCE_ID' => 'WEB',
        'SOURCE_DESCRIPTION' => 'Служебная проверка интеграции БКМ с сервера Beget',
        'OPENED' => 'N',
        'COMMENTS' => 'Разрешённая владельцем однократная техническая проверка. '
            . 'Это НЕ заявка клиента и НЕ отправка через публичную форму. '
            . 'Имена клиентов, телефоны и email не передавались. Reference: ' . TEST_REF,
    ];
}
function saveState($handle, array $state): void {
    $text = json_encode($state, JSON_THROW_ON_ERROR);
    if (!rewind($handle) || !ftruncate($handle, 0) ||
        fwrite($handle, $text) !== strlen($text) || !fflush($handle)) {
        stopTest('STATE_SAVE_FAILED_DO_NOT_REPEAT');
    }
}
function callApi(string $base, string $method, array $payload): array {
    if (!in_array($method, ['crm.lead.add', 'crm.lead.get'], true)) {
        stopTest('UNSUPPORTED_METHOD');
    }
    $curl = curl_init($base . $method . '.json');
    if ($curl === false) { stopTest('CURL_INIT'); }
    $body = '';
    curl_setopt_array($curl, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR),
        CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Accept: application/json'],
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT => 20,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
        CURLOPT_WRITEFUNCTION => static function ($c, string $chunk) use (&$body): int {
            if (strlen($body) + strlen($chunk) > 524288) { return 0; }
            $body .= $chunk;
            return strlen($chunk);
        },
    ]);
    $sent = curl_exec($curl);
    $http = (int) curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
    $errno = curl_errno($curl);
    curl_close($curl);
    $json = json_decode($body, true);
    if ($sent === false || $errno !== 0 || $http !== 200 || !is_array($json) ||
        isset($json['error']) || !array_key_exists('result', $json)) {
        // Never print webhook, response body, error descriptions or customer fields.
        echo 'API_FAILURE: transport=' . $errno . '; http=' . $http . PHP_EOL;
        return ['ok' => false, 'result' => null];
    }
    return ['ok' => true, 'result' => $json['result']];
}

try {
    if (($argv[1] ?? '') === '--self-test') {
        $fields = testFields();
        if ($fields['ASSIGNED_BY_ID'] !== 7 || $fields['TITLE'] !== TEST_TITLE ||
            array_intersect(['PHONE', 'EMAIL', 'NAME', 'LAST_NAME', 'CONTACT_ID'], array_keys($fields))) {
            stopTest('FIXED_PAYLOAD_SELF_TEST_FAILED');
        }
        echo "SELF_TEST_PASS: fixed synthetic record only; no configuration or network used.\n";
        exit(0);
    }
    if (($argv[1] ?? '') !== 'CREATE_ONE_SYNTHETIC_LEAD_ASSIGNEE_7') {
        stopTest('EXPLICIT_TEST_MODE_REQUIRED');
    }
    if (!extension_loaded('curl')) { stopTest('CURL_NOT_AVAILABLE'); }
    $configPath = PRIVATE_DIR . '/config.php';
    if (!is_readable($configPath) || is_link($configPath)) { stopTest('CONFIG_UNAVAILABLE'); }
    $configHash = hash_file('sha256', $configPath);
    ob_start();
    try { $config = require $configPath; } finally { ob_end_clean(); }
    if (!is_array($config) || ($config['enabled'] ?? null) !== false ||
        ($config['privacy_approved'] ?? null) !== false ||
        filter_var($config['assigned_by_id'] ?? null, FILTER_VALIDATE_INT) !== 7) {
        stopTest('REQUIRE_DISABLED_PUBLIC_FLAGS_AND_ASSIGNEE_7');
    }
    $base = trim((string) ($config['bitrix_webhook_url'] ?? ''));
    if (!preg_match('~\Ahttps://bitrix\.24bkm\.com/rest/[0-9]+/[A-Za-z0-9_-]+/\z~D', $base)) {
        stopTest('INVALID_BASE_URL');
    }
    $statePath = PRIVATE_DIR . '/cli-one-lead-20261028.json';
    if (is_link($statePath)) { stopTest('STATE_SYMLINK_REFUSED'); }
    umask(0077);
    $handle = fopen($statePath, 'c+');
    if (!$handle || !flock($handle, LOCK_EX)) { stopTest('STATE_LOCK_FAILED'); }
    chmod($statePath, 0600);
    $existing = stream_get_contents($handle, 16385);
    if ($existing === false || strlen($existing) > 16384) { stopTest('INVALID_STATE'); }
    $state = $existing === '' ? ['status' => 'ready', 'reference' => TEST_REF] : json_decode($existing, true);
    if (!is_array($state) || ($state['reference'] ?? '') !== TEST_REF) { stopTest('INVALID_STATE'); }
    if (($state['status'] ?? '') === 'ready') {
        $state['status'] = 'submitted';
        $state['sent_at_utc'] = gmdate('c');
        saveState($handle, $state); // Before API: ambiguous failures NEVER retry creation.
        $add = callApi($base, 'crm.lead.add', [
            'fields' => testFields(), 'params' => ['REGISTER_SONET_EVENT' => 'Y'],
        ]);
        $id = $add['ok'] ? filter_var($add['result'], FILTER_VALIDATE_INT) : false;
        if ($id === false || $id <= 0) {
            $state['status'] = 'uncertain'; saveState($handle, $state);
            stopTest('ADD_RESULT_UNCERTAIN_NO_AUTOMATIC_RETRY');
        }
        $state['lead_id'] = $id; $state['status'] = 'created'; saveState($handle, $state);
        echo 'CREATED_LEAD_ID: ' . $id . PHP_EOL;
    } elseif (!isset($state['lead_id'])) {
        stopTest('PRIOR_REQUEST_UNCERTAIN_DO_NOT_RETRY');
    } else {
        echo 'EXISTING_TEST_LEAD_ID: ' . (int) $state['lead_id'] . PHP_EOL;
    }
    $id = (int) $state['lead_id'];
    $get = callApi($base, 'crm.lead.get', ['id' => $id]);
    $record = $get['result'];
    if (!$get['ok'] || !is_array($record) || (int) ($record['ID'] ?? 0) !== $id ||
        ($record['TITLE'] ?? '') !== TEST_TITLE || (int) ($record['ASSIGNED_BY_ID'] ?? 0) !== 7) {
        stopTest('CREATED_BUT_READBACK_OR_ASSIGNMENT_NOT_CONFIRMED');
    }
    $state['verified'] = true; saveState($handle, $state);
    if (hash_file('sha256', $configPath) !== $configHash) { stopTest('CONFIG_CHANGED_DURING_TEST'); }
    echo 'LEAD_READBACK_PASS: id=' . $id . '; assignee=7; title_matched=yes' . PHP_EOL;
    echo 'LEAD_URL: https://bitrix.24bkm.com/crm/lead/details/' . $id . '/' . PHP_EOL;
    echo "PUBLIC_INTAKE_OFF: config not modified, no public files deployed, no browser form tested.\n";
    echo "NOTIFICATION_REQUESTED: delivery not verified.\n";
    flock($handle, LOCK_UN); fclose($handle);
} catch (Throwable $e) {
    stopTest('UNEXPECTED_FAILURE_NO_SECRETS_LOGGED_DO_NOT_RETRY_CREATION');
}
