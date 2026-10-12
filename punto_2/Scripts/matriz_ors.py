"""
Recolecta la matriz de distancias y tiempos entre las 47 capitales con
OpenRouteService y la guarda en CSV dentro de la carpeta de datos del repo.

Se ejecuta UNA vez (necesita internet y una API key). Los experimentos de
ACO y GA leen despues los CSV y nunca llaman a la API.

Uso:
    python matriz_ors.py
    python matriz_ors.py --entrada datos.xlsx --hoja Hoja1 --salida datos

La API key se toma de la variable de entorno ORS_API_KEY; si no existe,
el script la pide por pantalla. Nunca la escribas dentro del codigo.
"""
import argparse
import getpass
import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import requests

URL = "https://api.openrouteservice.org/v2/matrix/driving-car"
PERFIL = "driving-car"
N_CIUDADES = 47
UMBRAL_AJUSTE_M = 500  # avisar si un punto se ajusto a la carretera a mas de esto


def leer_coordenadas(ruta, hoja):
    df = pd.read_excel(ruta, sheet_name=hoja)
    df = df[["Capital", "Longitud", "Latitud"]].copy()

    # Si alguna coordenada quedo como texto ("40,41") esto falla y te avisa
    for col in ["Longitud", "Latitud"]:
        df[col] = pd.to_numeric(df[col], errors="raise")

    if len(df) != N_CIUDADES:
        raise ValueError(f"Se esperaban {N_CIUDADES} ciudades y hay {len(df)}")
    if not df["Capital"].is_unique:
        raise ValueError("Hay nombres de capital repetidos")
    if not df["Longitud"].between(-9.5, 3.5).all():
        raise ValueError("Longitud fuera de rango para la Espana peninsular (falta el signo -?)")
    if not df["Latitud"].between(36, 43.9).all():
        raise ValueError("Latitud fuera de rango para la Espana peninsular")
    return df


def pedir_matriz(df, api_key):
    cuerpo = {
        "locations": df[["Longitud", "Latitud"]].values.tolist(),  # orden [lon, lat]
        "metrics": ["distance", "duration"],
        "units": "km",
        "resolve_locations": True,
    }
    cabeceras = {
        "Authorization": api_key,
        "Content-Type": "application/json; charset=utf-8",
    }
    respuesta = requests.post(URL, headers=cabeceras, json=cuerpo, timeout=120)
    if respuesta.status_code != 200:
        raise SystemExit(f"Error {respuesta.status_code}: {respuesta.text}")
    return respuesta.json()


def main():
    parser = argparse.ArgumentParser(description="Matriz de distancias y tiempos con OpenRouteService")
    parser.add_argument("--entrada", default="datos.xlsx", help="Excel con Capital, Longitud, Latitud")
    parser.add_argument("--hoja", default="Hoja1")
    parser.add_argument("--salida", default="datos", help="Carpeta donde se guardan los CSV")
    # parse_known_args ignora los argumentos extra que agrega Jupyter / la ventana interactiva
    args, _ = parser.parse_known_args()

    api_key = os.environ.get("ORS_API_KEY") or getpass.getpass("Pega tu API key de ORS: ")

    df = leer_coordenadas(args.entrada, args.hoja)
    nombres = df["Capital"].tolist()

    print("Pidiendo la matriz a OpenRouteService...")
    datos = pedir_matriz(df, api_key)

    dist = pd.DataFrame(datos["distances"], index=nombres, columns=nombres)
    tiempo_h = pd.DataFrame(datos["durations"], index=nombres, columns=nombres) / 3600

    if dist.isna().any().any() or tiempo_h.isna().any().any():
        raise SystemExit("Hay pares de ciudades sin ruta (valores nulos). Revisa esas coordenadas.")

    # Revision de puntos que se ajustaron lejos de una carretera
    max_ajuste = 0.0
    for i, d in enumerate(datos.get("destinations", [])):
        ajuste_m = d.get("snapped_distance")
        if ajuste_m is None:
            continue
        max_ajuste = max(max_ajuste, ajuste_m)
        if ajuste_m > UMBRAL_AJUSTE_M:
            print(f"Aviso: {nombres[i]} se ajusto a {ajuste_m:.0f} m de la carretera mas cercana")

    # Revision de asimetria (ir de i a j no tiene por que costar lo mismo que de j a i)
    asim_km = (dist - dist.T).abs().max().max()
    asim_h = (tiempo_h - tiempo_h.T).abs().max().max()
    print(f"Maxima asimetria: {asim_km:.2f} km y {asim_h:.3f} h")

    meta = pd.DataFrame(
        {
            "clave": [
                "fuente",
                "perfil",
                "fecha_consulta",
                "n_ciudades",
                "unidad_distancia",
                "unidad_tiempo",
                "max_ajuste_a_carretera_m",
            ],
            "valor": [
                "OpenRouteService Matrix API v2",
                PERFIL,
                date.today().isoformat(),
                len(df),
                "km",
                "horas",
                round(max_ajuste, 1),
            ],
        }
    )

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    # utf-8-sig para que Excel muestre bien las tildes; pandas lo lee sin problema
    df.to_csv(salida / "coordenadas.csv", index=False, encoding="utf-8-sig")
    dist.to_csv(salida / "distancias_km.csv", index_label="Capital", encoding="utf-8-sig")
    tiempo_h.to_csv(salida / "tiempos_horas.csv", index_label="Capital", encoding="utf-8-sig")
    meta.to_csv(salida / "metadatos_ors.csv", index=False, encoding="utf-8-sig")
    (salida / "ors_respuesta_cruda.json").write_text(
        json.dumps(datos, ensure_ascii=False), encoding="utf-8"
    )

    print(f"Listo. Archivos guardados en '{salida}/'")


if __name__ == "__main__":
    main()
