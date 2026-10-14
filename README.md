# Trabajo 1 — Optimización numérica, metaheurística y combinatoria

Este repositorio resuelve los dos problemas del trabajo. Cada uno se ejecuta **con un solo comando** desde la terminal:

| Problema | Qué resuelve | Carpeta | Tiempo |
|---|---|---|---|
| **1** | Buscar el mínimo de las funciones Rosenbrock y Rastrigin (2D y 3D) con descenso por gradiente, algoritmo genético, PSO y evolución diferencial | `punto_1/` | < 1 min |
| **2.1** | Ruta más **corta** para recorrer las 47 capitales de la España peninsular (TSP) con colonia de hormigas (ACO) y algoritmo genético (GA) | `punto_2/parte_1/` | ~10 s |
| **2.2** | Ruta más **barata** para el mismo recorrido: tiempo + combustible + peajes, escenarios 2016 y 2026 | `punto_2/parte_2/` | ~1,5 min |

Todos los datos están dentro del repositorio: **no hace falta conexión a internet** para ejecutar nada.

---

## 1. Instalación (una sola vez)

**Requisito:** Python **3.10 a 3.13**. Compruébalo con `python3 --version`.

```bash
git clone https://github.com/MgtDevNet/T01_REDES_NEURONALES_.git
cd T01_REDES_NEURONALES_

python3 -m venv .venv                 # crea un entorno aislado
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements.txt       # instala las versiones exactas
```

> En Windows, escribe `python` en lugar de `python3` en todos los comandos.

Las versiones de las librerías están fijadas en `requirements.txt`, y todos los programas usan **semillas fijas**: la misma configuración da siempre el mismo resultado.

Cada vez que abras una terminal nueva, activa el entorno antes de ejecutar: `source .venv/bin/activate`.

---

## 2. Problema 1 — Rosenbrock y Rastrigin

```bash
cd punto_1
python3 funcion1.py check                               # verificación rápida (1 s)
python3 funcion1.py run   --algo pso --dim 2 --seed 42  # una corrida
python3 funcion1.py stats --runs 30 --dims 2 3          # comparación de algoritmos (~45 s)
python3 funcion1.py gif   --algo gradient_descent       # animación 2D (~10 s)
```

| Comando | Qué hace | Dónde guarda |
|---|---|---|
| `check` | Comprueba que todo funciona | — |
| `run` | Una corrida de un algoritmo | pantalla |
| `stats` | 30 corridas por algoritmo: media, desviación, % de éxito | `results/stats_rosenbrock.csv` |
| `gif` | Animación de la búsqueda (solo 2D) | `figs/` |

**Opciones útiles**
- Algoritmo: `--algo gradient_descent | genetic | pso | differential_evolution`
- Función: `--problem rosenbrock | rastrigin`
- Hiperparámetros sin tocar el código: `--param pso.inercia=0.6` o `--config config.json`

Todos los algoritmos tienen el **mismo presupuesto de evaluaciones** de la función (`--max-evals`, por defecto 20 000), para que la comparación sea justa.

El cuaderno `Experimentos.ipynb` contiene los experimentos del informe.

---

## 3. Problema 2.1 — Ruta más corta (TSP)

```bash
cd punto_2/parte_1
python3 tsp_bio.py
```

**Qué verás:** la ruta tramo a tramo de cada algoritmo y una tabla comparativa con la distancia a la solución óptima exacta (6207,7 km).

**Resultados:** `resultados_puro.csv` (orden de las ciudades) y `resultados_puro.png` (mapa y convergencia).

**Parámetros:** se cambian en `config.ini` (ciudad de inicio, semilla, hormigas, generaciones…). Opciones útiles:
```bash
python3 tsp_bio.py --modo hibrido     # añade búsqueda local (2-opt + Or-opt)
python3 tsp_bio.py --al-reves         # compara la ruta en los dos sentidos
python3 optimo_exacto.py              # óptimo exacto con programación lineal entera (~10 s)
```

Las distancias son kilómetros **por carretera** (OSRM sobre OpenStreetMap), y la ida puede medir distinto que la vuelta.

---

## 4. Problema 2.2 — Ruta más barata (costos)

```bash
cd punto_2/parte_2
python3 src/tsp_espana.py                      # completo: 2016 y 2026, con GIF (~1,5 min)
python3 src/tsp_espana.py --scenario 2026      # demo rápida (~45 s)
```

**Modelo de costo** de cada tramo:

```
costo = valor_hora × tiempo  +  combustible  +  peaje
        tiempo      = km / 80 km/h                 (supuesto: velocidad constante)
        combustible = km × 4,7 L/100 km × precio   (Toyota Corolla)
        peaje       = matriz de peajes sintéticos
```

**Qué verás:** la ruta de cada algoritmo tramo a tramo (km, horas y €), una comparación ACO vs GA que indica cuál es mejor y un resumen final.

**Resultados** (en `results/2016/` y `results/2026/`):

| Archivo | Contenido |
|---|---|
| `ruta_aco.csv`, `ruta_ga.csv` | Orden de las ciudades con el costo de cada tramo |
| `mapa_ruta_*.gif` | Animación de la ruta sobre el mapa |
| `convergencia_*.png` | Evolución del mejor costo |
| `../resumen.csv` | Totales de cada escenario y algoritmo |

**Parámetros:** se cambian en `config.ini` (valor de la hora, precio del combustible, consumo, velocidad, parámetros de ACO y GA). También desde la terminal:
```bash
python3 src/tsp_espana.py --scenario 2016 --algorithm ga --seed 7 --sin-gif
```

**Datos y fuentes:** ver `data/README_DATOS.md`. La carpeta `recoleccion_datos/` contiene los scripts y el `docker-compose.yml` con los que se obtuvieron las matrices desde un servidor OpenRouteService local. **No hace falta ejecutarlos**: las matrices ya están en `data/`.

---

## 5. Estructura del repositorio

```
├── README.md                 ← este archivo
├── requirements.txt          ← versiones exactas de las librerías
├── punto_1/
│   ├── funcion1.py           ← problema 1 (todos los algoritmos)
│   └── Experimentos.ipynb
└── punto_2/
    ├── parte_1/              ← ruta más corta
    │   ├── tsp_bio.py        ← programa principal
    │   ├── config.ini        ← parámetros
    │   ├── datos_tsp.py      ← carga de datos
    │   ├── optimo_exacto.py  ← óptimo exacto (verificación)
    │   └── *.csv             ← coordenadas y distancias
    └── parte_2/              ← ruta más barata
        ├── src/tsp_espana.py ← programa principal
        ├── config.ini        ← parámetros
        ├── data/             ← matrices de distancias, peajes y fuentes
        ├── results/          ← se regenera al ejecutar
        └── recoleccion_datos/← cómo se obtuvieron los datos (opcional)
```

---

## 6. Problemas frecuentes

| Problema | Solución |
|---|---|
| `python3: command not found` (Windows) | Usa `python` |
| `ModuleNotFoundError: No module named 'numpy'` | Activa el entorno (`source .venv/bin/activate`) y repite `pip install -r requirements.txt` |
| `No se encontró config.ini` | Ejecuta el comando desde la carpeta indicada en cada sección |
| `Permission denied` en `recoleccion_datos/` | Son archivos creados por Docker: `sudo chown -R $USER:$USER punto_2/parte_2/recoleccion_datos` |
