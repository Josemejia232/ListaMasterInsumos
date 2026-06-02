<?php
require_once __DIR__ . '/config.php';

function conectar_bd(): PDO {
    global $DB_DSN, $DB_USER, $DB_PASS;
    $opts = [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ];
    $db = new PDO($DB_DSN, $DB_USER, $DB_PASS, $opts);
    crear_tabla_productos($db);
    return $db;
}
