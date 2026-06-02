<?php
// Configuración para Hostinger + Neon PostgreSQL
$DB_HOST = getenv('DB_HOST') ?: 'ep-flat-math-ap1g3ybe-pooler.c-7.us-east-1.aws.neon.tech';
$DB_PORT = getenv('DB_PORT') ?: '5432';
$DB_NAME = getenv('DB_NAME') ?: 'neondb';
$DB_USER = getenv('DB_USER') ?: 'neondb_owner';
$DB_PASS = getenv('DB_PASS') ?: 'npg_PoRl8zvWym6p';

$DB_DSN = "pgsql:host={$DB_HOST};port={$DB_PORT};dbname={$DB_NAME};sslmode=require";

// Crear tabla si no existe
function crear_tabla_productos(PDO $db): void {
    $db->exec("
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(100) NOT NULL,
            descripcion VARCHAR(500) NOT NULL,
            unidad VARCHAR(50) NOT NULL DEFAULT 'Unidad',
            valor DOUBLE PRECISION NOT NULL DEFAULT 0,
            tienda VARCHAR(200) NOT NULL,
            url_origen VARCHAR(1000) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_productos_codigo ON productos(codigo);
        CREATE INDEX IF NOT EXISTS idx_productos_tienda ON productos(tienda);
        CREATE INDEX IF NOT EXISTS idx_productos_created ON productos(created_at DESC);
    ");
}
