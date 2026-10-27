<?php
/* BKM_FIXED_ONE_SHOT_FORM_v1. Not the public customer intake handler. */
ini_set('display_errors', '0');
ini_set('log_errors', '0');
const BKM_TEST_ID = '20261027-2c54bb9e';
const BKM_TEST_ROOT = '/home/h/help24pw/24bkm.com/public_html';
const BKM_PRIVATE = '/home/h/help24pw/.bkm_private';
const BKM_TEST_TITLE = 'ТЕСТ БКМ — проверка формы сайта';

function test_state_path() { return BKM_PRIVATE . '/form-check-' . BKM_TEST_ID . '.json'; }
function test_public_dir() { return BKM_TEST_ROOT . '/bkm-test-' . BKM_TEST_ID; }
function answer($status, $value) {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($value, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}
function load_private_config() {
    $path = BKM_PRIVATE . '/config.php';
    if (!is_file($path) || !is_readable($path)) { throw new Exception('CONFIG_UNAVAILABLE'); }
    ob_start();
    try { $config = require $path; } finally { ob_end_clean(); }
    if (!is_array($config) || !isset($config['assigned_by_id']) || (int)$config['assigned_by_id'] !== 7 ||
        !array_key_exists('enabled', $config) || $config['enabled'] !== false ||
        !array_key_exists('privacy_approved', $config) || $config['privacy_approved'] !== false) {
        throw new Exception('KEEP_PUBLIC_INTAKE_OFF_AND_ASSIGNEE_7');
    }
    $url = isset($config['bitrix_webhook_url']) ? trim($config['bitrix_webhook_url']) : '';
    if (!preg_match('~\Ahttps://bitrix\.24bkm\.com/rest/[0-9]+/[A-Za-z0-9_-]+/\z~D', $url)) {
        throw new Exception('WEBHOOK_FORMAT_INVALID');
    }
    $config['bitrix_webhook_url'] = $url;
    return $config;
}
function store_state($handle, $state) {
    $encoded = json_encode($state, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    if ($encoded === false || !rewind($handle) || !ftruncate($handle, 0) ||
        fwrite($handle, $encoded) !== strlen($encoded) || !fflush($handle)) {
        throw new Exception('STATE_WRITE_FAILED');
    }
}
function api_call($url, $method, $payload) {
    if (!in_array($method, array('crm.lead.add', 'crm.lead.get'), true)) {
        throw new Exception('METHOD_NOT_ALLOWED');
    }
    $ch = curl_init($url . $method . '.json');
    if ($ch === false) { throw new Exception('TRANSPORT_INIT_FAILED'); }
    $body = '';
    curl_setopt_array($ch, array(
        CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_HTTPHEADER => array('Content-Type: application/json', 'Accept: application/json'),
        CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => 20,
        CURLOPT_FOLLOWLOCATION => false, CURLOPT_SSL_VERIFYPEER => true, CURLOPT_SSL_VERIFYHOST => 2,
        CURLOPT_WRITEFUNCTION => function ($curl, $chunk) use (&$body) {
            if (strlen($body) + strlen($chunk) > 524288) { return 0; }
            $body .= $chunk; return strlen($chunk);
        }
    ));
    $ok = curl_exec($ch);
    $http = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
    $errno = curl_errno($ch);
    curl_close($ch);
    $data = json_decode($body, true);
    if ($ok === false || $errno !== 0 || $http !== 200 || !is_array($data) ||
        isset($data['error']) || !array_key_exists('result', $data)) {
        return array('ok' => false, 'result' => null);
    }
    return array('ok' => true, 'result' => $data['result']);
}

if (PHP_SAPI === 'cli') {
    try {
        $mode = isset($argv[1]) ? $argv[1] : '';
        if ($mode === '--self-test') {
            if (!preg_match('/\A[0-9]{8}-[a-f0-9]{8}\z/D', BKM_TEST_ID) ||
                !hash_equals(hash('sha256', 'fixture'), hash('sha256', 'fixture'))) {
                throw new Exception('SELF_TEST_FAILED');
            }
            echo "ONE_SHOT_SELF_TEST_PASS; no config read, CRM request or publication.\n"; exit;
        }
        if ($mode === '--remove') {
            $dir = test_public_dir();
            if (is_link($dir) || is_link($dir . '/index.php') || is_link(test_state_path())) {
                throw new Exception('SYMLINK_REFUSED');
            }
            if (is_file($dir . '/index.php')) { unlink($dir . '/index.php'); }
            if (is_dir($dir)) { rmdir($dir); }
            echo "TEST_PAGE_REMOVED; private result retained; main website unchanged.\n"; exit;
        }
        if ($mode !== '--install' || !isset($argv[2]) ||
            !preg_match('/\A[a-f0-9]{64}\z/D', $argv[2])) { throw new Exception('INVALID_INSTALL'); }
        load_private_config();
        $dir = test_public_dir();
        $statePath = test_state_path();
        if (!is_dir(BKM_TEST_ROOT) || !is_dir(BKM_PRIVATE) || file_exists($dir) ||
            is_link($dir) || file_exists($statePath) || is_link($statePath)) {
            throw new Exception('INSTALL_TARGET_NOT_EMPTY_OR_MISSING');
        }
        umask(0077);
        $handle = fopen($statePath, 'x+');
        if (!$handle) { throw new Exception('STATE_CREATE_FAILED'); }
        store_state($handle, array('key_hash' => $argv[2], 'expires' => time() + 7200,
            'status' => 'ready', 'lead_id' => null, 'verified' => false));
        fclose($handle); chmod($statePath, 0600);
        if (!mkdir($dir, 0755) || !chmod($dir, 0755) || !copy(__FILE__, $dir . '/index.php') ||
            !chmod($dir . '/index.php', 0644)) {
            if (is_file($dir . '/index.php')) { unlink($dir . '/index.php'); }
            if (is_dir($dir)) { rmdir($dir); }
            unlink($statePath); throw new Exception('INSTALL_FAILED');
        }
        echo "ONE_SHOT_FORM_INSTALLED: /bkm-test-" . BKM_TEST_ID . "/\n";
        echo "Two-hour expiry; one fixed lead only; hash stored privately; no webhook exposed.\n";
        echo "No lead created; existing public files and live config flags unchanged.\n";
        exit;
    } catch (Throwable $e) {
        fwrite(STDERR, "TEST_SETUP_FAILED: " . preg_replace('/[^A-Z0-9_]/', '', $e->getMessage()) . "\n");
        exit(1);
    }
}

header('Cache-Control: no-store, private');
header('X-Robots-Tag: noindex, nofollow, noarchive');
header('Referrer-Policy: no-referrer');
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('Permissions-Policy: camera=(), microphone=(), geolocation=()');
if (PHP_VERSION_ID < 70000) { answer(503, array('ok'=>false, 'code'=>'WEB_PHP_TOO_OLD')); }
if (strtolower(isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : '') !== '24bkm.com' ||
    !in_array(isset($_SERVER['HTTPS']) ? $_SERVER['HTTPS'] : '', array('on', '1'), true)) {
    answer(403, array('ok'=>false, 'code'=>'HTTPS_REQUIRED'));
}
$method = isset($_SERVER['REQUEST_METHOD']) ? $_SERVER['REQUEST_METHOD'] : '';
if ($method === 'POST') {
    if ((isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '') !== 'https://24bkm.com') {
        answer(403, array('ok'=>false, 'code'=>'ORIGIN_REQUIRED'));
    }
    $token = isset($_SERVER['HTTP_X_BKM_TEST_KEY']) ? $_SERVER['HTTP_X_BKM_TEST_KEY'] : '';
    if (!preg_match('/\A[a-f0-9]{64}\z/D', $token) || !is_file(test_state_path())) {
        answer(403, array('ok'=>false, 'code'=>'TEST_ACCESS_REQUIRED'));
    }
    $h = @fopen(test_state_path(), 'r+');
    if (!$h || !flock($h, LOCK_EX)) { answer(503, array('ok'=>false, 'code'=>'TEST_UNAVAILABLE')); }
    $state = json_decode(stream_get_contents($h, 16384), true);
    if (!is_array($state) || !isset($state['key_hash']) ||
        !hash_equals($state['key_hash'], hash('sha256', $token))) {
        answer(403, array('ok'=>false, 'code'=>'TEST_ACCESS_REQUIRED'));
    }
    if ((int)$state['expires'] < time()) { answer(410, array('ok'=>false, 'code'=>'TEST_EXPIRED')); }
    $raw = file_get_contents('php://input', false, null, 0, 1025);
    $data = json_decode($raw, true);
    $ctype = isset($_SERVER['CONTENT_TYPE']) ? $_SERVER['CONTENT_TYPE'] : '';
    if (stripos($ctype, 'application/json') !== 0 || strlen($raw) > 1024 ||
        !is_array($data) || array_keys($data) !== array('action') ||
        !in_array($data['action'], array('status','create'), true)) {
        answer(400, array('ok'=>false, 'code'=>'FIXED_TEST_ONLY'));
    }
    if ($data['action'] === 'status' || $state['status'] !== 'ready') {
        answer(200, array('ok'=>true, 'state'=>$state['status'], 'lead_id'=>$state['lead_id'],
            'verified'=>$state['verified'], 'assignee'=>7, 'test_id'=>BKM_TEST_ID));
    }
    try {
        $cfg = load_private_config();
        if (!function_exists('curl_init')) { throw new Exception('CURL_UNAVAILABLE'); }
        // Persist BEFORE calling the API. Network uncertainty never permits a retry.
        $state['status'] = 'submitted'; $state['submitted_at'] = gmdate('c'); store_state($h, $state);
        $fields = array('TITLE'=>BKM_TEST_TITLE, 'ASSIGNED_BY_ID'=>7, 'STATUS_ID'=>'NEW',
            'SOURCE_ID'=>'WEB', 'SOURCE_DESCRIPTION'=>'Одноразовая тестовая форма БКМ', 'OPENED'=>'N',
            'COMMENTS'=>'Служебная проверка браузер → форма на 24bkm.com → Beget → Bitrix24. '
              .'Не обращение клиента. Контактные данные не передавались. Test ID: '.BKM_TEST_ID);
        $add = api_call($cfg['bitrix_webhook_url'], 'crm.lead.add', array('fields'=>$fields,
            'params'=>array('REGISTER_SONET_EVENT'=>'Y')));
        if (!$add['ok'] || !filter_var($add['result'], FILTER_VALIDATE_INT) || (int)$add['result'] <= 0) {
            $state['status']='needs_review'; store_state($h,$state);
            answer(502,array('ok'=>false,'code'=>'CHECK_CRM_BEFORE_ANY_RETRY','test_id'=>BKM_TEST_ID));
        }
        $state['lead_id']=(int)$add['result']; $state['status']='created'; store_state($h,$state);
        $get = api_call($cfg['bitrix_webhook_url'],'crm.lead.get',array('id'=>$state['lead_id']));
        if ($get['ok'] && is_array($get['result'])) {
            $v=$get['result'];
            $state['verified']=isset($v['ID'],$v['ASSIGNED_BY_ID'],$v['TITLE']) &&
                (int)$v['ID']===$state['lead_id'] && (int)$v['ASSIGNED_BY_ID']===7 &&
                $v['TITLE']===BKM_TEST_TITLE;
        }
        store_state($h,$state);
        answer(200,array('ok'=>true,'state'=>'created','lead_id'=>$state['lead_id'],
            'verified'=>$state['verified'],'assignee'=>7,'test_id'=>BKM_TEST_ID));
    } catch (Throwable $e) {
        answer(503,array('ok'=>false,'code'=>'TEST_STOPPED_DO_NOT_REPEAT','test_id'=>BKM_TEST_ID));
    }
}
if ($method !== 'GET') { answer(405,array('ok'=>false,'code'=>'METHOD_NOT_ALLOWED')); }
$nonce=base64_encode(random_bytes(18));
header("Content-Security-Policy: default-src 'none'; script-src 'nonce-".$nonce."'; style-src 'nonce-".$nonce."'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'");
header('Content-Type: text/html; charset=utf-8');
?>
<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>БКМ — контрольная отправка в Bitrix24</title>
<style nonce="<?= $nonce ?>">*{box-sizing:border-box}body{margin:0;background:#f3f6f5;color:#123e32;font:17px/1.55 system-ui,sans-serif}main{max-width:720px;margin:6vh auto;padding:32px;background:white;border-radius:16px;box-shadow:0 8px 40px #123e3214}img{max-width:220px}h1{font-size:30px;line-height:1.2}small,.note{color:#556862}dt{font-weight:700}dd{margin:0 0 18px}button{background:#ff7900;color:#122d25;border:0;border-radius:8px;padding:17px 24px;font:700 17px system-ui;cursor:pointer}button:disabled{opacity:.55;cursor:default}#status{border-left:4px solid #ff7900;padding:16px;margin-top:22px;background:#f4f7f6}a{color:#075d45;font-weight:700}@media(max-width:600px){main{margin:18px;padding:24px}}</style></head>
<body><main><img src="/assets/bkm-header.svg" alt="БКМ"><h1>Проверка заявки в Bitrix24</h1><p>Одноразовый тест формы на сайте. Создаётся только один служебный лид. Имена, телефоны и почта клиентов не запрашиваются.</p>
<form id="test-form"><dl><dt>Название лида</dt><dd>ТЕСТ БКМ — проверка формы сайта</dd><dt>Ответственный</dt><dd>Кирилл · ID 7</dd><dt>Источник</dt><dd>Веб-сайт</dd></dl><button id="send" type="submit" disabled>Создать один тестовый лид</button></form><div id="status" role="status" aria-live="polite">Проверяем доступ к тесту…</div><p class="note">Это отдельная диагностическая форма, не форма приёма обращений посетителей. Обычная форма и настройки её включения не меняются. Повторное нажатие не создаёт второй лид.</p></main>
<script nonce="<?= $nonce ?>">
(()=>{'use strict';const storage='bkm-form-check-<?= BKM_TEST_ID ?>';let key=location.hash.slice(1);try{if(key){sessionStorage.setItem(storage,key);history.replaceState(null,'',location.pathname);}else{key=sessionStorage.getItem(storage)||'';}}catch(_){}const status=document.getElementById('status'),button=document.getElementById('send');
function display(r){if(r.state==='created'&&Number.isInteger(r.lead_id)){status.textContent='Лид №'+r.lead_id+' создан.'+(r.verified?' Назначение на Кирилла (ID 7) проверено.':' Назначение нужно проверить в CRM.');const a=document.createElement('a');a.href='https://bitrix.24bkm.com/crm/lead/details/'+r.lead_id+'/';a.textContent=' Открыть лид в Bitrix24';a.target='_blank';a.rel='noopener noreferrer';status.append(a);button.disabled=true;}else if(r.state==='ready'){status.textContent='Тест готов. Нажмите кнопку один раз.';button.disabled=false;}else{status.textContent='Тест уже отправлялся. Не создавайте повтор: проверьте лиды в CRM по названию «ТЕСТ БКМ». Код: '+r.state;button.disabled=true;}}
async function request(action){const r=await fetch(location.pathname,{method:'POST',headers:{'Content-Type':'application/json','X-BKM-Test-Key':key},body:JSON.stringify({action}),cache:'no-store',credentials:'same-origin'});const j=await r.json();if(!r.ok||!j.ok)throw new Error(j.code||'TEST_FAILED');return j;}
if(!/^[a-f0-9]{64}$/.test(key)){status.textContent='Откройте полную персональную ссылку теста. Она не является вебхуком Bitrix24.';return;}request('status').then(display).catch(e=>{status.textContent='Проверка остановлена: '+e.message;});document.getElementById('test-form').addEventListener('submit',async e=>{e.preventDefault();if(button.disabled)return;button.disabled=true;status.textContent='Отправляем один тестовый лид…';try{display(await request('create'));}catch(e){status.textContent='Отправка остановлена: '+e.message+'. Не повторяйте отправку: сначала проверим результат в CRM.';}});})();
</script></body></html>
