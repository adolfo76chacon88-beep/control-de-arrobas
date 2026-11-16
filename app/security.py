from fastapi import Depends, Header, HTTPException
from . import config
from .services import db


def current_user(authorization: str = Header(default="")):
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "No autenticado")
    u = db.auth_user(authorization[7:])
    if not u:
        raise HTTPException(401, "Sesión inválida o expirada")
    rows = db.select("profiles", {"id": f"eq.{u['id']}", "select": "*"})
    if not rows or not rows[0]["active"]:
        raise HTTPException(403, "Acceso revocado o sin perfil")
    p = rows[0]
    # Doble verificación: admin solo si rol admin Y correo principal
    is_admin = p["role"] == "admin" and p["email"].lower() == config.ADMIN_EMAIL
    return {"id": p["id"], "email": p["email"], "role": "admin" if is_admin else "lector"}


def require_admin(user=Depends(current_user)):
    if user["role"] != "admin":
        raise HTTPException(403, "Solo el administrador puede realizar esta acción")
    return user
