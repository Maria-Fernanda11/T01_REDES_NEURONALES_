# Cómo ejecutar el punto 1

# Cómo ejecutar el punto 2, parte 1 (TSP de las 47 capitales)

## Requisitos

- **Python 3.8 o superior.** Compruébalo con `python3 --version`.
- **No hace falta instalar ninguna librería** ni tener conexión a internet.

## Pasos

```bash
git clone https://github.com/TU_USUARIO/TU_REPO.git
cd TU_REPO/punto_2/parte_1
python3 tsp_bio.py
```

En Windows, usa `python` en lugar de `python3`.

## Resultado esperado

En unos segundos, la terminal muestra la ruta tramo a tramo y un resumen:

```
   Algoritmo     Longitud  Dif. óptimo   Hallada en   Tiempo
   ACO          6442.5 km      +3.78 %    iter. 111    ...
   GA           6257.0 km      +0.79 %     gen. 705    ...
```

El orden de visita se guarda en `resultados_puro.csv`, dentro de la misma carpeta.

## Opcional: la gráfica

Para generar también la gráfica (`resultados_puro.png`), instala `matplotlib` una sola vez y vuelve a ejecutar:

```bash
pip install matplotlib
python3 tsp_bio.py
```

Sin `matplotlib` el programa funciona igual; solo omite la gráfica.

## Opcional: versión con búsqueda local

```bash
python3 tsp_bio.py --modo hibrido
```

Con búsqueda local, ambos algoritmos alcanzan el óptimo exacto de 6207,7 km.
Esta ejecución sobrescribe los archivos de resultados; vuelve a ejecutar `python3 tsp_bio.py` para recuperar los de la versión principal.


# Cómo ejecutar el punto 2, parte 2 (TSP de las 47 capitales con costos)
