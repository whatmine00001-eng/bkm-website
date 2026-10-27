<?php
declare(strict_types=1);
/** CLI maintenance only. Changes ONLY the live .htaccess legacy /services route. */
if (PHP_SAPI !== 'cli') { exit(1); }
umask(0077);
const ROOT = '/home/h/help24pw/24bkm.com/public_html';
const RULE = "# BEGIN BKM LEGACY SERVICES 20261027\nRedirectMatch 301 ^/services/?$ https://24bkm.com/services.html\n# END BKM LEGACY SERVICES 20261027\n";
function stop(string $text): void { fwrite(STDERR, $text . PHP_EOL); exit(1); }
function store(string $path, string $bytes, int $mode): void {
    $tmp = tempnam(dirname($path), '.bkm-route-');
    if ($tmp === false) { stop('Cannot create atomic replacement'); }
    if (file_put_contents($tmp, $bytes, LOCK_EX) !== strlen($bytes) || !rename($tmp, $path)) {
        @unlink($tmp); stop('Cannot store atomic replacement');
    }
    if (!chmod($path, $mode)) { stop('Cannot restore file permissions'); }
}
if (($argv[1] ?? '') === '--self-test') {
    foreach (['/services', '/services/'] as $path) {
        if (preg_match('~^/services/?$~D', $path) !== 1) { stop('Exact-match test failed'); }
    }
    foreach (['/services.html', '/services-old', '/services/foo', '/api/lead.php', '/'] as $path) {
        if (preg_match('~^/services/?$~D', $path) !== 0) { stop('Route scope test failed'); }
    }
    echo "EXACT_ROUTE_SELF_TEST_PASS\n"; exit(0);
}
$mode = $argv[1] ?? '';
$id = $argv[2] ?? '';
if (!in_array($mode, ['apply', 'rollback'], true) || !preg_match('/^[0-9]+-[0-9]+$/D', $id)) {
    stop('Invalid maintenance invocation');
}
if (!is_dir(ROOT) || is_link(ROOT . '/.htaccess')) { stop('Unexpected target directory or symlink'); }
$file = ROOT . '/.htaccess';
$backup = '/home/h/help24pw/.bkm_backups/services-route-' . $id;
if ($mode === 'rollback') {
    $state = is_file($backup . '/state.json') ? json_decode((string) file_get_contents($backup . '/state.json'), true) : null;
    if (!is_array($state)) { stop('No transaction state to restore'); }
    $current = is_file($file) ? hash_file('sha256', $file) : null;
    if ($current === $state['original_hash']) { echo "ROLLBACK_NOT_NEEDED\n"; exit(0); }
    if ($current !== $state['patched_hash']) { stop('Concurrent .htaccess edit detected; automatic rollback stopped'); }
    if ($state['existed']) {
        $original = file_get_contents($backup . '/htaccess.original');
        if (!is_string($original) || hash('sha256', $original) !== $state['original_hash']) { stop('Backup integrity error'); }
        store($file, $original, (int) $state['mode']);
    } elseif (!unlink($file)) { stop('Cannot remove newly created .htaccess'); }
    echo "ROLLBACK_OK: original web configuration restored\n"; exit(0);
}
if (!is_file(ROOT . '/services.html') || !is_readable(ROOT . '/services.html')) { stop('Target services.html missing'); }
if (file_exists($file) && !is_file($file)) { stop('Unexpected .htaccess type'); }
$existed = is_file($file);
$original = $existed ? file_get_contents($file) : '';
if (!is_string($original) || strlen($original) > 262144) { stop('Unexpected .htaccess size or read error'); }
if (strpos($original, '# BEGIN BKM LEGACY SERVICES 20261027') !== false && strpos($original, RULE) === false) {
    stop('Existing route block differs; manual review required');
}
$patched = strpos($original, RULE) !== false ? $original : RULE . "\n" . $original;
if (!is_dir(dirname($backup)) && !mkdir(dirname($backup), 0700, true)) { stop('Cannot create private backup parent'); }
if (!mkdir($backup, 0700)) { stop('Transaction already exists or backup failed'); }
$fileMode = $existed ? (fileperms($file) & 0777) : 0644;
$state = ['existed' => $existed, 'mode' => $fileMode,
    'original_hash' => $existed ? hash('sha256', $original) : null,
    'patched_hash' => hash('sha256', $patched)];
if (file_put_contents($backup . '/htaccess.original', $original, LOCK_EX) !== strlen($original) ||
    file_put_contents($backup . '/state.json', json_encode($state), LOCK_EX) === false) { stop('Backup write failed'); }
chmod($backup . '/htaccess.original', 0600); chmod($backup . '/state.json', 0600);
if (($existed && hash_file('sha256', $file) !== $state['original_hash']) || (!$existed && file_exists($file))) {
    stop('Concurrent web configuration change detected before write');
}
store($file, $patched, $fileMode);
echo "SERVICES_REDIRECT_APPLIED: only /services and /services/ redirect to HTTPS services.html\n";
echo "BACKUP_ID: services-route-" . $id . PHP_EOL;
echo "UNCHANGED: public page contents, DNS, CRM, private webhook, lead collection settings\n";
