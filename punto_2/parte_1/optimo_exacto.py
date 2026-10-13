"""
optimo_exacto.py — (OPCIONAL) Calcula el recorrido ÓPTIMO EXACTO para comprobar
qué tan cerca quedan ACO y GA. No es necesario para ejecutar tsp_bio.py.

USO:
    pip install numpy scipy
    python optimo_exacto.py                          # carretera (asimétrica)
    python optimo_exacto.py --simetrizar             # carretera, media de ida y vuelta
    python optimo_exacto.py --distancias haversine   # línea recta

El resultado se copia en config.ini (optimo_carretera_km, etc.).

MÉTODO: programación lineal entera, formulación DFJ (Dantzig–Fulkerson–Johnson)
para el TSP ASIMÉTRICO (también vale si la matriz es simétrica).
    Variables x_ij ∈ {0,1}: 1 si el recorrido va DE i HACIA j.
    Minimizar Σ d_ij · x_ij
    sujeto a  Σ_j x_ij = 1  (de cada ciudad se sale una vez)
              Σ_i x_ij = 1  (a cada ciudad se llega una vez)
    Si la solución tiene varios ciclos separados (subtours), se añade la restricción
    Σ_{i,j ∈ S} x_ij ≤ |S| − 1 para cada ciclo S y se resuelve otra vez, hasta que
    queda un único ciclo. Ese ciclo es el óptimo global garantizado.
"""
import argparse
import sys

try:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
except ImportError:
    sys.exit("Este script necesita numpy y scipy:  pip install numpy scipy")

try:    # ejecutado como parte del paquete
    from .datos_tsp import CIUDADES, cargar_distancias
except ImportError:    # ejecutado directamente (python optimo_exacto.py)
    from datos_tsp import CIUDADES, cargar_distancias


def resolver(D):
    n = len(D)
    arcos = [(i, j) for i in range(n) for j in range(n) if i != j]   # arcos dirigidos
    c = np.array([D[i][j] for i, j in arcos])
    sale, entra = np.zeros((n, len(arcos))), np.zeros((n, len(arcos)))
    for k, (i, j) in enumerate(arcos):
        sale[i, k] = 1
        entra[j, k] = 1
    restricciones = [LinearConstraint(sale, 1, 1), LinearConstraint(entra, 1, 1)]

    while True:
        r = milp(c, constraints=restricciones, integrality=np.ones(len(arcos)),
                 bounds=Bounds(0, 1))
        if not r.success:
            sys.exit(f"El solver falló: {r.message}")
        siguiente = {i: j for k, (i, j) in enumerate(arcos) if r.x[k] > 0.5}

        # Separar la solución en ciclos
        ciclos, vistos = [], set()
        for s in range(n):
            if s in vistos:
                continue
            ciclo, u = [], s
            while u not in vistos:
                vistos.add(u)
                ciclo.append(u)
                u = siguiente[u]
            ciclos.append(ciclo)

        if len(ciclos) == 1:
            return r.fun, ciclos[0]
        print(f"   {len(ciclos)} subtours encontrados → se añaden restricciones y se repite")
        for S in ciclos:                                       # eliminación de subtours
            S = set(S)
            fila = np.array([1.0 if i in S and j in S else 0.0 for i, j in arcos])
            restricciones.append(LinearConstraint(fila, -np.inf, len(S) - 1))


def main():
    ap = argparse.ArgumentParser(description="Óptimo exacto del TSP de las 47 capitales")
    ap.add_argument("--distancias", choices=["carretera", "haversine"], default="carretera")
    ap.add_argument("--simetrizar", action="store_true",
                    help="usar la media de ida y vuelta (solo con carretera)")
    args = ap.parse_args()

    D = cargar_distancias(args.distancias, sim=args.simetrizar)
    clave = args.distancias + ("_simetrizada" if args.simetrizar and
                               args.distancias == "carretera" else "")
    print(f"Resolviendo el óptimo exacto ({clave}) ...")
    L, ruta = resolver(D)
    k = ruta.index(CIUDADES.index("Madrid")) if "Madrid" in CIUDADES else 0
    ruta = ruta[k:] + ruta[:k]
    print(f"\nÓPTIMO EXACTO: {L:.1f} km")
    print(" → ".join(CIUDADES[c] for c in ruta + [ruta[0]]))
    print(f"\nEscribe en config.ini:  optimo_{clave}_km = {L:.1f}")


if __name__ == "__main__":
    main()
