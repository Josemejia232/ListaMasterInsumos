/**
 * ListaMasterInsumos — Google Apps Script (v3 · optimizado)
 *
 * Estrategia:
 *   ① Lee el sheet y detecta URLs NUEVAS (sin ÚLTIMO PRECIO)
 *   ② Scrapea max 25 URLs nuevas por ejecución → /scrape/sync una por una (con pausa)
 *   ③ Para URLs con precio existente → compara con /productos (cacheado, rápido)
 *   ④ Actualiza solo las celdas que cambiaron (batch al final)
 *   ⑤ Semilla col J en una sola operación de lectura/escritura (batch)
 *   ⑥ Sincroniza categorías desde el sheet hacia la BD
 *
 * Seguridad ante caída del scraper:
 *   · Solo escribe precio si valor > 0
 *   · Solo actualiza fecha si el precio realmente cambió
 *   · Respalda precio anterior en col J antes de sobrescribir
 *
 * Optimizaciones anti-timeout (límite 6 min de Google):
 *   · Máximo 25 URLs nuevas por ejecución (el trigger horario procesa el resto)
 *   · Búsqueda O(1) con Map indexado en vez de O(n) triple barrido
 *   · Semilla col J con getRange.getValues/setValues batch (2 lecturas + 1 escritura)
 *   · Logger.log solo en resúmenes, no por fila
 *
 * Configuración:
 *   Celda I1 = URL de la API (ej: https://listamasterinsumos.onrender.com)
 *   Celda I2 = Token de admin
 *
 * Uso:
 *   - Menú "ListaMaster" en la hoja → ejecutar manualmente
 *   - Trigger: Time-driven → cada hora (syncPrices)
 */

var MAX_NEW_PER_RUN = 25;  // URLs nuevas a scrapear por ejecución

// ─── Menú ─────────────────────────────────────────────────

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('ListaMaster')
    .addItem('Sincronizar todo (precios + categorías)', 'syncPrices')
    .addSeparator()
    .addItem('Sincronizar solo categorías', 'syncCategoriesOnly')
    .addItem('Forzar scrape de todas las URLs', 'forceFullScrape')
    .addToUi();
}

// ─── Config ───────────────────────────────────────────────

function getConfig() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var apiUrl = sheet.getRange('I1').getValue();
  var token  = sheet.getRange('I2').getValue();
  return {
    apiUrl: (apiUrl && apiUrl.toString().trim() && apiUrl.toString().trim().indexOf('http') === 0) ? apiUrl.toString().trim() : 'https://listamasterinsumos.onrender.com',
    token:  (token && token.toString().trim())  ? token.toString().trim()  : 'REDACTED_ADMIN_TOKEN'
  };
}

// ─── Principal ────────────────────────────────────────────

function syncPrices() {
  var cfg = getConfig();
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data  = sheet.getDataRange().getValues();
  if (data.length < 2) { Logger.log('Sin datos'); return; }

  var headers = data[0].map(function(h) { return h.toString().toLowerCase().trim(); });

  // Detectar columnas
  var urlCol = headers.indexOf('insumo');
  if (urlCol === -1) urlCol = headers.indexOf('url');
  if (urlCol === -1) {
    urlCol = 0; // Col A por defecto
    sheet.getRange(1, 1).setValue('URL');
    headers[0] = 'url';
  }

  // Col B = Nombre del producto
  var nombreCol = 1;
  if ((headers[nombreCol] || '').indexOf('nombre') === -1) {
    sheet.getRange(1, nombreCol + 1).setValue('NOMBRE PRODUCTO');
    headers[nombreCol] = 'nombre producto';
  }

  // Col F = ÚLTIMO PRECIO
  var precioCol = 5;
  if ((headers[precioCol] || '').indexOf('precio') === -1) {
    sheet.getRange(1, precioCol + 1).setValue('ÚLTIMO PRECIO');
    headers[precioCol] = 'último precio';
  }

  // Col G = ÚLTIMA ACTUALIZACIÓN
  var fechaCol = 6;
  if ((headers[fechaCol] || '').indexOf('actualizaci') === -1) {
    sheet.getRange(1, fechaCol + 1).setValue('ÚLTIMA ACTUALIZACIÓN');
    headers[fechaCol] = 'última actualización';
  }

  // Col J = PRECIO ANTERIOR (backup)
  var anteriorCol = 9;
  if ((headers[anteriorCol] || '').indexOf('anterior') === -1) {
    sheet.getRange(1, anteriorCol + 1).setValue('PRECIO ANTERIOR');
    headers[anteriorCol] = 'precio anterior';
  }

  // Detectar columna CATEGORIA
  var catCol = -1;
  for (var ch = 0; ch < headers.length; ch++) {
    if (headers[ch].indexOf('categ') !== -1) { catCol = ch; break; }
  }

  // ① Clasificar filas: nuevas vs existentes
  var nuevas = [];      // filas sin ÚLTIMO PRECIO
  var existentes = [];  // filas con ÚLTIMO PRECIO → comparar

  for (var i = 1; i < data.length; i++) {
    var url = data[i][urlCol] ? data[i][urlCol].toString().trim() : '';
    if (!url) continue;
    var precioActual = data[i][precioCol] ? data[i][precioCol].toString().trim() : '';
    if (!precioActual) {
      nuevas.push(i);
    } else {
      existentes.push(i);
    }
  }

  // ② Scrape solo URLs nuevas (max 25 por ejecución para no superar 6 min)
  var totalNuevas = nuevas.length;
  var pendientes = 0;
  if (totalNuevas > MAX_NEW_PER_RUN) {
    pendientes = totalNuevas - MAX_NEW_PER_RUN;
    nuevas = nuevas.slice(0, MAX_NEW_PER_RUN);
  }

  if (nuevas.length > 0) {
    Logger.log('Scrapeando ' + nuevas.length + ' de ' + totalNuevas + ' URLs nuevas' + (pendientes ? ' (quedan ' + pendientes + ' para proxima ejecucion)' : ''));
    for (var n = 0; n < nuevas.length; n++) {
      var rowIdx = nuevas[n];
      var rowUrl = data[rowIdx][urlCol].toString().trim();
      var cat = catCol !== -1 ? (data[rowIdx][catCol] || '').toString().trim() : '';
      var qs = '/scrape/sync?url=' + encodeURIComponent(rowUrl);
      if (cat) qs += '&categoria=' + encodeURIComponent(cat);
      try {
        var scrapeResp = UrlFetchApp.fetch(cfg.apiUrl + qs, {
          method: 'get',
          headers: { 'Authorization': 'Bearer ' + cfg.token },
          muteHttpExceptions: true,
        });
        if (scrapeResp.getResponseCode() >= 300) {
          Logger.log('  FAIL [' + (n+1) + '/' + nuevas.length + ']: ' + scrapeResp.getResponseCode());
        }
      } catch (e) {
        Logger.log('  ERROR [' + (n+1) + '/' + nuevas.length + ']: ' + e);
      }
      // Pausa 1-2s entre scrapes para evitar baneo
      Utilities.sleep(1000 + Math.floor(Math.random() * 1000));
    }
  } else {
    Logger.log('Sin URLs nuevas. Saltando scrape.');
  }

  Utilities.sleep(2000);

  // ③ Obtener productos actualizados desde la API (cacheado, rápido)
  var resp;
  try {
    resp = UrlFetchApp.fetch(cfg.apiUrl + '/productos?limit=500', {
      headers: { 'Authorization': 'Bearer ' + cfg.token },
      muteHttpExceptions: true
    });
    if (resp.getResponseCode() !== 200) {
      Logger.log('Productos respondió ' + resp.getResponseCode() + ' — preservando hoja');
      return;
    }
  } catch (e) {
    Logger.log('Error obteniendo productos (API caida?): ' + e);
    return;
  }

  var productos;
  try { productos = JSON.parse(resp.getContentText()); }
  catch (e) { Logger.log('Error parseando JSON — preservando hoja'); return; }

  if (!productos || !productos.length) { Logger.log('No hay productos (BD vacia?) — preservando hoja'); return; }

  // ✅ Optimización: indexar productos en Maps para búsqueda O(1)
  var urlMap = {};      // exact match:  url_origen → producto
  var normMap = {};     // normalized:   url sin trailing slash → producto
  var productosSinMatch = [];  // solo para el fallback contains (O(n) como último recurso)

  for (var pi = 0; pi < productos.length; pi++) {
    var p = productos[pi];
    var pu = p.url_origen;
    if (pu) {
      urlMap[pu] = p;
      var pn = pu.replace(/\/+$/, '').toLowerCase();
      if (!normMap[pn]) normMap[pn] = p;  // primera ocurrencia gana
    }
    productosSinMatch.push(p);
  }

  var now = new Date();
  var actualizados = 0;
  var cambios = 0;
  var backups = 0;
  var batchPrecioUpdates = [];
  var batchAnteriorUpdates = [];
  var batchFechaUpdates = [];
  var batchNombreUpdates = [];

  // ④ Comparar y actualizar (búsqueda optimizada con Maps)
  var matches = 0;
  var sinMatch = 0;
  var preciosInvalidos = 0;

  for (var k = 1; k < data.length; k++) {
    var sUrl = data[k][urlCol] ? data[k][urlCol].toString().trim() : '';
    if (!sUrl) continue;

    // Búsqueda O(1): exacta primero, luego normalizada
    var match = urlMap[sUrl];
    if (!match) {
      match = normMap[sUrl.replace(/\/+$/, '').toLowerCase()];
    }
    // Fallback O(n): substring (solo cuando los dos anteriores fallan, ~5% de casos)
    if (!match) {
      for (var fm = 0; fm < productosSinMatch.length; fm++) {
        var pu = (productosSinMatch[fm].url_origen || '').toLowerCase();
        if (sUrl.toLowerCase().indexOf(pu) !== -1 || pu.indexOf(sUrl.toLowerCase()) !== -1) {
          match = productosSinMatch[fm]; break;
        }
      }
    }

    if (!match) { sinMatch++; continue; }
    matches++;

    var precioDB = match.valor;
    var precioStr = '';

    // ✅ Validar precio (solo escribir si > 0)
    if (typeof precioDB !== 'number' || isNaN(precioDB) || precioDB <= 0) {
      preciosInvalidos++;
    } else {
      precioStr = '$' + precioDB.toLocaleString('es-CO');
    }

    var precioOld = data[k][precioCol] ? data[k][precioCol].toString().trim() : '';

    // Si el precio cambió (y es válido)
    if (precioStr && precioOld !== precioStr) {
      batchAnteriorUpdates.push({
        row: k + 1,
        col: anteriorCol + 1,
        value: precioOld || ''
      });
      batchPrecioUpdates.push({
        row: k + 1,
        col: precioCol + 1,
        value: precioStr
      });
      batchFechaUpdates.push({
        row: k + 1,
        col: fechaCol + 1,
        value: now
      });
      cambios++;
      if (precioOld) backups++;
    }

    batchNombreUpdates.push({
      row: k + 1,
      col: nombreCol + 1,
      value: match.descripcion || ''
    });
    actualizados++;
  }

  // ⑤ Escribir batch de precios/fechas/nombres
  if (batchAnteriorUpdates.length > 0) {
    for (var b = 0; b < batchAnteriorUpdates.length; b++) {
      var ab = batchAnteriorUpdates[b];
      sheet.getRange(ab.row, ab.col).setValue(ab.value);
    }
  }

  if (batchPrecioUpdates.length > 0) {
    for (var b = 0; b < batchPrecioUpdates.length; b++) {
      var up = batchPrecioUpdates[b];
      sheet.getRange(up.row, up.col).setValue(up.value);
    }
  }

  if (batchFechaUpdates.length > 0) {
    for (var d = 0; d < batchFechaUpdates.length; d++) {
      var du = batchFechaUpdates[d];
      sheet.getRange(du.row, du.col).setValue(du.value);
    }
  }

  if (batchNombreUpdates.length > 0) {
    for (var n = 0; n < batchNombreUpdates.length; n++) {
      var nu = batchNombreUpdates[n];
      sheet.getRange(nu.row, nu.col).setValue(nu.value);
    }
  }

  // ⑤.½ Semilla col J: BATCH read F y J, BATCH write solo donde J vacía
  var lastRow = sheet.getLastRow();
  if (lastRow >= 2) {
    // Leer toda la columna F de una vez
    var fRange = sheet.getRange(2, precioCol + 1, lastRow - 1, 1);
    var fValues = fRange.getValues();
    // Leer toda la columna J de una vez
    var jRange = sheet.getRange(2, anteriorCol + 1, lastRow - 1, 1);
    var jValues = jRange.getValues();

    var semilla = 0;
    for (var r = 0; r < fValues.length; r++) {
      var fv = fValues[r][0];
      var jv = jValues[r][0];
      var fStr = (fv != null) ? fv.toString().trim() : '';
      var jStr = (jv != null) ? jv.toString().trim() : '';
      if (fStr && !jStr) {
        jValues[r][0] = fv;  // copiar F → J en el array
        semilla++;
      }
    }

    // Escribir columna J de vuelta en una sola llamada (solo si hubo cambios)
    if (semilla > 0) {
      jRange.setValues(jValues);
    }
  }

  // ⑥ Sincronizar categorías automáticamente (sin scrape, rápido)
  try {
    var catResp = UrlFetchApp.fetch(cfg.apiUrl + '/sync/categories', {
      method: 'post',
      headers: { 'Authorization': 'Bearer ' + cfg.token },
      muteHttpExceptions: true
    });
    if (catResp.getResponseCode() === 200) {
      var catData = JSON.parse(catResp.getContentText());
    }
  } catch (e) {}

  // ─── Resumen final (único Logger.log pesado) ───
  Logger.log(
    'Sync OK | ' +
    'Nuevas: ' + totalNuevas + ' (scrapeadas: ' + nuevas.length + (pendientes ? ', pendientes: ' + pendientes : '') + ') | ' +
    'Matches: ' + matches + ' | Sin match: ' + sinMatch + ' | ' +
    'Precios act: ' + cambios + ' | Backups: ' + backups + ' | ' +
    'Nombres: ' + batchNombreUpdates.length + ' | ' +
    'Semilla J: ' + (typeof semilla !== 'undefined' ? semilla : 0)
  );
}


// ─── Menú: Solo categorías ─────────────────────────────────

function syncCategoriesOnly() {
  var cfg = getConfig();
  try {
    var resp = UrlFetchApp.fetch(cfg.apiUrl + '/sync/categories', {
      method: 'post',
      headers: { 'Authorization': 'Bearer ' + cfg.token },
      muteHttpExceptions: true
    });
    if (resp.getResponseCode() === 200) {
      var data = JSON.parse(resp.getContentText());
      SpreadsheetApp.getUi().alert(
        'Categorías sincronizadas\n\n' +
        'Actualizados: ' + data.actualizados + '\n' +
        'Sin cambio: ' + data.sin_cambio + '\n' +
        'Sin categoría en sheet: ' + data.sin_categoria + '\n' +
        'No encontrados en BD: ' + data.no_encontrados
      );
    } else {
      SpreadsheetApp.getUi().alert('Error: ' + resp.getResponseCode());
    }
  } catch (e) {
    SpreadsheetApp.getUi().alert('Error: ' + e);
  }
}


// ─── Menú: Forzar scrape completo ──────────────────────────

function forceFullScrape() {
  var ui = SpreadsheetApp.getUi();
  var respuesta = ui.alert(
    '⚠️ Forzar scrape completo',
    'Esto va a re-scrapear TODAS las URLs. Los precios actuales en la hoja se respaldarán en col J antes de sobrescribir.\n\n¿Continuar?',
    ui.ButtonSet.YES_NO
  );
  if (respuesta !== ui.Button.YES) return;

  var cfg = getConfig();
  try {
    var resp = UrlFetchApp.fetch(cfg.apiUrl + '/scrape/daily', {
      method: 'post',
      headers: { 'Authorization': 'Bearer ' + cfg.token },
      muteHttpExceptions: true
    });
    if (resp.getResponseCode() === 200) {
      var data = JSON.parse(resp.getContentText());
      SpreadsheetApp.getUi().alert(
        'Scrape completo ejecutado\n\n' +
        data.mensaje
      );
    } else {
      SpreadsheetApp.getUi().alert('Error: ' + resp.getResponseCode() + '\n\nLos datos existentes en la hoja NO fueron modificados.');
    }
  } catch (e) {
    SpreadsheetApp.getUi().alert('Error de conexión: ' + e + '\n\nLos datos existentes en la hoja NO fueron modificados.');
  }
}
