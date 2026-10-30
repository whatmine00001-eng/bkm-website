<?php
declare(strict_types=1);
/**
 * CLI-only read-after-write verification of ONE synthetic test lead.
 * Never prints CRM API secrets, full lead data or other customers' records.
 */
if (PHP_SAPI !== 'cli' || !isset($argv[1]) || !preg_match('/^[1-9][0-9]{0,11}$/D', $argv[1])) {
    exit(2);
}
$id = (int) $argv[1];
$cfg = require '/home/h/help24pw/.bkm_private/config.php';
$endpoint = rtrim((string) ($cfg['bitrix_webhook_url'] ?? ''), '/') . '/crm.lead.get.json';
$url = parse_url($endpoint);
if (!is_array($url) || ($url['scheme'] ?? '') !== 'https' ||
    ($url['host'] ?? '') !== 'bitrix.24bkm.com') { exit(3); }
$ch = curl_init($endpoint);
if ($ch === false) { exit(4); }
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => json_encode(['id' => $id]),
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
    CURLOPT_CONNECTTIMEOUT => 5,
    CURLOPT_TIMEOUT => 20,
    CURLOPT_SSL_VERIFYPEER => true,
    CURLOPT_SSL_VERIFYHOST => 2,
    CURLOPT_FOLLOWLOCATION => false,
]);
$data = curl_exec($ch);
$status = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
curl_close($ch);
$result = is_string($data) ? json_decode($data, true) : null;
if ($status !== 200 || !is_array($result) || !is_array($result['result'] ?? null)) { exit(5); }
$lead = $result['result'];
if ((int) ($lead['ID'] ?? 0) !== $id ||
    (int) ($lead['ASSIGNED_BY_ID'] ?? 0) !== 7 ||
    (string) ($lead['SOURCE_ID'] ?? '') !== 'WEB' ||
    strpos((string) ($lead['TITLE'] ?? ''), 'Сайт БКМ') !== 0 ||
    strpos((string) ($lead['NAME'] ?? ''), 'ТЕСТ БКМ') !== 0) { exit(6); }
echo 'TEST_LEAD_CONFIRMED: id=' . $id . ' assigned_by_id=7 source=WEB' . PHP_EOL;
