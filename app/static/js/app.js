window.cambiarLogin = function(modo, el){
  document.querySelectorAll('.login-tab').forEach(t=>t.classList.remove('active'));
  if(el) el.classList.add('active');
  document.getElementById('login-registro').style.display = modo==='registro' ? 'block' : 'none';
  document.getElementById('login-token-section').style.display = modo==='token' ? 'block' : 'none';
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
  var ver = 'v5';
  var stored = localStorage.getItem('ls_overridesVersion');
  if(stored !== ver){
    localStorage.removeItem('ls_materialOverrides');
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
async function entrarInvitado(){
  var email = document.getElementById('guest-email').value.trim();
  if(!email){ document.getElementById('login-error').textContent='Regístrate gratis para acceder'; return; }
  try {
    var check = await fetch(API+'/api/check-email?email='+encodeURIComponent(email));
    var cd = await check.json();
    if(cd.registrado){
      document.getElementById('login-error').textContent='Este email ya tiene token. Usa la pestaña "Ingresar con token".';
      return;
    }
    var reg = await fetch(API+'/api/auth/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email:email, token:''})});
    if(!reg.ok){ document.getElementById('login-error').textContent='Error al registrar'; return; }
    var u = await reg.json();
    _user = u; _viewMode = 'adjusted';
    localStorage.setItem('user', JSON.stringify(u));
    localStorage.setItem('auth_token', u.token || '');
    initGuest(email);
  } catch(e){
    _user = null; _viewMode = 'adjusted';
    initGuest(email);
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
function login(){
  const email = document.getElementById('login-email').value.trim();
  const token = document.getElementById('login-token').value.trim();
  if(!email || !token){ document.getElementById('login-error').textContent='Completa todos los campos'; return; }
  fetch(API+'/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email,token})})
  .then(r=>{ if(!r.ok){ document.getElementById('login-error').textContent='Credenciales inválidas'; throw new Error('fail'); } return r.json(); })
  .then(u=>{ _user=u; localStorage.setItem('user', JSON.stringify(u)); localStorage.setItem('auth_token', token); initApp(); })
  .catch(()=>{});
}
function logout(){
  _user = null; _viewMode = null;
  localStorage.removeItem('user'); localStorage.removeItem('auth_token');
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
  items.push({label:'INSUMOS', header:true});
  items.push({id:'ver-insumos', icon:'&#9632;', text:'Insumos', mode: isAdmin ? 'raw' : 'adjusted'});
  items.push({label:'CÁLCULOS', header:true});
  items.push({id:'insumos-calc', icon:'&#9679;', text:'InsCal'});
  items.push({id:'mezclas', icon:'&#9881;', text:'Mezclas'});
  items.push({id:'mamposteria', icon:'&#9881;', text:'Mamposterías'});
  items.push({id:'anclajes', icon:'&#9881;', text:'Anclajes'});
  const menu = document.getElementById('sidebar-menu');
  menu.innerHTML = items.map(i => {
    if(i.header) return '<div class="menu-label">'+i.label+'</div>';
    var mode = i.mode ? ' data-mode="'+i.mode+'"' : '';
    return '<div class="menu-item" data-section="'+i.id+'"'+mode+' onclick="irA(\''+i.id+'\',this)"><span class="ico">'+i.icon+'</span> '+i.text+'</div>';
  }).join('');
}

// ─── Navigation ────────────────────────────────────────
function irA(section, el){
  document.querySelectorAll('.menu-item').forEach(m=>m.classList.remove('active'));
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  if(el) el.classList.add('active');
  if(el && el.dataset.mode) _viewMode = el.dataset.mode;
  const sec = document.getElementById('section-'+section);
  if(sec) sec.classList.add('active');
  const titles = {'ver-insumos': 'Insumos', 'usuarios':'Usuarios', 'pagos':'Pagos', 'insumos-calc':'InsCal', 'mezclas':'Mezclas', 'mamposteria':'Mamposterías', 'anclajes':'Anclajes Químicos'};
  document.getElementById('page-title').textContent = titles[section]||'Insumos';
  if(window.innerWidth<=768) document.getElementById('sidebar').classList.add('collapsed');
  if(section==='ver-insumos') cargarVerInsumos();
  if(section==='usuarios') cargarUsuarios();
  if(section==='pagos') cargarPagos();
  if(section==='insumos-calc') cargarInsumosCalc();
  if(section==='mezclas') cargarSelectMezclas();
  if(section==='mamposteria') cargarSelectMamposteria();
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
  const saved = localStorage.getItem('user');
  const savedToken = localStorage.getItem('auth_token');
  if(saved){
    try{ _user = JSON.parse(saved); }catch(e){ _user = null; }
    if(_user && savedToken){
      fetch(API+'/api/auth/me', {headers:{'Authorization':'Bearer '+savedToken}})
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
const $auth = () => { var t = localStorage.getItem('auth_token'); return t ? 'Bearer '+t : ''; };

// ─── Cálculos ──────────────────────────────────────────
const _CONV = {
  "Cemento": { u:"Bolsa", f:50, pf:50 },
  "Arena de rio": { u:"Viaje", f:1.05 },
  "Arena de pozo": { u:"Viaje", f:1.05 },
  "Arena de peña": { u:"Viaje", f:1.05 },
  "Material de rio (gravilla)": { u:"Viaje", f:1.05 },
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
  _saveOverrides();
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
    var overrides = await _loadOverrides();
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

async function _loadOverrides(){
  if(_user){
    try {
      const r = await apiFetch('/api/calculos/overrides');
      if(r.ok){
        const data = await r.json();
        var overrides = {};
        data.forEach(function(o){
          overrides[o.nombre] = { nombre: o.nombre, unidad: o.unidad, cant: o.cantidad, vr_unitario: o.vr_unitario };
        });
        try { localStorage.setItem('ls_materialOverrides', JSON.stringify(overrides)); } catch(e) {}
        return overrides;
      }
    } catch(e) {}
  }
  try { return JSON.parse(localStorage.getItem('ls_materialOverrides') || '{}'); } catch(e) { return {}; }
}

async function _saveOverrides(){
  if(!_calcData || !_calcData.materiales) return;
  var overrides = _calcData.materiales.map(function(mat){
    return { nombre: mat.nombre, unidad: mat.unidad, cantidad: mat.cantidad, vr_unitario: mat.vr_unitario };
  });
  var map = {};
  overrides.forEach(function(o){ map[o.nombre] = o; });
  try { localStorage.setItem('ls_materialOverrides', JSON.stringify(map)); } catch(e) {}
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

async function apiFetch(url, opts){
  opts = opts || {};
  opts.headers = opts.headers || {};
  var t = localStorage.getItem('auth_token');
  if(t) opts.headers['Authorization'] = 'Bearer '+t;
  var r = await fetch(API+url, opts);
  if(t && r.status === 401){ logout(); throw new Error('Sesion expirada'); }
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

  const totalCount = document.getElementById('total-count');
  const adminWrap = document.getElementById('admin-table-wrap');
  const userWrap = document.getElementById('user-table-wrap');

  totalCount.style.display = 'inline-flex';
  if(_freeTierInfo && !isAdmin){
    totalCount.textContent = '📦 '+_verProds.length+' de '+_freeTierInfo.total+' insumos (10 x '+_freeTierInfo.categorias+' cat)';
  } else {
    totalCount.textContent = '📦 '+_verProds.length+' insumos';
  }
  document.getElementById('btn-sync').style.display = isAdmin ? '' : 'none';

  if(isAdmin && _viewMode === 'raw'){
    adminWrap.style.display = 'block'; userWrap.style.display = 'none';
    const tbody = document.getElementById('admin-ins-tbody');
    const empty = document.getElementById('admin-ins-empty');
    if(!filtrados.length){ tbody.innerHTML=''; empty.style.display='block'; }
    else {
      empty.style.display='none';
      tbody.innerHTML = filtrados.map(p => `<tr>
        <td>${escapeHtml(p.descripcion)}</td>
        <td>${escapeHtml(descripcionAjustada(p.descripcion,p.id,p.descripcion_ajustada))}</td>
        <td>${escapeHtml(p.unidad)}</td>
        <td style="font-weight:600;color:var(--accent)">$${Number(p.valor).toLocaleString('es-CO',{minimumFractionDigits:0})}${diffHtml(p)}</td>
        <td style="font-weight:600;color:var(--text2)">$${precioAjustado(p.valor,p.id).toLocaleString('es-CO')}${diffHtml(p)}</td>
        <td>${escapeHtml(p.proveedor||'')}</td>
      </tr>`).join('');
    }
  } else {
    adminWrap.style.display = 'none';
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