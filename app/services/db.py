"""Cliente mínimo de Supabase (PostgREST + Auth) con httpx. Usa la service key SOLO en el backend."""
import httpx
from fastapi import HTTPException
from .. import config

_c = httpx.Client(timeout=20)


def _h(key=None, token=None, extra=None):
    key = key or config.SUPABASE_SERVICE_ROLE_KEY
    h = {"apikey": key, "Authorization": f"Bearer {token or key}", "Content-Type": "application/json"}
    h.update(extra or {})
    return h


def _check(r):
    if r.status_code >= 400:
        try:
            j = r.json()
            msg = j.get("message") or j.get("msg") or r.text
        except Exception:
            msg = r.text
        code = 409 if r.status_code == 409 or "duplicate" in msg.lower() else 400
        raise HTTPException(code, msg)
    return r


def select(table, params=None):
    return _check(_c.get(f"{config.SUPABASE_URL}/rest/v1/{table}", params=params or {}, headers=_h())).json()


def insert(table, data):
    r = _check(_c.post(f"{config.SUPABASE_URL}/rest/v1/{table}", json=data,
                       headers=_h(extra={"Prefer": "return=representation"})))
    return r.json()


def update(table, match, data):
    r = _check(_c.patch(f"{config.SUPABASE_URL}/rest/v1/{table}", params=match, json=data,
                        headers=_h(extra={"Prefer": "return=representation"})))
    return r.json()


def delete(table, match):
    _check(_c.delete(f"{config.SUPABASE_URL}/rest/v1/{table}", params=match, headers=_h()))


def rpc(fn, args):
    return _check(_c.post(f"{config.SUPABASE_URL}/rest/v1/rpc/{fn}", json=args, headers=_h())).json()


# ---- Auth ----
def auth_user(token):
    r = _c.get(f"{config.SUPABASE_URL}/auth/v1/user", headers=_h(key=config.SUPABASE_ANON_KEY, token=token))
    return r.json() if r.status_code == 200 else None


def auth_login(email, password):
    r = _c.post(f"{config.SUPABASE_URL}/auth/v1/token", params={"grant_type": "password"},
                json={"email": email, "password": password}, headers=_h(key=config.SUPABASE_ANON_KEY))
    if r.status_code != 200:
        raise HTTPException(401, "Correo o contraseña incorrectos")
    return r.json()


def auth_refresh(refresh_token):
    r = _c.post(f"{config.SUPABASE_URL}/auth/v1/token", params={"grant_type": "refresh_token"},
                json={"refresh_token": refresh_token}, headers=_h(key=config.SUPABASE_ANON_KEY))
    if r.status_code != 200:
        raise HTTPException(401, "Sesión expirada")
    return r.json()


def auth_invite(email):
    # Supabase envía el correo (SMTP/Resend configurado en el panel) y redirige al sitio para crear contraseña.
    r = _c.post(f"{config.SUPABASE_URL}/auth/v1/invite", params={"redirect_to": config.SITE_URL},
                json={"email": email}, headers=_h())
    return _check(r).json()


def auth_set_password(token, password):
    r = _c.put(f"{config.SUPABASE_URL}/auth/v1/user", json={"password": password},
               headers=_h(key=config.SUPABASE_ANON_KEY, token=token))
    if r.status_code != 200:
        raise HTTPException(400, "No se pudo guardar la contraseña (mínimo 8 caracteres)")


def auth_delete_user(user_id):
    _check(_c.delete(f"{config.SUPABASE_URL}/auth/v1/admin/users/{user_id}", headers=_h()))
