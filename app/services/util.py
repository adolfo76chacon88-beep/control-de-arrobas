from . import db
from . import calculos as c


def audit(actor, action, entity, entity_id=None, detail=None):
    db.insert("audit_log", {"actor": actor, "action": action, "entity": entity,
                            "entity_id": str(entity_id) if entity_id else None, "detail": detail or {}})


def notify(user_id, tipo, mensaje):
    db.insert("notifications", {"user_id": user_id, "type": tipo, "message": mensaje})


def notify_admin(tipo, mensaje):
    for p in db.select("profiles", {"role": "eq.admin", "select": "id"}):
        notify(p["id"], tipo, mensaje)


def notify_readers(tipo, mensaje):
    rows = db.select("profiles", {"role": "eq.lector", "active": "eq.true", "select": "id"})
    if rows:
        db.insert("notifications", [{"user_id": r["id"], "type": tipo, "message": mensaje} for r in rows])


def record_view(r):
    dia, anio = c.dia_anio(r["work_date"])
    total = c.total_arrobas(r["full_count"], r["half_count"])
    return {"id": r["id"], "cut_id": r["cut_id"], "worker_id": r["worker_id"],
            "nombre": (r.get("workers") or {}).get("full_name", ""), "fecha": r["work_date"], "dia": dia, "anio": anio,
            "arrobas": r["full_count"], "medias": r["half_count"], "medias_txt": c.fmt_medias(r["half_count"]),
            "total": float(total), "total_txt": "AUSENTE" if r["absent"] else c.fmt_arrobas(total),
            "ausente": r["absent"], "estado": "Ausente" if r["absent"] else "Activo"}
