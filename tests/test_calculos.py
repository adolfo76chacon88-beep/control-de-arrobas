import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from decimal import Decimal
import pytest
from app.services import calculos as c


def test_medias():
    assert c.total_arrobas(0, 2) == 1
    assert c.total_arrobas(1, 1) == Decimal("1.5")
    assert c.total_arrobas(2, 1) == Decimal("2.5")
    assert c.total_arrobas(3, 2) == 4


def test_dinero_ejemplo_spec():
    assert c.dinero(15, 1, "12.00") == Decimal("186.00")
    assert c.precio_media("12.00") == Decimal("6")


def test_decimales_exactos():
    assert c.dinero(0, 3, "0.10") == Decimal("0.15")
    assert c.dinero(10, 1, "12.01") == Decimal("126.11")


def test_ausente():
    assert c.validar_cantidades(5, 3, ausente=True) == (0, 0)


@pytest.mark.parametrize("a,m", [(-1, 0), (0, -1), (1.5, 0), ("2", 0)])
def test_invalidos(a, m):
    with pytest.raises(ValueError):
        c.validar_cantidades(a, m)


def test_formato():
    assert c.fmt_arrobas(Decimal("2.5")) == "2 ½"
    assert c.fmt_arrobas(Decimal("0.5")) == "½"
    assert c.fmt_arrobas(3) == "3"
    assert c.dia_anio("2026-11-16") == ("Lunes", 2026)
