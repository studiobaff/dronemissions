<?php
// Preparation only: storing a decoder key does not enable cloud synchronization.
if ($action === 'dji-log-settings') {
    owner();
    $path = dm_private().'/dji-log-key.json';
    $lock = fopen(dm_private().'/.dji-log-key.lock', 'c');
    if (!$lock || !flock($lock, LOCK_EX)) throw new RuntimeException('DJI configuration lock unavailable.');
    chmod(dm_private().'/.dji-log-key.lock', 0600);
    $stored = is_file($path) ? json_decode(file_get_contents($path), true, 16, JSON_THROW_ON_ERROR) : [];
    $revision = $stored['revision'] ?? '';
    if ($method === 'POST') {
        if (!is_string($input['revision'] ?? null) || !hash_equals($revision, $input['revision'])) problem('DJI-Einstellung wurde inzwischen geändert. Bitte neu öffnen.', 409);
        $key = $input['apiKey'] ?? null;
        if ($key !== null && (!is_string($key) || !preg_match('/^[A-Za-z0-9_-]{16,256}$/D', $key))) problem('Bitte den App Key aus deiner DJI-Open-API-Anwendung eingeben.');
        // A null key explicitly clears the setting. No secret is ever returned to the browser.
        $stored = ['revision'=>bin2hex(random_bytes(16)), 'apiKey'=>$key];
        $tmp = tempnam(dm_private(), '.dji-key-');
        if ($tmp === false) throw new RuntimeException('DJI configuration unavailable.');
        try {
            if (!chmod($tmp, 0600) || file_put_contents($tmp, json_encode($stored, JSON_THROW_ON_ERROR), LOCK_EX) === false || !rename($tmp, $path)) throw new RuntimeException('DJI configuration not saved.');
        } finally {
            if (is_file($tmp)) unlink($tmp);
        }
    }
    flock($lock, LOCK_UN);fclose($lock);
    respond(['configured'=>!empty($stored['apiKey']), 'revision'=>$stored['revision'] ?? '', 'cloudSyncReady'=>false]);
}
