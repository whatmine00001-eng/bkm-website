<?php
declare(strict_types=1);
/** CLI-only maintenance. Writes ONLY the four listed CSS/JS assets. No CRM. */
if (PHP_SAPI !== 'cli') { exit(1); }
const UI_FILES = ['bkm-ui-polish.css','home-brand-final.css','interior-redesign.css','home.js'];
const UI_ROOT = '/home/h/help24pw/24bkm.com/public_html/assets';
const UI_BACKUPS = '/home/h/help24pw/.bkm_backups';
function abortUi(string $why): void { throw new RuntimeException($why); }
function putUi(string $path, string $data, int $mode): void {
    if (is_link($path)) { abortUi('Symlink refused'); }
    $temp = $path . '.bkm-ui-' . bin2hex(random_bytes(6));
    if (file_put_contents($temp,$data,LOCK_EX) !== strlen($data) || !chmod($temp,$mode) || !rename($temp,$path)) {
        @unlink($temp); abortUi('Atomic write failed');
    }
}
try {
    $mode = $argv[1] ?? '';
    if ($mode === '--self-test') {
        foreach (UI_FILES as $file) {
            if (!preg_match('/^[a-z0-9-]+\.(css|js)$/D',$file)) abortUi('Unsafe scope');
        }
        echo "UI_SCOPE_SELF_TEST_PASS: static CSS/JS only; no site/config access.\n"; exit(0);
    }
    $id = $argv[2] ?? '';
    if (!in_array($mode,['apply','rollback'],true) || !preg_match('/^[0-9]+-[0-9]+$/D',$id)) abortUi('Invalid mode or run ID');
    if (!is_dir(UI_ROOT) || is_link(UI_ROOT) || !is_dir(UI_BACKUPS)) abortUi('Expected directories missing');
    $backup = UI_BACKUPS . '/ui-polish-' . $id;
    if (is_link($backup)) abortUi('Backup symlink refused');
    if ($mode === 'rollback') {
        if (!is_file($backup.'/state.json')) abortUi('No backup state');
        $state=json_decode((string)file_get_contents($backup.'/state.json'),true);
        if (!is_array($state) || array_keys($state)!==UI_FILES) abortUi('Invalid backup manifest');
        foreach (UI_FILES as $name) {
            $target=UI_ROOT.'/'.$name;
            if ($state[$name]['exists']) {
                $old=file_get_contents($backup.'/'.$name);
                if (!is_string($old) || hash('sha256',$old)!==$state[$name]['sha256']) abortUi('Backup checksum mismatch');
                putUi($target,$old,0644);
            } elseif (is_file($target)) {
                if (is_link($target)) abortUi('Target symlink refused');
                if (!unlink($target)) abortUi('Cannot remove new static asset');
            }
        }
        echo "UI_ROLLBACK_PASS: original static assets restored.\n"; exit(0);
    }
    if (file_exists($backup)) abortUi('Backup already exists; do not repeat apply');
    $new=[]; $state=[]; $old=[];
    foreach (UI_FILES as $name) {
        $src=__DIR__.'/assets/'.$name; $dest=UI_ROOT.'/'.$name;
        if (!is_file($src) || is_link($src) || is_link($dest)) abortUi('Missing or unsafe asset');
        $data=file_get_contents($src);
        if (!is_string($data) || strlen($data)<200 || strlen($data)>60000 || str_contains($data,'<?php') || str_contains($data,'bitrix_webhook_url')) abortUi('Unexpected asset content');
        if ($name!=='bkm-ui-polish.css' && !is_file($dest)) abortUi('Existing asset not found');
        $new[$name]=$data;
        $exists=is_file($dest);
        $old[$name]=$exists ? file_get_contents($dest) : null;
        if ($exists && !is_string($old[$name])) abortUi('Cannot read current asset');
        $state[$name]=['exists'=>$exists,'sha256'=>$exists?hash('sha256',$old[$name]):null];
    }
    if (!str_contains($new['bkm-ui-polish.css'],'BKM_UI_POLISH_20261028_v1') ||
        !str_starts_with($new['home-brand-final.css'],"@import url('bkm-ui-polish.css?v=20261028a');") ||
        !str_starts_with($new['interior-redesign.css'],"@import url('bkm-ui-polish.css?v=20261028a');") ||
        !str_contains($new['home.js'],'min-width: 1051px')) abortUi('Expected patch markers absent');
    umask(0077);
    if (!mkdir($backup,0700)) abortUi('Backup creation failed');
    foreach (UI_FILES as $name) {
        if ($state[$name]['exists']) putUi($backup.'/'.$name,$old[$name],0600);
    }
    putUi($backup.'/state.json',json_encode($state,JSON_THROW_ON_ERROR),0600);
    foreach (UI_FILES as $name) putUi(UI_ROOT.'/'.$name,$new[$name],0644);
    foreach (UI_FILES as $name) {
        if (hash_file('sha256',UI_ROOT.'/'.$name)!==hash('sha256',$new[$name])) abortUi('Published checksum mismatch');
    }
    echo "UI_STATIC_ASSETS_APPLIED: 4 CSS/JS files, backup ui-polish-".$id."\n";
    echo "UNCHANGED: HTML pages, logos, .htaccess, DNS, CRM, private configuration, lead collection switches.\n";
} catch (Throwable $e) {
    fwrite(STDERR,'UI_MAINTENANCE_FAILED: '.$e->getMessage().PHP_EOL); exit(1);
}
