from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..security import current_user
from ..services import db
from ..services.util import notify_admin

router = APIRouter(prefix="/api", tags=["auth"])


class Login(BaseModel):
    email: str
    password: str


class SetPassword(BaseModel):
    access_token: str
    password: str


def _accept_invitation(user):
    inv = db.select("invitations", {"email": f"eq.{user['email'].lower()}", "status": "eq.pendiente", "select": "id"})
    if inv:
        db.update("invitations", {"id": f"eq.{inv[0]['id']}"}, {"status": "aceptada", "user_id": user["id"]})
        notify_admin("invitacion", f"{user['email']} aceptó la invitación")


@router.post("/auth/login")
def login(b: Login):
    s = db.auth_login(b.email.strip().lower(), b.password)
    u = db.auth_user(s["access_token"])
    p = db.select("profiles", {"id": f"eq.{u['id']}", "select": "email,role,active"})
    if not p or not p[0]["active"]:
        raise HTTPException(403, "Acceso revocado o sin perfil")
    _accept_invitation({"id": u["id"], "email": p[0]["email"]})
    return {"access_token": s["access_token"], "refresh_token": s.get("refresh_token"), "user": {"email": p[0]["email"], "role": p[0]["role"]}}


class Refresh(BaseModel):
    refresh_token: str


@router.post("/auth/refresh")
def refresh(b: Refresh):
    s = db.auth_refresh(b.refresh_token)
    return {"access_token": s["access_token"], "refresh_token": s.get("refresh_token")}


@router.post("/auth/set-password")
def set_password(b: SetPassword):
    """Flujo de invitación: el invitado crea su contraseña con el token del enlace del correo."""
    if len(b.password) < 8:
        raise HTTPException(400, "La contraseña debe tener al menos 8 caracteres")
    u = db.auth_user(b.access_token)
    if not u:
        raise HTTPException(401, "El enlace de invitación expiró. Pida una nueva invitación.")
    db.auth_set_password(b.access_token, b.password)
    return {"ok": True, "email": u["email"]}


@router.get("/me")
def me(user=Depends(current_user)):
    return {"email": user["email"], "role": user["role"]}
