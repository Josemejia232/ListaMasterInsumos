<?php
// Funciones compartidas

require_once __DIR__ . '/database.php';
require_once __DIR__ . '/scraper.php';

function leerUrlsDeSheet(string $sheetUrl): array {
    // Extraer ID del sheet
    if (!preg_match('#/spreadsheets/d/([a-zA-Z0-9_-]+)#', $sheetUrl, $m)) {
        throw new RuntimeException("No se pudo extraer el ID del Google Sheet");
    }
    $sheetId = $m[1];
    $csvUrl = "https://docs.google.com/spreadsheets/d/{$sheetId}/export?format=csv";

    $ch = curl_init($csvUrl);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_FOLLOWLOCATION => true,
        CURLOPT_TIMEOUT        => 20,
    ]);
    $csv = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($code !== 200 || !$csv) {
        throw new RuntimeException("No se pudo leer el Google Sheet (HTTP $code)");
    }

    $urls = [];
    foreach (explode("\n", $csv) as $line) {
        $line = trim($line, " \t\n\r\0\x0B\"");
        if ($line && str_starts_with($line, 'http')) {
            $urls[] = $line;
        }
    }
    return $urls;
}

function procesarUrl(string $url, PDO $db): array {
    $scraper = new Scraper($url);
    $data = $scraper->scrape();

    if ($data['codigo'] || $data['descripcion'] || $data['valor'] > 0) {
        $stmt = $db->prepare("
            INSERT INTO productos (codigo, descripcion, unidad, valor, tienda, url_origen)
            VALUES (:codigo, :desc, :unidad, :valor, :tienda, :url)
        ");
        $stmt->execute([
            ':codigo' => $data['codigo'],
            ':desc'   => $data['descripcion'],
            ':unidad' => $data['unidad'],
            ':valor'  => $data['valor'],
            ':tienda' => $data['tienda'],
            ':url'    => $data['url'],
        ]);
        return ['ok' => true, 'id' => $db->lastInsertId(), 'data' => $data];
    }
    return ['ok' => false, 'error' => 'No se pudo extraer información', 'url' => $url];
}

function listarProductos(PDO $db, ?string $tienda = null, int $skip = 0, int $limit = 100): array {
    $sql = "SELECT * FROM productos";
    $params = [];
    if ($tienda) {
        $sql .= " WHERE tienda ILIKE :tienda";
        $params[':tienda'] = "%{$tienda}%";
    }
    $sql .= " ORDER BY created_at DESC";
    if ($limit > 0) {
        $sql .= " OFFSET :skip LIMIT :limit";
        $params[':skip'] = $skip;
        $params[':limit'] = $limit;
    }
    $stmt = $db->prepare($sql);
    foreach ($params as $k => $v) {
        $stmt->bindValue($k, $v, is_int($v) ? PDO::PARAM_INT : PDO::PARAM_STR);
    }
    $stmt->execute();
    return $stmt->fetchAll();
}
