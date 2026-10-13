import argparse
import json
import os
from datetime import date
from pathlib import Path
import pandas as pd
import requests

# ¡Atención aquí! Esta URL apunta a TU PROPIA COMPUTADORA (localhost)
URL = "http://localhost:8080/v2/matrix/driving-car"
N_CIUDADES = 47

def leer_coordenadas(ruta, hoja):
    df = pd.read_excel(ruta, sheet_name=hoja)
    df = df[["Capital", "Longitud", "Latitud"]].copy()
    for col in ["Longitud", "Latitud"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    return df

def pedir_matriz_local(df):
    cuerpo = {
        "locations": df[["Longitud", "Latitud"]].values.tolist(),
        "metrics": ["distance", "duration"],
        "units": "km",
        "resolve_locations": True
    }
    cabeceras = {
        "Content-Type": "application/json; charset=utf-8",
    }
    # Le damos un timeout muy alto (3600 segundos) porque al ser local y 47x47, 
    # tu computadora se tomará unos minutos en procesar todas las combinaciones.
    print("Enviando petición a tu servidor local. Esto puede tardar un par de minutos, no lo canceles...")
    respuesta = requests.post(URL, headers=cabeceras, json=cuerpo, timeout=3600)
    
    if respuesta.status_code != 200:
        raise SystemExit(f"Error {respuesta.status_code}: {respuesta.text}")
    return respuesta.json()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entrada", default="datos.xlsx")
    parser.add_argument("--hoja", default="Hoja1")
    parser.add_argument("--salida", default="datos_100_por_ciento_espana")
    args, _ = parser.parse_known_args()

    df = leer_coordenadas(args.entrada, args.hoja)
    nombres = df["Capital"].tolist()

    datos = pedir_matriz_local(df)

    dist = pd.DataFrame(datos["distances"], index=nombres, columns=nombres)
    tiempo_h = pd.DataFrame(datos["durations"], index=nombres, columns=nombres) / 3600

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    df.to_csv(salida / "coordenadas.csv", index=False, encoding="utf-8-sig")
    dist.to_csv(salida / "distancias_km.csv", index_label="Capital", encoding="utf-8-sig")
    tiempo_h.to_csv(salida / "tiempos_horas.csv", index_label="Capital", encoding="utf-8-sig")
    (salida / "ors_respuesta_cruda.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")

    print(f"\n¡Éxito! Matrices 100% españolas guardadas en la carpeta '{salida}/'")

if __name__ == "__main__":
    main()
