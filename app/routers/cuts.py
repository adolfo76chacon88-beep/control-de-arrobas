from datetime import date
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..security import current_user, require_admin
from ..services import db
from ..services import calculos as c
from ..services.util import audit, notify_readers, record_view

router = APIRouter(prefix="/api", tags=["cortes"])


class CutIn(BaseModel):
    name: str
    start_date: str
    worker_ids: List[str] = []


class WorkersIn(BaseModel):
    worker_ids: List[str]


class RecordIn(BaseModel):
    worker_id: str
    work_date: str
    full_count: int = 0
    half_count: int = 0
    absent: bool = False


class PriceIn(BaseModel):
    price: str


def get_cut(cut_id):
    r = db.select("cuts", {"id": f"eq.{cut_id}", "select": "*"})
    if not r:
        raise HTTPException(404, "Corte no encontrado")
    return r[0]


def compute_summary(cut_id, price=None, stored=None):
    """Resumen por trabajador. Dinero solo si se entrega price (preview) o stored (resultados guardados)."""
    cws = db.select("cut_workers", {"cut_id": f"eq.{cut_id}", "select": "worker_id,workers(full_name,active)"})
    recs = db.select("daily_records", {"cut_id": f"eq.{cut_id}", "select": "worker_id,full_count,half_count,absent"})
    agg = {}
    for r in recs:
        a = agg.setdefault(r["worker_id"], [0, 0, 0])
        a[0] += r["full_count"]; a[1] += r["half_count"]; a[2] += 1 if r["absent"] else 0
    rows = []
    for cw in sorted(cws, key=lambda x: x["workers"]["full_name"].lower()):
        f, h, aus = agg.get(cw["worker_id"], [0, 0, 0])
        tot = c.total_arrobas(f, h)
        row = {"worker_id": cw["worker_id"], "nombre": cw["workers"]["full_name"], "arrobas": f, "medias": h,
               "total": float(tot), "total_txt": c.fmt_arrobas(tot), "ausencias": aus,
               "estado": "Activo" if cw["workers"]["active"] else "Inactivo"}
        if stored is not None:
            s = stored.get(cw["worker_id"])
            row["dinero"] = float(s["money"]) if s else 0.0
        elif price is not None:
            row["dinero"] = float(c.dinero(f, h, price))
        rows.append(row)
    return rows


@router.get("/cuts")
def listar(q: str = "", desde: str = "", hasta: str = "", user=Depends(current_user)):
    p = {"select": "*", "order": "start_date.desc"}
    if desde: p["start_date"] = f"gte.{desde}"
    cuts = db.select("cuts", p)
    if hasta: cuts = [x for x in cuts if x["start_date"] <= hasta]
    if q: cuts = [x for x in cuts if q.lower() in x["name"].lower() or q in x["start_date"] or q in (x["end_date"] or "")]
    cw = db.select("cut_workers", {"select": "cut_id"})
    recs = db.select("daily_records", {"select": "cut_id,full_count,half_count"})
    fin = {f["cut_id"]: f for f in db.select("cut_finance", {"select": "*"})} if user["role"] == "admin" else {}
    out = []
    for x in cuts:
        tot = sum((c.total_arrobas(r["full_count"], r["half_count"]) for r in recs if r["cut_id"] == x["id"]), Decimal(0))
        row = {**x, "trabajadores": sum(1 for w in cw if w["cut_id"] == x["id"]), "total_arrobas": float(tot), "total_txt": c.fmt_arrobas(tot)}
        if user["role"] == "admin" and x["id"] in fin:
            row["precio"] = float(fin[x["id"]]["price_per_arroba"]); row["total_dinero"] = float(fin[x["id"]]["total_money"])
        out.append(row)
    return out


@router.post("/cuts")
def crear(b: CutIn, user=Depends(require_admin)):
    try:
        date.fromisoformat(b.start_date)
    except ValueError:
        raise HTTPException(400, "Fecha de inicio inválida")
    if not b.name.strip():
        raise HTTPException(400, "El corte necesita un nombre")
    cut = db.insert("cuts", {"name": b.name.strip(), "start_date": b.start_date, "created_by": user["id"]})[0]
    if b.worker_ids:
        db.insert("cut_workers", [{"cut_id": cut["id"], "worker_id": w} for w in b.worker_ids])
    audit(user["id"], "crear_corte", "cuts", cut["id"], {"nombre": cut["name"], "trabajadores": len(b.worker_ids)})
    return cut


@router.get("/cuts/{cut_id}")
def detalle(cut_id: str, user=Depends(current_user)):
    cut = get_cut(cut_id)
    ws = db.select("cut_workers", {"cut_id": f"eq.{cut_id}", "select": "worker_id,workers(id,full_name,active)"})
    cut["workers"] = [w["workers"] for w in ws]
    if user["role"] == "admin":
        f = db.select("cut_finance", {"cut_id": f"eq.{cut_id}", "select": "*"})
        cut["finance"] = f[0] if f else None
    return cut


@router.post("/cuts/{cut_id}/workers")
def agregar_trabajadores(cut_id: str, b: WorkersIn, user=Depends(require_admin)):
    if get_cut(cut_id)["status"] == "finalizado":
        raise HTTPException(400, "El corte está finalizado")
    have = {w["worker_id"] for w in db.select("cut_workers", {"cut_id": f"eq.{cut_id}", "select": "worker_id"})}
    new = [w for w in b.worker_ids if w not in have]
    if new:
        db.insert("cut_workers", [{"cut_id": cut_id, "worker_id": w} for w in new])
    return {"agregados": len(new)}


# ---------- Registros ----------
@router.get("/cuts/{cut_id}/records")
def registros(cut_id: str, worker_id: str = "", fecha: str = "", q: str = "", user=Depends(current_user)):
    p = {"cut_id": f"eq.{cut_id}", "select": "*,workers(full_name)", "order": "work_date.desc"}
    if worker_id: p["worker_id"] = f"eq.{worker_id}"
    if fecha: p["work_date"] = f"eq.{fecha}"
    rows = [record_view(r) for r in db.select("daily_records", p)]
    if q: rows = [r for r in rows if q.lower() in r["nombre"].lower()]
    rows.sort(key=lambda r: (r["fecha"], r["nombre"].lower()), reverse=True)
    for i, r in enumerate(rows, 1): r["n"] = i
    dias = {}
    for r in rows: dias[r["fecha"]] = dias.get(r["fecha"], Decimal(0)) + Decimal(str(r["total"]))
    total = sum(dias.values(), Decimal(0))
    return {"registros": rows, "totales_diarios": {k: c.fmt_arrobas(v) for k, v in dias.items()},
            "total_general": c.fmt_arrobas(total), "total_general_num": float(total)}


def _validar(cut_id, b: RecordIn):
    cut = get_cut(cut_id)
    if cut["status"] == "finalizado":
        raise HTTPException(400, "El corte está finalizado. Reábralo para modificar registros.")
    try:
        date.fromisoformat(b.work_date)
        f, h = c.validar_cantidades(b.full_count, b.half_count, b.absent)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not db.select("cut_workers", {"cut_id": f"eq.{cut_id}", "worker_id": f"eq.{b.worker_id}", "select": "worker_id"}):
        raise HTTPException(400, "El trabajador no pertenece a este corte")
    return {"cut_id": cut_id, "worker_id": b.worker_id, "work_date": b.work_date, "full_count": f, "half_count": h, "absent": b.absent}


@router.post("/cuts/{cut_id}/records")
def crear_registro(cut_id: str, b: RecordIn, user=Depends(require_admin)):
    data = _validar(cut_id, b)
    if db.select("daily_records", {"cut_id": f"eq.{cut_id}", "worker_id": f"eq.{b.worker_id}", "work_date": f"eq.{b.work_date}", "select": "id"}):
        raise HTTPException(409, "Ya existe un registro de este trabajador en esa fecha. Edítelo en lugar de crear otro.")
    r = db.insert("daily_records", data)[0]
    audit(user["id"], "crear_registro", "daily_records", r["id"])
    return r


@router.put("/records/{rid}")
def editar_registro(rid: str, b: RecordIn, user=Depends(require_admin)):
    old = db.select("daily_records", {"id": f"eq.{rid}", "select": "*"})
    if not old:
        raise HTTPException(404, "Registro no encontrado")
    data = _validar(old[0]["cut_id"], b)
    r = db.update("daily_records", {"id": f"eq.{rid}"}, data)
    audit(user["id"], "editar_registro", "daily_records", rid)
    return r[0]


@router.delete("/records/{rid}")
def borrar_registro(rid: str, user=Depends(require_admin)):
    old = db.select("daily_records", {"id": f"eq.{rid}", "select": "cut_id"})
    if not old:
        raise HTTPException(404, "Registro no encontrado")
    if get_cut(old[0]["cut_id"])["status"] == "finalizado":
        raise HTTPException(400, "El corte está finalizado")
    db.delete("daily_records", {"id": f"eq.{rid}"})
    audit(user["id"], "eliminar_registro", "daily_records", rid)
    return {"ok": True}


# ---------- Resumen / cierre ----------
@router.get("/cuts/{cut_id}/summary")
def resumen(cut_id: str, price: Optional[str] = None, user=Depends(current_user)):
    cut = get_cut(cut_id)
    admin = user["role"] == "admin"
    stored = price_used = None
    if admin and cut["status"] == "finalizado":
        stored = {r["worker_id"]: r for r in db.select("cut_results", {"cut_id": f"eq.{cut_id}", "select": "*"})}
        price_used = float(db.select("cut_finance", {"cut_id": f"eq.{cut_id}", "select": "price_per_arroba"})[0]["price_per_arroba"])
    elif admin and price:
        try:
            price_used = float(c.validar_precio(price))
        except ValueError as e:
            raise HTTPException(400, str(e))
    rows = compute_summary(cut_id, price=price_used if stored is None else None, stored=stored)
    total = sum((Decimal(str(r["total"])) for r in rows), Decimal(0))
    out = {"filas": rows, "total_arrobas": c.fmt_arrobas(total), "total_arrobas_num": float(total), "status": cut["status"]}
    if admin and price_used is not None:
        out["precio"] = price_used
        out["total_dinero"] = float(sum((Decimal(str(r["dinero"])) for r in rows), Decimal(0)))
    return out


@router.get("/cuts/{cut_id}/finalize-preview")
def previa(cut_id: str, price: str, user=Depends(require_admin)):
    cut = get_cut(cut_id)
    if cut["status"] == "finalizado":
        raise HTTPException(400, "El corte ya está finalizado")
    try:
        p = c.validar_precio(price)
    except ValueError as e:
        raise HTTPException(400, str(e))
    rows = compute_summary(cut_id, price=p)
    return {"trabajadores": len(rows), "total_arrobas": c.fmt_arrobas(sum((Decimal(str(r["total"])) for r in rows), Decimal(0))),
            "precio": float(p), "precio_media": float(c.precio_media(p)),
            "total_dinero": float(sum((Decimal(str(r["dinero"])) for r in rows), Decimal(0))), "fecha_cierre": date.today().isoformat()}


@router.post("/cuts/{cut_id}/finalize")
def finalizar(cut_id: str, b: PriceIn, user=Depends(require_admin)):
    try:
        p = c.validar_precio(b.price)
    except ValueError as e:
        raise HTTPException(400, str(e))
    res = db.rpc("finalizar_corte", {"p_cut": cut_id, "p_price": str(p), "p_actor": user["id"]})
    notify_readers("corte", f"El corte «{get_cut(cut_id)['name']}» fue finalizado")
    return res


@router.post("/cuts/{cut_id}/reopen")
def reabrir(cut_id: str, user=Depends(require_admin)):
    db.rpc("reabrir_corte", {"p_cut": cut_id, "p_actor": user["id"]})
    notify_readers("corte", f"El corte «{get_cut(cut_id)['name']}» fue reabierto")
    return {"ok": True}


@router.get("/compare")
def comparar(a: str, b: str, user=Depends(current_user)):
    out = []
    for cid in (a, b):
        cut = get_cut(cid)
        rows = compute_summary(cid)
        tot = sum((Decimal(str(r["total"])) for r in rows), Decimal(0))
        item = {"id": cid, "nombre": cut["name"], "inicio": cut["start_date"], "fin": cut["end_date"], "estado": cut["status"],
                "trabajadores": len(rows), "total_arrobas": float(tot), "total_txt": c.fmt_arrobas(tot)}
        if user["role"] == "admin":
            f = db.select("cut_finance", {"cut_id": f"eq.{cid}", "select": "*"})
            if f: item["precio"] = float(f[0]["price_per_arroba"]); item["total_dinero"] = float(f[0]["total_money"])
        out.append(item)
    out.append({"diferencia_arrobas": out[1]["total_arrobas"] - out[0]["total_arrobas"]})
    return out


@router.get("/audit")
def auditoria(user=Depends(require_admin)):
    return db.select("audit_log", {"select": "*", "order": "created_at.desc", "limit": "100"})
