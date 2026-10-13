"""
optimo_exacto.py — (OPCIONAL) Calcula el recorrido ÓPTIMO EXACTO para comprobar
qué tan cerca quedan ACO y GA. No es necesario para ejecutar tsp_bio.py.

USO:
    pip install numpy scipy
    python optimo_exacto.py                     # distancias por carretera
    python optimo_exacto.py --distancias haversine

El resultado se copia en config.ini (optimo_carretera_km u optimo_haversine_km).

MÉTODO: programación lineal entera, formulación DFJ (Dantzig–Fulkerson–Johnson).
    Variables x_ij ∈ {0,1}: 1 si la arista i–j está en el recorrido.
    Minimizar Σ d_ij · x_ij
    sujeto a  Σ_j x_ij = 2 para cada ciudad i   (entra y sale una vez)
    Si la solución tiene varios ciclos separados (subtours), se añade la restricción
    Σ_{i,j ∈ S} x_ij ≤ |S| − 1 para cada ciclo S y se resuelve otra vez, hasta que
    queda un único ciclo. Ese ciclo es el óptimo global garantizado.
"""
import argparse
import itertools
import sys

try:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
except ImportError:
    sys.exit("Este script necesita numpy y scipy:  pip install numpy scipy")

from punto_2.parte_1.datos_tsp import CIUDADES, cargar_distancias


def resolver(D):
    n = len(D)
    aristas = list(itertools.combinations(range(n), 2))       # i < j (problema simétrico)
    c = np.array([D[i][j] for i, j in aristas])
    grado = np.zeros((n, len(aristas)))
    for k, (i, j) in enumerate(aristas):
        grado[i, k] = grado[j, k] = 1
    restricciones = [LinearConstraint(grado, 2, 2)]

    while True:
        r = milp(c, constraints=restricciones, integrality=np.ones(len(aristas)),
                 bounds=Bounds(0, 1))
        if not r.success:
            sys.exit(f"El solver falló: {r.message}")
        usadas = [aristas[k] for k in range(len(aristas)) if r.x[k] > 0.5]

        # Separar la solución en ciclos (componentes conexas)
        vecinos = {i: [] for i in range(n)}
        for i, j in usadas:
            vecinos[i].append(j)
            vecinos[j].append(i)
        ciclos, vistos = [], set()
        for s in range(n):
            if s in vistos:
                continue
            ciclo, pila = [], [s]
            while pila:
                u = pila.pop()
                if u not in vistos:
                    vistos.add(u)
                    ciclo.append(u)
                    pila.extend(vecinos[u])
            ciclos.append(set(ciclo))

        if len(ciclos) == 1:
            break
        print(f"   {len(ciclos)} subtours encontrados → se añaden restricciones y se repite")
        for S in ciclos:                                       # eliminación de subtours
            fila = np.array([1.0 if i in S and j in S else 0.0 for i, j in aristas])
            restricciones.append(LinearConstraint(fila, -np.inf, len(S) - 1))

    # Reconstruir el orden del recorrido empezando en la ciudad 0
    ruta, previa = [0], None
    while len(ruta) < n:
        siguiente = next(v for v in vecinos[ruta[-1]] if v != previa)
        previa = ruta[-1]
        ruta.append(siguiente)
    return r.fun, ruta


def main():
    ap = argparse.ArgumentParser(description="Óptimo exacto del TSP de las 47 capitales")
    ap.add_argument("--distancias", choices=["carretera", "haversine"], default="carretera")
    args = ap.parse_args()

    D = cargar_distancias(args.distancias)
    print(f"Resolviendo el óptimo exacto (distancias por {args.distancias}) ...")
    L, ruta = resolver(D)
    print(f"\nÓPTIMO EXACTO: {L:.1f} km")
    print(" → ".join(CIUDADES[c] for c in ruta + [ruta[0]]))
    print(f"\nEscribe en config.ini:  optimo_{args.distancias}_km = {L:.1f}")


if __name__ == "__main__":
    main()
