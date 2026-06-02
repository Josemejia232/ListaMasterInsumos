/**
 * ListaMasterInsumos — Google Apps Script
 *
 * Sincroniza los precios scrapeados con tu Google Sheet.
 *
 * ⚠️ IMPORTANTE: Google Apps Script corre en servidores de Google,
 *    NO puede acceder a localhost. Necesitas una URL pública.
 *
 * Para desarrollo local:
 *   Usa ngrok (https://ngrok.com) para exponer localhost:
 *     ngrok http 8000
 *   Luego pon la URL de ngrok en CONFIG_API_URL abajo o en celda Z1.
 *
 * Configuración (en el Sheet):
 *   Celda Z1 = URL de la API (ej: http://localhost:8000 o https://miapp.onrender.com)
 *   Celda Z2 = Token de admin
 *
 * Instalación:
 *   1. Abre tu Google Sheet → Extensiones → Apps Script
 *   2. Copia este código y pega en el editor
 *   3. Guarda (Ctrl+S) y ejecuta syncPrices() una vez para probar
 *   4. Ve al reloj ⏰ → Agregar trigger:
 *      - Función: syncPrices
 *      - Tipo: Time-driven → Cada hora
 */

// ─── Config (se lee del Sheet si existe, si no usa defaults) ──

function getConfig() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var apiUrl = sheet.getRange('Z1').getValue();
  var token  = sheet.getRange('Z2').getValue();
  return {
    apiUrl: (apiUrl && apiUrl.toString().trim()) ? apiUrl.toString().trim() : 'http://localhost:8000',
    token:  (token && token.toString().trim())  ? token.toString().trim()  : 'admin123'
  };
}

// ─── Principal ────────────────────────────────────────────────

function syncPrices() {
  var cfg = getConfig();
  var sheet = SpreadsheetApp.getActiveSheet();
  var data  = sheet.getDataRange().getValues();
  if (data.length < 2) { Logger.log('Sin datos'); return; }

  var headers = data[0].map(function(h) { return h.toString().toLowerCase().trim(); });

  // Detectar columnas por nombre
  var urlCol = headers.indexOf('url');
  if (urlCol === -1) { Logger.log('No se encontró columna URL'); return; }

  var fechaCol = -1;
  for (var i = 0; i < headers.length; i++) {
    if (headers[i].indexOf('actualizaci') !== -1) { fechaCol = i; break; }
  }

  // 1. Disparar scrape diario
  try {
    var scrapeResp = UrlFetchApp.fetch(cfg.apiUrl + '/scrape/daily', {
      method: 'get',
      headers: { 'Authorization': 'Bearer ' + cfg.token },
      muteHttpExceptions: true
    });
    var code = scrapeResp.getResponseCode();
    if (code !== 200) {
      Logger.log('Scrape respondió ' + code + ': ' + scrapeResp.getContentText().substring(0, 200));
    } else {
      Logger.log('Scrape OK');
    }
  } catch (e) {
    Logger.log('Error llamando a /scrape/daily: ' + e);
    Logger.log('¿Está la app corriendo y accesible desde internet?');
    return;
  }

  Utilities.sleep(3000);

  // 2. Obtener productos actualizados
  var resp;
  try {
    resp = UrlFetchApp.fetch(cfg.apiUrl + '/productos?limit=500', {
      headers: { 'Authorization': 'Bearer ' + cfg.token },
      muteHttpExceptions: true
    });
    if (resp.getResponseCode() !== 200) {
      Logger.log('Productos respondió ' + resp.getResponseCode() + ': ' + resp.getContentText().substring(0, 200));
      return;
    }
  } catch (e) { Logger.log('Error obteniendo productos: ' + e); return; }

  var productos;
  try { productos = JSON.parse(resp.getContentText()); }
  catch (e) { Logger.log('Error parseando JSON: ' + e + ' — Respuesta: ' + resp.getContentText().substring(0, 100)); return; }

  if (!productos || !productos.length) { Logger.log('No hay productos'); return; }

  var now = new Date();
  var actualizados = 0;

  // 3. Crear columna ÚLTIMA ACTUALIZACIÓN si no existe
  if (fechaCol === -1) {
    fechaCol = headers.length;
    sheet.getRange(1, fechaCol + 1).setValue('ÚLTIMA ACTUALIZACIÓN');
  }

  // 4. Recorrer filas y actualizar precios
  for (var i = 1; i < data.length; i++) {
    var url = data[i][urlCol] ? data[i][urlCol].toString().trim() : '';
    if (!url) continue;

    var match = null;
    for (var j = 0; j < productos.length; j++) {
      if (productos[j].url_origen === url) { match = productos[j]; break; }
    }

    if (match) {
      sheet.getRange(i + 1, fechaCol + 1).setValue(now);
      actualizados++;
    }
  }

  Logger.log('Sincronización completa — ' + actualizados + ' filas actualizadas');
}
