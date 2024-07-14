from simulacioncalzado.hiperparametros import Hiperparametros
import pytest

hiperparmetros = Hiperparametros()


def test_hiperparametros():

    assert hiperparmetros.intervalo_cambio_orden == 1


@pytest.mark.xfail
def test_error():
    assert (1/0) == 1
