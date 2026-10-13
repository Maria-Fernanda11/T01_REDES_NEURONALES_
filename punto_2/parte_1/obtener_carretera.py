"""
obtener_carretera.py — Descarga la matriz 47x47 de distancias POR CARRETERA (km)
entre las 47 capitales y la guarda en distancias_carretera.csv.

SE EJECUTA UNA SOLA VEZ (necesita internet):
    python obtener_carretera.py

Después, tsp_bio.py lee el CSV sin conexión. Sube distancias_carretera.csv a
GitHub: quien clone el repositorio no necesitará internet ni este script.

FUENTE: OSRM (Open Source Routing Machine), motor de rutas sobre los datos de
OpenStreetMap. Servicio "table": una sola petición devuelve todas las distancias
de la ruta más rápida en coche entre cada par de ciudades.

Solo usa la librería estándar de Python.
"""
import argparse
import csv
import json
import os
import urllib.error
import urllib.request

from punto_2.parte_1.datos_tsp import CAPITALES, CIUDADES

SERVIDOR_POR_DEFECTO = "https://router.project-osrm.org"  # servidor público de demostración
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "distancias_carretera.csv")


def descargar(servidor):
    """Pide a OSRM la matriz de distancias (metros) y la devuelve en km."""
    # OSRM espera las coordenadas como "lon,lat" separadas por ';'
    coords = ";".join(f"{lon},{lat}" for _, lat, lon in CAPITALES)
    url = f"{servidor.rstrip('/')}/table/v1/driving/{coords}?annotations=distance"
    peticion = urllib.request.Request(url, headers={"User-Agent": "tsp-47-capitales/1.0"})

    with urllib.request.urlopen(peticion, timeout=120) as r:
        datos = json.load(r)

    if datos.get("code") != "Ok":
        raise RuntimeError(f"OSRM respondió con error: {datos.get('code')} {datos.get('message', '')}")

    M = datos["distances"]
    n = len(CIUDADES)
    if len(M) != n or any(len(fila) != n for fila in M):
        raise RuntimeError("La matriz recibida no es de 47x47.")
    for i in range(n):
        for j in range(n):
            if M[i][j] is None:  # OSRM devuelve null si no encuentra ruta
                raise RuntimeError(f"Sin ruta por carretera: {CIUDADES[i]} → {CIUDADES[j]}")
    return [[d / 1000.0 for d in fila] for fila in M]  # metros → km


def guardar(M, archivo=SALIDA):
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ciudad"] + CIUDADES)
        for c, fila in zip(CIUDADES, M):
            w.writerow([c] + [f"{d:.2f}" for d in fila])


def main():
    ap = argparse.ArgumentParser(description="Descarga la matriz de distancias por carretera")
    ap.add_argument("--servidor", default=SERVIDOR_POR_DEFECTO,
                    help="URL de un servidor OSRM (por defecto, el público)")
    args = ap.parse_args()

    print(f"Descargando matriz {len(CIUDADES)}x{len(CIUDADES)} desde {args.servidor} ...")
    try:
        M = descargar(args.servidor)
    except urllib.error.URLError as e:
        raise SystemExit(f"No se pudo conectar con el servidor OSRM: {e}\n"
                         "Comprueba tu conexión a internet e inténtalo de nuevo en unos minutos.")
    guardar(M)

    # Comprobaciones para el usuario
    n = len(M)
    asim = max(abs(M[i][j] - M[j][i]) for i in range(n) for j in range(n))
    i, j = CIUDADES.index("Madrid"), CIUDADES.index("Barcelona")
    print(f"Guardado: {SALIDA}")
    print(f"Madrid → Barcelona por carretera: {M[i][j]:.1f} km (esperado ≈ 620 km)")
    print(f"Máxima diferencia ida/vuelta: {asim:.1f} km (tsp_bio.py usa la media de ambos sentidos)")


if __name__ == "__main__":
    main()
