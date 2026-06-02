/**
 * ListaMasterInsumos — Google Apps Script (optimizado)
 *
 * Estrategia:
 *   ① Lee el sheet y detecta URLs NUEVAS (sin ÚLTIMO PRECIO)
 *   ② Solo scrapea las URLs nuevas → llama a /scrape/sync una por una (con pausa)
 *   ③ Para URLs con precio existente → compara con /productos (cacheado, rápido)
 *   ④ Actualiza solo las celdas que cambiaron (batch al final)
 *
 * Configuración:
 *   Celda Z1 = URL de la API (ej: https://listamasterinsumos.onrender.com)
 *   Celda Z2 = Token de admin
 *
 * Trigger: Time-driven → cada hora
 */

// ─── Config ───────────────────────────────────────────────

function getConfig() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var apiUrl = sheet.getRange('Z1').getValue();
  var token  = sheet.getRange('Z2').getValue();
  return {
    apiUrl: (apiUrl && apiUrl.toString().trim()) ? apiUrl.toString().trim() : 'https://listamasterinsumos.onrender.com',
    token:  (token && token.toString().trim())  ? token.toString().trim()  : 'admin123'
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
  if (urlCol === -1) { Logger.log('No se encontró columna URL/INSUMO'); return; }

  var precioCol = -1;
  for (var i = 0; i < headers.length; i++) {
    if (headers[i].indexOf('precio') !== -1) { precioCol = i; break; }
  }
  var fechaCol = -1;
  for (var j = 0; j < headers.length; j++) {
    if (headers[j].indexOf('actualizaci') !== -1) { fechaCol = j; break; }
  }

  // Crear columnas si no existen
  if (precioCol === -1) {
    precioCol = headers.length;
    sheet.getRange(1, precioCol + 1).setValue('ÚLTIMO PRECIO');
  }
  if (fechaCol === -1) {
    fechaCol = headers.length + (precioCol === headers.length ? 1 : 0);
    sheet.getRange(1, fechaCol + 1).setValue('ÚLTIMA ACTUALIZACIÓN');
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

  // ② Scrape solo URLs nuevas (con pausa para evitar bloqueo)
  if (nuevas.length > 0) {
    Logger.log('Scrapeando ' + nuevas.length + ' URLs nuevas...');
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
        if (scrapeResp.getResponseCode() < 300) {
          Logger.log('  OK [' + (n+1) + '/' + nuevas.length + ']: ' + rowUrl.substring(0, 60));
        } else {
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
      Logger.log('Productos respondió ' + resp.getResponseCode());
      return;
    }
  } catch (e) { Logger.log('Error obteniendo productos: ' + e); return; }

  var productos;
  try { productos = JSON.parse(resp.getContentText()); }
  catch (e) { Logger.log('Error parseando JSON'); return; }

  if (!productos || !productos.length) { Logger.log('No hay productos'); return; }

  var now = new Date();
  var actualizados = 0;
  var cambios = 0;
  var batchUpdates = [];  // [fila, colPrecio, valor, colFecha]
  var batchDateUpdates = [];

  // ④ Comparar y actualizar
  for (var k = 1; k < data.length; k++) {
    var sUrl = data[k][urlCol] ? data[k][urlCol].toString().trim() : '';
    if (!sUrl) continue;

    // Buscar producto por URL
    var match = null;
    for (var m = 0; m < productos.length; m++) {
      if (productos[m].url_origen === sUrl) { match = productos[m]; break; }
    }
    if (!match) continue;

    var precioDB = match.valor;
    var precioStr = '$' + precioDB.toLocaleString('es-CO');
    var precioOld = data[k][precioCol] ? data[k][precioCol].toString().trim() : '';

    // Si el precio cambió o es nuevo
    if (precioOld !== precioStr) {
      batchUpdates.push({
        row: k + 1,
        col: precioCol + 1,
        value: precioStr
      });
      cambios++;
    }

    // Siempre actualizar fecha
    batchDateUpdates.push({
      row: k + 1,
      col: fechaCol + 1,
      value: now
    });
    actualizados++;
  }

  // ⑤ Escribir batch (más eficiente que setValue por celda)
  if (batchUpdates.length > 0) {
    for (var b = 0; b < batchUpdates.length; b++) {
      var up = batchUpdates[b];
      sheet.getRange(up.row, up.col).setValue(up.value);
    }
    Logger.log('Precios actualizados: ' + cambios);
  }

  if (batchDateUpdates.length > 0) {
    for (var d = 0; d < batchDateUpdates.length; d++) {
      var du = batchDateUpdates[d];
      sheet.getRange(du.row, du.col).setValue(du.value);
    }
  }

  Logger.log('Sincronización completa — ' + nuevas.length + ' nuevas, ' + actualizados + ' filas actualizadas, ' + cambios + ' cambios de precio');
}
