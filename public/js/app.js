/* Control de Arrobas · interfaz. La seguridad real está en el backend y en RLS; aquí solo se oculta lo que el rol no usa. */
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const enc = encodeURIComponent;
const fm = (n) => '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const ICONS = {
  home: '<path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/>', list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  sum: '<path d="M18 7V4H6l6 8-6 8h12v-3"/>', flag: '<path d="M4 22V4M4 4h14l-3 5 3 5H4"/>', hist: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>', chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0"/>', menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  plus: '<path d="M12 5v14M5 12h14"/>', edit: '<path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>', trash: '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
  pdf: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M12 12v6m-3-3l3 3 3-3"/>', out: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
  undo: '<path d="M3 7v6h6M3 13a9 9 0 1 0 3-7"/>', check: '<path d="M20 6L9 17l-5-5"/>', eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
  cmp: '<path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/>', send: '<path d="M22 2L11 13M22 2l-7 20-4-9-9-4z"/>'
};
const ic = (n) => `<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n] || ''}</svg>`;
const S = { user: null, cuts: [], cut: localStorage.getItem('ca_cut') || '', view: 'dashboard', unread: 0, f: { worker: '', fecha: '', q: '' }, h: { q: '', desde: '', hasta: '' }, w: { q: '', active: '' } };
const isAdmin = () => S.user && S.user.role === 'admin';
const curCut = () => S.cuts.find((c) => c.id === S.cut);
const today = () => new Date().toISOString().slice(0, 10);

/* ---------- UI helpers ---------- */
function toast(msg, kind = 'ok') {
  const t = document.createElement('div'); t.className = 'toast ' + kind; t.textContent = msg; $('#toasts').append(t);
  setTimeout(() => t.remove(), 4200);
}
function modal(title, body, { ok = 'Guardar', cancel = 'Cancelar', danger = false, onOpen } = {}) {
  return new Promise((resolve) => {
    const o = document.createElement('div'); o.className = 'overlay';
    o.innerHTML = `<div class="modal" role="dialog" aria-modal="true" aria-label="${esc(title)}"><h2>${esc(title)}</h2><form>${body}<div class="foot">${cancel ? `<button type="button" class="btn" data-x>${cancel}</button>` : ''}<button class="btn ${danger ? 'danger' : 'primary'}" type="submit">${ok}</button></div></form></div>`;
    $('#modal-root').append(o);
    const close = (v) => { o.remove(); resolve(v); };
    o.addEventListener('mousedown', (e) => { if (e.target === o) close(null); });
    o.querySelector('[data-x]')?.addEventListener('click', () => close(null));
    o.querySelector('form').addEventListener('submit', (e) => { e.preventDefault(); close(Object.fromEntries(new FormData(e.target).entries()) || {}); });
    o.querySelector('input:not([type=hidden]),select,textarea,button.primary')?.focus();
    onOpen && onOpen(o);
  });
}
const confirmBox = async (title, html, ok = 'Confirmar', danger = false) => (await modal(title, html, { ok, danger })) !== null;
const guard = (fn) => async (...a) => { try { return await fn(...a); } catch (e) { toast(e.message || 'Error', 'err'); } };
const table = (heads, rows, empty = 'Sin datos todavía') =>
  `<div class="tablewrap"><table><thead><tr>${heads.map((h) => `<th class="${h.num ? 'num' : ''}">${h.t || h}</th>`).join('')}</tr></thead><tbody>${rows.length ? rows.join('') : `<tr><td colspan="${heads.length}" class="empty">${empty}</td></tr>`}</tbody></table></div>`;
const statusBadge = (s) => `<span class="badge ${s === 'finalizado' ? 'ok' : 'warn'}">${s === 'finalizado' ? 'Finalizado' : 'Abierto'}</span>`;
const pdfBtn = (url, name, label = 'PDF') => `<button class="btn sm" data-pdf="${url}" data-name="${esc(name)}">${ic('pdf')}${label}</button>`;
function bindPdf(root) { root.querySelectorAll('[data-pdf]').forEach((b) => b.onclick = guard(async () => { await API.pdf(b.dataset.pdf, b.dataset.name); toast('PDF generado'); })); }
const noCut = () => `<div class="card empty">No hay un corte seleccionado.${isAdmin() ? ' <button class="btn primary" id="nc">' + ic('plus') + 'Crear corte</button>' : ' El administrador aún no ha creado cortes.'}</div>`;
const hookNc = () => $('#nc') && ($('#nc').onclick = newCut);

/* ---------- Sesión ---------- */
function showAuth(which = 'login') { $('#app').classList.add('hidden'); $('#auth').classList.remove('hidden'); $('#login-form').classList.toggle('hidden', which !== 'login'); $('#pass-form').classList.toggle('hidden', which !== 'pass'); }
function logout() { ['ca_token', 'ca_refresh'].forEach((k) => localStorage.removeItem(k)); S.user = null; showAuth(); }
window.addEventListener('ca-logout', () => { if (S.user) { toast('Tu sesión expiró. Inicia sesión de nuevo.', 'err'); logout(); } });
$('#logout').onclick = logout;
$('#login-form').onsubmit = guard(async (e) => {
  e.preventDefault(); const f = new FormData(e.target);
  const r = await API.post('/auth/login', { email: f.get('email'), password: f.get('password') });
  localStorage.setItem('ca_token', r.access_token); if (r.refresh_token) localStorage.setItem('ca_refresh', r.refresh_token);
  e.target.reset(); await boot();
});
$('#pass-form').onsubmit = guard(async (e) => {
  e.preventDefault(); const f = new FormData(e.target);
  if (f.get('p1') !== f.get('p2')) return toast('Las contraseñas no coinciden', 'err');
  const h = new URLSearchParams(location.hash.slice(1));
  const r = await API.post('/auth/set-password', { access_token: h.get('access_token'), password: f.get('p1') });
  history.replaceState(null, '', location.pathname);
  const s = await API.post('/auth/login', { email: r.email, password: f.get('p1') });
  localStorage.setItem('ca_token', s.access_token); if (s.refresh_token) localStorage.setItem('ca_refresh', s.refresh_token);
  toast('Contraseña creada. ¡Bienvenido!'); await boot();
});

async function boot() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get('access_token') && ['invite', 'recovery', 'signup'].includes(h.get('type'))) return showAuth('pass');
  if (!API.token()) return showAuth();
  try { S.user = await API.get('/me'); } catch (e) { return showAuth(); }
  $('#auth').classList.add('hidden'); $('#app').classList.remove('hidden');
  $('#who').textContent = `${S.user.email} · ${isAdmin() ? 'Administrador' : 'Lector'}`;
  $('#menu').innerHTML = ic('menu'); $('#bell').innerHTML = ic('bell');
  buildNav(); await loadCuts(); go(S.view); pollNotifs();
}
function buildNav() {
  const items = [['dashboard', 'home', 'Inicio'], ['diario', 'list', 'Registro Diario'], ['resumen', 'sum', 'Resumen por Trabajador']];
  if (isAdmin()) items.push(['finalizar', 'flag', 'Finalizar Corte']);
  items.push(['historial', 'hist', 'Historial de Cortes'], ['trabajadores', 'users', 'Trabajadores']);
  if (isAdmin()) items.push(['invitar', 'mail', 'Invitar Lectores']);
  items.push(['mensajes', 'chat', 'Mensajes y Observaciones']);
  $('#nav').innerHTML = items.map(([id, i, t]) => `<button data-v="${id}">${ic(i)}<span>${t}</span></button>`).join('');
  $('#nav').onclick = (e) => { const b = e.target.closest('button'); if (b) go(b.dataset.v); };
}
async function loadCuts() {
  S.cuts = await API.get('/cuts');
  if (!curCut()) S.cut = (S.cuts.find((c) => c.status === 'abierto') || S.cuts[0] || {}).id || '';
  localStorage.setItem('ca_cut', S.cut);
  $('#cut-select').innerHTML = S.cuts.length ? S.cuts.map((c) => `<option value="${c.id}" ${c.id === S.cut ? 'selected' : ''}>${esc(c.name)} (${c.status})</option>`).join('') : '<option value="">Sin cortes</option>';
}
$('#cut-select').onchange = (e) => { S.cut = e.target.value; localStorage.setItem('ca_cut', S.cut); go(S.view); };
$('#menu').onclick = () => $('#sidebar').classList.toggle('open');
$('#search-form').onsubmit = (e) => { e.preventDefault(); go('buscar'); };
const VIEWS = {};
async function go(v) {
  S.view = v; $('#sidebar').classList.remove('open');
  document.querySelectorAll('#nav button').forEach((b) => b.classList.toggle('on', b.dataset.v === v));
  const el = $('#view'); el.innerHTML = '<div class="empty">Cargando…</div>';
  try { await VIEWS[v](el); } catch (e) { el.innerHTML = `<div class="card empty">${esc(e.message)}</div>`; }
  el.focus({ preventScroll: true });
}

/* ---------- Notificaciones ---------- */
async function pollNotifs() {
  if (!S.user) return;
  try { const n = await API.get('/notifications'); S.notifs = n; S.unread = n.filter((x) => !x.read).length; $('#bell').innerHTML = ic('bell') + (S.unread ? `<span class="badge">${S.unread}</span>` : ''); } catch (e) {}
  clearTimeout(S.pt); S.pt = setTimeout(pollNotifs, 60000);
}
$('#bell').onclick = guard(async () => {
  const p = $('#notif-panel'); if (!p.classList.contains('hidden')) return p.classList.add('hidden');
  p.innerHTML = S.notifs.length ? S.notifs.map((n) => `<div class="n ${n.read ? '' : 'new'}">${esc(n.message)}<div class="muted small">${new Date(n.created_at).toLocaleString()}</div></div>`).join('') : '<div class="empty">Sin notificaciones</div>';
  p.classList.remove('hidden');
  if (S.unread) { await API.post('/notifications/read'); S.unread = 0; $('#bell').innerHTML = ic('bell'); }
});
document.addEventListener('click', (e) => { if (!e.target.closest('#notif-panel,#bell')) $('#notif-panel').classList.add('hidden'); });

/* ---------- Inicio ---------- */
VIEWS.dashboard = async (el) => {
  const [ws] = await Promise.all([API.get('/workers?active=true')]);
  const cut = curCut(); let sum = null, pend = 0;
  if (cut) sum = await API.get(`/cuts/${cut.id}/summary`);
  if (isAdmin()) pend = (await API.get('/comments?status=pendiente')).length;
  const stat = (l, v, hot) => `<div class="card stat ${hot ? 'hot' : ''}"><div class="l">${l}</div><div class="v">${v}</div></div>`;
  el.innerHTML = `<div class="head"><div><h1>Inicio</h1><div class="muted">${cut ? esc(cut.name) + ' · ' + statusBadge(cut.status) : 'Sin corte seleccionado'}</div></div>${isAdmin() ? `<button class="btn primary" id="nc2">${ic('plus')}Nuevo corte</button>` : ''}</div>
  <div class="cards">${stat('Total de arrobas del corte', sum ? sum.total_arrobas : '—', true)}${stat('Trabajadores activos', ws.length)}${stat('Trabajadores en el corte', sum ? sum.filas.length : '—')}${stat('Cortes registrados', S.cuts.length)}
  ${isAdmin() ? stat('Comentarios pendientes', pend) : ''}${isAdmin() && sum && sum.total_dinero !== undefined ? stat('Dinero del corte', fm(sum.total_dinero)) : ''}</div>
  ${sum ? `<h2>Top del corte</h2>${table(['Nombre y apellido', { t: 'Total de arrobas', num: 1 }], [...sum.filas].sort((a, b) => b.total - a.total).slice(0, 5).map((r) => `<tr><td>${esc(r.nombre)}</td><td class="num">${r.total_txt}</td></tr>`))}` : noCut()}`;
  $('#nc2') && ($('#nc2').onclick = newCut); hookNc();
};

/* ---------- Nuevo corte ---------- */
async function newCut() {
  const ws = (await API.get('/workers?active=true'));
  const r = await modal('Nuevo corte', `<label>Nombre<input name="name" value="Corte ${today()}" required></label><label>Fecha de inicio<input type="date" name="start_date" value="${today()}" required></label>
  <div><div class="muted small" style="margin-bottom:6px">Trabajadores del corte (permanentes, reutilizables)</div>${ws.length ? `<label style="flex-direction:row;gap:8px;align-items:center"><input type="checkbox" id="all" checked>Seleccionar todos</label>` : '<div class="muted">Aún no hay trabajadores. Agrégalos en Trabajadores.</div>'}
  ${ws.map((w) => `<label style="flex-direction:row;gap:8px;align-items:center"><input type="checkbox" name="w_${w.id}" checked>${esc(w.full_name)}</label>`).join('')}</div>`,
    { ok: 'Crear corte', onOpen: (o) => { const a = o.querySelector('#all'); a && (a.onchange = () => o.querySelectorAll('input[name^=w_]').forEach((c) => (c.checked = a.checked))); } });
  if (!r) return;
  await guard(async () => {
    const c = await API.post('/cuts', { name: r.name, start_date: r.start_date, worker_ids: Object.keys(r).filter((k) => k.startsWith('w_')).map((k) => k.slice(2)) });
    S.cut = c.id; localStorage.setItem('ca_cut', c.id); await loadCuts(); toast('Corte creado'); go('diario');
  })();
}

/* ---------- Registro diario ---------- */
VIEWS.diario = async (el) => {
  const cut = curCut(); if (!cut) { el.innerHTML = noCut(); return hookNc(); }
  const cd = await API.get('/cuts/' + cut.id); const f = S.f;
  el.innerHTML = `<div class="head"><div><h1>Registro Diario</h1><div class="muted">${esc(cut.name)} · ${statusBadge(cut.status)}</div></div>
  <div class="actions">${isAdmin() && cut.status === 'abierto' ? `<button class="btn primary" id="add">${ic('plus')}Agregar registro</button>` : ''}${pdfBtn(`/reports/cut/${cut.id}/diario`, 'registro_diario', 'PDF diario')}</div></div>
  <div class="filters"><select id="fw"><option value="">Todos los trabajadores</option>${cd.workers.map((w) => `<option value="${w.id}" ${f.worker === w.id ? 'selected' : ''}>${esc(w.full_name)}</option>`).join('')}</select>
  <input type="date" id="ff" value="${f.fecha}" aria-label="Filtrar por fecha"><input type="search" id="fq" placeholder="Buscar por nombre" value="${esc(f.q)}"><button class="btn" id="fc">Limpiar filtros</button></div>
  <div id="tbl"></div><div id="daily" class="card" style="margin-top:14px"></div>`;
  bindPdf(el);
  const load = guard(async () => {
    const d = await API.get(`/cuts/${cut.id}/records?worker_id=${f.worker}&fecha=${f.fecha}&q=${enc(f.q)}`);
    const canEdit = isAdmin() && cut.status === 'abierto';
    $('#tbl').innerHTML = table(['N°', 'Nombre y apellido', 'Fecha', 'Día', 'Año', { t: 'Arrobas', num: 1 }, { t: 'Medias arrobas', num: 1 }, { t: 'Total de arrobas', num: 1 }, 'Estado', ...(canEdit ? ['Acciones'] : [])],
      d.registros.map((r) => `<tr class="${r.ausente ? 'absent' : ''}"><td>${r.n}</td><td>${esc(r.nombre)}</td><td>${r.fecha}</td><td>${r.dia}</td><td>${r.anio}</td><td class="num">${r.arrobas}</td><td class="num">${r.medias_txt}</td><td class="num"><b>${r.total_txt}</b></td>
      <td>${r.ausente ? '<span class="badge warn">AUSENTE</span>' : '<span class="badge ok">Activo</span>'}</td>${canEdit ? `<td><div class="row-actions"><button class="btn sm" data-e="${r.id}" aria-label="Editar">${ic('edit')}</button><button class="btn sm danger" data-d="${r.id}" aria-label="Eliminar">${ic('trash')}</button></div></td>` : ''}</tr>`), 'No hay registros con estos filtros');
    const days = Object.entries(d.totales_diarios);
    $('#daily').innerHTML = `<b>Total general de arrobas: ${d.total_general}</b>${days.length ? `<div class="muted small" style="margin-top:6px">Totales por día: ${days.map(([k, v]) => `${k}: <b>${v}</b>`).join(' · ')}</div>` : ''}`;
    $('#tbl').onclick = (e) => {
      const eb = e.target.closest('[data-e]'), db = e.target.closest('[data-d]');
      if (eb) recordForm(cd, d.registros.find((r) => r.id === eb.dataset.e), load);
      if (db) guard(async () => { if (await confirmBox('Eliminar registro', '<p>¿Eliminar este registro? Esta acción no se puede deshacer.</p>', 'Eliminar', true)) { await API.del('/records/' + db.dataset.d); toast('Registro eliminado'); load(); } })();
    };
  });
  $('#fw').onchange = (e) => { f.worker = e.target.value; load(); }; $('#ff').onchange = (e) => { f.fecha = e.target.value; load(); };
  let t; $('#fq').oninput = (e) => { f.q = e.target.value; clearTimeout(t); t = setTimeout(load, 250); };
  $('#fc').onclick = () => { S.f = { worker: '', fecha: '', q: '' }; VIEWS.diario(el); };
  $('#add') && ($('#add').onclick = () => recordForm(cd, null, load));
  load();
};
async function recordForm(cd, rec, reload) {
  const ws = cd.workers.filter((w) => w.active || (rec && w.id === rec.worker_id));
  const r = await modal(rec ? 'Editar registro' : 'Agregar registro', `<label>Trabajador<select name="worker_id" required>${ws.map((w) => `<option value="${w.id}" ${rec && rec.worker_id === w.id ? 'selected' : ''}>${esc(w.full_name)}</option>`).join('')}</select></label>
  <label>Fecha<input type="date" name="work_date" value="${rec ? rec.fecha : today()}" required></label>
  <div class="filters" style="margin:0"><label>Arrobas completas<input type="number" name="full_count" min="0" step="1" value="${rec ? rec.arrobas : 0}" required></label><label>Medias arrobas (½)<input type="number" name="half_count" min="0" step="1" value="${rec ? rec.medias : 0}" required></label></div>
  <label style="flex-direction:row;gap:8px;align-items:center"><input type="checkbox" name="absent" ${rec && rec.ausente ? 'checked' : ''}>Ausente (total del día en cero)</label><div id="pv" class="muted"></div>`,
    { onOpen: (o) => { const upd = () => { const a = +o.querySelector('[name=full_count]').value || 0, m = +o.querySelector('[name=half_count]').value || 0, ab = o.querySelector('[name=absent]').checked, t = ab ? 0 : a + m / 2;
      o.querySelector('#pv').innerHTML = `Total: <b>${ab ? 'AUSENTE' : (Math.floor(t) + (t % 1 ? ' ½' : '')).replace(/^0 ½$/, '½')}</b> (${t} arrobas)`; o.querySelectorAll('[name=full_count],[name=half_count]').forEach((i) => (i.disabled = ab)); }; o.addEventListener('input', upd); upd(); } });
  if (!r) return;
  const body = { worker_id: r.worker_id, work_date: r.work_date, absent: !!r.absent, full_count: r.absent ? 0 : parseInt(r.full_count ?? 0, 10) || 0, half_count: r.absent ? 0 : parseInt(r.half_count ?? 0, 10) || 0 };
  await guard(async () => { rec ? await API.put('/records/' + rec.id, body) : await API.post(`/cuts/${cd.id}/records`, body); toast('Registro guardado'); reload(); })();
}

/* ---------- Resumen ---------- */
VIEWS.resumen = async (el) => {
  const cut = curCut(); if (!cut) { el.innerHTML = noCut(); return hookNc(); }
  const price = S.prev || '';
  const d = await API.get(`/cuts/${cut.id}/summary${isAdmin() && cut.status === 'abierto' && price ? '?price=' + enc(price) : ''}`);
  const money = isAdmin() && d.precio !== undefined;
  el.innerHTML = `<div class="head"><div><h1>Resumen por Trabajador</h1><div class="muted">${esc(cut.name)} · ${statusBadge(cut.status)}</div></div>
  <div class="actions">${pdfBtn(`/reports/cut/${cut.id}/resumen`, 'resumen_arrobas', 'PDF resumen')}${isAdmin() && cut.status === 'finalizado' ? pdfBtn(`/reports/cut/${cut.id}/dinero`, 'resumen_dinero', 'PDF dinero') : ''}${pdfBtn(`/reports/cut/${cut.id}/completo`, 'reporte_corte', 'PDF del corte')}</div></div>
  ${isAdmin() && cut.status === 'abierto' ? `<div class="filters"><label>Precio de una arroba para vista previa<input id="pv" type="number" min="0" step="0.01" value="${esc(price)}" placeholder="Ej. 12.00"></label></div>` : ''}
  ${table(['N°', 'Nombre y apellido', { t: 'Total de arrobas', num: 1 }, ...(money ? [{ t: 'Total de dinero', num: 1 }] : []), 'Estado'],
    d.filas.map((r, i) => `<tr><td>${i + 1}</td><td>${esc(r.nombre)}</td><td class="num"><b>${r.total_txt}</b></td>${money ? `<td class="num">${fm(r.dinero)}</td>` : ''}<td><span class="badge ${r.estado === 'Activo' ? 'ok' : 'off'}">${r.estado}</span>${r.ausencias ? ` <span class="badge warn">${r.ausencias} ausencia${r.ausencias > 1 ? 's' : ''}</span>` : ''}</td></tr>`))}
  <div class="card" style="margin-top:14px"><b>Total general de arrobas: ${d.total_arrobas}</b>${money ? ` · <b>Total de dinero: ${fm(d.total_dinero)}</b>` : ''}</div>`;
  bindPdf(el); const pv = $('#pv'); pv && (pv.onchange = () => { S.prev = pv.value; VIEWS.resumen(el); });
};

/* ---------- Finalizar corte (solo admin) ---------- */
VIEWS.finalizar = async (el) => {
  const cut = curCut(); if (!cut) { el.innerHTML = noCut(); return hookNc(); }
  const cd = await API.get('/cuts/' + cut.id);
  if (cut.status === 'finalizado') {
    const f = cd.finance; const d = await API.get(`/cuts/${cut.id}/summary`);
    el.innerHTML = `<div class="head"><h1>Corte finalizado</h1></div><div class="finalize"><h2>${esc(cut.name)}</h2><div class="muted">Cerrado el ${new Date(f.closed_at).toLocaleString()}</div>
    <div class="kv"><span>Trabajadores</span><b>${f.total_workers}</b><span>Total de arrobas</span><b>${d.total_arrobas}</b><span>Precio por arroba</span><b>${fm(f.price_per_arroba)}</b><span>Precio por media arroba</span><b>${fm(f.price_per_arroba / 2)}</b><span>Total de dinero</span><b>${fm(f.total_money)}</b></div>
    <button class="btn danger" id="reopen">${ic('undo')}Reabrir corte</button></div>`;
    $('#reopen').onclick = guard(async () => { if (await confirmBox('Reabrir corte', '<p>El corte volverá a estar abierto, se eliminarán sus resultados monetarios actuales y quedará registrado en la bitácora de auditoría con el precio y total anteriores.</p>', 'Reabrir', true)) { await API.post(`/cuts/${cut.id}/reopen`); await loadCuts(); toast('Corte reabierto'); go('diario'); } });
    return;
  }
  el.innerHTML = `<div class="head"><h1>Finalizar corte</h1></div><div class="finalize"><h2>${esc(cut.name)}</h2><p class="muted">Introduce el precio de una arroba. La media arroba siempre vale exactamente la mitad.</p>
  <div class="filters"><label>Precio de una arroba ($)<input id="price" type="number" min="0" step="0.01" placeholder="12.00"></label><label>Precio de media arroba (automático)<input id="half" readonly value="—"></label></div>
  <div id="prev" class="kv"></div><button class="btn primary" id="fin" disabled>${ic('flag')}FINALIZAR CORTE</button></div>`;
  let t; const price = $('#price');
  price.oninput = () => { clearTimeout(t); $('#fin').disabled = true; t = setTimeout(guard(async () => {
    if (!price.value) { $('#half').value = '—'; $('#prev').innerHTML = ''; return; }
    const p = await API.get(`/cuts/${cut.id}/finalize-preview?price=${enc(price.value)}`);
    $('#half').value = fm(p.precio_media); $('#prev').innerHTML = `<span>Trabajadores</span><b>${p.trabajadores}</b><span>Total de arrobas</span><b>${p.total_arrobas}</b><span>Total de dinero</span><b>${fm(p.total_dinero)}</b>`; $('#fin').disabled = false; S.prevData = p;
  }), 300); };
  $('#fin').onclick = guard(async () => {
    const p = await API.get(`/cuts/${cut.id}/finalize-preview?price=${enc(price.value)}`);
    const ok = await confirmBox('¿Finalizar el corte?', `<div class="kv"><span>Cantidad de trabajadores</span><b>${p.trabajadores}</b><span>Total general de arrobas</span><b>${p.total_arrobas}</b><span>Precio por arroba</span><b>${fm(p.precio)}</b><span>Total de dinero</span><b>${fm(p.total_dinero)}</b><span>Fecha del cierre</span><b>${p.fecha_cierre}</b></div><p class="muted">Los registros quedarán bloqueados hasta que reabras el corte.</p>`, 'Finalizar corte');
    if (!ok) return; await API.post(`/cuts/${cut.id}/finalize`, { price: price.value }); await loadCuts(); toast('Corte finalizado'); go('finalizar');
  });
};

/* ---------- Historial ---------- */
VIEWS.historial = async (el) => {
  const h = S.h;
  el.innerHTML = `<div class="head"><div><h1>Historial de Cortes</h1></div><div class="actions">${isAdmin() ? `<button class="btn primary" id="nc3">${ic('plus')}Nuevo corte</button>${pdfBtn('/reports/historial', 'historial_cortes', 'PDF historial')}` : ''}<button class="btn" id="cmp">${ic('cmp')}Comparar</button></div></div>
  <div class="filters"><input type="search" id="hq" placeholder="Buscar por nombre o fecha (AAAA-MM-DD)" value="${esc(h.q)}"><label>Desde<input type="date" id="hd" value="${h.desde}"></label><label>Hasta<input type="date" id="hh" value="${h.hasta}"></label></div><div id="ht"></div>`;
  bindPdf(el);
  const load = guard(async () => {
    const cuts = await API.get(`/cuts?q=${enc(h.q)}&desde=${h.desde}&hasta=${h.hasta}`);
    $('#ht').innerHTML = table(['ID', 'Corte', 'Inicio', 'Fin', 'Estado', { t: 'Trabajadores', num: 1 }, { t: 'Arrobas', num: 1 }, ...(isAdmin() ? [{ t: 'Precio', num: 1 }, { t: 'Total dinero', num: 1 }] : []), 'Acciones'],
      cuts.map((c) => `<tr><td>${c.id.slice(0, 8)}</td><td>${esc(c.name)}</td><td>${c.start_date}</td><td>${c.end_date || '—'}</td><td>${statusBadge(c.status)}</td><td class="num">${c.trabajadores}</td><td class="num">${c.total_txt}</td>
      ${isAdmin() ? `<td class="num">${c.precio !== undefined ? fm(c.precio) : '—'}</td><td class="num">${c.total_dinero !== undefined ? fm(c.total_dinero) : '—'}</td>` : ''}
      <td><div class="row-actions"><button class="btn sm" data-view="${c.id}">${ic('eye')}Ver</button>${pdfBtn(`/reports/cut/${c.id}/completo`, 'corte_' + c.name.replace(/\s+/g, '_'), 'PDF')}${isAdmin() && c.status === 'finalizado' ? `<button class="btn sm danger" data-reopen="${c.id}">${ic('undo')}Reabrir</button>` : ''}</div></td></tr>`), 'No hay cortes');
    bindPdf($('#ht'));
    $('#ht').onclick = guard(async (e) => {
      const v = e.target.closest('[data-view]'), r = e.target.closest('[data-reopen]');
      if (v) { S.cut = v.dataset.view; localStorage.setItem('ca_cut', S.cut); await loadCuts(); go('diario'); }
      if (r && await confirmBox('Reabrir corte', '<p>Se eliminarán los resultados monetarios actuales; quedará registrado en la auditoría.</p>', 'Reabrir', true)) { await API.post(`/cuts/${r.dataset.reopen}/reopen`); await loadCuts(); toast('Corte reabierto'); load(); }
    });
  });
  let t; $('#hq').oninput = (e) => { h.q = e.target.value; clearTimeout(t); t = setTimeout(load, 250); }; $('#hd').onchange = (e) => { h.desde = e.target.value; load(); }; $('#hh').onchange = (e) => { h.hasta = e.target.value; load(); };
  $('#nc3') && ($('#nc3').onclick = newCut);
  $('#cmp').onclick = guard(async () => {
    if (S.cuts.length < 2) return toast('Necesitas al menos dos cortes para comparar', 'err');
    const opts = S.cuts.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join('');
    const r = await modal('Comparar cortes', `<label>Corte A<select name="a">${opts}</select></label><label>Corte B<select name="b">${opts}</select></label>`, { ok: 'Comparar' }); if (!r) return;
    if (r.a === r.b) return toast('Elige dos cortes distintos', 'err');
    const [A, B, dif] = await API.get(`/compare?a=${r.a}&b=${r.b}`);
    const money = isAdmin();
    await modal('Comparación', table(['', 'A', 'B'], [['Corte', A.nombre, B.nombre], ['Estado', A.estado, B.estado], ['Trabajadores', A.trabajadores, B.trabajadores], ['Total de arrobas', A.total_txt, B.total_txt], ...(money ? [['Precio', A.precio !== undefined ? fm(A.precio) : '—', B.precio !== undefined ? fm(B.precio) : '—'], ['Total de dinero', A.total_dinero !== undefined ? fm(A.total_dinero) : '—', B.total_dinero !== undefined ? fm(B.total_dinero) : '—']] : [])].map((x) => `<tr>${x.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`)) + `<p>Diferencia de arrobas (B − A): <b>${dif.diferencia_arrobas}</b></p>`, { ok: 'Cerrar', cancel: '' });
  });
  load();
};

/* ---------- Trabajadores ---------- */
VIEWS.trabajadores = async (el) => {
  const w = S.w;
  el.innerHTML = `<div class="head"><h1>Trabajadores</h1>${isAdmin() ? `<button class="btn primary" id="aw">${ic('plus')}Agregar trabajador</button>` : ''}</div>
  <div class="filters"><input type="search" id="wq" placeholder="Buscar por nombre o apellido" value="${esc(w.q)}"><select id="wa"><option value="">Todos</option><option value="true">Activos</option><option value="false">Inactivos</option></select></div><div id="wt"></div>`;
  $('#wa').value = w.active;
  const load = guard(async () => {
    const list = await API.get(`/workers?q=${enc(w.q)}&active=${w.active}`);
    $('#wt').innerHTML = table(['N°', 'Nombre', 'Apellido', 'Estado', 'Creado', 'Acciones'], list.map((x, i) => `<tr><td>${i + 1}</td><td>${esc(x.first_name)}</td><td>${esc(x.last_name)}</td><td><span class="badge ${x.active ? 'ok' : 'off'}">${x.active ? 'Activo' : 'Inactivo'}</span></td><td>${x.created_at.slice(0, 10)}</td>
      <td><div class="row-actions"><button class="btn sm" data-h="${x.id}" data-n="${esc(x.full_name)}">${ic('hist')}Historial</button>${isAdmin() ? `<button class="btn sm" data-e="${x.id}">${ic('edit')}</button><button class="btn sm ${x.active ? 'danger' : ''}" data-t="${x.id}" data-a="${x.active}">${x.active ? 'Desactivar' : 'Reactivar'}</button>` : ''}</div></td></tr>`), 'No hay trabajadores');
    $('#wt').onclick = guard(async (e) => {
      const hb = e.target.closest('[data-h]'), eb = e.target.closest('[data-e]'), tb = e.target.closest('[data-t]');
      if (hb) { const d = await API.get(`/workers/${hb.dataset.h}/history`); await modal('Historial · ' + hb.dataset.n, table(['Corte', 'Fecha', 'Día', { t: 'Total', num: 1 }], d.registros.map((r) => `<tr><td>${esc(r.corte)}</td><td>${r.fecha}</td><td>${r.dia}</td><td class="num">${r.total_txt}</td></tr>`), 'Sin historial') + `<p><b>Total acumulado: ${d.total_txt} arrobas</b></p>`, { ok: 'Cerrar', cancel: '' }); }
      if (eb) workerForm(list.find((x) => x.id === eb.dataset.e), load);
      if (tb) { const act = tb.dataset.a === 'true'; if (!act || await confirmBox('Desactivar trabajador', '<p>El historial se conserva. No aparecerá para nuevos registros.</p>', 'Desactivar', true)) { await API.patch(`/workers/${tb.dataset.t}/active`, { active: !act }); toast(act ? 'Trabajador desactivado' : 'Trabajador reactivado'); load(); } }
    });
  });
  let t; $('#wq').oninput = (e) => { w.q = e.target.value; clearTimeout(t); t = setTimeout(load, 250); }; $('#wa').onchange = (e) => { w.active = e.target.value; load(); };
  $('#aw') && ($('#aw').onclick = () => workerForm(null, load)); load();
};
async function workerForm(x, reload) {
  const r = await modal(x ? 'Editar trabajador' : 'Agregar trabajador', `<label>Nombre<input name="first_name" value="${esc(x?.first_name)}" required></label><label>Apellido<input name="last_name" value="${esc(x?.last_name)}" required></label>`); if (!r) return;
  await guard(async () => { x ? await API.put('/workers/' + x.id, r) : await API.post('/workers', r); toast('Trabajador guardado'); reload(); })();
}

/* ---------- Invitar lectores ---------- */
VIEWS.invitar = async (el) => {
  const inv = await API.get('/invitations');
  el.innerHTML = `<div class="head"><div><h1>Invitar Lectores</h1><div class="muted">Los invitados reciben un correo para crear su contraseña y entran siempre como lectores.</div></div></div>
  <form class="card filters" id="inv"><input type="email" name="email" placeholder="correo@ejemplo.com" required><button class="btn primary" type="submit">${ic('send')}Enviar invitación</button></form>
  ${table(['Correo', 'Estado', 'Fecha', 'Acciones'], inv.map((i) => `<tr><td>${esc(i.email)}</td><td><span class="badge ${i.status === 'aceptada' ? 'ok' : i.status === 'pendiente' ? 'warn' : 'off'}">${i.status}</span></td><td>${i.created_at.slice(0, 10)}</td><td>${i.status !== 'revocada' ? `<button class="btn sm danger" data-r="${i.id}">Revocar acceso</button>` : ''}</td></tr>`), 'No hay invitaciones')}`;
  $('#inv').onsubmit = guard(async (e) => { e.preventDefault(); await API.post('/invitations', { email: new FormData(e.target).get('email') }); toast('Invitación enviada'); VIEWS.invitar(el); });
  el.onclick = guard(async (e) => { const b = e.target.closest('[data-r]'); if (b && await confirmBox('Revocar acceso', '<p>El lector perderá el acceso de inmediato.</p>', 'Revocar', true)) { await API.del('/invitations/' + b.dataset.r); toast('Acceso revocado'); VIEWS.invitar(el); } });
};

/* ---------- Mensajes ---------- */
VIEWS.mensajes = async (el) => {
  const st = S.mst || ''; const list = await API.get('/comments' + (st ? '?status=' + st : ''));
  const cuts = S.cuts, ws = isAdmin() ? [] : await API.get('/workers');
  el.innerHTML = `<div class="head"><h1>Mensajes y Observaciones</h1><select id="ms" style="width:200px"><option value="">Todos</option><option value="pendiente">Pendientes</option><option value="respondido">Respondidos</option></select></div>
  ${isAdmin() ? '' : `<form class="card" id="cf" style="display:flex;flex-direction:column;gap:10px;margin-bottom:16px"><h2>Enviar comentario al administrador</h2><textarea name="body" rows="3" maxlength="2000" required placeholder="Ej.: Falta registrar media arroba de Juan Pérez el día 15"></textarea>
  <div class="filters" style="margin:0"><select name="cut_id"><option value="">Corte (opcional)</option>${cuts.map((c) => `<option value="${c.id}">${esc(c.name)}</option>`).join('')}</select><select name="worker_id"><option value="">Trabajador (opcional)</option>${ws.map((w) => `<option value="${w.id}">${esc(w.full_name)}</option>`).join('')}</select><input type="date" name="record_date" aria-label="Fecha relacionada"></div><div><button class="btn primary" type="submit">${ic('send')}Enviar</button></div></form>`}
  ${list.length ? list.map((c) => `<div class="card" style="margin-bottom:12px"><div class="actions" style="justify-content:space-between"><div><span class="badge ${c.status === 'pendiente' ? 'warn' : 'ok'}">${c.status}</span> ${c.cuts ? `<span class="tag">${esc(c.cuts.name)}</span>` : ''}${c.workers ? `<span class="tag">${esc(c.workers.full_name)}</span>` : ''}${c.record_date ? `<span class="tag">${c.record_date}</span>` : ''}</div>${isAdmin() ? `<button class="btn sm" data-s="${c.id}" data-v="${c.status === 'pendiente' ? 'respondido' : 'pendiente'}">Marcar ${c.status === 'pendiente' ? 'respondido' : 'pendiente'}</button>` : ''}</div>
  <div class="chat"><div class="msg"><div class="meta">${esc(c.profiles?.email || '')} · ${new Date(c.created_at).toLocaleString()}</div>${esc(c.body)}</div>${c.replies.map((r) => `<div class="msg admin"><div class="meta">${esc(r.profiles?.email || 'Administrador')} (Administrador) · ${new Date(r.created_at).toLocaleString()}</div>${esc(r.body)}</div>`).join('')}</div>
  ${isAdmin() ? `<form data-reply="${c.id}" class="actions"><input name="body" placeholder="Escribe una respuesta" required style="flex:1;min-width:200px"><button class="btn primary sm" type="submit">Responder</button></form>` : ''}</div>`).join('') : '<div class="card empty">No hay mensajes</div>'}`;
  $('#ms').value = st; $('#ms').onchange = (e) => { S.mst = e.target.value; VIEWS.mensajes(el); };
  $('#cf') && ($('#cf').onsubmit = guard(async (e) => { e.preventDefault(); const f = Object.fromEntries(new FormData(e.target)); await API.post('/comments', { body: f.body, cut_id: f.cut_id || null, worker_id: f.worker_id || null, record_date: f.record_date || null }); toast('Comentario enviado'); VIEWS.mensajes(el); }));
  el.querySelectorAll('[data-reply]').forEach((f) => (f.onsubmit = guard(async (e) => { e.preventDefault(); await API.post(`/comments/${f.dataset.reply}/replies`, { body: new FormData(f).get('body') }); toast('Respuesta enviada'); VIEWS.mensajes(el); })));
  el.querySelectorAll('[data-s]').forEach((b) => (b.onclick = guard(async () => { await API.patch(`/comments/${b.dataset.s}/status`, { status: b.dataset.v }); VIEWS.mensajes(el); })));
};

/* ---------- Búsqueda ---------- */
VIEWS.buscar = async (el) => {
  const q = $('#search').value.trim(); const d = await API.get('/search?q=' + enc(q));
  el.innerHTML = `<div class="head"><h1>Resultados para «${esc(q)}»</h1></div><h2>Trabajadores</h2>${table(['Nombre', 'Estado'], d.trabajadores.map((w) => `<tr><td>${esc(w.full_name)}</td><td>${w.active ? 'Activo' : 'Inactivo'}</td></tr>`), 'Sin coincidencias')}
  <h2 style="margin-top:18px">Cortes</h2>${table(['Corte', 'Inicio', 'Fin', 'Estado', ''], d.cortes.map((c) => `<tr><td>${esc(c.name)}</td><td>${c.start_date}</td><td>${c.end_date || '—'}</td><td>${statusBadge(c.status)}</td><td><button class="btn sm" data-c="${c.id}">Abrir</button></td></tr>`), 'Sin coincidencias')}
  <h2 style="margin-top:18px">Registros</h2>${table(['Corte', 'Nombre', 'Fecha', 'Día', { t: 'Total', num: 1 }], d.registros.map((r) => `<tr><td>${esc(r.corte)}</td><td>${esc(r.nombre)}</td><td>${r.fecha}</td><td>${r.dia}</td><td class="num">${r.total_txt}</td></tr>`), 'Sin coincidencias')}`;
  el.onclick = guard(async (e) => { const b = e.target.closest('[data-c]'); if (b) { S.cut = b.dataset.c; localStorage.setItem('ca_cut', S.cut); await loadCuts(); go('diario'); } });
};

boot();
