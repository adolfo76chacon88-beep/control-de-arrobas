from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..security import current_user, require_admin
from ..services import db
from ..services import calculos as c
from ..services.util import audit

router = APIRouter(prefix="/api/workers", tags=["trabajadores"])


class WorkerIn(BaseModel):
    first_name: str
    last_name: str


class ActiveIn(BaseModel):
    active: bool


@router.get("")
def listar(q: str = "", active: str = "", user=Depends(current_user)):
    p = {"select": "*", "order": "full_name.asc"}
    if q:
        p["full_name"] = f"ilike.*{q.replace('*', '')}*"
    if active in ("true", "false"):
        p["active"] = f"eq.{active}"
    return db.select("workers", p)


@router.post("")
def crear(b: WorkerIn, user=Depends(require_admin)):
    if not b.first_name.strip() or not b.last_name.strip():
        raise HTTPException(400, "Nombre y apellido son obligatorios")
    w = db.insert("workers", {"first_name": b.first_name.strip(), "last_name": b.last_name.strip()})[0]
    audit(user["id"], "crear_trabajador", "workers", w["id"], {"nombre": w["full_name"]})
    return w


@router.put("/{wid}")
def editar(wid: str, b: WorkerIn, user=Depends(require_admin)):
    if not b.first_name.strip() or not b.last_name.strip():
        raise HTTPException(400, "Nombre y apellido son obligatorios")
    r = db.update("workers", {"id": f"eq.{wid}"}, {"first_name": b.first_name.strip(), "last_name": b.last_name.strip()})
    if not r:
        raise HTTPException(404, "Trabajador no encontrado")
    audit(user["id"], "editar_trabajador", "workers", wid)
    return r[0]


@router.patch("/{wid}/active")
def activar(wid: str, b: ActiveIn, user=Depends(require_admin)):
    r = db.update("workers", {"id": f"eq.{wid}"}, {"active": b.active})
    if not r:
        raise HTTPException(404, "Trabajador no encontrado")
    audit(user["id"], "reactivar_trabajador" if b.active else "desactivar_trabajador", "workers", wid)
    return r[0]


@router.get("/{wid}/history")
def historial(wid: str, user=Depends(current_user)):
    """Historial de arrobas del trabajador (sin dinero)."""
    rows = db.select("daily_records", {"worker_id": f"eq.{wid}", "select": "*,cuts(name)", "order": "work_date.desc"})
    out, total = [], 0
    for r in rows:
        dia, anio = c.dia_anio(r["work_date"])
        t = c.total_arrobas(r["full_count"], r["half_count"])
        total += t
        out.append({"corte": (r.get("cuts") or {}).get("name"), "fecha": r["work_date"], "dia": dia,
                    "total_txt": "AUSENTE" if r["absent"] else c.fmt_arrobas(t), "ausente": r["absent"]})
    return {"registros": out, "total_arrobas": float(total), "total_txt": c.fmt_arrobas(total)}
