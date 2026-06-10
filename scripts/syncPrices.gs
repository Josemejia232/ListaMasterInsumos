/**
 * ListaMasterInsumos — Google Apps Script (v2 · resiliente)
 *
 * Estrategia:
 *   ① Lee el sheet y detecta URLs NUEVAS (sin ÚLTIMO PRECIO)
 *   ② Solo scrapea las URLs nuevas → llama a /scrape/sync una por una (con pausa)
 *   ③ Para URLs con precio existente → compara con /productos (cacheado, rápido)
 *   ④ Actualiza solo las celdas que cambiaron (batch al final)
 *   ⑤ Sincroniza categorías desde el sheet hacia la BD
 *
 * Seguridad ante caída del scraper:
 *   · Solo escribe precio si valor > 0
 *   · Solo actualiza fecha si el precio realmente cambió
 *   · Respalda precio anterior en col I antes de sobrescribir
 *
 * Configuración:
 *   Celda K1 = URL de la API (ej: https://listamasterinsumos.onrender.com)
 *   Celda K2 = Token de admin
 *
 * Uso:
 *   - Menú "ListaMaster" en la hoja → ejecutar manualmente
 *   - Trigger: Time-driven → cada hora (syncPrices)
 */

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
  // Config principal en col K (antes estaba en I, ahora I = PRECIO ANTERIOR)
  var apiUrl = sheet.getRange('K1').getValue();
  var token  = sheet.getRange('K2').getValue();
  // Fallback: si K vacío, leer de I (solo si I1 parece URL)
  var i1Val = sheet.getRange('I1').getValue();
  if ((!apiUrl || !apiUrl.toString().trim()) && i1Val) {
    var i1Str = i1Val.toString().trim();
    if (i1Str.indexOf('http') === 0) {
      apiUrl = i1Str;
    }
  }
  if (!token || !token.toString().trim()) {
    var i2Val = sheet.getRange('I2').getValue();
    if (i2Val && i2Val.toString().trim()) {
      token = i2Val;
    }
  }
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

  // Col I = PRECIO ANTERIOR (backup)
  // ⚠️ No pisar celdas con contenido que no sea header (ej: config antigua)
  var anteriorCol = 8;
  var i1Content = sheet.getRange(1, anteriorCol + 1).getValue();
  var i1Str = (i1Content && i1Content.toString().trim()) || '';
  if (!i1Str || i1Str.toLowerCase().indexOf('anterior') !== -1) {
    sheet.getRange(1, anteriorCol + 1).setValue('PRECIO ANTERIOR');
    headers[anteriorCol] = 'precio anterior';
  } else if (i1Str.toLowerCase().indexOf('http') === 0) {
    // Es la API URL antigua → no tocar, config sigue en I1
    headers[anteriorCol] = i1Str;
  } else {
    // Otro contenido (ej: token) → no tocar
    headers[anteriorCol] = i1Str;
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
      // ⚠️ Scraper o API caídos → no tocar la hoja
      return;
    }
  } catch (e) {
    // ⚠️ Error de red o API caída → preservar datos
    Logger.log('Error obteniendo productos (API caida?): ' + e);
    return;
  }

  var productos;
  try { productos = JSON.parse(resp.getContentText()); }
  catch (e) { Logger.log('Error parseando JSON (respuesta corrupta?): ' + e); return; }

  if (!productos || !productos.length) { Logger.log('No hay productos (BD vacia?) - preservando hoja'); return; }

  Logger.log('Productos obtenidos: ' + productos.length);

  var now = new Date();
  var actualizados = 0;
  var cambios = 0;
  var backups = 0;
  var batchPrecioUpdates = [];
  var batchAnteriorUpdates = [];
  var batchFechaUpdates = [];
  var batchNombreUpdates = [];

  // ④ Comparar y actualizar
  var matches = 0;
  var sinMatch = 0;
  var preciosInvalidos = 0;

  for (var k = 1; k < data.length; k++) {
    var sUrl = data[k][urlCol] ? data[k][urlCol].toString().trim() : '';
    if (!sUrl) continue;

    // Buscar producto por URL (exacta primero, luego normalizada)
    var match = null;
    for (var m = 0; m < productos.length; m++) {
      var pu = productos[m].url_origen;
      if (pu === sUrl) { match = productos[m]; break; }
    }

    // Fallback: normalizar ambas URLs (sin trailing slash)
    if (!match) {
      var sNorm = sUrl.replace(/\/+$/, '').toLowerCase();
      for (var m = 0; m < productos.length; m++) {
        var pNorm = (productos[m].url_origen || '').replace(/\/+$/, '').toLowerCase();
        if (pNorm === sNorm) { match = productos[m]; break; }
      }
    }

    // Fallback 2: si la URL del sheet contiene la URL de BD o viceversa
    if (!match) {
      for (var m = 0; m < productos.length; m++) {
        var pu = (productos[m].url_origen || '').toLowerCase();
        if (sUrl.toLowerCase().indexOf(pu) !== -1 || pu.indexOf(sUrl.toLowerCase()) !== -1) {
          match = productos[m]; break;
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
      Logger.log('  Precio invalido para ' + sUrl.substring(0, 50) + ': ' + precioDB + ' — preservando hoja');
    } else {
      precioStr = '$' + precioDB.toLocaleString('es-CO');
    }

    var precioOld = data[k][precioCol] ? data[k][precioCol].toString().trim() : '';

    // Si el precio cambió (y es válido)
    if (precioStr && precioOld !== precioStr) {
      // ✅ Backup: guardar precio anterior en col I
      batchAnteriorUpdates.push({
        row: k + 1,
        col: anteriorCol + 1,
        value: precioOld || ''
      });

      // ✅ Escribir nuevo precio en col F
      batchPrecioUpdates.push({
        row: k + 1,
        col: precioCol + 1,
        value: precioStr
      });

      // ✅ Solo actualizar fecha si el precio cambió
      batchFechaUpdates.push({
        row: k + 1,
        col: fechaCol + 1,
        value: now
      });

      cambios++;
      if (precioOld) backups++;
    }

    // Escribir nombre del producto en col B (siempre, es informativo)
    batchNombreUpdates.push({
      row: k + 1,
      col: nombreCol + 1,
      value: match.descripcion || ''
    });

    actualizados++;
  }

  Logger.log('Matches: ' + matches + ', Sin match: ' + sinMatch + ', Precios invalidos: ' + preciosInvalidos);

  // ⑤ Escribir batch
  if (batchAnteriorUpdates.length > 0) {
    for (var b = 0; b < batchAnteriorUpdates.length; b++) {
      var ab = batchAnteriorUpdates[b];
      sheet.getRange(ab.row, ab.col).setValue(ab.value);
    }
    Logger.log('Backups (precio anterior en col I): ' + backups);
  }

  if (batchPrecioUpdates.length > 0) {
    for (var b = 0; b < batchPrecioUpdates.length; b++) {
      var up = batchPrecioUpdates[b];
      sheet.getRange(up.row, up.col).setValue(up.value);
    }
    Logger.log('Precios actualizados: ' + cambios);
  }

  if (batchFechaUpdates.length > 0) {
    for (var d = 0; d < batchFechaUpdates.length; d++) {
      var du = batchFechaUpdates[d];
      sheet.getRange(du.row, du.col).setValue(du.value);
    }
    Logger.log('Fechas actualizadas: ' + batchFechaUpdates.length + ' (solo donde cambió precio)');
  }

  if (batchNombreUpdates.length > 0) {
    for (var n = 0; n < batchNombreUpdates.length; n++) {
      var nu = batchNombreUpdates[n];
      sheet.getRange(nu.row, nu.col).setValue(nu.value);
    }
    Logger.log('Nombres actualizados: ' + batchNombreUpdates.length);
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
      Logger.log('Categorías sincronizadas: ' + catData.actualizados);
    }
  } catch (e) { Logger.log('Sync categorías error: ' + e); }

  Logger.log('Sincronización completa — ' + nuevas.length + ' nuevas, ' + actualizados + ' filas, ' + cambios + ' precios, ' + backups + ' backups');
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
  // ✅ Confirmación antes de scrape masivo
  var ui = SpreadsheetApp.getUi();
  var respuesta = ui.alert(
    '⚠️ Forzar scrape completo',
    'Esto va a re-scrapear TODAS las URLs. Los precios actuales en la hoja se respaldarán en col I antes de sobrescribir.\n\n¿Continuar?',
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
