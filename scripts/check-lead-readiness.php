<?php
declare(strict_types=1);

/**
 * CLI-only read-only readiness check. NO lead creation, lead listing or writes.
 * Upload alongside check-crm-config.php to a PRIVATE Beget directory.
 * --self-test uses synthetic metadata only and never reads configuration.
 */
if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit(1);
}

function requiredUnmapped(array $fields, array $guaranteed): array {
    $yes = static fn($v): bool => in_array($v, [true, 1, '1', 'Y', 'true'], true);
    $missing = [];
    foreach ($fields as $code => $field) {
        if (!is_array($field) || !is_string($code)) { continue; }
        if ($yes($field['isRequired'] ?? false) &&
            !$yes($field['isReadOnly'] ?? false) &&
            !in_array($code, $guaranteed, true)) {
            // Only schema identifiers; never output field labels or values.
            $missing[] = preg_replace('/[^A-Za-z0-9_]/', '', $code);
        }
    }
    return $missing;
}

function hasStatus(array $rows, string $expected): bool {
    foreach ($rows as $row) {
        if (is_array($row) && (string) ($row['STATUS_ID'] ?? '') === $expected) {
            return true;
        }
    }
    return false;
}

if (in_array('--self-test', $argv, true)) {
    $fixture = [
        'ID' => ['isRequired' => true, 'isReadOnly' => true],
        'TITLE' => ['isRequired' => true, 'isReadOnly' => false],
        'UF_CRM_TEST' => ['isRequired' => 'Y', 'isReadOnly' => false],
        'OPTIONAL' => ['isRequired' => false, 'isReadOnly' => false],
    ];
    if (requiredUnmapped($fixture, ['TITLE']) !== ['UF_CRM_TEST'] ||
        !hasStatus([['STATUS_ID' => 'NEW']], 'NEW') ||
        hasStatus([], 'WEB')) {
        fwrite(STDERR, "Readiness self-test FAILED\n");
        exit(1);
    }
    echo "Readiness metadata self-test PASSED; no configuration or network used.\n";
    exit(0);
}

$argv[] = '--connection-only';
require __DIR__ . '/check-crm-config.php';
// The existing checker validates the hostname, TLS, token structure and fields.
// Its result is schema metadata, NOT customer records.
$fields = $json['result'];
if (($config['enabled'] ?? null) !== false ||
    ($config['privacy_approved'] ?? null) !== false) {
    failCheck('Readiness diagnostic requires both live collection switches to stay false');
}

function metadataRead(string $base, string $method, array $params = []): array {
    // Intentionally impossible to call an add/update/delete or lead-list method.
    if (!in_array($method, ['crm.settings.mode.get', 'crm.status.list'], true)) {
        failCheck('Read-only method allowlist rejected request');
    }
    $c = curl_init(rtrim($base, '/') . '/' . $method . '.json');
    if ($c === false) { failCheck('Cannot initialize metadata request'); }
    curl_setopt_array($c, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => json_encode($params === [] ? new stdClass() : $params),
        CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Accept: application/json'],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT => 12,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
    ]);
    $body = curl_exec($c);
    $http = (int) curl_getinfo($c, CURLINFO_RESPONSE_CODE);
    $err = curl_errno($c);
    curl_close($c);
    $value = is_string($body) ? json_decode($body, true) : null;
    if ($err !== 0 || $http !== 200 || !is_array($value) ||
        isset($value['error']) || !array_key_exists('result', $value)) {
        // Never print response bodies, webhook URLs or error descriptions.
        return ['ok' => false, 'result' => null];
    }
    return ['ok' => true, 'result' => $value['result']];
}

$expected = ['TITLE', 'NAME', 'PHONE', 'EMAIL', 'COMPANY_TITLE', 'COMMENTS',
             'SOURCE_ID', 'STATUS_ID', 'ASSIGNED_BY_ID'];
$absent = array_values(array_diff($expected, array_keys($fields)));
echo 'LEAD_SCHEMA: ' . ($absent === [] ? 'PASS' : 'MISSING ' . implode(',', $absent)) . PHP_EOL;
$guaranteed = ['TITLE', 'NAME', 'PHONE', 'COMMENTS', 'SOURCE_ID',
               'SOURCE_DESCRIPTION', 'OPENED', 'STATUS_ID'];
if (isset($config['assigned_by_id'])) { $guaranteed[] = 'ASSIGNED_BY_ID'; }
$unmapped = requiredUnmapped($fields, $guaranteed);
echo 'REQUIRED_FIELDS_REVIEW: ' . ($unmapped === [] ? 'NONE' : implode(',', $unmapped)) . PHP_EOL;

$mode = metadataRead($webhook, 'crm.settings.mode.get');
$modeCode = $mode['ok'] && is_scalar($mode['result']) ? (string) $mode['result'] : '';
echo 'CRM_MODE: ' . ($modeCode === '1' ? 'CLASSIC_WITH_LEADS' :
    ($modeCode === '2' ? 'SIMPLE_WITHOUT_LEADS' : 'UNVERIFIED')) . PHP_EOL;

$stage = (string) ($config['lead_status_id'] ?? 'NEW');
$stages = metadataRead($webhook, 'crm.status.list', [
    'filter' => ['ENTITY_ID' => 'STATUS', 'STATUS_ID' => $stage]
]);
$stageOk = $stages['ok'] && is_array($stages['result']) && hasStatus($stages['result'], $stage);
echo 'LEAD_STAGE: ' . ($stageOk ? 'PASS' : 'MISSING_OR_UNVERIFIED') . PHP_EOL;

$sources = metadataRead($webhook, 'crm.status.list', [
    'filter' => ['ENTITY_ID' => 'SOURCE', 'STATUS_ID' => 'WEB']
]);
$sourceOk = $sources['ok'] && is_array($sources['result']) && hasStatus($sources['result'], 'WEB');
echo 'SOURCE_WEB: ' . ($sourceOk ? 'PASS' : 'MISSING_OR_UNVERIFIED') . PHP_EOL;
echo 'ASSIGNMENT: ' . (isset($config['assigned_by_id']) ? 'EXPLICIT_ID_CONFIGURED_NOT_VERIFIED' : 'PORTAL_DEFAULT_NOT_VERIFIED') . PHP_EOL;
echo "COLLECTION_FLAGS: BOTH_FALSE\n";
echo "NO_WRITES: no leads created; no contacts read; website and private settings unchanged.\n";
echo "NOT_VERIFIED: create permission, assignment validity, stage-specific requirements, robots, web PHP and end-to-end submission.\n";
$ok = $absent === [] && $unmapped === [] && $modeCode === '1' && $stageOk && $sourceOk;
echo 'READINESS_METADATA: ' . ($ok ? 'PASS' : 'REVIEW_REQUIRED') . PHP_EOL;
exit($ok ? 0 : 2);
