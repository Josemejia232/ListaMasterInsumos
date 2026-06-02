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
$nuevos = 0;
$actualizados = 0;
$sin_cambio = 0;
$fallidos = 0;

foreach (array_unique($urls) as $url) {
    $scraper = new Scraper($url);
    $data = $scraper->scrape();
    if ($data['codigo'] || $data['descripcion'] || $data['valor'] > 0) {
        $resultado = upsertProducto(
            $db, $data['codigo'], $data['descripcion'], $data['unidad'],
            $data['valor'], $data['tienda'], $data['url']
        );
        if ($resultado === 'nuevo') $nuevos++;
        elseif ($resultado === 'actualizado') $actualizados++;
        else $sin_cambio++;
    } else {
        $fallidos++;
    }
}

echo json_encode([
    'total' => count($urls),
    'nuevos' => $nuevos,
    'actualizados' => $actualizados,
    'sin_cambio' => $sin_cambio,
    'fallidos' => $fallidos,
    'mensaje' => "Nuevos: {$nuevos} | Actualizados: {$actualizados} | Sin cambio: {$sin_cambio} | Fallidos: {$fallidos}",
]);
