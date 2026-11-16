const API = {
  token: () => localStorage.getItem('ca_token'),
  async refresh() {
    const rt = localStorage.getItem('ca_refresh');
    if (!rt) return false;
    const r = await fetch('/api/auth/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: rt }) });
    if (!r.ok) return false;
    const j = await r.json();
    localStorage.setItem('ca_token', j.access_token);
    if (j.refresh_token) localStorage.setItem('ca_refresh', j.refresh_token);
    return true;
  },
  async raw(method, url, body, retry = true) {
    const r = await fetch('/api' + url, {
      method, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (API.token() || '') },
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    if (r.status === 401 && retry && (await API.refresh())) return API.raw(method, url, body, false);
    if (r.status === 401) { window.dispatchEvent(new Event('ca-logout')); }
    return r;
  },
  async call(method, url, body) {
    const r = await API.raw(method, url, body);
    let j = null; try { j = await r.json(); } catch (e) {}
    if (!r.ok) throw new Error((j && (typeof j.detail === 'string' ? j.detail : 'Datos inválidos')) || 'Error del servidor');
    return j;
  },
  get: (u) => API.call('GET', u), post: (u, b) => API.call('POST', u, b || {}),
  put: (u, b) => API.call('PUT', u, b), patch: (u, b) => API.call('PATCH', u, b), del: (u) => API.call('DELETE', u),
  async pdf(url, name) {
    const r = await API.raw('GET', url);
    if (!r.ok) { let m = 'No se pudo generar el PDF'; try { m = (await r.json()).detail || m; } catch (e) {} throw new Error(m); }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(await r.blob()); a.download = name + '.pdf'; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }
};
