import argparse
import json
from pathlib import Path

import pandas as pd
import requests

# Servidor ORS local (v8): el prefijo /ors es obligatorio
URL = "http://localhost:8080/ors/v2/matrix/driving-car"
HEALTH_URL = "http://localhost:8080/ors/v2/health"
N_CIUDADES = 47


def verificar_servidor():
    try:
        estado = requests.get(HEALTH_URL, timeout=10).json().get("status")
    except requests.RequestException as e:
        raise SystemExit(f"No se pudo conectar con ORS en localhost:8080 ({e}). "
                         "¿Está corriendo el contenedor? -> docker compose up -d")
    if estado != "ready":
        raise SystemExit(f"ORS responde pero aún no está listo (status={estado}). Espera un poco.")


def leer_coordenadas(ruta, hoja):
    df = pd.read_excel(ruta, sheet_name=hoja)
    df = df[["Capital", "Longitud", "Latitud"]].copy()
    for col in ["Longitud", "Latitud"]:
        df[col] = pd.to_numeric(df[col], errors="raise")

    if len(df) != N_CIUDADES:
        raise SystemExit(f"Se esperaban {N_CIUDADES} ciudades y el archivo tiene {len(df)}.")

    # Comprobación básica: longitud y latitud no intercambiadas (España peninsular)
    fuera = df[~df["Longitud"].between(-10, 5) | ~df["Latitud"].between(35, 44.5)]
    if not fuera.empty:
        raise SystemExit("Coordenadas fuera de la España peninsular (¿longitud y latitud "
                         f"invertidas?):\n{fuera.to_string(index=False)}")
    return df


def pedir_matriz_local(df):
    cuerpo = {
        "locations": df[["Longitud", "Latitud"]].values.tolist(),  # orden [lon, lat]
        "metrics": ["distance", "duration"],
        "units": "km",
    }
    print("Calculando matriz en el servidor local...")
    respuesta = requests.post(URL, json=cuerpo, timeout=300)

    if respuesta.status_code != 200:
        raise SystemExit(f"Error {respuesta.status_code}: {respuesta.text}")
    return respuesta.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entrada", default="datos_capitales.xlsx")
    parser.add_argument("--hoja", default="Hoja1")
    parser.add_argument("--salida", default="datos_100_por_ciento_espana")
    args = parser.parse_args()

    verificar_servidor()
    df = leer_coordenadas(args.entrada, args.hoja)
    nombres = df["Capital"].tolist()

    datos = pedir_matriz_local(df)

    dist = pd.DataFrame(datos["distances"], index=nombres, columns=nombres)
    tiempo_h = pd.DataFrame(datos["durations"], index=nombres, columns=nombres) / 3600

    # Pares sin ruta posible: ORS devuelve null -> NaN
    sin_ruta = int(dist.isna().sum().sum())
    if sin_ruta:
        print(f"ATENCIÓN: {sin_ruta} pares sin ruta. Revisa esas coordenadas.")

    # Distancia que ORS tuvo que "mover" cada punto hasta la carretera más cercana
    snaps = [s.get("snapped_distance", 0) for s in datos.get("sources", [])]
    lejanos = [(n, round(d)) for n, d in zip(nombres, snaps) if d and d > 500]
    if lejanos:
        print(f"Puntos a más de 500 m de una carretera (revisa coordenadas): {lejanos}")

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    df.to_csv(salida / "coordenadas.csv", index=False, encoding="utf-8-sig")
    dist.to_csv(salida / "distancias_km.csv", index_label="Capital", encoding="utf-8-sig")
    tiempo_h.to_csv(salida / "tiempos_horas.csv", index_label="Capital", encoding="utf-8-sig")
    (salida / "ors_respuesta_cruda.json").write_text(
        json.dumps(datos, ensure_ascii=False), encoding="utf-8")

    asimetria = (dist - dist.T).abs().max().max()
    print(f"\nListo. Matrices guardadas en '{salida}/'")
    print(f"Máxima diferencia ida/vuelta entre dos ciudades: {asimetria:.1f} km")


if __name__ == "__main__":
    main()