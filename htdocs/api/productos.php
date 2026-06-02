<?php
// GET /api/productos.php?tienda=X&skip=0&limit=100
header('Content-Type: application/json');
require_once __DIR__ . '/../functions.php';

$tienda = $_GET['tienda'] ?? null;
$skip   = (int)($_GET['skip'] ?? 0);
$limit  = (int)($_GET['limit'] ?? 100);

$db = conectar_bd();
$productos = listarProductos($db, $tienda, $skip, $limit);
echo json_encode($productos);
