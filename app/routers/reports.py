from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from ..security import current_user, require_admin
from ..services import db
from ..services import calculos as c
from ..services.pdf import build_pdf
from ..services.util import record_view
from .cuts import compute_summary, get_cut

router = APIRouter(prefix="/api/reports", tags=["pdf"])
KINDS = {"diario", "resumen", "dinero", "completo"}


def _pdf(data, name):
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{name}.pdf"'})


def _registros_rows(cut_id):
    recs = [record_view(r) for r in db.select("daily_records", {"cut_id": f"eq.{cut_id}", "select": "*,workers(full_name)"})]
    recs.sort(key=lambda r: (r["fecha"], r["nombre"].lower()))
    rows = [[str(i), r["nombre"], r["fecha"], r["dia"], str(r["anio"]), str(r["arrobas"]), r["medias_txt"], r["total_txt"], r["estado"]]
            for i, r in enumerate(recs, 1)]
    total = sum((Decimal(str(r["total"])) for r in recs), Decimal(0))
    return rows, total


@router.get("/cut/{cut_id}/{kind}")
def reporte_corte(cut_id: str, kind: str, user=Depends(current_user)):
    admin = user["role"] == "admin"
    if kind not in KINDS:
        raise HTTPException(404, "Tipo de reporte inválido")
    if kind == "dinero" and not admin:
        raise HTTPException(403, "Los lectores no pueden descargar información monetaria")
    cut = get_cut(cut_id)
    sub = f"Corte: {cut['name']} (ID {cut['id'][:8]}) · Inicio {cut['start_date']} · Estado: {cut['status'].upper()}"
    h_reg = ["N°", "Nombre y apellido", "Fecha", "Día", "Año", "Arrobas", "Medias", "Total", "Estado"]
    money_rows = {}
    price = None
    if admin and kind in ("dinero", "completo"):
        fin = db.select("cut_finance", {"cut_id": f"eq.{cut_id}", "select": "*"})
        if not fin:
            raise HTTPException(400, "El corte aún no está finalizado: no hay dinero calculado")
        price = Decimal(str(fin[0]["price_per_arroba"]))
        money_rows = {r["worker_id"]: r for r in db.select("cut_results", {"cut_id": f"eq.{cut_id}", "select": "*"})}
    summ = compute_summary(cut_id, stored=money_rows or None)
    tot_arr = sum((Decimal(str(r["total"])) for r in summ), Decimal(0))

    def res_rows(with_money):
        return [[str(i), r["nombre"], r["total_txt"], *( [c.fmt_money(r["dinero"])] if with_money else []), r["estado"]]
                for i, r in enumerate(summ, 1)]

    if kind == "diario":
        rows, total = _registros_rows(cut_id)
        data = build_pdf("Registro diario de arrobas", sub, h_reg, rows, [("Total general de arrobas", c.fmt_arrobas(total))])
    elif kind == "resumen":
        data = build_pdf("Resumen de arrobas por trabajador", sub, ["N°", "Nombre y apellido", "Total de arrobas", "Estado"],
                         res_rows(False), [("Total general de arrobas", c.fmt_arrobas(tot_arr))])
    elif kind == "dinero":
        total_m = sum((Decimal(str(r["dinero"])) for r in summ), Decimal(0))
        data = build_pdf("Resumen de dinero", sub + f" · Precio por arroba {c.fmt_money(price)}",
                         ["N°", "Nombre y apellido", "Total de arrobas", "Total de dinero", "Estado"], res_rows(True),
                         [("Total de arrobas", c.fmt_arrobas(tot_arr)), ("Total de dinero", c.fmt_money(total_m))])
    else:  # completo
        rows, _ = _registros_rows(cut_id)
        if admin:
            total_m = sum((Decimal(str(r["dinero"])) for r in summ), Decimal(0))
            data = build_pdf("Reporte completo del corte", sub + f" · Precio por arroba {c.fmt_money(price)}", h_reg, rows,
                             [("Total de arrobas", c.fmt_arrobas(tot_arr)), ("Total de dinero", c.fmt_money(total_m))],
                             extra=[("Resumen por trabajador", ["N°", "Nombre y apellido", "Total de arrobas", "Total de dinero", "Estado"], res_rows(True))])
        else:  # lector: reporte de arrobas, SIN dinero
            data = build_pdf("Reporte de arrobas del corte", sub, h_reg, rows, [("Total general de arrobas", c.fmt_arrobas(tot_arr))],
                             extra=[("Resumen por trabajador", ["N°", "Nombre y apellido", "Total de arrobas", "Estado"], res_rows(False))])
    return _pdf(data, f"{kind}_{cut['name']}".replace(" ", "_"))


@router.get("/historial")
def historial(user=Depends(require_admin)):
    cuts = db.select("cuts", {"select": "*", "order": "start_date.desc"})
    fin = {f["cut_id"]: f for f in db.select("cut_finance", {"select": "*"})}
    rows = []
    for i, x in enumerate(cuts, 1):
        s = compute_summary(x["id"])
        t = sum((Decimal(str(r["total"])) for r in s), Decimal(0))
        f = fin.get(x["id"])
        rows.append([str(i), x["name"], x["start_date"], x["end_date"] or "—", x["status"].upper(), str(len(s)), c.fmt_arrobas(t),
                     c.fmt_money(f["price_per_arroba"]) if f else "—", c.fmt_money(f["total_money"]) if f else "—"])
    return _pdf(build_pdf("Historial de cortes", f"{len(cuts)} cortes", ["N°", "Corte", "Inicio", "Fin", "Estado", "Trabajadores", "Arrobas", "Precio", "Total dinero"], rows), "historial_cortes")
