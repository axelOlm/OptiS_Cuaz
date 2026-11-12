import numpy as np

from simplex import Problema, imprimir_historial, resolver


def caso_primal():
    return Problema("max", [3, 5], [[1, 0], [0, 2], [3, 2]], ["<=", "<=", "<="], [4, 12, 18])


def caso_dual():
    return Problema("min", [2, 3], [[1, 1], [1, 2]], [">=", ">="], [5, 8])


def caso_no_acotado():
    return Problema("max", [1, 1], [[1, -1], [1, -2]], ["<=", "<="], [1, 2])


def caso_infactible():
    return Problema("min", [1, 1], [[1, 1], [1, 1]], [">=", "<="], [5, 2])


def test_primal():
    r = resolver(caso_primal(), "primal")
    assert r.estado == "optimo"
    assert np.allclose(r.x, [2, 6])
    assert np.isclose(r.z, 36)


def test_dual():
    r = resolver(caso_dual(), "dual")
    assert r.estado == "optimo"
    assert np.allclose(r.x, [2, 3])
    assert np.isclose(r.z, 13)


def test_no_acotado():
    r = resolver(caso_no_acotado(), "primal")
    assert r.estado == "no_acotado"


def test_infactible():
    r = resolver(caso_infactible(), "dual")
    assert r.estado == "infactible"


def test_metodo_inadecuado():
    assert resolver(caso_dual(), "primal").estado == "metodo_inadecuado"
    assert resolver(caso_primal(), "dual").estado in ("optimo", "metodo_inadecuado")


if __name__ == "__main__":
    casos = [
        ("PRIMAL", caso_primal(), "primal"),
        ("DUAL", caso_dual(), "dual"),
        ("NO ACOTADO", caso_no_acotado(), "primal"),
        ("INFACTIBLE", caso_infactible(), "dual"),
    ]
    for nombre, problema, metodo in casos:
        print(f"\n{'=' * 20} {nombre} {'=' * 20}")
        imprimir_historial(resolver(problema, metodo))