<?php
// GET /api/scrape-url.php?url=...
header('Content-Type: application/json');
require_once __DIR__ . '/../functions.php';

$url = $_GET['url'] ?? '';
if (!$url) {
    http_response_code(400);
    echo json_encode(['error' => 'Falta url']);
    exit;
}

$db = conectar_bd();
$result = procesarUrl($url, $db);

if ($result['ok']) {
    echo json_encode($result['data']);
} else {
    http_response_code(500);
    echo json_encode($result);
}
