from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

import numpy as np

TOL = 1e-9
MAX_ITER = 1000


class SimplexError(Exception):
    pass


class NoAcotadoError(SimplexError):
    pass


class InfactibleError(SimplexError):
    pass


class MetodoInadecuadoError(SimplexError):
    pass


@dataclass
class Problema:
    tipo: str                    # "max" | "min"
    c: list[float]
    A: list[list[float]]
    signos: list[str]            # "<=", ">=", "="
    b: list[float]


@dataclass
class Iteracion:
    numero: int
    tableau: np.ndarray
    basicas: list[str]
    columnas: list[str]
    fila_pivote: int | None = None
    col_pivote: int | None = None
    entra: str | None = None
    sale: str | None = None
    texto: str = ""


@dataclass
class Resultado:
    estado: str                  # optimo | no_acotado | infactible | metodo_inadecuado
    mensaje: str
    historial: list[Iteracion]
    x: np.ndarray | None = None
    z: float | None = None
    basicas: dict[str, float] | None = None


class Simplex:
    def __init__(self, problema: Problema):
        self.p = problema
        self._validar()
        self._forma_estandar()
        self.historial: list[Iteracion] = []

    def _validar(self):
        p = self.p
        if p.tipo not in ("max", "min"):
            raise ValueError("El tipo debe ser 'max' o 'min'.")
        if len(p.A) != len(p.b) or len(p.A) != len(p.signos):
            raise ValueError("A, b y signos deben tener el mismo número de filas.")
        if any(len(f) != len(p.c) for f in p.A):
            raise ValueError("Cada restricción debe tener un coeficiente por variable.")
        if any(s not in ("<=", ">=", "=") for s in p.signos):
            raise ValueError("Signo de restricción inválido.")

    def _forma_estandar(self):
        p = self.p
        self.n = len(p.c)
        c = np.array(p.c, float) * (1 if p.tipo == "max" else -1)

        filas, rhs = [], []
        for a, s, bi in zip(p.A, p.signos, p.b):
            a = np.array(a, float)
            if s == "<=":
                filas.append(a)
                rhs.append(bi)
            elif s == ">=":
                filas.append(-a)
                rhs.append(-bi)
            else:
                filas += [a, -a]
                rhs += [bi, -bi]

        m = len(filas)
        T = np.zeros((m + 1, self.n + m + 1))
        T[:m, :self.n] = filas
        T[:m, self.n:self.n + m] = np.eye(m)
        T[:m, -1] = rhs
        T[-1, :self.n] = -c

        self.T = T
        self.m = m
        self.columnas = [f"x{j + 1}" for j in range(self.n)] + [f"s{i + 1}" for i in range(m)]
        self.basicas = [f"s{i + 1}" for i in range(m)]

    def _registrar(self, fila=None, col=None, texto=""):
        entra = sale = None
        if fila is not None and col is not None:
            entra, sale = self.columnas[col], self.basicas[fila]
            texto = texto or f"Entra {entra}, sale {sale}. Pivote en fila {sale}, columna {entra}."
        self.historial.append(Iteracion(
            len(self.historial), self.T.copy(), self.basicas.copy(), self.columnas,
            fila, col, entra, sale, texto,
        ))
        if len(self.historial) > MAX_ITER:
            raise SimplexError("Se excedió el máximo de iteraciones.")

    def _pivotar(self, r, c):
        T = self.T
        T[r] /= T[r, c]
        for i in range(T.shape[0]):
            if i != r:
                T[i] -= T[i, c] * T[r]
        T[np.abs(T) < TOL] = 0.0
        self.basicas[r] = self.columnas[c]

    def _primal(self):
        if np.any(self.T[:-1, -1] < -TOL):
            raise MetodoInadecuadoError(
                "Hay lados derechos negativos: la solución inicial es infactible. Usa el Simplex Dual."
            )
        while True:
            z = self.T[-1, :-1]
            c = int(np.argmin(z))
            if z[c] >= -TOL:
                self._registrar(texto="Óptimo: no hay coeficientes negativos en la fila Z.")
                return

            col = self.T[:-1, c]
            pos = np.where(col > TOL)[0]
            if pos.size == 0:
                self._registrar(col=c, texto=f"La columna {self.columnas[c]} no tiene elementos positivos.")
                raise NoAcotadoError(
                    f"Solución no acotada: {self.columnas[c]} puede crecer indefinidamente."
                )

            cocientes = self.T[pos, -1] / col[pos]
            empatadas = pos[np.isclose(cocientes, cocientes.min(), atol=TOL)]
            r = min(empatadas, key=lambda i: self.columnas.index(self.basicas[i]))  # Bland
            self._registrar(r, c)
            self._pivotar(r, c)

    def _dual(self):
        if np.any(self.T[-1, :-1] < -TOL):
            raise MetodoInadecuadoError(
                "La fila Z tiene coeficientes negativos: el problema no es dual-factible. Usa el Simplex Primal."
            )
        while True:
            b = self.T[:-1, -1]
            r = int(np.argmin(b))
            if b[r] >= -TOL:
                self._registrar(texto="Óptimo: todos los lados derechos son no negativos.")
                return

            fila = self.T[r, :-1]
            neg = np.where(fila < -TOL)[0]
            if neg.size == 0:
                self._registrar(texto=f"La fila {self.basicas[r]} tiene b < 0 y ningún coeficiente negativo.")
                raise InfactibleError(
                    f"Problema infactible: la restricción de {self.basicas[r]} no puede satisfacerse."
                )

            cocientes = self.T[-1, neg] / -fila[neg]
            c = int(neg[np.isclose(cocientes, cocientes.min(), atol=TOL)][0])
            self._registrar(r, c)
            self._pivotar(r, c)

    def _resultado_optimo(self) -> Resultado:
        x = np.zeros(self.n)
        valores = {}
        for i, nombre in enumerate(self.basicas):
            valores[nombre] = float(self.T[i, -1])
            if nombre.startswith("x"):
                x[int(nombre[1:]) - 1] = self.T[i, -1]
        z = float(self.T[-1, -1]) * (1 if self.p.tipo == "max" else -1)
        return Resultado("optimo", "Solución óptima encontrada.", self.historial,
                         x + 0.0, z + 0.0, valores)

    def resolver(self, metodo: str) -> Resultado:
        try:
            if metodo == "primal":
                self._primal()
            elif metodo == "dual":
                self._dual()
            else:
                raise ValueError("El método debe ser 'primal' o 'dual'.")
            return self._resultado_optimo()
        except NoAcotadoError as e:
            return Resultado("no_acotado", str(e), self.historial)
        except InfactibleError as e:
            return Resultado("infactible", str(e), self.historial)
        except MetodoInadecuadoError as e:
            return Resultado("metodo_inadecuado", str(e), self.historial)


def resolver(problema: Problema, metodo: str) -> Resultado:
    return Simplex(problema).resolver(metodo)


def fmt(v: float, fracciones: bool = True) -> str:
    if abs(v) < TOL:
        return "0"
    if fracciones:
        f = Fraction(float(v)).limit_denominator(1000)
        if abs(float(f) - v) < 1e-7:
            return str(f)
    return f"{v:.4f}".rstrip("0").rstrip(".")


def imprimir_historial(res: Resultado):
    for it in res.historial:
        print(f"\nIteración {it.numero}: {it.texto}")
        print(f"{'':>5}" + "".join(f"{c:>8}" for c in it.columnas + ["b"]))
        for nombre, fila in zip(it.basicas + ["Z"], it.tableau):
            print(f"{nombre:>5}" + "".join(f"{fmt(v):>8}" for v in fila))
    print(f"\n[{res.estado}] {res.mensaje}")
    if res.estado == "optimo":
        print("x =", [fmt(v) for v in res.x], "| Z =", fmt(res.z))