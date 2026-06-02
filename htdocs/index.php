<?php
require_once __DIR__ . '/functions.php';
$db = conectar_bd();
$tiendaFilter = $_GET['tienda'] ?? '';
$productos = listarProductos($db, $tiendaFilter ?: null);

// Tiendas para el dropdown
$tiendas = $db->query("SELECT DISTINCT tienda FROM productos ORDER BY tienda")->fetchAll();
?>
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ListaMasterInsumos</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        :root {
            --bg: #0f172a; --card: #1e293b; --border: #334155;
            --text: #e2e8f0; --muted: #94a3b8; --accent: #3b82f6;
            --green: #22c55e; --red: #ef4444; --yellow: #eab308;
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }
        .container { max-width:1400px; margin:0 auto; padding:1.5rem; }
        h1 { font-size:1.5rem; font-weight:700; margin-bottom:.25rem; }
        .subtitle { color:var(--muted); font-size:.875rem; margin-bottom:1.5rem; }

        /* Cards */
        .cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:1rem; margin-bottom:1.5rem; }
        .card { background:var(--card); border:1px solid var(--border); border-radius:.5rem; padding:1rem; }
        .card-label { font-size:.75rem; color:var(--muted); text-transform:uppercase; margin-bottom:.25rem; }
        .card-value { font-size:1.5rem; font-weight:700; }

        /* Form */
        .form-row { display:flex; gap:.5rem; margin-bottom:1.5rem; }
        .form-row input { flex:1; background:var(--card); border:1px solid var(--border); border-radius:.375rem; padding:.5rem .75rem; color:var(--text); font-size:.875rem; }
        .form-row input:focus { outline:none; border-color:var(--accent); }
        .btn { background:var(--accent); color:#fff; border:none; border-radius:.375rem; padding:.5rem 1rem; font-size:.875rem; cursor:pointer; white-space:nowrap; }
        .btn:hover { opacity:.9; }
        .btn-outline { background:transparent; border:1px solid var(--border); color:var(--text); }
        .btn-sm { padding:.25rem .5rem; font-size:.75rem; }
        .btn-green { background:var(--green); }

        /* Toolbar */
        .toolbar { display:flex; gap:.5rem; margin-bottom:1rem; align-items:center; flex-wrap:wrap; }
        .toolbar select { background:var(--card); border:1px solid var(--border); border-radius:.375rem; padding:.375rem .5rem; color:var(--text); font-size:.8125rem; }

        /* Table */
        .table-wrap { background:var(--card); border:1px solid var(--border); border-radius:.5rem; overflow-x:auto; }
        table { width:100%; border-collapse:collapse; font-size:.8125rem; }
        th { text-align:left; padding:.625rem .75rem; color:var(--muted); font-weight:600; border-bottom:1px solid var(--border); position:sticky; top:0; background:var(--card); }
        td { padding:.5rem .75rem; border-bottom:1px solid var(--border); }
        tr:last-child td { border-bottom:none; }
        tr:hover td { background:rgba(255,255,255,.02); }
        td:nth-child(3) { max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        td:nth-child(7) { max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
        td:nth-child(7) a { color:var(--accent); text-decoration:none; font-size:.75rem; }
        .badge { display:inline-block; padding:.125rem .5rem; border-radius:999px; font-size:.6875rem; font-weight:600; }
        .badge-homecenter { background:rgba(59,130,246,.2); color:#60a5fa; }
        .badge-sodimac { background:rgba(239,68,68,.2); color:#f87171; }
        .badge-promart { background:rgba(34,197,94,.2); color:#4ade80; }
        .badge-easy { background:rgba(234,179,8,.2); color:#facc15; }
        .badge-maestro { background:rgba(168,85,247,.2); color:#c084fc; }
        .badge-otra { background:rgba(148,163,184,.2); color:#94a3b8; }

        /* Live indicator */
        .live { display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--green); margin-right:.375rem; }
        .status-ok { color:var(--green); font-weight:600; }
        .status-err { color:var(--red); }

        .empty { text-align:center; padding:3rem; color:var(--muted); }

        /* Loading */
        .htmx-indicator { opacity:0; transition:opacity .2s; }
        .htmx-request .htmx-indicator { opacity:1; }
        .htmx-request.btn { opacity:.5; pointer-events:none; }

        #result-box { margin-top:1rem; }
        #result-box pre { background:var(--card); border:1px solid var(--border); border-radius:.375rem; padding:.75rem; font-size:.75rem; overflow-x:auto; }
    </style>
</head>
<body>
<div class="container">

    <h1><span class="live"></span>ListaMasterInsumos</h1>
    <p class="subtitle">Insumos de construcción — Scraping desde Google Sheets a PostgreSQL</p>

    <!-- Scrape individual -->
    <form class="form-row" hx-post="api/scrape-url.php" hx-target="#result-box" hx-swap="innerHTML">
        <input type="url" name="url" placeholder="URL de producto (Homecenter, Sodimac, Promart...)" required
               value="<?= htmlspecialchars($tiendaFilter ? 'https://www.homecenter.com.co/homecenter-co/product/' : '') ?>">
        <button type="submit" class="btn">Scrape</button>
        <span class="htmx-indicator" style="color:var(--muted);align-self:center;">Scrapeando...</span>
    </form>

    <!-- Scrape Google Sheets -->
    <form class="form-row" hx-post="api/scrape-sheets.php" hx-target="#result-box" hx-swap="innerHTML">
        <input type="url" name="sheet_url" placeholder="URL de Google Sheets con lista de links" required>
        <button type="submit" class="btn btn-green">Scrape Sheet</button>
        <span class="htmx-indicator" style="color:var(--muted);align-self:center;">Procesando sheet...</span>
    </form>

    <div id="result-box"></div>

    <!-- Stats cards -->
    <div class="cards">
        <?php
        $total = $db->query("SELECT COUNT(*) FROM productos")->fetchColumn();
        $totalValor = $db->query("SELECT COALESCE(SUM(valor),0) FROM productos")->fetchColumn();
        $hoy = $db->query("SELECT COUNT(*) FROM productos WHERE created_at::date = CURRENT_DATE")->fetchColumn();
        $tiendasCount = $db->query("SELECT COUNT(DISTINCT tienda) FROM productos")->fetchColumn();
        ?>
        <div class="card"><div class="card-label">Total Insumos</div><div class="card-value"><?= $total ?></div></div>
        <div class="card"><div class="card-label">Valor Total</div><div class="card-value">$<?= number_format($totalValor, 2) ?></div></div>
        <div class="card"><div class="card-label">Scrapeados Hoy</div><div class="card-value"><?= $hoy ?></div></div>
        <div class="card"><div class="card-label">Tiendas</div><div class="card-value"><?= $tiendasCount ?></div></div>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
        <select name="tienda" hx-get="index.php" hx-target="#tabla" hx-swap="innerHTML" hx-trigger="change" hx-indicator="#tabla">
            <option value="">Todas las tiendas</option>
            <?php foreach ($tiendas as $t): ?>
            <option value="<?= htmlspecialchars($t['tienda']) ?>" <?= $tiendaFilter === $t['tienda'] ? 'selected' : '' ?>>
                <?= htmlspecialchars($t['tienda']) ?>
            </option>
            <?php endforeach; ?>
        </select>
        <button class="btn btn-sm btn-outline" hx-get="api/productos.php" hx-target="#tabla" hx-swap="innerHTML" hx-indicator="#tabla">
            ↻ Recargar
        </button>
        <span id="tabla-indicator" class="htmx-indicator" style="color:var(--muted);font-size:.75rem;">Cargando...</span>
    </div>

    <!-- Tabla -->
    <div class="table-wrap" id="tabla">
        <?php if (empty($productos)): ?>
        <div class="empty">No hay productos scrapeados. Usa los formularios para empezar.</div>
        <?php else: ?>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Código</th>
                    <th>Descripción</th>
                    <th>Unidad</th>
                    <th>Valor</th>
                    <th>Tienda</th>
                    <th>URL</th>
                    <th>Fecha</th>
                </tr>
            </thead>
            <tbody>
            <?php foreach ($productos as $p): ?>
                <tr>
                    <td><?= $p['id'] ?></td>
                    <td><?= htmlspecialchars($p['codigo']) ?></td>
                    <td title="<?= htmlspecialchars($p['descripcion']) ?>"><?= htmlspecialchars($p['descripcion']) ?></td>
                    <td><?= htmlspecialchars($p['unidad']) ?></td>
                    <td>$<?= number_format($p['valor'], 2) ?></td>
                    <td><span class="badge badge-<?= strtolower($p['tienda']) ?>"><?= htmlspecialchars($p['tienda']) ?></span></td>
                    <td><a href="<?= htmlspecialchars($p['url_origen']) ?>" target="_blank"><?= htmlspecialchars($p['url_origen']) ?></a></td>
                    <td><?= date('d/m/y H:i', strtotime($p['created_at'])) ?></td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>
        <?php endif; ?>
    </div>

</div>
</body>
</html>
