<?php
// POST /api/scrape-sheets.php
header('Content-Type: application/json');
require_once __DIR__ . '/../functions.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Solo POST']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
$sheetUrl = $input['sheet_url'] ?? '';

if (!$sheetUrl) {
    http_response_code(400);
    echo json_encode(['error' => 'Falta sheet_url']);
    exit;
}

try {
    $urls = leerUrlsDeSheet($sheetUrl);
} catch (Exception $e) {
    http_response_code(400);
    echo json_encode(['error' => $e->getMessage()]);
    exit;
}

if (empty($urls)) {
    http_response_code(400);
    echo json_encode(['error' => 'No se encontraron URLs en la hoja']);
    exit;
}

$db = conectar_bd();
$exitosos = 0;
$fallidos = 0;

foreach ($urls as $url) {
    $r = procesarUrl($url, $db);
    if ($r['ok']) $exitosos++; else $fallidos++;
}

echo json_encode([
    'total' => count($urls),
    'exitosos' => $exitosos,
    'fallidos' => $fallidos,
    'mensaje' => "Procesadas " . count($urls) . " URLs: {$exitosos} OK, {$fallidos} fallaron",
]);
