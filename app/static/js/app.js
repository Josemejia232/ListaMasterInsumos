
window.cambiarLogin = function(modo, el){
  document.querySelectorAll('.login-tab').forEach(t=>t.classList.remove('active'));
  if(el) el.classList.add('active');
  document.getElementById('login-token-section').style.display = modo==='token' ? 'block' : 'none';
  document.getElementById('login-code-section').style.display = modo==='code' ? 'block' : 'none';
  document.getElementById('login-free-section').style.display = modo==='free' ? 'block' : 'none';
  document.getElementById('login-error').textContent = '';
};

const API = '';
let _user = null;
let _editUsrId = null;
let _verProds = [];
let _viewMode = null;
let _debounceTimer = null;
let _freeTierInfo = null;
function _limiteCalcMsg(detail){
  return '<div class="section-card" style="padding:1rem;text-align:center">'+
    '<div style="font-size:1.2rem;margin-bottom:.5rem">🔒</div>'+
    '<div style="font-weight:600;color:var(--text);margin-bottom:.3rem">Limite alcanzado</div>'+
    '<div style="font-size:.82rem;color:var(--muted);margin-bottom:.8rem">'+escapeHtml(detail||'Actualiza a Plus para acceder a la calculadora completa.')+'</div>'+
    '<button class="btn btn-green" onclick="accionPlan()" style="font-size:.8rem">Actualizar a Plus</button></div>';
}

let _calcData = null;
let _calcCache = {};

// Limpiar overrides si la version cambio (evita datos viejos)
(function(){
  var ver = 'v6';
  var stored = localStorage.getItem('ls_overridesVersion');
  if(stored !== ver){
    localStorage.removeItem('ls_materialOverrides');
    // Limpiar todos los keys viejos de overrides
    for(var i=localStorage.length-1; i>=0; i--){
      var k = localStorage.key(i);
      if(k && k.indexOf('ls_overrides_v2_') === 0){
        localStorage.removeItem(k);
      }
    }
    localStorage.setItem('ls_overridesVersion', ver);
  }
})();

function _showLoading(elId){
  const el = document.getElementById(elId);
  if(el) el.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--muted)"><div class="loading-spinner" style="margin:0 auto 1rem;border-top-color:var(--accent)"></div>Cargando...</div>';
}

function debounce(fn, ms){ return function(){ var ctx=this, args=arguments; clearTimeout(_debounceTimer); _debounceTimer=setTimeout(function(){ fn.apply(ctx, args); }, ms); }; }
var filtrarVerDebounced = debounce(function(){ renderVer(); }, 200);

// ─── XSS Protection ───────────────────────────────────
function escapeHtml(s){
  if(!s) return '';
  var d = document.createElement('div');
  d.appendChild(document.createTextNode(String(s)));
  return d.innerHTML;
}

// ─── Auth ──────────────────────────────────────────────
async function login(){
  var email = document.getElementById('login-email').value.trim();
  var token = document.getElementById('login-password').value.trim();
  if(!email || !token){ document.getElementById('login-error').textContent='Completa todos los campos'; return; }
  try {
    var r = await fetch(API+'/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email,token})});
    if(!r.ok){
      var err = await r.json().catch(function(){ return {detail:'Credenciales invalidas'}; });
      document.getElementById('login-error').textContent = err.detail || 'Credenciales invalidas';
      return;
    }
    var u = await r.json();
    _user = u; _viewMode = 'adjusted';
    initApp();
  } catch(e){
    document.getElementById('login-error').textContent = 'Error de conexion';
  }
}

async function solicitarCodigo(){
  var email = document.getElementById('code-email').value.trim();
  if(!email){ document.getElementById('login-error').textContent='Ingresa tu email'; return; }
  try {
    var r = await fetch(API+'/api/auth/send-code', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email})});
    if(!r.ok){
      var err = await r.json().catch(function(){ return {detail:'Error'}; });
      document.getElementById('login-error').textContent = err.detail || 'Error al enviar codigo';
      return;
    }
    document.getElementById('code-step1-inputs').style.display = 'none';
    document.getElementById('code-step2').style.display = 'block';
    document.getElementById('login-error').textContent = '';
  } catch(e){
    document.getElementById('login-error').textContent = 'Error de conexion';
  }
}

async function verificarCodigo(){
  var email = document.getElementById('code-email').value.trim();
  var code = document.getElementById('code-input').value.trim();
  if(!code || code.length < 6){ document.getElementById('login-error').textContent='Ingresa el codigo de 6 digitos'; return; }
  try {
    var r = await fetch(API+'/api/auth/verify-code', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email, code})});
    if(!r.ok){
      var err = await r.json().catch(function(){ return {detail:'Codigo invalido'}; });
      document.getElementById('login-error').textContent = err.detail || 'Codigo invalido';
      return;
    }
    var u = await r.json();
    _user = u; _viewMode = 'adjusted';
    initApp();
  } catch(e){
    document.getElementById('login-error').textContent = 'Error de conexion';
  }
}

async function entrarInvitado(){
  var email = document.getElementById('free-email').value.trim();
  if(!email){ document.getElementById('login-error').textContent='Ingresa tu email'; return; }
  try {
    var r = await fetch(API+'/api/auth/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email:email, token:''})});
    if(!r.ok){
      var err = await r.json().catch(function(){ return {detail:'Error'}; });
      document.getElementById('login-error').textContent = err.detail || 'Error al registrar';
      return;
    }
    var u = await r.json();
    _user = u; _viewMode = 'adjusted';
    initApp();
  } catch(e){
    document.getElementById('login-error').textContent = 'Error de conexion';
  }
}
function initGuest(email){
  document.getElementById('login-wrap').style.display='none';
  document.getElementById('sidebar').style.display='flex';
  document.querySelector('.content').style.display='flex';
  document.getElementById('side-email').textContent = email;
  document.getElementById('whatsapp-btn').style.display = 'none';
  buildSidebar(); cargarVerInsumos();
  irA('ver-insumos', document.querySelector('[data-section="ver-insumos"]'));
}
function logout(){
  _user = null; _viewMode = null;
  localStorage.removeItem('user');
  fetch(API+'/api/auth/logout', {method:'POST', credentials:'include'}).catch(function(){});
  document.getElementById('login-wrap').style.display='flex';
  document.getElementById('sidebar').style.display='none';
  document.querySelector('.content').style.display='none';
  document.getElementById('whatsapp-btn').style.display = '';
}

// ─── Sidebar ───────────────────────────────────────────
function toggleSidebar(){
  document.getElementById('sidebar').classList.toggle('collapsed');
}
function buildSidebar(){
  const isAdmin = _user && _user.tipo === 'admin';
  const items = [];
  if(isAdmin){
    items.push({label:'ADMIN', header:true});
    items.push({id:'usuarios', icon:'&#128101;', text:'Usuarios'});
    items.push({id:'pagos', icon:'&#128179;', text:'Pagos'});
  }
  items.push({id:'mi-token', icon:'&#128273;', text:'Mi Token'});
  items.push({label:'INSUMOS', header:true});
  items.push({id:'ver-insumos', icon:'&#9632;', text:'Insumos', mode:'adjusted'});
  items.push({label:'CÁLCULOS', header:true});
  items.push({id:'insumos-calc', icon:'&#9679;', text:'InsCal'});
  items.push({id:'mezclas', icon:'&#9881;', text:'Mezclas'});
  items.push({id:'mamposteria', icon:'&#9881;', text:'Mamposterías'});
  items.push({id:'anclajes', icon:'&#9881;', text:'Anclajes'});
  items.push({id:'boquilla', icon:'&#9881;', text:'Boquilla'});
  items.push({label:'DRYWALL', submenu:true, children:[
    {id:'yeso', icon:'&#9881;', text:'Muro Yeso DC'},
    {id:'yesouc', icon:'&#9881;', text:'Muro Yeso 1C'},
    {id:'cieloraso', icon:'&#9881;', text:'Cielo Raso'},
  ]});
  items.push({label:'NÓMINA', submenu:true, children:[
    {id:'nomina', icon:'&#9881;', text:'Dashboard'},
  ]});
  const menu = document.getElementById('sidebar-menu');
  menu.innerHTML = items.map(i => {
    if(i.header) return '<div class="menu-label">'+i.label+'</div>';
    if(i.submenu){
      var collapsed = sessionStorage.getItem('submenu_'+i.label) !== 'open';
      var childrenHtml = i.children.map(c => {
        var mode = c.mode ? ' data-mode="'+c.mode+'"' : '';
        return '<div class="menu-item sub-item" data-section="'+c.id+'"'+mode+' onclick="irA(\''+c.id+'\',this)"><span class="ico">'+c.icon+'</span> '+c.text+'</div>';
      }).join('');
      return '<div class="menu-submenu">'+
        '<div class="menu-submenu-header" onclick="toggleSubmenu(this)">'+
          '<span class="ico sub-arrow">'+(collapsed?'&#9654;':'&#9660;')+'</span> '+i.label+
        '</div>'+
        '<div class="menu-submenu-body" style="display:'+(collapsed?'none':'block')+'">'+childrenHtml+'</div>'+
      '</div>';
    }
    var mode = i.mode ? ' data-mode="'+i.mode+'"' : '';
    return '<div class="menu-item" data-section="'+i.id+'"'+mode+' onclick="irA(\''+i.id+'\',this)"><span class="ico">'+i.icon+'</span> '+i.text+'</div>';
  }).join('');
}

function toggleSubmenu(el){
  var body = el.parentElement.querySelector('.menu-submenu-body');
  var arrow = el.querySelector('.sub-arrow');
  if(body.style.display === 'none'){
    body.style.display = 'block';
    arrow.innerHTML = '&#9660;';
    sessionStorage.setItem('submenu_'+el.textContent.trim(), 'open');
  } else {
    body.style.display = 'none';
    arrow.innerHTML = '&#9654;';
    sessionStorage.removeItem('submenu_'+el.textContent.trim());
  }
}

// ─── Navigation ────────────────────────────────────────
function irA(section, el){
  document.querySelectorAll('.menu-item').forEach(m=>m.classList.remove('active'));
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  if(el) el.classList.add('active');
  if(el && el.dataset.mode) _viewMode = el.dataset.mode;
  const sec = document.getElementById('section-'+section);
  if(sec) sec.classList.add('active');
  const titles = {'ver-insumos': 'Insumos', 'usuarios':'Usuarios', 'pagos':'Pagos', 'mi-token':'Mi Token', 'insumos-calc':'InsCal', 'mezclas':'Mezclas', 'mamposteria':'Mamposterías', 'anclajes':'Anclajes Químicos', 'boquilla':'Boquilla', 'yeso':'Muro Doble Cara en Yeso', 'yesouc':'Muro Una Cara en Yeso', 'cieloraso':'Cielo Raso en Lámina de Yeso', 'nomina':'Nómina'};
  document.getElementById('page-title').textContent = titles[section]||'Insumos';
  if(window.innerWidth<=768) document.getElementById('sidebar').classList.add('collapsed');
  if(section==='ver-insumos') cargarVerInsumos();
  if(section==='usuarios') cargarUsuarios();
  if(section==='pagos') cargarPagos();
  if(section==='mi-token') cargarMiToken();
  if(section==='insumos-calc') cargarInsumosCalc();
  if(section==='mezclas') cargarSelectMezclas();
  if(section==='mamposteria') cargarSelectMamposteria();
  if(section==='yeso') cargarParametrosYeso();
  if(section==='yesouc') cargarParametrosYesoUC();
  if(section==='cieloraso') cargarParametrosCR();
  if(section==='nomina') cargarNomina();
}
document.addEventListener('click', function(e){
  const s = document.getElementById('sidebar');
  if(window.innerWidth<=768 && s && !s.contains(e.target) && !e.target.closest('.btn-menu') && !e.target.closest('#btn-menu-toggle')){
    s.classList.add('collapsed');
  }
});

// ─── Init App ──────────────────────────────────────────
function initApp(){
  if(!_user) return;
  document.getElementById('login-wrap').style.display='none';
  document.getElementById('sidebar').style.display='flex';
  document.querySelector('.content').style.display='flex';
  document.getElementById('side-email').textContent = _user.email;
  document.getElementById('whatsapp-btn').style.display = 'none';
  buildSidebar();
  if(_user.tipo === 'admin') cargarUsuarios();
  irA('ver-insumos', document.querySelectorAll('[data-section="ver-insumos"]')[document.querySelectorAll('[data-section="ver-insumos"]').length-1]);
}
(function(){
  var saved = localStorage.getItem('user');
  if(saved){
    try{ _user = JSON.parse(saved); }catch(e){ _user = null; }
    if(_user){
      fetch(API+'/api/auth/me', {credentials:'include'})
        .then(r => { if(r.ok) return r.json().then(u => { _user = u; initApp(); }); logout(); })
        .catch(() => logout());
    } else { logout(); }
  }
  setInterval(() => {
    if(_viewMode && document.visibilityState !== 'hidden'){
      cargarVerInsumos();
      if(_user && _user.tipo==='admin') cargarUsuarios();
    }
  }, 30000);
  document.addEventListener('visibilitychange', function(){
    if(document.visibilityState === 'visible' && _viewMode){ cargarVerInsumos(); }
  });
})();

// ─── Helpers ───────────────────────────────────────────
function precioAjustado(valor, id){
  const seed = ((id * 9301 + 49297) % 233280) / 233280;
  return Math.round(valor * (0.9996 + seed * 0.0002));
}
function diffHtml(p){
  if(p.valor_anterior == null) return '';
  const cambio = p.valor - p.valor_anterior;
  const pct = (cambio / p.valor_anterior * 100);
  if(cambio > 0) return `<span style="color:#e63946;font-size:.75rem;font-weight:600"> ↑ ${pct.toFixed(2)}%</span>`;
  if(cambio < 0) return `<span style="color:#00a878;font-size:.75rem;font-weight:600"> ↓ ${Math.abs(pct).toFixed(2)}%</span>`;
  return '';
}
function descripcionAjustada(desc, id, ajustada){
  if(ajustada) return ajustada;
  const sufijos = [" - A", " *", " +", " /", " v2", ""];
  const idx = ((id * 7919 + 12345) % 233280) % sufijos.length;
  return desc + sufijos[idx];
}
const $auth = () => '';

// ─── Mi Token ──────────────────────────────────────────
async function cargarMiToken(){
  try {
    var r = await apiFetch('/api/auth/mi-token');
    if(!r.ok) return;
    var data = await r.json();
    document.getElementById('mi-token-masked').textContent = 'Token actual: ' + (data.token || '******');
  } catch(e){}
}

async function cambiarMiToken(){
  var nuevo = document.getElementById('mi-token-nuevo').value.trim();
  var msg = document.getElementById('mi-token-msg');
  if(!nuevo || nuevo.length < 6){ msg.textContent = 'Minimo 6 caracteres'; msg.style.color = '#e63946'; return; }
  try {
    var r = await apiFetch('/api/auth/mi-token', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({token: nuevo})});
    if(!r.ok){
      var err = await r.json().catch(function(){ return {detail:'Error'}; });
      msg.textContent = err.detail || 'Error al cambiar token';
      msg.style.color = '#e63946';
      return;
    }
    document.getElementById('mi-token-nuevo').value = '';
    msg.textContent = 'Token actualizado correctamente';
    msg.style.color = 'var(--green)';
    setTimeout(function(){ msg.textContent = ''; }, 3000);
  } catch(e){
    msg.textContent = 'Error de conexion';
    msg.style.color = '#e63946';
  }
}

// ─── Cálculos ──────────────────────────────────────────
const _CONV = {
  "Cemento": { u:"Bolsa", f:50, pf:50 },
  "Arena De peña": { u:"Viaje", f:1.05 },
  "Arena Lavada De Rio": { u:"Viaje", f:1.05 },
  "Arena Lavada De Peña": { u:"Viaje", f:1.05 },
  "Agregado grueso": { u:"Viaje", f:1.05 },
  "Agua": { u:"lt", f:1 },
  "M.O. CUADRILLA AG 1:2": { u:"hc", f:1 },
  "M.O. CUADRILLA AG 0:2": { u:"hc", f:1 },
  "Mezcladora a gasolina 1 1/2 bulto": { u:"hr", f:1 },
  "Bloque #4 (10x20x40)": { u:"und", f:1 },
  "Bloque #5 (10x20x40)": { u:"und", f:1 },
  "Ladrillo tolete (5x10x20)": { u:"und", f:1 },
  "Ladrillo farol (10x20x30)": { u:"und", f:1 },
  "Ladrillo tablete (4x10x20)": { u:"und", f:1 },
  "Mortero de pega": { u:"m³", f:1 },
  "M.O. Mampostería": { u:"m²", f:1 },
  "Arena de Base": { u:"Viaje", f:1.05 },
  "Arena de Sello": { u:"Viaje", f:1.05 },
  "Adhesivo cementicio": { u:"Saco", f:1 },
};

function _convertir(nombre, cantidad){
  const c = _CONV[nombre];
  if(!c) return { und:null, cant:Math.round(cantidad*100)/100, ent:Math.round(cantidad*100)/100 };
  if(c.f<=1) return { und:c.u, cant:Math.round(cantidad*100)/100, ent:Math.round(cantidad*100)/100 };
  const ent = Math.ceil(cantidad / c.f);
  return { und:c.u, cant:Math.round(cantidad*100)/100, ent:ent };
}

function _precioTotal(nombre, cant, vr){
  var c = _CONV[nombre];
  var pf = (c && c.pf) || 1;
  return Math.round((cant / pf) * vr);
}

function recalcularMezcla(el){
  const card = el.closest('.calc-card');
  if(!card) return;
  const rows = card.querySelectorAll('.calc-row');
  let total = 0;
  let prefix = 'mez';
  if(document.getElementById('mamp-card-wrap') && document.getElementById('mamp-card-wrap').contains(card)) prefix = 'mamp';
  rows.forEach((tr,i) => {
    const nom = tr.querySelector('.calc-nom').value;
    const und = tr.querySelector('.calc-und').value;
    const elCant = tr.querySelector('.calc-cant');
    const cant = parseFloat(elCant.value) || 0;
    const vr = parseFloat(tr.querySelector('.calc-vr').value) || 0;
    const vt = _precioTotal(nom, cant, vr);
    total += vt;
    tr.querySelector('.calc-vt').textContent = '$'+Math.round(vt).toLocaleString('es-CO');
    if(_calcData && _calcData.materiales[i]){
      _calcData.materiales[i].nombre = nom;
      _calcData.materiales[i].unidad = und;
      _calcData.materiales[i].cantidad = cant;
      _calcData.materiales[i].vr_unitario = vr;
    }
  });
  card.querySelector('.calc-total').textContent = '$'+Math.round(total).toLocaleString('es-CO');
  _renderVolumen(prefix);
  _saveOverrides(_currentMezclaId);
}

// ─── Insumos Calculos ───────────────────────────────────
async function cargarInsumosCalc(){
  const wrap = document.getElementById('insumos-calc-wrap');
  wrap.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--muted)"><div class="loading-spinner" style="margin:0 auto 1rem;border-top-color:var(--accent)"></div>Cargando...</div>';
  try {
    const r = await apiFetch('/api/calculos/materiales');
    if(!r.ok){ wrap.innerHTML = '<div style="padding:1rem;color:var(--muted)">Error al cargar materiales.</div>'; return; }
    const data = await r.json();
    if(!data.length){ wrap.innerHTML = '<div style="padding:1rem;color:var(--muted)">No hay materiales.</div>'; return; }
    renderInsumosCalc(data);
  } catch(e){}
}

function renderInsumosCalc(materiales){
  const wrap = document.getElementById('insumos-calc-wrap');
  const rows = materiales.map((m, i) => {
    var tipos = (m.tipos||[]).join(', ');
    var nombre = escapeHtml(m.nombre);
    var unidad = escapeHtml(m.unidad);
    return '<tr class="calc-row" data-idx="'+i+'">'+
      '<td style="padding:.3rem .3rem;font-size:.78rem">'+
        '<input class="calc-nom-insumo" type="text" value="'+nombre+'" data-original="'+nombre+'" data-nom="'+nombre+'" style="width:100%;min-width:140px;border:1px solid var(--border);background:#fff;font:inherit;font-size:.78rem;color:inherit;padding:.15rem .4rem;border-radius:3px" onfocus="this.style.borderColor=\'var(--accent)\'" onblur="this.style.borderColor=\'var(--border)\';guardarFilaInsumo(this)">'+
      '</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:center">'+
        '<input class="calc-und-insumo" type="text" value="'+unidad+'" style="width:60px;border:1px solid var(--border);background:#fff;font:inherit;font-size:.78rem;color:inherit;text-align:center;padding:.15rem .3rem;border-radius:3px" onfocus="this.style.borderColor=\'var(--accent)\'" onblur="this.style.borderColor=\'var(--border)\';guardarFilaInsumo(this)">'+
      '</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">'+
        '<input class="calc-vr-insumo" type="number" step="1" value="'+m.vr_unitario+'" style="width:90px;border:1px solid var(--border);background:#fff;font:inherit;font-size:.78rem;color:inherit;text-align:right;padding:.15rem .3rem;border-radius:3px" onfocus="this.style.borderColor=\'var(--accent)\'" onblur="this.style.borderColor=\'var(--border)\';guardarFilaInsumo(this)">'+
      '</td>'+
      '<td style="padding:.3rem .3rem;font-size:.72rem;color:var(--muted);text-align:center">'+
        escapeHtml(tipos)+
      '</td>'+
      '<td style="padding:.3rem .3rem;text-align:center;width:30px">'+
        '<button onclick="eliminarFilaInsumo(this)" style="background:none;border:none;color:#e63946;cursor:pointer;font-size:.82rem;padding:.1rem" title="Eliminar material">✕</button>'+
      '</td>'+
      '</tr>';
  }).join('');
  wrap.innerHTML = '<div class="calc-card section-card" style="padding:0;overflow:hidden">'+
    '<table style="width:100%;border-collapse:collapse">'+
    '<thead><tr>'+
    '<th style="padding:.4rem .5rem;font-size:.75rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border);background:var(--card2)">Material</th>'+
    '<th style="padding:.4rem .3rem;font-size:.75rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border);background:var(--card2)">Unidad</th>'+
    '<th style="padding:.4rem .3rem;font-size:.75rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border);background:var(--card2)">Vr Unit</th>'+
    '<th style="padding:.4rem .3rem;font-size:.75rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border);background:var(--card2)">Aparece en</th>'+
    '<th style="padding:.4rem .3rem;font-size:.75rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border);background:var(--card2);width:30px"></th>'+
    '</tr></thead><tbody>'+rows+'</tbody></table>'+
    '<div style="padding:.5rem;border-top:1px solid var(--border);text-align:center">'+
      '<button onclick="agregarFilaInsumo()" style="background:var(--accent);color:#fff;border:none;border-radius:.3rem;padding:.35rem 1rem;font-family:inherit;font-size:.78rem;font-weight:600;cursor:pointer">+ Agregar material</button>'+
    '</div></div>';
}

async function guardarFilaInsumo(el){
  var tr = el.closest('tr');
  if(!tr) return;
  var nomInput = tr.querySelector('.calc-nom-insumo');
  var undInput = tr.querySelector('.calc-und-insumo');
  var vrInput = tr.querySelector('.calc-vr-insumo');
  var nombre = (nomInput.value||'').trim();
  var unidad = (undInput.value||'').trim();
  var vr = parseFloat(vrInput.value) || 0;
  var original = nomInput.dataset.original;
  if(!nombre) return;
  // Si el nombre cambió, eliminar el override anterior (si existe)
  if(original && original !== nombre){
    try { await apiFetch('/api/calculos/overrides/'+encodeURIComponent(original), {method:'DELETE'}); } catch(e){}
    nomInput.dataset.original = nombre;
  }
  try {
    await apiFetch('/api/calculos/overrides', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify([{nombre: nombre, unidad: unidad, cantidad: 0, vr_unitario: vr}])
    });
    var overrides = {};
    try { overrides = JSON.parse(localStorage.getItem('ls_materialOverrides') || '{}'); } catch(e) {}
    overrides[nombre] = overrides[nombre] || {};
    overrides[nombre].vr_unitario = vr;
    overrides[nombre].unidad = unidad;
    try { localStorage.setItem('ls_materialOverrides', JSON.stringify(overrides)); } catch(e) {}
  } catch(e){}
}

async function eliminarFilaInsumo(btn){
  var tr = btn.closest('tr');
  if(!tr) return;
  var nomInput = tr.querySelector('.calc-nom-insumo');
  var nombre = nomInput ? nomInput.dataset.original : '';
  if(nombre && !confirm('¿Eliminar "'+nombre+'"?')) return;
  if(nombre){
    try {
      await apiFetch('/api/calculos/overrides/'+encodeURIComponent(nombre), {method:'DELETE'});
    } catch(e){}
  }
  tr.remove();
}

async function agregarFilaInsumo(){
  var tbody = document.querySelector('#insumos-calc-wrap table tbody');
  if(!tbody) return;
  var tr = document.createElement('tr');
  tr.className = 'calc-row';
  tr.innerHTML =
    '<td style="padding:.3rem .3rem;font-size:.78rem">'+
      '<input class="calc-nom-insumo" type="text" placeholder="Nuevo material" data-original="" style="width:100%;min-width:140px;border:1px solid var(--accent);background:#fff;font:inherit;font-size:.78rem;color:inherit;padding:.15rem .4rem;border-radius:3px" onfocus="this.style.borderColor=\'var(--accent)\'" onblur="this.style.borderColor=\'var(--border)\';guardarFilaInsumo(this)">'+
    '</td>'+
    '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:center">'+
      '<input class="calc-und-insumo" type="text" value="Unidad" style="width:60px;border:1px solid var(--border);background:#fff;font:inherit;font-size:.78rem;color:inherit;text-align:center;padding:.15rem .3rem;border-radius:3px" onfocus="this.style.borderColor=\'var(--accent)\'" onblur="this.style.borderColor=\'var(--border)\';guardarFilaInsumo(this)">'+
    '</td>'+
    '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">'+
      '<input class="calc-vr-insumo" type="number" step="1" value="0" style="width:90px;border:1px solid var(--border);background:#fff;font:inherit;font-size:.78rem;color:inherit;text-align:right;padding:.15rem .3rem;border-radius:3px" onfocus="this.style.borderColor=\'var(--accent)\'" onblur="this.style.borderColor=\'var(--border)\';guardarFilaInsumo(this)">'+
    '</td>'+
    '<td style="padding:.3rem .3rem;font-size:.72rem;color:var(--muted);text-align:center">personalizado</td>'+
    '<td style="padding:.3rem .3rem;text-align:center;width:30px">'+
      '<button onclick="eliminarFilaInsumo(this)" style="background:none;border:none;color:#e63946;cursor:pointer;font-size:.82rem;padding:.1rem" title="Eliminar material">✕</button>'+
    '</td>';
  tbody.appendChild(tr);
  tr.querySelector('.calc-nom-insumo').focus();
}

async function guardarVrInsumo(el){
  var nombre = el.dataset.nombre;
  var vr = parseFloat(el.value) || 0;
  try {
    await apiFetch('/api/calculos/overrides', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify([{nombre: nombre, unidad: '', cantidad: 0, vr_unitario: vr}])
    });
    var overrides = {};
    try { overrides = JSON.parse(localStorage.getItem('ls_materialOverrides') || '{}'); } catch(e) {}
    overrides[nombre] = overrides[nombre] || {};
    overrides[nombre].vr_unitario = vr;
    try { localStorage.setItem('ls_materialOverrides', JSON.stringify(overrides)); } catch(e) {}
  } catch(e) {}
}



async function cargarSelectMezclas(){
  const tipo = document.getElementById('mez-tipo').value || '';
  if(_calcCache[tipo||'all']){ _renderSelectMezclas(tipo, _calcCache[tipo||'all']); return; }
  const params = [];
  if(tipo) params.push('tipo='+tipo);
  const path = '/api/calculos' + (params.length ? '?'+params.join('&') : '');
  _showLoading('mez-card-wrap');
  try {
    const r = await apiFetch(path);
    if(r.status === 403){ const me = await r.json(); document.getElementById('mez-card-wrap').innerHTML = _limiteCalcMsg(me.detail||'Sin acceso a calculadora.'); return; }
    if(!r.ok) return;
    const data = await r.json();
    _calcCache[tipo||'all'] = data;
    _renderSelectMezclas(tipo, data);
  } catch(e){}
}

function _renderSelectMezclas(tipo, data){
  const sel = document.getElementById('mez-select');
  const current = sel.value;
  sel.innerHTML = '<option value="">Seleccione una mezcla...</option>'+
    data.map(m => '<option value="'+m.id+'">'+escapeHtml(m.nombre)+'</option>').join('');
  if(current && data.some(m => m.id===current)) sel.value = current;
  // No llamar cargarMezcla() automáticamente — el onchange del select ya lo hace cuando el usuario elige
  document.getElementById('mez-card-wrap').innerHTML = '';
  document.getElementById('mez-result-wrap').style.display = 'none';
  _calcData = null;
}

async function cargarMezcla(){
  const id = document.getElementById('mez-select').value;
  const wrap = document.getElementById('mez-card-wrap');
  const rwrap = document.getElementById('mez-result-wrap');
  rwrap.style.display = 'none';
  if(!id){ wrap.innerHTML=''; _calcData=null; return; }
  await _renderCard(id, wrap, rwrap, 'mez');
}

async function cargarSelectMamposteria(){
  const cat = document.getElementById('mamp-cat').value;
  if(_calcCache['mamposteria']){
    const filtered = cat ? _calcCache['mamposteria'].filter(m => m.categoria === cat) : _calcCache['mamposteria'];
    _renderSelectMamposteria(filtered); return;
  }
  _showLoading('mamp-card-wrap');
  try {
    const r = await apiFetch('/api/calculos?tipo=mamposteria');
    if(!r.ok) return;
    const data = await r.json();
    _calcCache['mamposteria'] = data;
    const filtered = cat ? data.filter(m => m.categoria === cat) : data;
    _renderSelectMamposteria(filtered);
  } catch(e){}
}

function _renderSelectMamposteria(data){
  const sel = document.getElementById('mamp-select');
  const current = sel.value;
  sel.innerHTML = '<option value="">Seleccione un tipo de muro...</option>'+
    data.map(m => '<option value="'+m.id+'" data-categoria="'+(m.categoria||'')+'">'+escapeHtml(m.nombre)+'</option>').join('');
  if(current && data.some(m => m.id===current)) sel.value = current;
  // No llamar cargarMamposteria() automáticamente — el onchange del select ya lo hace cuando el usuario elige
  document.getElementById('mamp-card-wrap').innerHTML = '';
  document.getElementById('mamp-result-wrap').style.display = 'none';
  _calcData = null;
}

async function cargarMamposteria(){
  const id = document.getElementById('mamp-select').value;
  const wrap = document.getElementById('mamp-card-wrap');
  const rwrap = document.getElementById('mamp-result-wrap');
  rwrap.style.display = 'none';
  if(!id){ wrap.innerHTML=''; _calcData=null; return; }
  await _renderCard(id, wrap, rwrap, 'mamp');
}

async function _renderCard(id, wrap, rwrap, prefix){
  wrap.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--muted)"><div class="loading-spinner" style="margin:0 auto 1rem;border-top-color:var(--accent)"></div>Cargando...</div>';
  rwrap.style.display = 'none';
  try {
    const r = await apiFetch('/api/calculos/'+id);
    if(r.status === 403){ const e = await r.json(); wrap.innerHTML = _limiteCalcMsg(e.detail||'Sin acceso'); return; }
    if(!r.ok) return;
    const m = await r.json();
    _calcData = m;
    _currentMezclaId = id;
    var overrides = await _loadOverrides(id);
    const matRows = m.materiales.map(mat => {
      var ov = overrides[mat.nombre] || {};
      var nom = ov.nombre || mat.nombre;
      var und = ov.unidad || mat.unidad;
      var cant = ov.cant !== undefined ? ov.cant : mat.cantidad;
      var vr = ov.vr_unitario !== undefined ? ov.vr_unitario : mat.vr_unitario;
      return '<tr class="calc-row">'+
      '<td style="padding:.25rem .4rem;font-size:.76rem"><input class="calc-nom" value="'+escapeHtml(nom)+'" oninput="recalcularMezcla(this)" style="width:100%;border:1px solid transparent;background:transparent;font:inherit;color:inherit;padding:.1rem .2rem;border-radius:3px" onfocus="this.style.borderColor=\'var(--accent)\';this.style.background=\'#fff\'" onblur="this.style.borderColor=\'transparent\';this.style.background=\'transparent\'" title="Editar nombre del material"></td>'+
      '<td style="padding:.25rem .2rem;font-size:.76rem;text-align:center;white-space:nowrap"><input class="calc-und" value="'+escapeHtml(und)+'" oninput="recalcularMezcla(this)" style="width:40px;border:1px solid transparent;background:transparent;font:inherit;color:inherit;text-align:center;padding:.1rem .2rem;border-radius:3px" onfocus="this.style.borderColor=\'var(--accent)\';this.style.background=\'#fff\'" onblur="this.style.borderColor=\'transparent\';this.style.background=\'transparent\'" title="Editar unidad"></td>'+
      '<td style="padding:.25rem .2rem;font-size:.76rem;text-align:right;white-space:nowrap"><input class="calc-cant" type="number" step="0.01" value="'+cant.toFixed(2)+'" oninput="recalcularMezcla(this)" style="width:60px;border:1px solid transparent;background:transparent;font:inherit;color:inherit;text-align:right;padding:.1rem .2rem;border-radius:3px" onfocus="this.style.borderColor=\'var(--accent)\';this.style.background=\'#fff\'" onblur="this.style.borderColor=\'transparent\';this.style.background=\'transparent\'" title="Editar cantidad"></td>'+
      '<td style="padding:.25rem .2rem;font-size:.76rem;text-align:right;white-space:nowrap"><input class="calc-vr" type="number" step="1" value="'+vr+'" oninput="recalcularMezcla(this)" style="width:80px;border:1px solid transparent;background:transparent;font:inherit;color:inherit;text-align:right;padding:.1rem .2rem;border-radius:3px" onfocus="this.style.borderColor=\'var(--accent)\';this.style.background=\'#fff\'" onblur="this.style.borderColor=\'transparent\';this.style.background=\'transparent\'" title="Editar valor unitario"></td>'+
      '<td style="padding:.25rem .2rem;font-size:.76rem;text-align:right;white-space:nowrap;font-weight:600" class="calc-vt">$'+_precioTotal(nom,cant,vr).toLocaleString('es-CO')+'</td></tr>';
    }).join('');
    wrap.innerHTML = '<div class="calc-card section-card" style="padding:0;overflow:hidden">'+
      '<div style="padding:.7rem 1rem;background:var(--card2);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">'+
      '<div><div style="font-weight:600;font-size:.88rem">'+escapeHtml(m.nombre)+'</div>'+
      '<div style="font-size:.76rem;color:var(--muted)">'+escapeHtml(m.proporcion)+(m.resistencia_psi?' &middot; '+m.resistencia_psi+' psi':'')+'</div>'+
      '<div style="font-size:.68rem;color:var(--accent);font-weight:600;margin-top:2px">Personaliza los campos dando clic sobre ellos de acuerdo a tu necesidad</div></div>'+
      '<div style="font-size:1.1rem;font-weight:700;color:var(--accent);white-space:nowrap" class="calc-total">$'+Math.round(m.total).toLocaleString('es-CO')+'</div></div>'+
      '<div style="padding:.2rem .6rem .5rem">'+
      '<table style="width:100%;border-collapse:collapse">'+
      '<colgroup><col style="width:auto"><col style="width:48px"><col style="width:52px"><col style="width:80px"><col style="width:80px"></colgroup><thead><tr>'+
      '<th style="padding:.25rem .4rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border);min-width:140px">Material</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)">Unidad</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Cant</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Vr Unit</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Vr Total</th>'+
      '</tr></thead><tbody>'+matRows+'</tbody></table></div></div>';
    _renderVolumen(prefix);
  } catch(e){}
}

async function _loadOverrides(mezclaId){
  var key = 'ls_overrides_v2_' + (mezclaId || 'global');
  if(_user){
    try {
      const path = mezclaId ? '/api/calculos/overrides?mezcla_id='+encodeURIComponent(mezclaId) : '/api/calculos/overrides';
      const r = await apiFetch(path);
      if(r.ok){
        const data = await r.json();
        var overrides = {};
        data.forEach(function(o){
          overrides[o.nombre] = { nombre: o.nombre, unidad: o.unidad, cant: o.cantidad, vr_unitario: o.vr_unitario };
        });
        try { localStorage.setItem(key, JSON.stringify(overrides)); } catch(e) {}
        return overrides;
      }
    } catch(e) {}
  }
  try { return JSON.parse(localStorage.getItem(key) || '{}'); } catch(e) { return {}; }
}

async function _saveOverrides(mezclaId){
  if(!_calcData || !_calcData.materiales) return;
  var overrides = _calcData.materiales.map(function(mat){
    return { nombre: mat.nombre, mezcla_id: mezclaId || '', unidad: mat.unidad, cantidad: mat.cantidad, vr_unitario: mat.vr_unitario };
  });
  var key = 'ls_overrides_v2_' + (mezclaId || 'global');
  var map = {};
  overrides.forEach(function(o){ map[o.nombre] = o; });
  try { localStorage.setItem(key, JSON.stringify(map)); } catch(e) {}
  if(_user){
    try {
      await apiFetch('/api/calculos/overrides', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(overrides)
      });
    } catch(e) {}
  }
}

function _renderVolumen(prefix){
  const rwrap = document.getElementById(prefix+'-result-wrap');
  const volInput = document.getElementById(prefix+'-vol');
  if(!_calcData || !rwrap || !volInput){ if(rwrap) rwrap.style.display='none'; return; }
  const vol = parseFloat(volInput.value) || 0;
  if(vol <= 0){ rwrap.style.display='none'; return; }
  rwrap.style.display = 'block';
  const unitLabel = prefix==='mamp' ? 'm²' : 'm³';
  const rows = _calcData.materiales.map(mat => {
    const base = mat.cantidad;
    const vr = mat.vr_unitario;
    const scaled = base * vol;
    const conv = _convertir(mat.nombre, scaled);
    const total = _precioTotal(mat.nombre, mat.cantidad, mat.vr_unitario) * vol;
    return '<tr>'+
      '<td style="padding:.3rem .5rem;font-size:.8rem">'+escapeHtml(mat.nombre)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:center">'+escapeHtml(mat.unidad)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">'+Number(scaled).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">'+conv.ent+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:center">'+escapeHtml(conv.und||mat.unidad)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">$'+Number(vr).toLocaleString('es-CO')+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right;font-weight:600">$'+Math.round(total).toLocaleString('es-CO')+'</td></tr>';
  }).join('');
  const gTotal = _calcData.materiales.reduce((s,m) => s + _precioTotal(m.nombre, m.cantidad, m.vr_unitario) * vol, 0);
  // Build summary note
  const skipWords = ['mezcladora', 'agua'];
  const parts = _calcData.materiales.map(mat => {
    const scaled = mat.cantidad * vol;
    const conv = _convertir(mat.nombre, scaled);
    const name = mat.nombre;
    const isLabor = skipWords.some(w => name.toLowerCase().includes(w));
    if(isLabor) return null;
    if(conv.und && conv.und !== mat.unidad) {
      return conv.ent+' '+conv.und+' de '+name;
    }
    return Number(scaled).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+' '+escapeHtml(mat.unidad)+' de '+escapeHtml(name);
  }).filter(Boolean);
  const note = parts.length ? '<div style="padding:.5rem .7rem .6rem;font-size:.8rem;color:var(--text2);border-top:1px solid var(--border);background:var(--card2)"><strong style="display:block;margin-bottom:.3rem">Nota: debes comprar</strong><ul style="margin:0;padding-left:1.2rem;list-style:disc">'+parts.map(p => '<li>'+p+'</li>').join('')+'</ul></div>' : '';
  rwrap.innerHTML = '<div class="calc-card section-card" style="padding:0;overflow:hidden">'+
    '<div style="padding:.6rem 1rem;background:var(--card2);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">'+
    '<div style="font-weight:600;font-size:.85rem">Resultado para <span style="color:var(--accent)">'+Number(vol).toLocaleString('es-CO',{minimumFractionDigits:1,maximumFractionDigits:1})+' '+unitLabel+'</span></div>'+
    '<div style="font-size:1.05rem;font-weight:700;color:var(--accent)">$'+Math.round(gTotal).toLocaleString('es-CO')+'</div></div>'+
    '<div style="padding:.2rem .6rem .5rem">'+
    '<table style="width:100%;border-collapse:collapse">'+
    '<colgroup><col style="width:auto"><col style="width:48px"><col style="width:72px"><col style="width:55px"><col style="width:50px"><col style="width:72px"><col style="width:80px"></colgroup><thead><tr>'+
    '<th style="padding:.25rem .4rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border);min-width:120px">Material</th>'+
    '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)">Und</th>'+
    '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Cant Necesaria</th>'+
    '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Und Enteras</th>'+
    '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)">Tipo Und</th>'+
    '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Vr Unit</th>'+
    '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Total</th>'+
    '</tr></thead><tbody>'+rows+'</tbody></table></div>'+note+'</div>';
}

async function calcularAnclajes(){
  const diam = parseInt(document.getElementById('anc-diam').value) || 0;
  const prof = parseInt(document.getElementById('anc-profundidad').value) || 0;
  const cant = parseInt(document.getElementById('anc-cant').value) || 0;
  const base = document.getElementById('anc-base').value;
  const wrap = document.getElementById('anc-card-wrap');
  const rwrap = document.getElementById('anc-result-wrap');
  rwrap.style.display = 'none';
  if(diam < 4 || prof < 20 || cant < 1){ wrap.innerHTML='<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Verifique los valores ingresados</div>'; return; }
  _showLoading('anc-card-wrap');
  try {
    const r = await apiFetch('/api/calculos/anclajes', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({diametro_mm:diam, profundidad_mm:prof, cantidad:cant, material_base:base})
    });
    if(!r.ok) return;
    const data = await r.json();
    _calcData = data;
    const matRows = data.materiales.map(m =>
      '<tr class="calc-row">'+
      '<td style="padding:.3rem .5rem;font-size:.8rem">'+escapeHtml(m.nombre)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:center">'+escapeHtml(m.unidad)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">'+Number(m.cantidad).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">$'+Number(m.vr_unitario).toLocaleString('es-CO')+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right;font-weight:600">$'+Math.round(m.vr_total).toLocaleString('es-CO')+'</td></tr>'
    ).join('');
    const skipWords = ['M.O.'];
    const parts = data.materiales.map(m => {
      if(skipWords.some(w => m.nombre.includes(w))) return null;
      return Number(m.cantidad).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+' '+escapeHtml(m.unidad)+' de '+escapeHtml(m.nombre);
    }).filter(Boolean);
    const note = '<div style="padding:.5rem .7rem .6rem;font-size:.8rem;color:var(--text2);border-top:1px solid var(--border);background:var(--card2)"><strong style="display:block;margin-bottom:.3rem">Nota: debes comprar</strong><ul style="margin:0;padding-left:1.2rem;list-style:disc">'+parts.map(p => '<li>'+p+'</li>').join('')+'</ul></div>';
    wrap.innerHTML = '<div class="calc-card section-card" style="padding:0;overflow:hidden">'+
    '<div style="padding:.7rem 1rem;background:var(--card2);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">'+
      '<div><div style="font-weight:600;font-size:.85rem">Anclaje Químico ø'+diam+'mm × '+prof+'mm</div>'+
      '<div style="font-size:.76rem;color:var(--muted)">'+cant+' puntos · '+data.volumen_total_cm3.toFixed(1)+' cm³ resina · '+data.tubos_calculados+' tubo(s) 300ml</div></div>'+
      '<div style="font-size:1.05rem;font-weight:700;color:var(--accent);white-space:nowrap">$'+Math.round(data.total).toLocaleString('es-CO')+'</div></div>'+
      '<div style="padding:.2rem .6rem .5rem">'+
      '<table style="width:100%;border-collapse:collapse">'+
      '<colgroup><col style="width:auto"><col style="width:48px"><col style="width:72px"><col style="width:80px"><col style="width:80px"></colgroup><thead><tr>'+
      '<th style="padding:.25rem .4rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border);min-width:120px">Material</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)">Und</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Cant</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Vr Unit</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Total</th>'+
      '</tr></thead><tbody>'+matRows+'</tbody></table></div>'+note+'</div>';
    rwrap.style.display = 'block';
  } catch(e){}
}

async function calcularBoquilla(){
  const formato = document.getElementById('boq-formato').value;
  const ancho = parseInt(document.getElementById('boq-ancho').value) || 0;
  const area = parseFloat(document.getElementById('boq-area').value) || 0;
  const wrap = document.getElementById('boq-card-wrap');
  const rwrap = document.getElementById('boq-result-wrap');
  rwrap.style.display = 'none';
  if(area <= 0){ wrap.innerHTML='<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Ingrese un área válida</div>'; return; }
  _showLoading('boq-card-wrap');
  try {
    const r = await apiFetch('/api/calculos/boquillas', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({formato:formato, ancho_mm:ancho, area_m2:area})
    });
    if(!r.ok) return;
    const data = await r.json();
    _calcData = data;
    const matRows = data.materiales.map(m =>
      '<tr class="calc-row">'+
      '<td style="padding:.3rem .5rem;font-size:.8rem">'+escapeHtml(m.nombre)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:center">'+escapeHtml(m.unidad)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">'+Number(m.cantidad).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">$'+Number(m.vr_unitario).toLocaleString('es-CO')+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right;font-weight:600">$'+Math.round(m.vr_total).toLocaleString('es-CO')+'</td></tr>'
    ).join('');
    const skipWords = ['M.O.'];
    const parts = data.materiales.map(m => {
      if(skipWords.some(w => m.nombre.includes(w))) return null;
      return Number(m.cantidad).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+' '+escapeHtml(m.unidad)+' de '+escapeHtml(m.nombre);
    }).filter(Boolean);
    const note = '<div style="padding:.5rem .7rem .6rem;font-size:.8rem;color:var(--text2);border-top:1px solid var(--border);background:var(--card2)"><strong style="display:block;margin-bottom:.3rem">Nota: debes comprar</strong><ul style="margin:0;padding-left:1.2rem;list-style:disc">'+parts.map(p => '<li>'+p+'</li>').join('')+'</ul></div>';
    wrap.innerHTML = '<div class="calc-card section-card" style="padding:0;overflow:hidden">'+
    '<div style="padding:.7rem 1rem;background:var(--card2);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">'+
      '<div><div style="font-weight:600;font-size:.85rem">Boquilla '+data.formato.replace(/x/g,'×')+' · Junta '+data.ancho_mm+'mm</div>'+
      '<div style="font-size:.76rem;color:var(--muted)">'+data.area_m2+' m² · Factor consumo '+data.factor_consumo+' kg/m² · '+data.kg_totales+' kg totales</div></div>'+
      '<div style="font-size:1.05rem;font-weight:700;color:var(--accent);white-space:nowrap">$'+Math.round(data.total).toLocaleString('es-CO')+'</div></div>'+
      '<div style="padding:.2rem .6rem .5rem">'+
      '<table style="width:100%;border-collapse:collapse">'+
      '<colgroup><col style="width:auto"><col style="width:48px"><col style="width:72px"><col style="width:80px"><col style="width:80px"></colgroup><thead><tr>'+
      '<th style="padding:.25rem .4rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border);min-width:120px">Material</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)">Und</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Cant</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Vr Unit</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Total</th>'+
      '</tr></thead><tbody>'+matRows+'</tbody></table></div>'+note+'</div>';
    rwrap.style.display = 'block';
  } catch(e){}
}

let _yesoParams = null;

async function cargarParametrosYeso(){
  try {
    const r = await apiFetch('/api/calculos/parametros/yeso');
    if(r.ok){
      const data = await r.json();
      _yesoParams = Object.keys(data).length > 0 ? data : null;
    }
  } catch(e){}
}

function llenarModalYeso(){
  const p = _yesoParams || {};
  document.getElementById('yeso-desp').value = p.desp != null ? (p.desp * 100) : 5;
  document.getElementById('yeso-factor-torn').value = p.factor_torn || 30;
  document.getElementById('yeso-kg-masilla').value = p.kg_m2_masilla || 0.5;
  document.getElementById('yeso-n-manos').value = p.n_manos_masilla || 2;
  document.getElementById('yeso-rend').value = p.rendimiento_m2_dia || 12;
  document.getElementById('yeso-op').value = p.n_operarios || 2;
  document.getElementById('yeso-jornal').value = p.jornal || 120000;
  const precios = p.precios || {};
  document.getElementById('yeso-p-lamina').value = precios['Lamina de yeso 1.22x2.44'] || 35000;
  document.getElementById('yeso-p-montante').value = precios['Montante 3.05m'] || 12000;
  document.getElementById('yeso-p-canal').value = precios['Canal 3.05m'] || 10000;
  document.getElementById('yeso-p-tornillo').value = precios['Tornillo punta broca'] || 80;
  document.getElementById('yeso-p-cinta').value = precios['Cinta de papel'] || 8000;
  document.getElementById('yeso-p-masilla').value = precios['Masilla / pasta (bolsa 20kg)'] || 35000;
  document.getElementById('yeso-p-lana').value = precios['Lana mineral (m²)'] || 18000;
  document.getElementById('yeso-p-mo').value = precios['M.O. Drywall'] || 25000;
}

function abrirModalYeso(){
  llenarModalYeso();
  document.getElementById('modal-yeso').style.display = 'flex';
}

function cerrarModalYeso(){
  document.getElementById('modal-yeso').style.display = 'none';
}

async function guardarModalYeso(){
  _yesoParams = {
    desp: parseFloat(document.getElementById('yeso-desp').value) / 100,
    factor_torn: parseInt(document.getElementById('yeso-factor-torn').value) || 30,
    kg_m2_masilla: parseFloat(document.getElementById('yeso-kg-masilla').value) || 0.5,
    n_manos_masilla: parseInt(document.getElementById('yeso-n-manos').value) || 2,
    rendimiento_m2_dia: parseFloat(document.getElementById('yeso-rend').value) || 12,
    n_operarios: parseInt(document.getElementById('yeso-op').value) || 2,
    jornal: parseFloat(document.getElementById('yeso-jornal').value) || 120000,
    precios: {
      'Lamina de yeso 1.22x2.44': parseFloat(document.getElementById('yeso-p-lamina').value) || 35000,
      'Montante 3.05m': parseFloat(document.getElementById('yeso-p-montante').value) || 12000,
      'Canal 3.05m': parseFloat(document.getElementById('yeso-p-canal').value) || 10000,
      'Tornillo punta broca': parseFloat(document.getElementById('yeso-p-tornillo').value) || 80,
      'Cinta de papel': parseFloat(document.getElementById('yeso-p-cinta').value) || 8000,
      'Masilla / pasta (bolsa 20kg)': parseFloat(document.getElementById('yeso-p-masilla').value) || 35000,
      'Lana mineral (m²)': parseFloat(document.getElementById('yeso-p-lana').value) || 18000,
      'M.O. Drywall': parseFloat(document.getElementById('yeso-p-mo').value) || 25000,
    }
  };
  await apiFetch('/api/calculos/parametros/yeso', {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tipo:'yeso', config_json:JSON.stringify(_yesoParams)})
  });
  cerrarModalYeso();
}

async function calcularYeso(){
  const h = parseFloat(document.getElementById('yeso-h').value) || 0;
  const l = parseFloat(document.getElementById('yeso-l').value) || 0;
  const e = parseFloat(document.getElementById('yeso-e').value) || 0.6;
  const conLana = document.getElementById('yeso-lana').checked;
  const wrap = document.getElementById('yeso-card-wrap');
  const rwrap = document.getElementById('yeso-result-wrap');
  rwrap.style.display = 'none';
  if(h <= 0 || l <= 0){ wrap.innerHTML='<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Ingrese altura y longitud</div>'; return; }
  _showLoading('yeso-card-wrap');
  try {
    const body = {h, l, e, con_lana: conLana};
    if(_yesoParams){
      body.desp = _yesoParams.desp;
      body.factor_torn = _yesoParams.factor_torn;
      body.kg_m2_masilla = _yesoParams.kg_m2_masilla;
      body.n_manos_masilla = _yesoParams.n_manos_masilla;
      body.rendimiento_m2_dia = _yesoParams.rendimiento_m2_dia;
      body.n_operarios = _yesoParams.n_operarios;
      body.jornal = _yesoParams.jornal;
      body.precios = _yesoParams.precios;
    }
    const r = await apiFetch('/api/calculos/yeso', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)
    });
    if(!r.ok) return;
    const data = await r.json();
    _calcData = data;
    const matRows = data.materiales.map(m =>
      '<tr class="calc-row">'+
      '<td style="padding:.3rem .5rem;font-size:.8rem">'+escapeHtml(m.nombre)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:center">'+escapeHtml(m.unidad)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">'+Number(m.cantidad).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">$'+Number(m.vr_unitario).toLocaleString('es-CO')+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right;font-weight:600">$'+Math.round(m.vr_total).toLocaleString('es-CO')+'</td></tr>'
    ).join('');
    const skipWords = ['M.O.'];
    const parts = data.materiales.map(m => {
      if(skipWords.some(w => m.nombre.includes(w))) return null;
      return Number(m.cantidad).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+' '+escapeHtml(m.unidad)+' de '+escapeHtml(m.nombre);
    }).filter(Boolean);
    const note = '<div style="padding:.5rem .7rem .6rem;font-size:.8rem;color:var(--text2);border-top:1px solid var(--border);background:var(--card2)"><strong style="display:block;margin-bottom:.3rem">Nota: debes comprar</strong><ul style="margin:0;padding-left:1.2rem;list-style:disc">'+parts.map(p => '<li>'+p+'</li>').join('')+'</ul></div>';
    wrap.innerHTML = '<div class="calc-card section-card" style="padding:0;overflow:hidden">'+
    '<div style="padding:.7rem 1rem;background:var(--card2);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">'+
      '<div><div style="font-weight:600;font-size:.85rem">Muro Yeso DC '+h+'×'+l+'m</div>'+
      '<div style="font-size:.76rem;color:var(--muted)">'+data.area_m2+' m² · Sep. mont. '+data.e+'m'+(data.con_lana ? ' · +Lana mineral' : '')+'</div></div>'+
      '<div style="font-size:1.05rem;font-weight:700;color:var(--accent);white-space:nowrap">$'+Math.round(data.total).toLocaleString('es-CO')+'</div></div>'+
      '<div style="padding:.2rem .6rem .5rem">'+
      '<table style="width:100%;border-collapse:collapse">'+
      '<colgroup><col style="width:auto"><col style="width:48px"><col style="width:72px"><col style="width:80px"><col style="width:80px"></colgroup><thead><tr>'+
      '<th style="padding:.25rem .4rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border);min-width:120px">Material</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)">Und</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Cant</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Vr Unit</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Total</th>'+
      '</tr></thead><tbody>'+matRows+'</tbody></table></div>'+note+'</div>';
    rwrap.style.display = 'block';
  } catch(e){}
}

let _crParams = null;

async function cargarParametrosCR(){
  try {
    const r = await apiFetch('/api/calculos/parametros/cieloraso');
    if(r.ok){
      const data = await r.json();
      _crParams = Object.keys(data).length > 0 ? data : null;
    }
  } catch(e){}
}

function llenarModalCR(){
  const p = _crParams || {};
  document.getElementById('cr-desp').value = p.desp != null ? (p.desp * 100) : 5;
  document.getElementById('cr-sep-vp').value = p.sep_vp || 1.2;
  document.getElementById('cr-sep-vs').value = p.sep_vs || 0.5;
  document.getElementById('cr-sep-colg').value = p.sep_colg || 1.2;
  document.getElementById('cr-h-colg').value = p.h_colg || 0.5;
  document.getElementById('cr-l-varilla').value = p.l_varilla || 3;
  document.getElementById('cr-factor-torn').value = p.factor_torn || 25;
  document.getElementById('cr-kg-masilla').value = p.kg_m2_masilla || 0.5;
  document.getElementById('cr-n-manos').value = p.n_manos_masilla || 2;
  document.getElementById('cr-rend').value = p.rendimiento_m2_dia || 12;
  document.getElementById('cr-op').value = p.n_operarios || 2;
  document.getElementById('cr-jornal').value = p.jornal || 120000;
  const precios = p.precios || {};
  document.getElementById('cr-p-lamina').value = precios['Lamina de yeso 1.22x2.44'] || 35000;
  document.getElementById('cr-p-canal-per').value = precios['Canal perimetral 3.05m'] || 10000;
  document.getElementById('cr-p-vp').value = precios['Viga principal (canal) 3.05m'] || 11000;
  document.getElementById('cr-p-vs').value = precios['Viga secundaria (montante) 3.05m'] || 12000;
  document.getElementById('cr-p-colg').value = precios['Colgador / pendon'] || 1500;
  document.getElementById('cr-p-varilla').value = precios['Varilla roscada 3m'] || 8000;
  document.getElementById('cr-p-tornillo').value = precios['Tornillo punta broca'] || 70;
  document.getElementById('cr-p-cinta').value = precios['Cinta de papel'] || 8000;
  document.getElementById('cr-p-masilla').value = precios['Masilla / pasta (bolsa 20kg)'] || 35000;
  document.getElementById('cr-p-mo').value = precios['M.O. Cielo Raso'] || 25000;
}

function abrirModalCR(){
  llenarModalCR();
  document.getElementById('modal-cr').style.display = 'flex';
}

function cerrarModalCR(){
  document.getElementById('modal-cr').style.display = 'none';
}

async function guardarModalCR(){
  _crParams = {
    desp: parseFloat(document.getElementById('cr-desp').value) / 100,
    sep_vp: parseFloat(document.getElementById('cr-sep-vp').value) || 1.2,
    sep_vs: parseFloat(document.getElementById('cr-sep-vs').value) || 0.5,
    sep_colg: parseFloat(document.getElementById('cr-sep-colg').value) || 1.2,
    h_colg: parseFloat(document.getElementById('cr-h-colg').value) || 0.5,
    l_varilla: parseFloat(document.getElementById('cr-l-varilla').value) || 3,
    factor_torn: parseInt(document.getElementById('cr-factor-torn').value) || 25,
    kg_m2_masilla: parseFloat(document.getElementById('cr-kg-masilla').value) || 0.5,
    n_manos_masilla: parseInt(document.getElementById('cr-n-manos').value) || 2,
    rendimiento_m2_dia: parseFloat(document.getElementById('cr-rend').value) || 12,
    n_operarios: parseInt(document.getElementById('cr-op').value) || 2,
    jornal: parseFloat(document.getElementById('cr-jornal').value) || 120000,
    precios: {
      'Lamina de yeso 1.22x2.44': parseFloat(document.getElementById('cr-p-lamina').value) || 35000,
      'Canal perimetral 3.05m': parseFloat(document.getElementById('cr-p-canal-per').value) || 10000,
      'Viga principal (canal) 3.05m': parseFloat(document.getElementById('cr-p-vp').value) || 11000,
      'Viga secundaria (montante) 3.05m': parseFloat(document.getElementById('cr-p-vs').value) || 12000,
      'Colgador / pendon': parseFloat(document.getElementById('cr-p-colg').value) || 1500,
      'Varilla roscada 3m': parseFloat(document.getElementById('cr-p-varilla').value) || 8000,
      'Tornillo punta broca': parseFloat(document.getElementById('cr-p-tornillo').value) || 70,
      'Cinta de papel': parseFloat(document.getElementById('cr-p-cinta').value) || 8000,
      'Masilla / pasta (bolsa 20kg)': parseFloat(document.getElementById('cr-p-masilla').value) || 35000,
      'M.O. Cielo Raso': parseFloat(document.getElementById('cr-p-mo').value) || 25000,
    }
  };
  await apiFetch('/api/calculos/parametros/cieloraso', {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tipo:'cieloraso', config_json:JSON.stringify(_crParams)})
  });
  cerrarModalCR();
}

async function calcularCieloRaso(){
  const an = parseFloat(document.getElementById('cr-an').value) || 0;
  const la = parseFloat(document.getElementById('cr-la').value) || 0;
  const conVarilla = document.getElementById('cr-varilla').checked;
  const wrap = document.getElementById('cr-card-wrap');
  const rwrap = document.getElementById('cr-result-wrap');
  rwrap.style.display = 'none';
  if(an <= 0 || la <= 0){ wrap.innerHTML='<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Ingrese ancho y largo</div>'; return; }
  _showLoading('cr-card-wrap');
  try {
    const body = {an, la, con_varilla: conVarilla};
    if(_crParams){
      body.desp = _crParams.desp;
      body.sep_vp = _crParams.sep_vp;
      body.sep_vs = _crParams.sep_vs;
      body.sep_colg = _crParams.sep_colg;
      body.h_colg = _crParams.h_colg;
      body.l_varilla = _crParams.l_varilla;
      body.factor_torn = _crParams.factor_torn;
      body.kg_m2_masilla = _crParams.kg_m2_masilla;
      body.n_manos_masilla = _crParams.n_manos_masilla;
      body.rendimiento_m2_dia = _crParams.rendimiento_m2_dia;
      body.n_operarios = _crParams.n_operarios;
      body.jornal = _crParams.jornal;
      body.precios = _crParams.precios;
    }
    const r = await apiFetch('/api/calculos/cielo-raso', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)
    });
    if(!r.ok) return;
    const data = await r.json();
    _calcData = data;
    const matRows = data.materiales.map(m =>
      '<tr class="calc-row">'+
      '<td style="padding:.3rem .5rem;font-size:.8rem">'+escapeHtml(m.nombre)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:center">'+escapeHtml(m.unidad)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">'+Number(m.cantidad).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">$'+Number(m.vr_unitario).toLocaleString('es-CO')+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right;font-weight:600">$'+Math.round(m.vr_total).toLocaleString('es-CO')+'</td></tr>'
    ).join('');
    const skipWords = ['M.O.'];
    const parts = data.materiales.map(m => {
      if(skipWords.some(w => m.nombre.includes(w))) return null;
      return Number(m.cantidad).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+' '+escapeHtml(m.unidad)+' de '+escapeHtml(m.nombre);
    }).filter(Boolean);
    const note = '<div style="padding:.5rem .7rem .6rem;font-size:.8rem;color:var(--text2);border-top:1px solid var(--border);background:var(--card2)"><strong style="display:block;margin-bottom:.3rem">Nota: debes comprar</strong><ul style="margin:0;padding-left:1.2rem;list-style:disc">'+parts.map(p => '<li>'+p+'</li>').join('')+'</ul></div>';
    wrap.innerHTML = '<div class="calc-card section-card" style="padding:0;overflow:hidden">'+
    '<div style="padding:.7rem 1rem;background:var(--card2);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">'+
      '<div><div style="font-weight:600;font-size:.85rem">Cielo Raso '+an+'×'+la+'m</div>'+
      '<div style="font-size:.76rem;color:var(--muted)">'+data.area_m2+' m² · Perímetro '+data.perimetro_ml+'ml'+(conVarilla ? ' · +Varilla' : '')+'</div></div>'+
      '<div style="font-size:1.05rem;font-weight:700;color:var(--accent);white-space:nowrap">$'+Math.round(data.total).toLocaleString('es-CO')+'</div></div>'+
      '<div style="padding:.2rem .6rem .5rem">'+
      '<table style="width:100%;border-collapse:collapse">'+
      '<colgroup><col style="width:auto"><col style="width:48px"><col style="width:72px"><col style="width:80px"><col style="width:80px"></colgroup><thead><tr>'+
      '<th style="padding:.25rem .4rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border);min-width:120px">Material</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)">Und</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Cant</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Vr Unit</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Total</th>'+
      '</tr></thead><tbody>'+matRows+'</tbody></table></div>'+note+'</div>';
    rwrap.style.display = 'block';
  } catch(e){}
}

let _yesoUCParams = null;

async function cargarParametrosYesoUC(){
  try {
    const r = await apiFetch('/api/calculos/parametros/yesouc');
    if(r.ok){
      const data = await r.json();
      _yesoUCParams = Object.keys(data).length > 0 ? data : null;
    }
  } catch(e){}
}

function llenarModalYesoUC(){
  const p = _yesoUCParams || {};
  document.getElementById('yesouc-desp').value = p.desp != null ? (p.desp * 100) : 5;
  document.getElementById('yesouc-factor-torn').value = p.factor_torn || 15;
  document.getElementById('yesouc-kg-masilla').value = p.kg_m2_masilla || 0.5;
  document.getElementById('yesouc-n-manos').value = p.n_manos_masilla || 2;
  document.getElementById('yesouc-rend').value = p.rendimiento_m2_dia || 12;
  document.getElementById('yesouc-op').value = p.n_operarios || 2;
  document.getElementById('yesouc-jornal').value = p.jornal || 120000;
  const precios = p.precios || {};
  document.getElementById('yesouc-p-lamina').value = precios['Lamina de yeso 1.22x2.44'] || 35000;
  document.getElementById('yesouc-p-montante').value = precios['Montante 3.05m'] || 12000;
  document.getElementById('yesouc-p-canal').value = precios['Canal 3.05m'] || 10000;
  document.getElementById('yesouc-p-tornillo').value = precios['Tornillo punta broca'] || 80;
  document.getElementById('yesouc-p-cinta').value = precios['Cinta de papel'] || 8000;
  document.getElementById('yesouc-p-masilla').value = precios['Masilla / pasta (bolsa 20kg)'] || 35000;
  document.getElementById('yesouc-p-mo').value = precios['M.O. Drywall'] || 25000;
}

function abrirModalYesoUC(){
  llenarModalYesoUC();
  document.getElementById('modal-yesouc').style.display = 'flex';
}

function cerrarModalYesoUC(){
  document.getElementById('modal-yesouc').style.display = 'none';
}

async function guardarModalYesoUC(){
  _yesoUCParams = {
    desp: parseFloat(document.getElementById('yesouc-desp').value) / 100,
    factor_torn: parseInt(document.getElementById('yesouc-factor-torn').value) || 15,
    kg_m2_masilla: parseFloat(document.getElementById('yesouc-kg-masilla').value) || 0.5,
    n_manos_masilla: parseInt(document.getElementById('yesouc-n-manos').value) || 2,
    rendimiento_m2_dia: parseFloat(document.getElementById('yesouc-rend').value) || 12,
    n_operarios: parseInt(document.getElementById('yesouc-op').value) || 2,
    jornal: parseFloat(document.getElementById('yesouc-jornal').value) || 120000,
    precios: {
      'Lamina de yeso 1.22x2.44': parseFloat(document.getElementById('yesouc-p-lamina').value) || 35000,
      'Montante 3.05m': parseFloat(document.getElementById('yesouc-p-montante').value) || 12000,
      'Canal 3.05m': parseFloat(document.getElementById('yesouc-p-canal').value) || 10000,
      'Tornillo punta broca': parseFloat(document.getElementById('yesouc-p-tornillo').value) || 80,
      'Cinta de papel': parseFloat(document.getElementById('yesouc-p-cinta').value) || 8000,
      'Masilla / pasta (bolsa 20kg)': parseFloat(document.getElementById('yesouc-p-masilla').value) || 35000,
      'M.O. Drywall': parseFloat(document.getElementById('yesouc-p-mo').value) || 25000,
    }
  };
  await apiFetch('/api/calculos/parametros/yesouc', {
    method:'PUT',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({tipo:'yesouc', config_json:JSON.stringify(_yesoUCParams)})
  });
  cerrarModalYesoUC();
}

async function calcularYesoUnaCara(){
  const h = parseFloat(document.getElementById('yesouc-h').value) || 0;
  const l = parseFloat(document.getElementById('yesouc-l').value) || 0;
  const e = parseFloat(document.getElementById('yesouc-e').value) || 0.6;
  const wrap = document.getElementById('yesouc-card-wrap');
  const rwrap = document.getElementById('yesouc-result-wrap');
  rwrap.style.display = 'none';
  if(h <= 0 || l <= 0){ wrap.innerHTML='<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Ingrese altura y longitud</div>'; return; }
  _showLoading('yesouc-card-wrap');
  try {
    const body = {h, l, e};
    if(_yesoUCParams){
      body.desp = _yesoUCParams.desp;
      body.factor_torn = _yesoUCParams.factor_torn;
      body.kg_m2_masilla = _yesoUCParams.kg_m2_masilla;
      body.n_manos_masilla = _yesoUCParams.n_manos_masilla;
      body.rendimiento_m2_dia = _yesoUCParams.rendimiento_m2_dia;
      body.n_operarios = _yesoUCParams.n_operarios;
      body.jornal = _yesoUCParams.jornal;
      body.precios = _yesoUCParams.precios;
    }
    const r = await apiFetch('/api/calculos/yeso/una-cara', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)
    });
    if(!r.ok) return;
    const data = await r.json();
    _calcData = data;
    const matRows = data.materiales.map(m =>
      '<tr class="calc-row">'+
      '<td style="padding:.3rem .5rem;font-size:.8rem">'+escapeHtml(m.nombre)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:center">'+escapeHtml(m.unidad)+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">'+Number(m.cantidad).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right">$'+Number(m.vr_unitario).toLocaleString('es-CO')+'</td>'+
      '<td style="padding:.3rem .3rem;font-size:.78rem;text-align:right;font-weight:600">$'+Math.round(m.vr_total).toLocaleString('es-CO')+'</td></tr>'
    ).join('');
    const skipWords = ['M.O.'];
    const parts = data.materiales.map(m => {
      if(skipWords.some(w => m.nombre.includes(w))) return null;
      return Number(m.cantidad).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+' '+escapeHtml(m.unidad)+' de '+escapeHtml(m.nombre);
    }).filter(Boolean);
    const note = '<div style="padding:.5rem .7rem .6rem;font-size:.8rem;color:var(--text2);border-top:1px solid var(--border);background:var(--card2)"><strong style="display:block;margin-bottom:.3rem">Nota: debes comprar</strong><ul style="margin:0;padding-left:1.2rem;list-style:disc">'+parts.map(p => '<li>'+p+'</li>').join('')+'</ul></div>';
    wrap.innerHTML = '<div class="calc-card section-card" style="padding:0;overflow:hidden">'+
    '<div style="padding:.7rem 1rem;background:var(--card2);border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">'+
      '<div><div style="font-weight:600;font-size:.85rem">Muro Yeso 1C '+h+'×'+l+'m</div>'+
      '<div style="font-size:.76rem;color:var(--muted)">'+data.area_m2+' m² · Sep. mont. '+data.e+'m</div></div>'+
      '<div style="font-size:1.05rem;font-weight:700;color:var(--accent);white-space:nowrap">$'+Math.round(data.total).toLocaleString('es-CO')+'</div></div>'+
      '<div style="padding:.2rem .6rem .5rem">'+
      '<table style="width:100%;border-collapse:collapse">'+
      '<colgroup><col style="width:auto"><col style="width:48px"><col style="width:72px"><col style="width:80px"><col style="width:80px"></colgroup><thead><tr>'+
      '<th style="padding:.25rem .4rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border);min-width:120px">Material</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)">Und</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Cant</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Vr Unit</th>'+
      '<th style="padding:.25rem .2rem;font-size:.72rem;text-align:right;color:var(--muted);border-bottom:1px solid var(--border)">Total</th>'+
      '</tr></thead><tbody>'+matRows+'</tbody></table></div>'+note+'</div>';
    rwrap.style.display = 'block';
  } catch(e){}
}

// ─── NÓMINA ────────────────────────────────────────────
function cambiarTabNomina(tab, el){
  document.querySelectorAll('.nomina-tab').forEach(t=>{
    t.style.background = 'var(--card2)';
    t.style.color = 'var(--text)';
    t.style.border = '1px solid var(--border)';
    t.classList.remove('active');
  });
  if(el){
    el.style.background = 'var(--accent)';
    el.style.color = '#fff';
    el.style.border = 'none';
    el.classList.add('active');
  }
  _renderTabNomina(tab);
}

async function cargarNomina(){
  _renderTabNomina('proyecto');
}

async function _renderTabNomina(tab){
  const content = document.getElementById('nomina-content');
  content.innerHTML = '<div style="padding:2rem;text-align:center;color:var(--muted)"><div class="loading-spinner" style="margin:0 auto 1rem;border-top-color:var(--accent)"></div>Cargando...</div>';
  switch(tab){
    case 'proyecto': await _renderProyecto(content); break;
    case 'persona': await _renderPersona(content); break;
    case 'vinculacion': await _renderVinculacion(content); break;
    case 'quincena': await _renderQuincena(content); break;
    case 'prestamo': await _renderPrestamo(content); break;
    case 'abono': await _renderAbono(content); break;
  }
}

async function _apiNomina(path, opts){
  opts = opts || {};
  opts.headers = opts.headers || {};
  opts.headers['Content-Type'] = 'application/json';
  opts.credentials = 'include';
  const r = await fetch('/api/nomina'+path, opts);
  if(r.status === 401){ logout(); throw new Error('Sesion expirada'); }
  return r;
}

// ─── Proyecto ────────────────────────────────
async function _renderProyecto(content){
  try {
    const [proyectos, usos] = await Promise.all([
      _apiNomina('/proyectos').then(r=>r.ok?r.json():[]),
      _apiNomina('/usos-proyecto').then(r=>r.ok?r.json():[]),
    ]);
    const usoOpts = usos.map(u => `<option value="${u.id_uso}">${escapeHtml(u.descripcion)}</option>`).join('');
    const btnUso = '<button type="button" onclick="abrirModalUso()" style="background:var(--accent);color:#fff;border:none;border-radius:.35rem;padding:0 .55rem;font-size:1.1rem;font-weight:700;cursor:pointer;line-height:1" title="Crear nuevo uso">+</button>';
    content.innerHTML = _nomFormTable({
      title:'Proyectos', singular:'proyecto',
      fields:[
        {key:'nombre',label:'Nombre'},
        {key:'direccion',label:'Dirección'},
        {key:'responsable',label:'Responsable'},
        {key:'id_uso',label:'Uso',type:'select',options:usoOpts,suffixHtml:btnUso},
      ],
      data:proyectos, idKey:'id_proyecto',
      onSave: async (body) => { await _apiNomina('/proyectos', {method:'POST',body:JSON.stringify(body)}); await _renderTabNomina('proyecto'); },
      onDelete: async (id) => { await _apiNomina('/proyectos/'+id, {method:'DELETE'}); await _renderTabNomina('proyecto'); },
    });
  } catch(e){ content.innerHTML = '<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Error al cargar</div>'; }
}

// ─── Persona ─────────────────────────────────
async function _renderPersona(content){
  try {
    const [personas, epsList, afpList] = await Promise.all([
      _apiNomina('/personas').then(r=>r.ok?r.json():[]),
      _apiNomina('/eps').then(r=>r.ok?r.json():[]),
      _apiNomina('/afp').then(r=>r.ok?r.json():[]),
    ]);
    const epsOpts = '<option value="">--</option>'+epsList.map(e => `<option value="${e.id_eps}">${escapeHtml(e.nombre_eps)}</option>`).join('');
    const afpOpts = '<option value="">--</option>'+afpList.map(a => `<option value="${a.id_afp}">${escapeHtml(a.nombre_afp)}</option>`).join('');
    const cargoBtn = '<div style="margin-bottom:.5rem"><button onclick="abrirModalCargo()" style="background:none;border:1.5px solid var(--border);border-radius:.4rem;padding:.3rem .6rem;font-size:.75rem;cursor:pointer;color:var(--text2)">⚙️ Gestionar Cargos</button></div>';
    content.innerHTML = cargoBtn + _nomFormTable({
      title:'Personas', singular:'persona',
      fields:[
        {key:'nombre',label:'Nombre'},
        {key:'celular',label:'Celular'},
        {key:'cedula',label:'Cédula',type:'number'},
        {key:'fecha_expedicion',label:'F. Expedición',type:'date'},
        {key:'id_eps',label:'EPS',type:'select',options:epsOpts,suffixHtml:'<button type="button" onclick="abrirModalEps()" style="background:var(--accent);color:#fff;border:none;border-radius:.35rem;padding:0 .55rem;font-size:1.1rem;font-weight:700;cursor:pointer;line-height:1" title="Administrar EPS">+</button>'},
        {key:'id_afp',label:'AFP',type:'select',options:afpOpts,suffixHtml:'<button type="button" onclick="abrirModalAfp()" style="background:var(--accent);color:#fff;border:none;border-radius:.35rem;padding:0 .55rem;font-size:1.1rem;font-weight:700;cursor:pointer;line-height:1" title="Administrar AFP">+</button>'},
      ],
      data:personas, idKey:'cedula',
    });
  } catch(e){ content.innerHTML = '<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Error</div>'; }
}

// ─── Vinculacion ─────────────────────────────
async function _renderVinculacion(content){
  try {
    const [vinculaciones, personas, proyectos, cargos] = await Promise.all([
      _apiNomina('/vinculaciones').then(r=>r.ok?r.json():[]),
      _apiNomina('/personas').then(r=>r.ok?r.json():[]),
      _apiNomina('/proyectos').then(r=>r.ok?r.json():[]),
      _apiNomina('/cargos').then(r=>r.ok?r.json():[]),
    ]);
    const cedOpts = personas.map(p => `<option value="${p.cedula}">${escapeHtml(p.nombre)} (${p.cedula})</option>`).join('');
    const proyOpts = proyectos.map(p => `<option value="${p.id_proyecto}">${escapeHtml(p.nombre)}</option>`).join('');
    const cargOpts = cargos.map(c => `<option value="${c.id_cargo}">${escapeHtml(c.descripcion)}</option>`).join('');
    content.innerHTML = _nomFormTable({
      title:'Vinculaciones (Persona ↔ Proyecto)', singular:'vinculación',
      fields:[
        {key:'cedula',label:'Persona',type:'select',options:cedOpts},
        {key:'id_cargo',label:'Cargo',type:'select',options:cargOpts},
        {key:'salario_quincenal',label:'Salario Q',type:'number'},
        {key:'fecha_ingreso',label:'F. Ingreso',type:'date'},
        {key:'fecha_retiro',label:'F. Retiro',type:'date'},
        {key:'id_proyecto',label:'Proyecto',type:'select',options:proyOpts},
        {key:'estado',label:'Estado',type:'select',options:'<option value="Activo">Activo</option><option value="Retirado">Retirado</option>'},
      ],
      data:vinculaciones, idKey:'id_vinculacion',
    });
  } catch(e){ content.innerHTML = '<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Error</div>'; }
}

// ─── Quincena ────────────────────────────────
async function _renderQuincena(content){
  try {
    const [quincenas, vinculaciones] = await Promise.all([
      _apiNomina('/quincenas').then(r=>r.ok?r.json():[]),
      _apiNomina('/vinculaciones').then(r=>r.ok?r.json():[]),
    ]);
    const vincOpts = vinculaciones.map(v => `<option value="${v.id_vinculacion}">${escapeHtml(v.persona_nombre||'')} - ${escapeHtml(v.proyecto_nombre||'')}</option>`).join('');
    content.innerHTML = _nomFormTable({
      title:'Quincenas', singular:'quincena',
      fields:[
        {key:'id_vinculacion',label:'Vinculación',type:'select',options:vincOpts},
        {key:'numero_quincena',label:'N° Quincena',type:'number'},
        {key:'fecha_pago',label:'F. Pago',type:'date'},
        {key:'valor_bruto',label:'Bruto',type:'number'},
        {key:'desc_abono',label:'Desc. Abono',type:'number'},
        {key:'desc_seguro',label:'Desc. Seguro',type:'number'},
      ],
      data:quincenas, idKey:'id_quincena',
      extraHeaders:['Neto'],
      extraCols: d => '<td style="font-size:.78rem;text-align:right;font-weight:600">$'+Number(d.valor_neto).toLocaleString('es-CO')+'</td>',
    });
  } catch(e){ content.innerHTML = '<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Error</div>'; }
}

// ─── Prestamo ────────────────────────────────
async function _renderPrestamo(content){
  try {
    const [prestamos, vinculaciones] = await Promise.all([
      _apiNomina('/prestamos').then(r=>r.ok?r.json():[]),
      _apiNomina('/vinculaciones').then(r=>r.ok?r.json():[]),
    ]);
    const vincOpts = vinculaciones.map(v => `<option value="${v.id_vinculacion}">${escapeHtml(v.persona_nombre||'')} - ${escapeHtml(v.proyecto_nombre||'')}</option>`).join('');
    content.innerHTML = _nomFormTable({
      title:'Préstamos', singular:'préstamo',
      fields:[
        {key:'id_vinculacion',label:'Vinculación',type:'select',options:vincOpts},
        {key:'fecha_prestamo',label:'F. Préstamo',type:'date'},
        {key:'valor',label:'Valor',type:'number'},
      ],
      data:prestamos, idKey:'id_prestamo',
      extraHeaders:['Saldo'],
      extraCols: d => '<td style="font-size:.78rem;text-align:right;font-weight:600">$'+Number(d.saldo).toLocaleString('es-CO')+'</td>',
    });
  } catch(e){ content.innerHTML = '<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Error</div>'; }
}

// ─── Abono ───────────────────────────────────
async function _renderAbono(content){
  try {
    const [abonos, prestamos] = await Promise.all([
      _apiNomina('/abonos').then(r=>r.ok?r.json():[]),
      _apiNomina('/prestamos').then(r=>r.ok?r.json():[]),
    ]);
    const presOpts = prestamos.map(p => `<option value="${p.id_prestamo}">#${p.id_prestamo} - ${escapeHtml(p.vinculacion_info||'')} (saldo: $${Number(p.saldo).toLocaleString('es-CO')})</option>`).join('');
    content.innerHTML = _nomFormTable({
      title:'Abonos a Préstamos', singular:'abono',
      fields:[
        {key:'id_prestamo',label:'Préstamo',type:'select',options:presOpts},
        {key:'fecha_abono',label:'F. Abono',type:'date'},
        {key:'valor_abono',label:'Valor',type:'number'},
      ],
      data:abonos, idKey:'id_abono',
    });
  } catch(e){ content.innerHTML = '<div class="section-card" style="padding:1rem;text-align:center;color:var(--muted)">Error</div>'; }
}

// ─── Helper: form + table generator ──────────
function _nomFormTable({title, singular, fields, data, idKey, onSave, onDelete, extraHeaders, extraCols}){
  const tableFields = fields.filter(f => !f.noTable);
  const cols = tableFields.map(f => `<th style="padding:.3rem .3rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border)">${escapeHtml(f.label)}</th>`).join('');
  const extraH = extraHeaders ? extraHeaders.map(h => `<th style="padding:.3rem .3rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border)">${escapeHtml(h)}</th>`).join('') : '';
  const rows = data.map(d => {
    const id = d[idKey];
    const valCols = tableFields.map(f => {
      const v = d[f.key];
      const display = _nomCellDisplay(f, v);
      return `<td class="nom-cell" data-key="${f.key}" data-type="${f.type||'text'}" data-orig="${escapeHtml(v != null ? String(v) : '')}" data-display="${escapeHtml(display)}">${display}</td>`;
    }).join('');
    const extra = extraCols ? extraCols(d) : '';
    return `<tr data-id="${id}">${valCols}${extra}<td style="text-align:center;white-space:nowrap">`+
      `<button class="nom-btn-edit" onclick="_nomInlineEdit(this, ${id})" style="background:none;border:none;color:var(--accent);cursor:pointer;font-size:.82rem;padding:.1rem .25rem" title="Editar">✏️</button>`+
      `<button class="nom-btn-del" onclick="if(confirm('Eliminar ${singular}?')){ _nomDel(${id}) }" style="background:none;border:none;color:#e63946;cursor:pointer;font-size:.82rem;padding:.1rem .25rem" title="Eliminar">✕</button></td></tr>`;
  }).join('');

  return `<div class="section-card" style="padding:1rem">
    <div style="display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;margin-bottom:.8rem">
      <h3 style="margin:0;flex:1;font-size:.95rem">${title}</h3>
      <button onclick="_nomInlineAdd(this)" data-fields='${escapeHtml(JSON.stringify(fields))}' data-singular="${escapeHtml(singular)}" data-idkey="${escapeHtml(idKey)}" style="background:var(--accent);color:#fff;border:none;border-radius:.4rem;padding:.35rem .85rem;font-size:.8rem;font-weight:600;cursor:pointer">+ Agregar ${singular}</button>
    </div>
    <div class="table-wrap" style="max-height:400px;overflow-y:auto">
      <table style="width:100%;border-collapse:collapse">
        <thead><tr>${cols}${extraH}<th style="padding:.3rem .3rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border);width:70px"></th></tr></thead>
        <tbody>${rows||'<tr><td colspan="99" style="padding:1rem;text-align:center;color:var(--muted);font-size:.8rem">Sin registros</td></tr>'}</tbody>
      </table>
    </div>
  </div>`;
}

function _nomCellDisplay(f, v){
  if(f.type === 'select'){
    const re = new RegExp('value="(' + String(v ?? '') + ')"[^>]*>([^<]+)');
    const m = (f.options || '').match(re);
    return escapeHtml(m ? m[2] : (v != null ? '# ' + v : ''));
  }
  if(/^(valor|saldo|desc_|salario)/.test(f.key))
    return '$'+(v != null ? Number(v).toLocaleString('es-CO') : '0');
  if(f.type === 'date' && v) return v;
  return escapeHtml(v != null ? String(v) : '');
}

function _nomMakeInput(f, val){
  const id = 'nom-'+f.key;
  const sv = val != null ? String(val) : '';
  if(f.type === 'select'){
    const suffix = f.suffixHtml || '';
    return `<div style="display:flex;gap:.2rem;align-items:stretch"><select id="${id}" style="flex:1;min-width:60px;padding:.2rem .3rem;border:1px solid var(--accent);border-radius:.3rem;font-size:.75rem;background:#fff;color:#000">${f.options}</select>${suffix}</div>`;
  }
  const typeAttr = `type="${f.type||'text'}"`;
  const stepAttr = f.type === 'number' ? 'step="0.01"' : '';
  return `<input ${typeAttr} ${stepAttr} id="${id}" value="${escapeHtml(sv)}" style="width:100%;min-width:50px;padding:.2rem .3rem;border:1px solid var(--accent);border-radius:.3rem;font-size:.75rem;background:#fff;color:#000">`;
}

const _NOM_ENDPOINTS = {proyecto:'proyectos', persona:'personas', vinculacion:'vinculaciones', quincena:'quincenas', prestamo:'prestamos', abono:'abonos'};

function _nomGetFields(btn){
  const card = btn ? btn.closest('.section-card') : null;
  if(!card) return null;
  const addBtn = card.querySelector('[data-fields]');
  if(!addBtn) return null;
  try { return {fields: JSON.parse(addBtn.dataset.fields), singular: addBtn.dataset.singular, idKey: addBtn.dataset.idkey}; }
  catch(e){ return null; }
}

async function _nomInlineEdit(btn, id){
  const tr = btn.closest('tr');
  if(!tr) return;
  const card = tr.closest('.section-card');
  if(!card) return;
  const info = _nomGetFields(btn);
  if(!info) return;
  const fields = info.fields;
  const ep = _NOM_ENDPOINTS[document.querySelector('.nomina-tab.active')?.dataset.tab];
  if(!ep) return;
  let data;
  try {
    const r = await _apiNomina('/'+ep+'/'+id);
    if(!r.ok) return;
    data = await r.json();
  } catch(e){ return; }
  tr.querySelectorAll('.nom-cell').forEach(td => {
    const key = td.dataset.key;
    const f = fields.find(fi => fi.key === key);
    if(!f) return;
    const v = data[key];
    td.innerHTML = _nomMakeInput(f, v);
  });
  fields.forEach(f => {
    if(f.noTable && !tr.querySelector('#nom-'+f.key)){
      const inp = document.createElement('input');
      inp.type = 'hidden';
      inp.id = 'nom-'+f.key;
      inp.value = data[f.key] != null ? String(data[f.key]) : '';
      tr.appendChild(inp);
    }
  });
  const actionTd = tr.querySelector('td:last-child');
  if(actionTd){
    actionTd.innerHTML =
      `<button onclick="_nomInlineSave(this, ${id})" style="background:var(--accent);color:#fff;border:none;border-radius:.3rem;padding:.15rem .45rem;font-size:.75rem;font-weight:600;cursor:pointer">💾</button>`+
      `<button onclick="_nomInlineCancel(this)" style="background:none;border:none;color:var(--text2);cursor:pointer;font-size:.85rem;padding:.1rem .25rem" title="Cancelar">✕</button>`;
  }
}

async function _nomInlineSave(btn, id){
  const tr = btn.closest('tr');
  if(!tr) return;
  const card = tr.closest('.section-card');
  if(!card) return;
  const info = _nomGetFields(btn);
  if(!info) return;
  const fields = info.fields;
  const activeTab = document.querySelector('.nomina-tab.active');
  if(!activeTab) return;
  const tab = activeTab.dataset.tab;
  const ep = _NOM_ENDPOINTS[tab];
  if(!ep) return;
  const body = {};
  fields.forEach(f => {
    const el = tr.querySelector('#nom-'+f.key);
    if(!el) return;
    const v = el.value;
    if(f.type === 'select'){
      body[f.key] = (v === '' || v === null) ? null : (isNaN(v) ? v : Number(v));
    } else if(f.type === 'number'){
      body[f.key] = parseFloat(v) || 0;
    } else if(f.type === 'date'){
      body[f.key] = v || null;
    } else {
      body[f.key] = v;
    }
  });
  try {
    const r = await _apiNomina('/'+ep+'/'+id, {method:'PUT', body:JSON.stringify(body)});
    if(!r.ok){
      const err = await r.json().catch(()=>({detail:'Error'}));
      alert('Error: '+(err.detail||''));
      return;
    }
    if(activeTab) cambiarTabNomina(tab, activeTab);
  } catch(e){ alert('Error de conexion'); }
}

function _nomInlineCancel(btn){
  const tr = btn.closest('tr');
  if(!tr) return;
  tr.querySelectorAll('.nom-cell').forEach(td => {
    td.innerHTML = td.dataset.display || escapeHtml(td.dataset.orig || '');
  });
  tr.querySelectorAll('input[type="hidden"]').forEach(inp => {
    if(inp.id && inp.id.startsWith('nom-')) inp.remove();
  });
  const actionTd = tr.querySelector('td:last-child');
  if(actionTd){
    actionTd.innerHTML =
      `<button class="nom-btn-edit" onclick="_nomInlineEdit(this, ${tr.dataset.id})" style="background:none;border:none;color:var(--accent);cursor:pointer;font-size:.82rem;padding:.1rem .25rem" title="Editar">✏️</button>`+
      `<button class="nom-btn-del" onclick="if(confirm('Eliminar?')){ _nomDel(${tr.dataset.id}) }" style="background:none;border:none;color:#e63946;cursor:pointer;font-size:.82rem;padding:.1rem .25rem" title="Eliminar">✕</button>`;
  }
}

function _nomInlineAdd(btn){
  const card = btn.closest('.section-card');
  if(!card) return;
  const tbody = card.querySelector('tbody');
  if(!tbody) return;
  const info = _nomGetFields(btn);
  if(!info) return;
  const singular = info.singular;
  const tableFields = info.fields.filter(f => !f.noTable);
  const valCols = tableFields.map(f => {
    const td = document.createElement('td');
    td.className = 'nom-cell';
    td.dataset.key = f.key;
    td.dataset.type = f.type || 'text';
    td.dataset.orig = '';
    td.innerHTML = _nomMakeInput(f, '');
    return td;
  });
  const tr = document.createElement('tr');
  valCols.forEach(td => tr.appendChild(td));
  info.fields.forEach(f => {
    if(f.noTable){
      const inp = document.createElement('input');
      inp.type = 'hidden';
      inp.id = 'nom-'+f.key;
      inp.value = '';
      tr.appendChild(inp);
    }
  });
  const actionTd = document.createElement('td');
  actionTd.style.cssText = 'text-align:center;white-space:nowrap';
  actionTd.innerHTML =
    `<button onclick="_nomInlineSaveNew(this)" style="background:var(--accent);color:#fff;border:none;border-radius:.3rem;padding:.15rem .45rem;font-size:.75rem;font-weight:600;cursor:pointer">💾</button>`+
    `<button onclick="this.closest('tr').remove()" style="background:none;border:none;color:#e63946;cursor:pointer;font-size:.85rem;padding:.1mm .25rem" title="Cancelar">✕</button>`;
  tr.appendChild(actionTd);
  tbody.insertBefore(tr, tbody.firstChild);
}

async function _nomInlineSaveNew(btn){
  const tr = btn.closest('tr');
  if(!tr) return;
  const card = tr.closest('.section-card');
  if(!card) return;
  const info = _nomGetFields(btn);
  if(!info) return;
  const fields = info.fields;
  const activeTab = document.querySelector('.nomina-tab.active');
  if(!activeTab) return;
  const tab = activeTab.dataset.tab;
  const ep = _NOM_ENDPOINTS[tab];
  if(!ep) return;
  const body = {};
  fields.forEach(f => {
    const el = tr.querySelector('#nom-'+f.key);
    if(!el) return;
    const v = el.value;
    if(f.type === 'select'){
      body[f.key] = (v === '' || v === null) ? null : (isNaN(v) ? v : Number(v));
    } else if(f.type === 'number'){
      body[f.key] = parseFloat(v) || 0;
    } else if(f.type === 'date'){
      body[f.key] = v || null;
    } else {
      body[f.key] = v;
    }
  });
  try {
    const r = await _apiNomina('/'+ep, {method:'POST', body:JSON.stringify(body)});
    if(!r.ok){
      const err = await r.json().catch(()=>({detail:'Error'}));
      alert('Error: '+(err.detail||''));
      return;
    }
    if(activeTab) cambiarTabNomina(tab, activeTab);
  } catch(e){ alert('Error de conexion'); }
}

function _nomCerrarModal(){
  document.getElementById('modal-nomina-form').style.display = 'none';
  document.getElementById('modal-nomina-body').innerHTML = '';
  document.getElementById('modal-nomina-msg').textContent = '';
  document.getElementById('modal-nomina-edit-id').value = '';
}

function _nomDel(id){
  const activeTab = document.querySelector('.nomina-tab.active');
  if(!activeTab) return;
  const tab = activeTab.dataset.tab;
  const ep = _NOM_ENDPOINTS[tab];
  if(!ep) return;
  _apiNomina('/'+ep+'/'+id, {method:'DELETE'}).then(() => { if(activeTab) cambiarTabNomina(tab, activeTab); });
}

async function apiFetch(url, opts){
  opts = opts || {};
  opts.headers = opts.headers || {};
  opts.credentials = 'include';
  var r = await fetch(API+url, opts);
  if(r.status === 401){ logout(); throw new Error('Sesion expirada'); }
  return r;
}

async function guardarAjustada(id, texto){
  var original = _verProds.find(p => p.id === id);
  if(!original) return;
  texto = (texto||'').trim(); if(!texto) texto = null;
  try {
    await apiFetch('/productos/'+id+'/ajustada', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({descripcion_ajustada:texto})});
    original.descripcion_ajustada = texto; renderVer();
  } catch(e){}
}
async function guardarCategoria(id, texto){
  var original = _verProds.find(p => p.id === id);
  if(!original) return;
  texto = (texto||'').trim(); if(!texto) texto = null;
  try {
    await apiFetch('/productos/'+id+'/ajustada', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({categoria:texto})});
    original.categoria = texto; renderVer();
  } catch(e){}
}
async function guardarProveedor(id, texto){
  var original = _verProds.find(p => p.id === id);
  if(!original) return;
  texto = (texto||'').trim(); if(!texto) texto = null;
  try {
    await apiFetch('/productos/'+id+'/ajustada', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({proveedor:texto})});
    original.proveedor = texto; renderVer();
  } catch(e){}
}

async function syncCategorias(){
  var btn = document.getElementById('btn-sync');
  var msg = document.getElementById('sync-msg');
  btn.disabled = true; btn.textContent = 'Sincronizando...'; msg.style.display = 'none';
  try {
    var r = await apiFetch('/sync/categories', {method:'POST'});
    var d = await r.json();
    if(!r.ok){
      msg.style.background = '#fdecea'; msg.style.borderColor = 'rgba(230,57,70,0.25)';
      msg.style.color = '#e63946';
      msg.textContent = 'Error: ' + (d.detail || 'No se pudo sincronizar');
    } else {
      msg.style.background = '#e6f9f4'; msg.style.borderColor = 'rgba(0,168,120,0.25)';
      msg.style.color = '#00a878';
      msg.textContent = 'Actualizados: ' + d.actualizados + ' | Sin categoría: ' + d.sin_categoria + ' | No encontrados: ' + d.no_encontrados;
    }
    msg.style.display = 'inline-block';
    cargarVerInsumos();
  } catch(e){
    msg.style.display = 'inline-block'; msg.style.color = '#e63946';
    msg.textContent = 'Error al sincronizar';
  }
  btn.disabled = false; btn.textContent = 'Sincronizar categorías';
}

// ─── Productos ─────────────────────────────────────────
async function cargarVerInsumos(){
  try {
    var url = '/productos?limit=500';
    if(!_user) url = '/api/insumos';
    const r = await apiFetch(url);
    if(!r.ok) return;
    var newData = JSON.parse(await r.text());
    if(!_user){
      newData = newData.map(function(p){
        return {id:p.id, descripcion:p.descripcion, unidad:p.unidad, valor:p.valor, categoria:p.categoria||'', n01:p.n01||'', n02:p.n02||'', n03:p.n03||'', proveedor:p.proveedor||'', descripcion_ajustada:null, valor_anterior:null};
      });
    }
    var total = parseInt(r.headers.get('X-Total-Count') || '0');
    var cats = parseInt(r.headers.get('X-Free-Cats') || '0');
    if(total && cats){
      _freeTierInfo = {total:total, categorias:cats};
    } else {
      _freeTierInfo = null;
    }
    console.log('[cargarVerInsumos] productos recibidos:', newData.length, '| total:', total, '| categorias:', cats, '| freeTier:', !!_freeTierInfo);
    if(_freeTierInfo){
      var catDist = {};
      newData.forEach(function(p){ var c = p.n01 || 'SinCat'; catDist[c] = (catDist[c]||0)+1; });
      console.log('[cargarVerInsumos] distribucion por categoria:', JSON.stringify(catDist));
    }
    var changed = true;
    if(_verProds.length === newData.length){
      var oldIds = _verProds.map(p=> p.id+'|'+p.valor+'|'+p.categoria+'|'+p.descripcion_ajustada).join();
      var newIds = newData.map(p=> p.id+'|'+p.valor+'|'+p.categoria+'|'+p.descripcion_ajustada).join();
      changed = oldIds !== newIds;
    }
    _verProds = newData;
    if(changed || !_verProds.length){ renderVer(); }
  } catch(e){}
}

function renderVer(){
  renderPlanBanner();
  const q = (document.getElementById('ver-filtro').value||'').toLowerCase().trim();
  const isAdmin = _user && _user.tipo === 'admin';
  const filtrados = !q ? _verProds : _verProds.filter(p=>
    (p.descripcion||'').toLowerCase().includes(q)||(p.categoria||'').toLowerCase().includes(q)
  );

  const userWrap = document.getElementById('user-table-wrap');
  const totalCount = document.getElementById('total-count');

  totalCount.style.display = 'inline-flex';
  if(_freeTierInfo && !isAdmin){
    totalCount.textContent = '📦 '+_verProds.length+' de '+_freeTierInfo.total+' insumos (10 x '+_freeTierInfo.categorias+' cat)';
  } else {
    totalCount.textContent = '📦 '+_verProds.length+' insumos';
  }
  document.getElementById('btn-sync').style.display = isAdmin ? '' : 'none';

  userWrap.style.display = 'block';
  var table = document.getElementById('ver-ins-table');
  var empty = document.getElementById('ver-ins-empty');
  if(!filtrados.length){ table.innerHTML=''; empty.style.display='block'; }
  else {
    empty.style.display='none';
    var tree = {};
    for(var i=0;i<filtrados.length;i++){
      var p = filtrados[i];
      var n1=p.n01||'', n2=p.n02||'', n3=p.n03||'';
      if(!n1&&!n2&&!n3) n1='Sin clasificar';
      if(!tree[n1]) tree[n1]={};
      if(!tree[n1][n2]) tree[n1][n2]={};
      if(!tree[n1][n2][n3]) tree[n1][n2][n3]=[];
      tree[n1][n2][n3].push(p);
    }
    function countN2(m){ var t=0,ks=Object.keys(m); for(var i=0;i<ks.length;i++){ var ns=Object.keys(m[ks[i]]); for(var j=0;j<ns.length;j++){ t+=m[ks[i]][ns[j]].length; } } return t; }
    function countN3(m){ var t=0,ks=Object.keys(m); for(var i=0;i<ks.length;i++) t+=m[ks[i]].length; return t; }
    var thead = table.querySelector('thead');
    var html = thead ? thead.outerHTML : '';
    var gid = 0;
    var n1keys = Object.keys(tree).sort();
    for(var a=0;a<n1keys.length;a++){
      var n1=n1keys[a], n2map=tree[n1], n2keys=Object.keys(n2map).sort(), n1total=countN2(n2map);
      html += '<tbody class="cat-group"><tr class="cat-header cat-l1" onclick="toggleGrupo(this,\'g'+gid+'\')"><td colspan="4"><span class="arrow" id="arrow-g'+gid+'">&#9660;</span> '+escapeHtml(n1)+' <span style="font-weight:400;color:var(--muted);font-size:.73rem">('+n1total+')</span></td></tr></tbody>';
      html += '<tbody class="cat-body" id="cat-body-g'+gid+'">';
      gid++;
      for(var b=0;b<n2keys.length;b++){
        var n2=n2keys[b], n3map=n2map[n2], n3keys=Object.keys(n3map).sort(), n2total=countN3(n3map);
        if(n2) html += '<tr class="cat-header cat-l2"><td colspan="4" style="padding-left:1.4rem;font-weight:600;color:var(--accent2)">'+escapeHtml(n2)+' <span style="font-weight:400;color:var(--muted);font-size:.73rem">('+n2total+')</span></td></tr>';
        for(var c=0;c<n3keys.length;c++){
          var n3=n3keys[c], items=n3map[n3];
          if(n3) html += '<tr class="cat-header cat-l3"><td colspan="4" style="padding-left:2.2rem;font-weight:500;color:var(--muted)">'+escapeHtml(n3)+' <span style="font-weight:400;font-size:.73rem">('+items.length+')</span></td></tr>';
          for(var d=0;d<items.length;d++){
            var p=items[d];
            html += '<tr><td style="padding-left:'+(n3?'3rem':n2?'2.2rem':'1.4rem')+'">'+escapeHtml(p.descripcion)+'</td><td style="color:var(--muted)">'+escapeHtml(p.unidad)+'</td><td style="font-weight:600;color:var(--accent)">$'+Number(p.valor).toLocaleString('es-CO',{minimumFractionDigits:0})+diffHtml(p)+'</td><td style="color:var(--text2)">'+escapeHtml(p.proveedor||'')+'</td></tr>';
          }
        }
      }
      html += '</tbody>';
    }
    table.innerHTML = html;
  }
}
function filtrarVer(){ renderVer(); }
function toggleGrupo(el, gid){
  var body=document.getElementById('cat-body-'+gid); if(!body) return;
  body.classList.toggle('collapsed');
  var arrow=document.getElementById('arrow-'+gid);
  if(arrow) arrow.classList.toggle('collapsed', body.classList.contains('collapsed'));
}
function expandirTodo(){
  document.querySelectorAll('.cat-body').forEach(b=>b.classList.remove('collapsed'));
  document.querySelectorAll('.cat-header .arrow').forEach(a=>a.classList.remove('collapsed'));
}
function contraerTodo(){
  document.querySelectorAll('.cat-body').forEach(b=>b.classList.add('collapsed'));
  document.querySelectorAll('.cat-header .arrow').forEach(a=>a.classList.add('collapsed'));
}

// ─── Usuarios ──────────────────────────────────────────
async function cargarUsuarios(){
  var sec=document.getElementById('section-usuarios');
  if(!sec||!sec.classList.contains('active')) return;
  try {
    const r = await apiFetch('/api/usuarios'); if(!r.ok) return;
    const items = await r.json();
    const tbody=document.getElementById('usr-tbody'), empty=document.getElementById('usr-empty');
    if(!items.length){ tbody.innerHTML=''; empty.style.display='block'; return; }
    empty.style.display='none';
    tbody.innerHTML = items.map(u => {
      var fp=u.fecha_pago?new Date(u.fecha_pago):null;
      var vence=fp?new Date(fp.getTime()+30*24*60*60*1000):null;
      var dias=fp?Math.ceil((vence.getTime()-Date.now())/(1000*60*60*24)):null;
      var colorDias=dias!=null?(dias<=0?'var(--red)':dias<=5?'#f59e0b':'var(--green)'):'var(--muted)';
      return `<tr>
      <td style="color:var(--muted)">${u.id}</td>
      <td style="font-weight:500">${escapeHtml(u.email)}</td>
      <td><span style="background:${u.activo?'var(--green-light)':'var(--red-light)'};color:${u.activo?'var(--green)':'var(--red)'};padding:.2rem .55rem;border-radius:1rem;font-size:.73rem;font-weight:600">${u.activo?'Activo':'Bloqueado'}</span></td>
      <td style="color:var(--muted)">${escapeHtml(u.tipo)}</td>
      <td><code style="font-size:0.73rem;word-break:break-all;background:#f4f5ff;padding:.15rem .4rem;border-radius:.3rem;color:var(--accent2)">${escapeHtml(u.token)}</code> <button class="btn btn-sm btn-outline" onclick="resetearToken(${u.id})" title="Resetear token">⟳</button></td>
      <td style="color:var(--muted)">${fp?fp.toLocaleDateString('es-CO'):'-'}</td>
      <td style="color:${colorDias};font-weight:500">${vence?vence.toLocaleDateString('es-CO',{day:'numeric',month:'short',year:'2-digit'}):'-'}</td>
      <td style="color:${colorDias};font-weight:700">${dias!=null?dias:'-'}</td>
      <td><div class="actions">
        <button class="btn btn-sm btn-outline" data-edit-id="${u.id}" data-edit-email="${escapeHtml(u.email)}" data-edit-tipo="${escapeHtml(u.tipo)}" data-edit-activo="${u.activo}" onclick="editarUsuarioBtn(this)">Editar</button>
        <button class="btn btn-sm ${u.activo?'btn-red':'btn-green'}" onclick="toggleActivo(${u.id},${!u.activo})">${u.activo?'Bloquear':'Activar'}</button>
        <button class="btn btn-sm btn-green" onclick="renovarPago(${u.id})" title="Pagar">$</button>
        <button class="btn btn-sm btn-red" onclick="eliminarUsuario(${u.id})" title="Eliminar">✕</button>
      </div></td></tr>`;
    }).join('');
  } catch(e){}
}
function editarUsuarioBtn(el){
  _editUsrId=parseInt(el.dataset.editId);
  document.getElementById('usr-email').value=el.dataset.editEmail;
  document.getElementById('usr-token').value='';
  document.getElementById('usr-tipo').value=el.dataset.editTipo;
  document.querySelector('#section-usuarios .btn-green').textContent='Guardar';
}
async function guardarUsuario(){
  const email=document.getElementById('usr-email').value.trim();
  const token=document.getElementById('usr-token').value.trim();
  const tipo=document.getElementById('usr-tipo').value;
  if(!email) return;
  const body={email,token,tipo,activo:true};
  try {
    if(_editUsrId){
      await apiFetch('/api/usuarios/'+_editUsrId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      _editUsrId=null; document.querySelector('#section-usuarios .btn-green').textContent='Agregar';
    } else {
      const res=await apiFetch('/api/usuarios',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      const nuevo=await res.json();
      alert('Usuario creado!\n\nToken: '+nuevo.token+'\n\nCopia este token y enviaselo al usuario.');
    }
    document.getElementById('usr-email').value='';
    document.getElementById('usr-token').value='';
    document.getElementById('usr-tipo').value='usuario';
    await cargarUsuarios();
  } catch(e){ alert('Error: '+e.message); }
}
async function toggleActivo(id,activo){
  try{ await apiFetch('/api/usuarios/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'',activo:activo})}); await cargarUsuarios(); }catch(e){}
}
async function eliminarUsuario(id){
  if(!confirm('¿Eliminar este usuario?')) return;
  await apiFetch('/api/usuarios/'+id,{method:'DELETE'}); await cargarUsuarios();
}
async function renovarPago(id){
  try{ await apiFetch('/api/usuarios/'+id+'/pago',{method:'POST'}); await cargarUsuarios(); }catch(e){}
}
function copiarToken(token){
  navigator.clipboard.writeText(token).then(()=>alert('Token copiado!')).catch(()=>{
    var t=document.createElement('textarea'); t.value=token; document.body.appendChild(t); t.select(); document.execCommand('copy'); document.body.removeChild(t); alert('Token copiado!');
  });
}

async function resetearToken(id){
  if(!confirm('¿Resetear el token de este usuario? Debera usar el nuevo token para iniciar sesion.')) return;
  try{
    var r = await apiFetch('/api/usuarios/'+id+'/reset-token', {method:'POST'});
    if(r.ok){
      alert('Token reseteado. El usuario debera iniciar sesion nuevamente.');
      await cargarUsuarios();
    } else {
      alert('Error al resetear token.');
    }
  }catch(e){ alert('Error: '+e.message); }
}

var _planData = null;
function renderPlanBanner(){
  var banner = document.getElementById('plan-banner');
  if(!banner) return;
  if(_user && _user.tipo === 'admin'){ banner.style.display = 'none'; return; }
  banner.style.display = 'block';

  var plan = _user.plan || 'free';
  var fp = _user && _user.fecha_pago ? new Date(_user.fecha_pago) : null;
  var vence = fp ? new Date(fp.getTime() + 30*24*60*60*1000) : null;
  var dias = fp ? Math.ceil((vence.getTime()-Date.now())/(1000*60*60*24)) : null;
  var activo = fp && dias > 0;

  var statusEl = document.getElementById('plan-status');
  var vencEl = document.getElementById('plan-vencimiento');
  var msgEl = document.getElementById('plan-msg');
  var btn = document.getElementById('plan-btn');
  var upInfo = document.getElementById('plan-upgrade-info');
  var tagFree = document.getElementById('plan-tag-free');
  var cardFree = document.getElementById('plan-card-free');
  var cardBasico = document.getElementById('plan-card-basico');
  var cardPlus = document.getElementById('plan-card-plus');

  [cardFree, cardBasico, cardPlus].forEach(function(c){ c.style.border = '1px solid var(--border)'; });

  if(activo && plan === 'plus'){
    statusEl.textContent = 'Plus activo';
    statusEl.style.color = 'var(--green)';
    vencEl.textContent = 'Vence '+(vence? vence.toLocaleDateString('es-CO',{day:'numeric',month:'long',year:'numeric'}):'');
    msgEl.textContent = 'Tienes acceso ilimitado a productos y calculadora (mezclas, mamposteria, anclajes).';
    btn.textContent = 'Renovar Plus — $15.000';
    btn.onclick = function(){ comprarPlan('plus'); };
    upInfo.textContent = '';
    cardPlus.style.border = '2px solid var(--green)';
    tagFree.textContent = '';
  } else if(activo && plan === 'basico'){
    statusEl.textContent = 'Basico activo';
    statusEl.style.color = 'var(--accent)';
    vencEl.textContent = 'Vence '+(vence? vence.toLocaleDateString('es-CO',{day:'numeric',month:'long',year:'numeric'}):'');
    msgEl.textContent = 'Productos ilimitados pero sin acceso a la calculadora.';
    btn.textContent = 'Actualizar a Plus — desde $5.000';
    btn.onclick = function(){ upgradePlan(); };
    upInfo.textContent = dias ? 'Prorrateo: $15.000 - credito por '+dias+' dias restantes' : '';
    cardBasico.style.border = '2px solid var(--accent)';
    tagFree.textContent = '';
  } else if(activo){
    statusEl.textContent = 'Plan activo (legacy)';
    statusEl.style.color = 'var(--green)';
    vencEl.textContent = 'Vence '+(vence? vence.toLocaleDateString('es-CO',{day:'numeric',month:'long',year:'numeric'}):'');
    msgEl.textContent = 'Acceso completo. Renueva tu plan.';
    btn.textContent = 'Renovar — $10.000';
    btn.onclick = function(){ comprarPlan('basico'); };
    upInfo.textContent = '';
  } else {
    statusEl.textContent = 'Plan Free';
    statusEl.style.color = '#f59e0b';
    vencEl.textContent = '';
    var fi = _freeTierInfo;
    msgEl.textContent = 'Ves 10 insumos por categoria y 3 calculos por tipo. Actualiza para acceso completo.';
    btn.textContent = 'Comprar Basico — $10.000';
    btn.onclick = function(){ comprarPlan('basico'); };
    upInfo.innerHTML = '<button class="btn btn-green" style="font-size:.78rem;padding:.35rem .8rem" onclick="comprarPlan(\'plus\')">Comprar Plus — $15.000</button>';
    cardFree.style.border = '2px solid #f59e0b';
    tagFree.textContent = 'Plan actual';
  }
}

var _planPrice = {'basico':10000,'plus':15000};
async function accionPlan(){
  var plan = _user.plan || 'free';
  var fp = _user && _user.fecha_pago ? new Date(_user.fecha_pago) : null;
  var dias = fp ? Math.ceil((new Date(fp.getTime()+30*24*60*60*1000)-Date.now())/(1000*60*60*24)) : 0;
  if(dias > 0 && (plan === 'plus' || plan === 'basico')){
    if(plan === 'basico') upgradePlan();
    else comprarPlan(plan);
  } else {
    comprarPlan('basico');
  }
}

async function comprarPlan(tipo){
  var btn = document.getElementById('plan-btn');
  btn.disabled = true;
  btn.textContent = 'Creando link...';
  try {
    var r = await apiFetch('/api/auth/comprar-plan', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({plan:tipo})});
    if(!r.ok){
      var d = await r.json();
      alert('Error: ' + (d.detail || 'No se pudo crear el link'));
      btn.disabled = false;
      renderPlanBanner();
      return;
    }
    var pago = await r.json();
    window.open(pago.url, '_blank');
    btn.textContent = 'Link creado — continuar al pago';
    setTimeout(function(){ btn.disabled = false; renderPlanBanner(); }, 4000);
  } catch(e){
    alert('Error: ' + e.message);
    btn.disabled = false;
    renderPlanBanner();
  }
}

async function upgradePlan(){
  var btn = document.getElementById('plan-btn');
  btn.disabled = true;
  btn.textContent = 'Creando upgrade...';
  try {
    var r = await apiFetch('/api/auth/upgrade-plan', {method:'POST'});
    var d = await r.json();
    if(!r.ok){
      alert('Error: ' + (d.detail || 'No se pudo crear el upgrade'));
      btn.disabled = false;
      renderPlanBanner();
      return;
    }
    if(confirm('Upgrade a Plus por $'+Number(d.amount).toLocaleString('es-CO')+' (credito Basico: $'+Number(d.credito_basico).toLocaleString('es-CO')+'). Al pagar, el ciclo se reinicia por 30 dias.')){
      window.open(d.url, '_blank');
    }
    btn.disabled = false;
    renderPlanBanner();
  } catch(e){
    alert('Error: ' + e.message);
    btn.disabled = false;
    renderPlanBanner();
  }
}

var _pagosUsuariosCache = [];
async function cargarPagosUsuariosDropdown(){
  try {
    var r = await apiFetch('/api/usuarios');
    if(!r.ok) return;
    _pagosUsuariosCache = await r.json();
    var sel = document.getElementById('pago-usr');
    var currentVal = sel.value;
    sel.innerHTML = '<option value="">Seleccionar usuario...</option>' +
      _pagosUsuariosCache.map(function(u){ return '<option value="'+u.id+'">'+u.email+' (ID:'+u.id+')</option>'; }).join('');
    sel.value = currentVal;
  } catch(e){}
}
async function cargarPagos(){
  var sec=document.getElementById('section-pagos');
  if(!sec||!sec.classList.contains('active')) return;
  cargarPagosUsuariosDropdown();
  try {
    var r = await apiFetch('/api/pagos'); if(!r.ok) return;
    var items = await r.json();
    var tbody=document.getElementById('pagos-tbody'), empty=document.getElementById('pagos-empty');
    if(!items.length){ tbody.innerHTML=''; empty.style.display='block'; }
    else {
      empty.style.display='none';
      tbody.innerHTML = items.map(function(p){
        var statusColor = p.status==='PAID'?'var(--green)':p.status==='REJECTED'?'var(--red)':p.status==='ACTIVE'?'var(--accent)':'var(--muted)';
        return '<tr>'+
        '<td style="color:var(--muted)">'+p.id+'</td>'+
        '<td style="font-weight:500">ID:'+p.usuario_id+'</td>'+
        '<td><a href="'+escapeHtml(p.url)+'" target="_blank" style="color:var(--accent);text-decoration:none;font-weight:600">'+escapeHtml(p.payment_link)+'</a></td>'+
        '<td style="font-size:.73rem;color:var(--text2)">'+escapeHtml(p.reference)+'</td>'+
        '<td style="font-weight:600;color:var(--accent)">$'+Number(p.amount).toLocaleString('es-CO')+'</td>'+
        '<td style="font-weight:600;color:'+statusColor+'">'+escapeHtml(p.status)+'</td>'+
        '<td style="font-size:.73rem;color:var(--muted)">'+escapeHtml(p.transaction_id||'-')+'</td>'+
        '<td><div class="actions">'+
        '<button class="btn btn-sm btn-outline" onclick="sincronizarPago('+p.id+')" title="Sincronizar">&#8635;</button>'+
        '<button class="btn btn-sm btn-outline" onclick="eliminarPago('+p.id+')" title="Eliminar" style="color:var(--red)">&#10005;</button>'+
        '</div></td></tr>';
      }).join('');
    }
  } catch(e){}
}
async function crearLinkPago(){
  var usrId = document.getElementById('pago-usr').value;
  var amount = parseInt(document.getElementById('pago-amount').value) || 30000;
  var desc = document.getElementById('pago-desc').value.trim() || 'Suscripcion ListaMasterInsumos';
  if(!usrId){ alert('Selecciona un usuario'); return; }
  if(amount < 1000){ alert('Monto minimo: $1,000 COP'); return; }
  try {
    var r = await apiFetch('/api/pagos/crear-link', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({usuario_id:parseInt(usrId), amount:amount, description:desc})});
    if(!r.ok){ var err=await r.json(); alert('Error: '+(err.detail||'No se pudo crear el link')); return; }
    var pago = await r.json();
    var link = pago.url;
    navigator.clipboard.writeText(link).then(function(){ alert('Link creado y copiado!\n\n'+link); });
    await cargarPagos();
  } catch(e){ alert('Error: '+e.message); }
}
async function sincronizarPago(id){
  try {
    var r = await apiFetch('/api/pagos/sync/'+id, {method:'PUT'});
    if(!r.ok){ var err=await r.json(); alert('Error: '+(err.detail||'No se pudo sincronizar')); return; }
    await cargarPagos();
    if(document.getElementById('section-usuarios').classList.contains('active')) cargarUsuarios();
  } catch(e){ alert('Error: '+e.message); }
}
async function eliminarPago(id){
  if(!confirm('¿Eliminar este link de pago?')) return;
  try {
    var r = await apiFetch('/api/pagos/'+id, {method:'DELETE'});
    if(!r.ok){ var err=await r.json(); alert('Error: '+(err.detail||'No se pudo eliminar')); return; }
    await cargarPagos();
  } catch(e){ alert('Error: '+e.message); }
}

// ─── Modal Uso de Proyecto ─────────────────────
function abrirModalUso(){
  document.getElementById('modal-uso').style.display = 'flex';
  document.getElementById('modal-uso-desc').value = '';
  document.getElementById('modal-uso-id').value = '';
  document.getElementById('modal-uso-msg').textContent = '';
  document.getElementById('modal-uso-cancel').style.display = 'none';
  document.getElementById('modal-uso-desc').focus();
  renderListaUsos();
}
function cerrarModalUso(){
  document.getElementById('modal-uso').style.display = 'none';
}
function cancelarEdicionUso(){
  document.getElementById('modal-uso-desc').value = '';
  document.getElementById('modal-uso-id').value = '';
  document.getElementById('modal-uso-msg').textContent = '';
  document.getElementById('modal-uso-cancel').style.display = 'none';
  document.getElementById('modal-uso-desc').focus();
}
async function renderListaUsos(){
  const cont = document.getElementById('modal-uso-lista');
  try {
    const r = await _apiNomina('/usos-proyecto');
    if(!r.ok){ cont.innerHTML = '<div style="color:var(--red);font-size:.75rem">Error al cargar</div>'; return; }
    const usos = await r.json();
    if(!usos.length){ cont.innerHTML = '<div style="color:var(--muted);font-size:.78rem;text-align:center;padding:.5rem">Sin usos registrados</div>'; return; }
    cont.innerHTML = '<table style="width:100%;border-collapse:collapse"><thead><tr><th style="padding:.3rem .3rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border)">Descripción</th><th style="width:70px;padding:.3rem .3rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)"></th></tr></thead><tbody>'+
      usos.map(u => '<tr><td style="font-size:.78rem;padding:.25rem .3rem">'+escapeHtml(u.descripcion)+'</td>'+
        '<td style="text-align:center;white-space:nowrap">'+
        '<button onclick="editarUso('+u.id_uso+',\''+u.descripcion.replace(/'/g,"\\'")+'\')" style="background:none;border:none;color:var(--accent);cursor:pointer;font-size:.82rem;padding:.1rem .3rem" title="Editar">✏️</button>'+
        '<button onclick="eliminarUso('+u.id_uso+')" style="background:none;border:none;color:#e63946;cursor:pointer;font-size:.82rem;padding:.1rem .3rem" title="Eliminar">✕</button></td></tr>').join('')+
      '</tbody></table>';
  } catch(e){ cont.innerHTML = '<div style="color:var(--red);font-size:.75rem">Error de conexión</div>'; }
}
function editarUso(id, desc){
  document.getElementById('modal-uso-id').value = id;
  document.getElementById('modal-uso-desc').value = desc;
  document.getElementById('modal-uso-msg').textContent = '';
  document.getElementById('modal-uso-cancel').style.display = '';
  document.getElementById('modal-uso-desc').focus();
}
async function eliminarUso(id){
  if(!confirm('¿Eliminar este uso?')) return;
  try {
    const r = await _apiNomina('/usos-proyecto/'+id, {method:'DELETE'});
    if(!r.ok){ const e=await r.json().catch(()=>({})); document.getElementById('modal-uso-msg').textContent = 'Error: '+(e.detail||''); return; }
    renderListaUsos();
    actualizarSelectUso();
  } catch(e){ document.getElementById('modal-uso-msg').textContent = 'Error de conexión'; }
}
async function actualizarSelectUso(){
  const sel = document.getElementById('nom-modal-id_uso');
  if(!sel) return;
  try {
    const r = await _apiNomina('/usos-proyecto');
    if(!r.ok) return;
    const items = await r.json();
    const val = sel.value;
    sel.innerHTML = items.map(i => '<option value="'+i.id_uso+'">'+escapeHtml(i.descripcion)+'</option>').join('');
    if(items.some(i => String(i.id_uso) === val)) sel.value = val;
  } catch(e){}
}
async function guardarModalUso(){
  const desc = document.getElementById('modal-uso-desc').value.trim();
  const id = document.getElementById('modal-uso-id').value;
  const msg = document.getElementById('modal-uso-msg');
  if(!desc){ msg.textContent = 'Ingrese una descripción'; return; }
  try {
    let r;
    if(id){
      r = await _apiNomina('/usos-proyecto/'+id, {method:'PUT',body:JSON.stringify({descripcion:desc})});
    } else {
      r = await _apiNomina('/usos-proyecto', {method:'POST',body:JSON.stringify({descripcion:desc})});
    }
    if(!r.ok){ const e=await r.json().catch(()=>({})); msg.textContent = 'Error: '+(e.detail||''); return; }
    document.getElementById('modal-uso-desc').value = '';
    document.getElementById('modal-uso-id').value = '';
    document.getElementById('modal-uso-cancel').style.display = 'none';
    msg.textContent = '';
    renderListaUsos();
    actualizarSelectUso();
  } catch(e){ msg.textContent = 'Error de conexión'; }
}

// ─── Modal EPS ────────────────────────────────
function abrirModalEps(){
  document.getElementById('modal-eps').style.display = 'flex';
  document.getElementById('modal-eps-nombre').value = '';
  document.getElementById('modal-eps-id').value = '';
  document.getElementById('modal-eps-msg').textContent = '';
  document.getElementById('modal-eps-cancel').style.display = 'none';
  document.getElementById('modal-eps-nombre').focus();
  renderListaEps();
}
function cerrarModalEps(){
  document.getElementById('modal-eps').style.display = 'none';
}
function cancelarEdicionEps(){
  document.getElementById('modal-eps-nombre').value = '';
  document.getElementById('modal-eps-id').value = '';
  document.getElementById('modal-eps-msg').textContent = '';
  document.getElementById('modal-eps-cancel').style.display = 'none';
  document.getElementById('modal-eps-nombre').focus();
}
async function renderListaEps(){
  const cont = document.getElementById('modal-eps-lista');
  try {
    const r = await _apiNomina('/eps');
    if(!r.ok){ cont.innerHTML = '<div style="color:var(--red);font-size:.75rem">Error al cargar</div>'; return; }
    const items = await r.json();
    if(!items.length){ cont.innerHTML = '<div style="color:var(--muted);font-size:.78rem;text-align:center;padding:.5rem">Sin EPS registradas</div>'; return; }
    cont.innerHTML = '<table style="width:100%;border-collapse:collapse"><thead><tr><th style="padding:.3rem .3rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border)">Nombre EPS</th><th style="width:70px;padding:.3rem .3rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)"></th></tr></thead><tbody>'+
      items.map(i => '<tr><td style="font-size:.78rem;padding:.25rem .3rem">'+escapeHtml(i.nombre_eps)+'</td>'+
        '<td style="text-align:center;white-space:nowrap">'+
        '<button onclick="editarEps('+i.id_eps+',\''+i.nombre_eps.replace(/'/g,"\\'")+'\')" style="background:none;border:none;color:var(--accent);cursor:pointer;font-size:.82rem;padding:.1rem .3rem" title="Editar">✏️</button>'+
        '<button onclick="eliminarEps('+i.id_eps+')" style="background:none;border:none;color:#e63946;cursor:pointer;font-size:.82rem;padding:.1rem .3rem" title="Eliminar">✕</button></td></tr>').join('')+
      '</tbody></table>';
  } catch(e){ cont.innerHTML = '<div style="color:var(--red);font-size:.75rem">Error de conexión</div>'; }
}
function editarEps(id, nombre){
  document.getElementById('modal-eps-id').value = id;
  document.getElementById('modal-eps-nombre').value = nombre;
  document.getElementById('modal-eps-msg').textContent = '';
  document.getElementById('modal-eps-cancel').style.display = '';
  document.getElementById('modal-eps-nombre').focus();
}
async function eliminarEps(id){
  if(!confirm('¿Eliminar esta EPS?')) return;
  try {
    const r = await _apiNomina('/eps/'+id, {method:'DELETE'});
    if(!r.ok){ const e=await r.json().catch(()=>({})); document.getElementById('modal-eps-msg').textContent = 'Error: '+(e.detail||''); return; }
    renderListaEps();
    actualizarSelectEps();
  } catch(e){ document.getElementById('modal-eps-msg').textContent = 'Error de conexión'; }
}
async function actualizarSelectEps(){
  const sel = document.getElementById('nom-modal-id_eps');
  if(!sel) return;
  try {
    const r = await _apiNomina('/eps');
    if(!r.ok) return;
    const items = await r.json();
    const val = sel.value;
    sel.innerHTML = '<option value="">--</option>'+items.map(i => '<option value="'+i.id_eps+'">'+escapeHtml(i.nombre_eps)+'</option>').join('');
    if(items.some(i => String(i.id_eps) === val)) sel.value = val;
  } catch(e){}
}
async function guardarModalEps(){
  const nombre = document.getElementById('modal-eps-nombre').value.trim();
  const id = document.getElementById('modal-eps-id').value;
  const msg = document.getElementById('modal-eps-msg');
  if(!nombre){ msg.textContent = 'Ingrese el nombre de la EPS'; return; }
  try {
    let r;
    if(id){
      r = await _apiNomina('/eps/'+id, {method:'PUT',body:JSON.stringify({nombre_eps:nombre})});
    } else {
      r = await _apiNomina('/eps', {method:'POST',body:JSON.stringify({nombre_eps:nombre})});
    }
    if(!r.ok){ const e=await r.json().catch(()=>({})); msg.textContent = 'Error: '+(e.detail||''); return; }
    document.getElementById('modal-eps-nombre').value = '';
    document.getElementById('modal-eps-id').value = '';
    document.getElementById('modal-eps-cancel').style.display = 'none';
    msg.textContent = '';
    renderListaEps();
    actualizarSelectEps();
  } catch(e){ msg.textContent = 'Error de conexión'; }
}

// ─── Modal AFP ────────────────────────────────
function abrirModalAfp(){
  document.getElementById('modal-afp').style.display = 'flex';
  document.getElementById('modal-afp-nombre').value = '';
  document.getElementById('modal-afp-id').value = '';
  document.getElementById('modal-afp-msg').textContent = '';
  document.getElementById('modal-afp-cancel').style.display = 'none';
  document.getElementById('modal-afp-nombre').focus();
  renderListaAfp();
}
function cerrarModalAfp(){
  document.getElementById('modal-afp').style.display = 'none';
}
function cancelarEdicionAfp(){
  document.getElementById('modal-afp-nombre').value = '';
  document.getElementById('modal-afp-id').value = '';
  document.getElementById('modal-afp-msg').textContent = '';
  document.getElementById('modal-afp-cancel').style.display = 'none';
  document.getElementById('modal-afp-nombre').focus();
}
async function renderListaAfp(){
  const cont = document.getElementById('modal-afp-lista');
  try {
    const r = await _apiNomina('/afp');
    if(!r.ok){ cont.innerHTML = '<div style="color:var(--red);font-size:.75rem">Error al cargar</div>'; return; }
    const items = await r.json();
    if(!items.length){ cont.innerHTML = '<div style="color:var(--muted);font-size:.78rem;text-align:center;padding:.5rem">Sin AFP registradas</div>'; return; }
    cont.innerHTML = '<table style="width:100%;border-collapse:collapse"><thead><tr><th style="padding:.3rem .3rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border)">Nombre AFP</th><th style="width:70px;padding:.3rem .3rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)"></th></tr></thead><tbody>'+
      items.map(i => '<tr><td style="font-size:.78rem;padding:.25rem .3rem">'+escapeHtml(i.nombre_afp)+'</td>'+
        '<td style="text-align:center;white-space:nowrap">'+
        '<button onclick="editarAfp('+i.id_afp+',\''+i.nombre_afp.replace(/'/g,"\\'")+'\')" style="background:none;border:none;color:var(--accent);cursor:pointer;font-size:.82rem;padding:.1rem .3rem" title="Editar">✏️</button>'+
        '<button onclick="eliminarAfp('+i.id_afp+')" style="background:none;border:none;color:#e63946;cursor:pointer;font-size:.82rem;padding:.1rem .3rem" title="Eliminar">✕</button></td></tr>').join('')+
      '</tbody></table>';
  } catch(e){ cont.innerHTML = '<div style="color:var(--red);font-size:.75rem">Error de conexión</div>'; }
}
function editarAfp(id, nombre){
  document.getElementById('modal-afp-id').value = id;
  document.getElementById('modal-afp-nombre').value = nombre;
  document.getElementById('modal-afp-msg').textContent = '';
  document.getElementById('modal-afp-cancel').style.display = '';
  document.getElementById('modal-afp-nombre').focus();
}
async function eliminarAfp(id){
  if(!confirm('¿Eliminar esta AFP?')) return;
  try {
    const r = await _apiNomina('/afp/'+id, {method:'DELETE'});
    if(!r.ok){ const e=await r.json().catch(()=>({})); document.getElementById('modal-afp-msg').textContent = 'Error: '+(e.detail||''); return; }
    renderListaAfp();
    actualizarSelectAfp();
  } catch(e){ document.getElementById('modal-afp-msg').textContent = 'Error de conexión'; }
}
async function actualizarSelectAfp(){
  const sel = document.getElementById('nom-modal-id_afp');
  if(!sel) return;
  try {
    const r = await _apiNomina('/afp');
    if(!r.ok) return;
    const items = await r.json();
    const val = sel.value;
    sel.innerHTML = '<option value="">--</option>'+items.map(i => '<option value="'+i.id_afp+'">'+escapeHtml(i.nombre_afp)+'</option>').join('');
    if(items.some(i => String(i.id_afp) === val)) sel.value = val;
  } catch(e){}
}
async function guardarModalAfp(){
  const nombre = document.getElementById('modal-afp-nombre').value.trim();
  const id = document.getElementById('modal-afp-id').value;
  const msg = document.getElementById('modal-afp-msg');
  if(!nombre){ msg.textContent = 'Ingrese el nombre de la AFP'; return; }
  try {
    let r;
    if(id){
      r = await _apiNomina('/afp/'+id, {method:'PUT',body:JSON.stringify({nombre_afp:nombre})});
    } else {
      r = await _apiNomina('/afp', {method:'POST',body:JSON.stringify({nombre_afp:nombre})});
    }
    if(!r.ok){ const e=await r.json().catch(()=>({})); msg.textContent = 'Error: '+(e.detail||''); return; }
    document.getElementById('modal-afp-nombre').value = '';
    document.getElementById('modal-afp-id').value = '';
    document.getElementById('modal-afp-cancel').style.display = 'none';
    msg.textContent = '';
    renderListaAfp();
    actualizarSelectAfp();
  } catch(e){ msg.textContent = 'Error de conexión'; }
}

// ─── Modal Cargo ──────────────────────────────
function abrirModalCargo(){
  document.getElementById('modal-cargo').style.display = 'flex';
  document.getElementById('modal-cargo-desc').value = '';
  document.getElementById('modal-cargo-id').value = '';
  document.getElementById('modal-cargo-msg').textContent = '';
  document.getElementById('modal-cargo-cancel').style.display = 'none';
  document.getElementById('modal-cargo-desc').focus();
  renderListaCargos();
}
function cerrarModalCargo(){
  document.getElementById('modal-cargo').style.display = 'none';
}
function cancelarEdicionCargo(){
  document.getElementById('modal-cargo-desc').value = '';
  document.getElementById('modal-cargo-id').value = '';
  document.getElementById('modal-cargo-msg').textContent = '';
  document.getElementById('modal-cargo-cancel').style.display = 'none';
  document.getElementById('modal-cargo-desc').focus();
}
async function renderListaCargos(){
  const cont = document.getElementById('modal-cargo-lista');
  try {
    const r = await _apiNomina('/cargos');
    if(!r.ok){ cont.innerHTML = '<div style="color:var(--red);font-size:.75rem">Error al cargar</div>'; return; }
    const items = await r.json();
    if(!items.length){ cont.innerHTML = '<div style="color:var(--muted);font-size:.78rem;text-align:center;padding:.5rem">Sin cargos registrados</div>'; return; }
    cont.innerHTML = '<table style="width:100%;border-collapse:collapse"><thead><tr><th style="padding:.3rem .3rem;font-size:.72rem;text-align:left;color:var(--muted);border-bottom:1px solid var(--border)">Descripción</th><th style="width:70px;padding:.3rem .3rem;font-size:.72rem;text-align:center;color:var(--muted);border-bottom:1px solid var(--border)"></th></tr></thead><tbody>'+
      items.map(i => '<tr><td style="font-size:.78rem;padding:.25rem .3rem">'+escapeHtml(i.descripcion)+'</td>'+
        '<td style="text-align:center;white-space:nowrap">'+
        '<button onclick="editarCargo('+i.id_cargo+',\''+i.descripcion.replace(/'/g,"\\'")+'\')" style="background:none;border:none;color:var(--accent);cursor:pointer;font-size:.82rem;padding:.1rem .3rem" title="Editar">✏️</button>'+
        '<button onclick="eliminarCargo('+i.id_cargo+')" style="background:none;border:none;color:#e63946;cursor:pointer;font-size:.82rem;padding:.1rem .3rem" title="Eliminar">✕</button></td></tr>').join('')+
      '</tbody></table>';
  } catch(e){ cont.innerHTML = '<div style="color:var(--red);font-size:.75rem">Error de conexión</div>'; }
}
function editarCargo(id, desc){
  document.getElementById('modal-cargo-id').value = id;
  document.getElementById('modal-cargo-desc').value = desc;
  document.getElementById('modal-cargo-msg').textContent = '';
  document.getElementById('modal-cargo-cancel').style.display = '';
  document.getElementById('modal-cargo-desc').focus();
}
async function eliminarCargo(id){
  if(!confirm('¿Eliminar este cargo?')) return;
  try {
    const r = await _apiNomina('/cargos/'+id, {method:'DELETE'});
    if(!r.ok){ const e=await r.json().catch(()=>({})); document.getElementById('modal-cargo-msg').textContent = 'Error: '+(e.detail||''); return; }
    renderListaCargos();
  } catch(e){ document.getElementById('modal-cargo-msg').textContent = 'Error de conexión'; }
}
async function guardarModalCargo(){
  const desc = document.getElementById('modal-cargo-desc').value.trim();
  const id = document.getElementById('modal-cargo-id').value;
  const msg = document.getElementById('modal-cargo-msg');
  if(!desc){ msg.textContent = 'Ingrese la descripción del cargo'; return; }
  try {
    let r;
    if(id){
      r = await _apiNomina('/cargos/'+id, {method:'PUT',body:JSON.stringify({descripcion:desc})});
    } else {
      r = await _apiNomina('/cargos', {method:'POST',body:JSON.stringify({descripcion:desc})});
    }
    if(!r.ok){ const e=await r.json().catch(()=>({})); msg.textContent = 'Error: '+(e.detail||''); return; }
    document.getElementById('modal-cargo-desc').value = '';
    document.getElementById('modal-cargo-id').value = '';
    document.getElementById('modal-cargo-cancel').style.display = 'none';
    msg.textContent = '';
    renderListaCargos();
  } catch(e){ msg.textContent = 'Error de conexión'; }
}