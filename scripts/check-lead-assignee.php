<?php
declare(strict_types=1);

/** CLI-only, read-only private config check. No CRM requests or writes. */
if (PHP_SAPI !== 'cli') { http_response_code(404); exit(1); }
ini_set('display_errors', '0');
ini_set('log_errors', '0');

function assigneeMatches(array $config, int $expected): bool {
    $actual = filter_var($config['assigned_by_id'] ?? null, FILTER_VALIDATE_INT);
    return $expected > 0 && $actual !== false && $actual === $expected;
}
function stopAssigneeCheck(string $message): void {
    fwrite(STDERR, 'ASSIGNEE_CONFIG: ' . $message . PHP_EOL);
    exit(1);
}
if (in_array('--self-test', $argv, true)) {
    if (!assigneeMatches(['assigned_by_id' => 7], 7) ||
        !assigneeMatches(['assigned_by_id' => '7'], 7) ||
        assigneeMatches(['assigned_by_id' => 8], 7) ||
        assigneeMatches([], 7) ||
        assigneeMatches(['assigned_by_id' => 'invalid'], 7)) {
        stopAssigneeCheck('SELF_TEST_FAILED');
    }
    echo "Assignee config self-test PASSED; no private config or network used.\n";
    exit(0);
}

$expected = filter_var($argv[1] ?? null, FILTER_VALIDATE_INT);
if ($expected === false || $expected <= 0) {
    stopAssigneeCheck('EXPECTED_POSITIVE_ID_REQUIRED');
}
$path = '/home/h/help24pw/.bkm_private/config.php';
if (!is_readable($path)) { stopAssigneeCheck('PRIVATE_CONFIG_NOT_READABLE'); }

// A malformed PHP config must not print its content or token to CI logs.
$config = null;
$loadFailed = false;
ob_start();
set_error_handler(static function ($severity, $message): bool {
    throw new RuntimeException('Private configuration warning');
});
try { $config = require $path; }
catch (Throwable $e) { $loadFailed = true; }
finally { restore_error_handler(); ob_end_clean(); }
if ($loadFailed || !is_array($config)) {
    stopAssigneeCheck('PRIVATE_CONFIG_INVALID');
}
if (($config['enabled'] ?? null) !== false ||
    ($config['privacy_approved'] ?? null) !== false) {
    stopAssigneeCheck('LIVE_COLLECTION_MUST_REMAIN_DISABLED');
}
if (!assigneeMatches($config, $expected)) {
    stopAssigneeCheck('MISSING_OR_DIFFERENT_FROM_EXPECTED_ID');
}
echo 'ASSIGNEE_CONFIG: PASS; configured ID matches expected ID ' . $expected . PHP_EOL;
echo "COLLECTION_FLAGS: BOTH_FALSE\n";
echo "NO_WRITES: config and website unchanged; no CRM request sent.\n";
echo "NOT_VERIFIED: employee status, CRM assignment permission and actual lead creation.\n";
