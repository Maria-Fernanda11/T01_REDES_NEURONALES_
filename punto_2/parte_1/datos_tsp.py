"""
datos_tsp.py — Datos del TSP de las 47 capitales de provincia de la España peninsular.

FUENTE DE LOS DATOS (dos archivos en la misma carpeta que este script):
    coordenadas.csv    Capital, Longitud, Latitud  (grados decimales, WGS84)
    distancias_km.csv  Matriz 47x47 de distancias por carretera en km.
                       Fila = ciudad de ORIGEN, columna = ciudad de DESTINO.

La matriz por carretera es ASIMÉTRICA: ir de A a B no siempre mide lo mismo que
volver de B a A (sentidos únicos, accesos distintos, rutas alternativas). Por eso
se conserva tal cual: D[i][j] es la distancia de i hacia j.

Uso:
    python datos_tsp.py                         -> resumen y comprobación de los datos
    from datos_tsp import CIUDADES, CAPITALES, cargar_distancias   (desde tsp_bio.py)
"""
import csv
import math
import os

CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_COORDENADAS = os.path.join(CARPETA, "coordenadas.csv")
ARCHIVO_CARRETERA = os.path.join(CARPETA, "distancias_km.csv")
R_TIERRA_KM = 6371.0


# ─────────────────────────────────────────────────────────────────────────────
# 1. Coordenadas
# ─────────────────────────────────────────────────────────────────────────────
def leer_coordenadas(archivo=ARCHIVO_COORDENADAS):
    """Devuelve [(ciudad, latitud, longitud), ...] en el orden del archivo.
    OJO: el CSV trae primero la LONGITUD y después la LATITUD."""
    if not os.path.exists(archivo):
        raise FileNotFoundError(f"No se encontró {archivo}")
    with open(archivo, encoding="utf-8-sig") as f:
        lector = csv.DictReader(f)
        capitales = [(fila["Capital"].strip(), float(fila["Latitud"]), float(fila["Longitud"]))
                     for fila in lector if fila.get("Capital")]
    return capitales


CAPITALES = leer_coordenadas()          # (ciudad, lat, lon); el índice es el id del nodo
CIUDADES = [c[0] for c in CAPITALES]
N = len(CIUDADES)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Matrices de distancias
# ─────────────────────────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    """Distancia en línea recta (km) sobre la esfera terrestre."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_TIERRA_KM * math.asin(math.sqrt(a))


def matriz_haversine():
    return [[0.0 if i == j else haversine(CAPITALES[i][1], CAPITALES[i][2],
                                          CAPITALES[j][1], CAPITALES[j][2])
             for j in range(N)] for i in range(N)]


def leer_matriz_carretera(archivo=ARCHIVO_CARRETERA):
    """Lee la matriz por carretera y la ordena según CIUDADES.
    Las ciudades se emparejan POR NOMBRE (no por posición), así que el orden de
    filas y columnas del CSV no importa, pero los nombres deben coincidir con
    los de coordenadas.csv."""
    if not os.path.exists(archivo):
        raise FileNotFoundError(f"No se encontró {archivo}")
    with open(archivo, encoding="utf-8-sig") as f:
        filas = [fila for fila in csv.reader(f) if fila]
    columnas = [c.strip() for c in filas[0][1:]]
    datos = {fila[0].strip(): [float(x) for x in fila[1:]] for fila in filas[1:]}

    faltan = sorted(set(CIUDADES) - set(columnas)) + sorted(set(CIUDADES) - set(datos))
    sobran = sorted(set(columnas) - set(CIUDADES)) + sorted(set(datos) - set(CIUDADES))
    if faltan or sobran:
        raise ValueError(f"{archivo}: los nombres no coinciden con coordenadas.csv. "
                         f"Faltan: {faltan}. Sobran: {sobran}.")
    col = {c: k for k, c in enumerate(columnas)}
    return [[datos[o][col[d]] for d in CIUDADES] for o in CIUDADES]


def simetrizar(M):
    """Media de ida y vuelta: d(i,j) = d(j,i) = (M[i][j] + M[j][i]) / 2."""
    n = len(M)
    return [[(M[i][j] + M[j][i]) / 2 for j in range(n)] for i in range(n)]


def es_simetrica(M, tol=1e-9):
    n = len(M)
    return all(abs(M[i][j] - M[j][i]) <= tol for i in range(n) for j in range(i + 1, n))


def validar(M):
    """Comprobaciones básicas para detectar datos corruptos o mal copiados."""
    assert N == 47, f"Deben ser 47 capitales y hay {N}"
    assert len(set(CIUDADES)) == N, "Hay ciudades repetidas en coordenadas.csv"
    for nombre, lat, lon in CAPITALES:     # caja que contiene la España peninsular
        assert 35.9 < lat < 43.9 and -9.4 < lon < 3.4, \
            f"Coordenadas fuera de la península: {nombre} (¿latitud y longitud invertidas?)"
    assert len(M) == N and all(len(f) == N for f in M), "La matriz no es 47x47"
    assert all(M[i][i] == 0 for i in range(N)), "La diagonal debe ser 0"
    assert all(M[i][j] > 0 for i in range(N) for j in range(N) if i != j), \
        "Hay distancias nulas o negativas entre ciudades distintas"


def cargar_distancias(fuente="carretera", sim=False):
    """Devuelve la matriz D (km) según la fuente:
       'carretera' → distancias_km.csv (asimétrica; con sim=True se promedia ida y vuelta)
       'haversine' → línea recta calculada desde coordenadas.csv (simétrica)"""
    if fuente == "carretera":
        M = leer_matriz_carretera()
        M = simetrizar(M) if sim else M
    elif fuente == "haversine":
        M = matriz_haversine()
    else:
        raise ValueError(f"Fuente desconocida: '{fuente}' (usa carretera o haversine)")
    validar(M)
    return M


if __name__ == "__main__":
    D = cargar_distancias("carretera")
    n = len(D)
    asim = [abs(D[i][j] - D[j][i]) for i in range(n) for j in range(i + 1, n)]
    i, j = CIUDADES.index("Madrid"), CIUDADES.index("Barcelona")
    print(f"OK: {n} capitales, matriz {n}x{n} por carretera")
    print(f"Madrid → Barcelona: {D[i][j]:.1f} km | Barcelona → Madrid: {D[j][i]:.1f} km")
    print(f"Asimetría ida/vuelta: media {sum(asim) / len(asim):.2f} km, máxima {max(asim):.1f} km")
