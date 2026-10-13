"""
datos_tsp.py — Datos del TSP de las 47 capitales de provincia de la España peninsular.

Reproducible al 100 %: no usa internet ni librerías externas (solo la librería estándar).
Coordenadas: centro urbano de cada capital (WGS84, grados decimales, 4 decimales).
Distancias: Haversine (línea recta sobre la esfera terrestre, R = 6371 km).

Distancias por carretera (opcional): cargar_distancias("carretera") lee
distancias_carretera.csv, que se genera UNA vez con obtener_carretera.py.

Uso:
    python datos_tsp.py          -> genera capitales.csv y distancias.csv (Haversine)
    from datos_tsp import CIUDADES, cargar_distancias   (desde tsp_bio.py)
"""
import csv
import math
import os

# (ciudad, latitud, longitud) — el índice en la lista es el id del nodo (0..46)
CAPITALES = [
    # Andalucía
    ("Almería", 36.8340, -2.4637),
    ("Cádiz", 36.5271, -6.2886),
    ("Córdoba", 37.8882, -4.7794),
    ("Granada", 37.1773, -3.5986),
    ("Huelva", 37.2614, -6.9447),
    ("Jaén", 37.7796, -3.7849),
    ("Málaga", 36.7213, -4.4214),
    ("Sevilla", 37.3891, -5.9845),
    # Aragón
    ("Huesca", 42.1401, -0.4089),
    ("Teruel", 40.3456, -1.1065),
    ("Zaragoza", 41.6488, -0.8891),
    # Asturias y Cantabria
    ("Oviedo", 43.3614, -5.8494),
    ("Santander", 43.4623, -3.8099),
    # Castilla-La Mancha
    ("Albacete", 38.9943, -1.8585),
    ("Ciudad Real", 38.9848, -3.9274),
    ("Cuenca", 40.0704, -2.1374),
    ("Guadalajara", 40.6329, -3.1669),
    ("Toledo", 39.8628, -4.0273),
    # Castilla y León
    ("Ávila", 40.6564, -4.6818),
    ("Burgos", 42.3439, -3.6969),
    ("León", 42.5987, -5.5671),
    ("Palencia", 42.0095, -4.5288),
    ("Salamanca", 40.9701, -5.6635),
    ("Segovia", 40.9429, -4.1088),
    ("Soria", 41.7666, -2.4790),
    ("Valladolid", 41.6523, -4.7245),
    ("Zamora", 41.5034, -5.7467),
    # Cataluña
    ("Barcelona", 41.3874, 2.1686),
    ("Girona", 41.9794, 2.8214),
    ("Lleida", 41.6176, 0.6200),
    ("Tarragona", 41.1189, 1.2445),
    # Comunidad Valenciana
    ("Alicante", 38.3452, -0.4810),
    ("Castellón de la Plana", 39.9864, -0.0513),
    ("Valencia", 39.4699, -0.3763),
    # Extremadura
    ("Badajoz", 38.8794, -6.9707),
    ("Cáceres", 39.4753, -6.3724),
    # Galicia
    ("A Coruña", 43.3623, -8.4115),
    ("Lugo", 43.0097, -7.5568),
    ("Ourense", 42.3358, -7.8639),
    ("Pontevedra", 42.4310, -8.6444),
    # Madrid, Murcia, Navarra, La Rioja
    ("Madrid", 40.4168, -3.7038),
    ("Murcia", 37.9922, -1.1307),
    ("Pamplona", 42.8125, -1.6458),
    ("Logroño", 42.4627, -2.4450),
    # País Vasco
    ("Bilbao", 43.2630, -2.9350),
    ("San Sebastián", 43.3183, -1.9812),
    ("Vitoria-Gasteiz", 42.8467, -2.6716),
]

R_TIERRA_KM = 6371.0


def haversine(lat1, lon1, lat2, lon2):
    """Distancia en km entre dos puntos (lat/lon en grados) sobre la esfera."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_TIERRA_KM * math.asin(math.sqrt(a))


def matriz_distancias(capitales):
    """Matriz simétrica n x n (lista de listas) con la diagonal en 0."""
    n = len(capitales)
    D = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):  # solo media matriz: D es simétrica
            d = haversine(capitales[i][1], capitales[i][2], capitales[j][1], capitales[j][2])
            D[i][j] = D[j][i] = d
    return D


def validar(capitales, D):
    """Comprobaciones básicas para detectar datos corruptos o mal copiados."""
    assert len(capitales) == 47, "Deben ser exactamente 47 capitales"
    assert len({c[0] for c in capitales}) == 47, "Hay ciudades repetidas"
    for nombre, lat, lon in capitales:  # caja que contiene la España peninsular
        assert 35.9 < lat < 43.9 and -9.4 < lon < 3.4, f"Coordenadas fuera de rango: {nombre}"
    n = len(D)
    assert all(D[i][i] == 0 for i in range(n))
    assert all(D[i][j] > 0 for i in range(n) for j in range(n) if i != j), "Distancia nula entre ciudades distintas"


# Se calcula al importar el módulo, así GA y ACO usan exactamente los mismos datos
CIUDADES = [c[0] for c in CAPITALES]
D = matriz_distancias(CAPITALES)
validar(CAPITALES, D)


# ─────────────────────────────────────────────────────────────────────────────
# Distancias por carretera (opcional)
# ─────────────────────────────────────────────────────────────────────────────
CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_CARRETERA = os.path.join(CARPETA, "distancias_carretera.csv")


def leer_matriz_carretera(archivo=ARCHIVO_CARRETERA):
    """Lee la matriz por carretera generada (una sola vez) con obtener_carretera.py.

    - Comprueba que las ciudades estén en el mismo orden que CIUDADES.
    - Simetriza: por calles de sentido único, A→B y B→A pueden diferir unos metros;
      ACO y 2-opt suponen d(A,B) = d(B,A), así que se usa la media de ambos sentidos.
    """
    if not os.path.exists(archivo):
        raise FileNotFoundError(
            f"No se encontró {archivo}.\n"
            "Genera el archivo una vez (requiere internet) con:  python obtener_carretera.py\n"
            "o usa 'distancias = haversine' en config.ini.")

    with open(archivo, encoding="utf-8-sig") as f:
        filas = list(csv.reader(f))
    cabecera, filas = filas[0][1:], [f for f in filas[1:] if f]

    if cabecera != CIUDADES or [f[0] for f in filas] != CIUDADES:
        raise ValueError(f"{archivo}: las ciudades no coinciden (o no están en el mismo "
                         "orden) con las de datos_tsp.py. Vuelve a generarlo.")
    M = [[float(x) for x in f[1:]] for f in filas]
    n = len(M)
    D_carr = [[(M[i][j] + M[j][i]) / 2 for j in range(n)] for i in range(n)]
    validar(CAPITALES, D_carr)
    return D_carr


def cargar_distancias(fuente="haversine"):
    """Devuelve la matriz D según la fuente: 'haversine' (línea recta) o 'carretera'."""
    if fuente == "haversine":
        return D
    if fuente == "carretera":
        return leer_matriz_carretera()
    raise ValueError(f"Fuente de distancias desconocida: '{fuente}' (usa haversine o carretera)")


if __name__ == "__main__":
    with open("capitales.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "ciudad", "lat", "lon"])
        for i, (c, lat, lon) in enumerate(CAPITALES):
            w.writerow([i, c, lat, lon])

    with open("distancias.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ciudad"] + CIUDADES)
        for c, fila in zip(CIUDADES, D):
            w.writerow([c] + [f"{d:.2f}" for d in fila])

    i, j = CIUDADES.index("Madrid"), CIUDADES.index("Barcelona")
    print(f"OK: {len(CIUDADES)} capitales, matriz {len(D)}x{len(D)}")
    print(f"Comprobación Madrid–Barcelona: {D[i][j]:.1f} km (esperado ≈ 505 km)")
    print("Generados: capitales.csv, distancias.csv")
