import re
import unicodedata
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .. import config
from ..security import current_user, require_admin
from ..services import db
from ..services import calculos as c
from ..services.util import audit, notify, notify_admin

router = APIRouter(prefix="/api", tags=["social"])
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _norm(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(ch) != "Mn")


# ---------- Invitaciones ----------
class InviteIn(BaseModel):
    email: str


@router.get("/invitations")
def invitaciones(user=Depends(require_admin)):
    return db.select("invitations", {"select": "*", "order": "created_at.desc"})


@router.post("/invitations")
def invitar(b: InviteIn, user=Depends(require_admin)):
    email = b.email.strip().lower()
    if not EMAIL.match(email):
        raise HTTPException(400, "Correo inválido")
    if email == config.ADMIN_EMAIL:
        raise HTTPException(400, "Ese correo es el del administrador")
    prof = db.select("profiles", {"email": f"eq.{email}", "select": "id,active,role"})
    if prof and prof[0]["active"]:
        raise HTTPException(409, "Ese usuario ya tiene acceso")
    if prof:  # reactivar lector revocado (el rol sigue siendo lector, inmutable)
        db.update("profiles", {"id": f"eq.{prof[0]['id']}"}, {"active": True})
        uid = prof[0]["id"]
    else:
        uid = db.auth_invite(email).get("id")  # Supabase envía el correo; el trigger asigna rol LECTOR
    inv = db.insert("invitations", {"email": email, "invited_by": user["id"], "user_id": uid,
                                    "status": "aceptada" if prof else "pendiente"})[0]
    audit(user["id"], "invitar_lector", "invitations", inv["id"], {"email": email})
    notify_admin("invitacion", f"Invitación enviada a {email}")
    return inv


@router.delete("/invitations/{iid}")
def revocar(iid: str, user=Depends(require_admin)):
    inv = db.select("invitations", {"id": f"eq.{iid}", "select": "*"})
    if not inv:
        raise HTTPException(404, "Invitación no encontrada")
    db.update("invitations", {"id": f"eq.{iid}"}, {"status": "revocada"})
    db.update("profiles", {"email": f"eq.{inv[0]['email']}", "role": "eq.lector"}, {"active": False})
    audit(user["id"], "revocar_acceso", "invitations", iid, {"email": inv[0]["email"]})
    return {"ok": True}


# ---------- Comentarios ----------
class CommentIn(BaseModel):
    body: str
    cut_id: Optional[str] = None
    worker_id: Optional[str] = None
    record_date: Optional[str] = None
    record_id: Optional[str] = None


class ReplyIn(BaseModel):
    body: str


class StatusIn(BaseModel):
    status: str


@router.get("/comments")
def comentarios(status: str = "", user=Depends(current_user)):
    p = {"select": "*,replies(*,profiles(email)),cuts(name),workers(full_name),profiles!comments_author_id_fkey(email)",
         "order": "created_at.desc"}
    if user["role"] != "admin": p["author_id"] = f"eq.{user['id']}"
    if status in ("pendiente", "respondido"): p["status"] = f"eq.{status}"
    rows = db.select("comments", p)
    for r in rows:
        r["replies"].sort(key=lambda x: x["created_at"])
    return rows


@router.post("/comments")
def comentar(b: CommentIn, user=Depends(current_user)):
    body = b.body.strip()
    if not body or len(body) > 2000:
        raise HTTPException(400, "El mensaje debe tener entre 1 y 2000 caracteres")
    row = db.insert("comments", {"author_id": user["id"], "body": body, "cut_id": b.cut_id or None, "worker_id": b.worker_id or None,
                                 "record_date": b.record_date or None, "record_id": b.record_id or None})[0]
    notify_admin("comentario", f"Nuevo comentario de {user['email']}")
    return row


@router.post("/comments/{cid}/replies")
def responder(cid: str, b: ReplyIn, user=Depends(require_admin)):
    cm = db.select("comments", {"id": f"eq.{cid}", "select": "author_id"})
    if not cm or not b.body.strip():
        raise HTTPException(400, "Comentario no encontrado o respuesta vacía")
    r = db.insert("replies", {"comment_id": cid, "author_id": user["id"], "body": b.body.strip()})[0]
    db.update("comments", {"id": f"eq.{cid}"}, {"status": "respondido"})
    notify(cm[0]["author_id"], "respuesta", "El administrador respondió tu comentario")
    return r


@router.patch("/comments/{cid}/status")
def estado(cid: str, b: StatusIn, user=Depends(require_admin)):
    if b.status not in ("pendiente", "respondido"):
        raise HTTPException(400, "Estado inválido")
    return db.update("comments", {"id": f"eq.{cid}"}, {"status": b.status})


# ---------- Notificaciones ----------
@router.get("/notifications")
def notificaciones(user=Depends(current_user)):
    return db.select("notifications", {"user_id": f"eq.{user['id']}", "select": "*", "order": "created_at.desc", "limit": "50"})


@router.post("/notifications/read")
def leidas(user=Depends(current_user)):
    db.update("notifications", {"user_id": f"eq.{user['id']}", "read": "eq.false"}, {"read": True})
    return {"ok": True}


# ---------- Buscador general (sin dinero) ----------
@router.get("/search")
def buscar(q: str, user=Depends(current_user)):
    qn = _norm(q.strip())
    if len(qn) < 2:
        return {"trabajadores": [], "cortes": [], "registros": []}
    workers = [w for w in db.select("workers", {"select": "id,full_name,active"}) if qn in _norm(w["full_name"])]
    cuts = [x for x in db.select("cuts", {"select": "id,name,start_date,end_date,status"})
            if qn in _norm(x["name"]) or qn in x["start_date"] or qn in (x["end_date"] or "")]
    regs = []
    for r in db.select("daily_records", {"select": "*,workers(full_name),cuts(name)", "order": "work_date.desc", "limit": "2000"}):
        dia, _ = c.dia_anio(r["work_date"])
        if qn in _norm(r["workers"]["full_name"]) or qn in r["work_date"] or qn in _norm(dia):
            regs.append({"id": r["id"], "cut_id": r["cut_id"], "corte": r["cuts"]["name"], "nombre": r["workers"]["full_name"],
                         "fecha": r["work_date"], "dia": dia, "total_txt": "AUSENTE" if r["absent"] else c.fmt_arrobas(c.total_arrobas(r["full_count"], r["half_count"]))})
        if len(regs) >= 50:
            break
    return {"trabajadores": workers[:20], "cortes": cuts[:20], "registros": regs}
