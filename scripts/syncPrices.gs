/**
 * ListaMasterInsumos — Google Apps Script
 *
 * Configuración:
 *   1. Abre tu Google Sheet → Extensiones → Apps Script
 *   2. Copia este archivo en el editor
 *   3. Reemplaza API_BASE_URL con la URL de tu app (ej: https://tuapp.onrender.com)
 *   4. Guarda (Ctrl+S) y ejecuta syncPrices() para probar
 *   5. En el editor, ve al reloj ⏰ → Agregar trigger:
 *      - Función: syncPrices
 *      - Tipo: Time-driven → Every hour (o lo que prefieras)
 */

// ─── Config ───────────────────────────────────────────────
var API_BASE_URL = 'https://tuapp.onrender.com';  // ← CAMBIA ESTO
var AUTH_TOKEN   = 'admin123';                     // ← Token de admin

// Columnas esperadas en la hoja (fila 1 = headers)
// A: URL, B: CATEGORIA, C: ÚLTIMO PRECIO, D: ÚLTIMA ACTUALIZACIÓN
var COL_URL   = 1;  // Columna A
var COL_PRECIO = 3; // Columna C — se escribe aquí
var COL_FECHA  = 4; // Columna D — se escribe aquí

// ─── Principal ────────────────────────────────────────────

function syncPrices() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var data  = sheet.getDataRange().getValues();
  if (data.length < 2) { Logger.log('Sin datos'); return; }

  var headers = data[0];
  // Buscar columna URL si no está en A
  var urlCol = headers.findIndex(function(h) { return h.toString().toLowerCase() === 'url'; });
  if (urlCol === -1) urlCol = COL_URL - 1;
  // Buscar o crear columna ÚLTIMO PRECIO
  var precioCol = headers.findIndex(function(h) { return h.toString().toLowerCase().indexOf('ultimo') !== -1 || h.toString().toLowerCase().indexOf('precio') !== -1; });
  if (precioCol === -1) { precioCol = headers.length; sheet.getRange(1, precioCol+1).setValue('ÚLTIMO PRECIO'); }
  // Buscar o crear columna ÚLTIMA ACTUALIZACIÓN
  var fechaCol = headers.findIndex(function(h) { return h.toString().toLowerCase().indexOf('actualizaci') !== -1; });
  if (fechaCol === -1) { fechaCol = headers.length + (precioCol === headers.length ? 1 : 0); sheet.getRange(1, fechaCol+1).setValue('ÚLTIMA ACTUALIZACIÓN'); }
  // Ajustar index si creamos ambas
  if (precioCol === headers.length && fechaCol === headers.length + 1) { /*ok*/ }

  // 1. Disparar scrape diario
  try {
    UrlFetchApp.fetch(API_BASE_URL + '/scrape/daily', {
      method: 'get',
      headers: { 'Authorization': 'Bearer ' + AUTH_TOKEN },
      muteHttpExceptions: true
    });
    Logger.log('Scrape triggered');
  } catch (e) { Logger.log('Scrape error: ' + e); }

  Utilities.sleep(5000); // esperar 5s a que termine

  // 2. Obtener productos actualizados
  var resp;
  try {
    resp = UrlFetchApp.fetch(API_BASE_URL + '/productos?limit=500', {
      headers: { 'Authorization': 'Bearer ' + AUTH_TOKEN },
      muteHttpExceptions: true
    });
  } catch (e) { Logger.log('Fetch productos error: ' + e); return; }

  var productos = JSON.parse(resp.getContentText());
  var now = new Date();

  // 3. Actualizar filas
  for (var i = 1; i < data.length; i++) {
    var url = data[i][urlCol] ? data[i][urlCol].toString().trim() : '';
    if (!url) continue;
    var match = productos.filter(function(p) { return p.url_origen === url; });
    if (match.length) {
      var p = match[0];
      sheet.getRange(i+1, precioCol+1).setValue(p.valor);
      sheet.getRange(i+1, fechaCol+1).setValue(now);
    }
  }

  Logger.log('Sincronización completa: ' + (data.length - 1) + ' filas procesadas');
}

/**
 * Helper: Array.findIndex polyfill
 */
if (!Array.prototype.findIndex) {
  Array.prototype.findIndex = function(pred) {
    for (var i = 0; i < this.length; i++) { if (pred(this[i], i, this)) return i; }
    return -1;
  };
}
