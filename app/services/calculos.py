"""Cálculos de arrobas y dinero con Decimal (sin errores de redondeo)."""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
CENT = Decimal("0.01")


def validar_cantidades(arrobas, medias, ausente=False):
    if ausente:
        return 0, 0
    if isinstance(arrobas, bool) or isinstance(medias, bool) or not isinstance(arrobas, int) or not isinstance(medias, int):
        raise ValueError("Arrobas y medias deben ser números enteros")
    if arrobas < 0 or medias < 0:
        raise ValueError("No se permiten cantidades negativas")
    if arrobas > 100000 or medias > 100000:
        raise ValueError("Cantidad fuera de rango")
    return arrobas, medias


def total_arrobas(arrobas: int, medias: int) -> Decimal:
    return Decimal(arrobas) + Decimal(medias) / 2


def precio_media(precio) -> Decimal:
    return Decimal(str(precio)) / 2


def dinero(arrobas: int, medias: int, precio) -> Decimal:
    p = Decimal(str(precio))
    return (Decimal(arrobas) * p + Decimal(medias) * (p / 2)).quantize(CENT, ROUND_HALF_UP)


def validar_precio(precio) -> Decimal:
    try:
        p = Decimal(str(precio))
    except Exception:
        raise ValueError("Precio inválido")
    if p < 0 or p.as_tuple().exponent < -2:
        raise ValueError("El precio debe ser positivo y con máximo 2 decimales")
    return p.quantize(CENT)


def fmt_arrobas(x) -> str:
    """2.5 -> '2 ½', 0.5 -> '½', 3 -> '3'."""
    x = Decimal(str(x))
    entero = int(x)
    if (x - entero) >= Decimal("0.5"):
        return f"{entero} ½" if entero else "½"
    return str(entero)


def fmt_medias(n: int) -> str:
    return "0" if n == 0 else ("½" if n == 1 else f"{n} × ½")


def dia_anio(fecha: str):
    d = date.fromisoformat(fecha)
    return DIAS[d.weekday()], d.year


def fmt_money(x) -> str:
    return f"${Decimal(str(x)):,.2f}"
