# TSP · 47 capitales de la España peninsular · ACO vs GA

Problema del vendedor viajero (ruta cerrada) sobre las 47 capitales de provincia peninsulares,
resuelto con **Colonia de Hormigas (ACO)** y **Algoritmo Genético (GA)** en Python puro,
usando **distancias reales por carretera**.

## Ejecución

```bash
git clone https://github.com/TU\_USUARIO/TU\_REPO.git
cd TU\_REPO/punto_2/parte_1
python tsp\_bio.py
```

Requisitos: Python 3.8+. No hace falta instalar nada ni tener internet.
Opcional: `pip install matplotlib` para generar también `resultados.png`.

## Archivos

|Archivo|Para qué|¿Necesario para ejecutar?|
|-|-|-|
|`tsp\_bio.py`|Programa principal: ACO, GA, 2-opt y resultados|✅|
|`datos\_tsp.py`|Las 47 capitales con sus coordenadas, y la lectura de la matriz|✅|
|`distancias\_carretera.csv`|Matriz 47×47 de distancias por carretera (km)|✅|
|`config.ini`|Hiperparámetros (sin él se usan los valores por defecto)|Recomendado|
|`obtener\_carretera.py`|Genera `distancias\_carretera.csv` (una vez, con internet)|❌ Solo documenta el origen de los datos|
|`optimo\_exacto.py`|Calcula el óptimo exacto para comparar (requiere numpy y scipy)|❌ Opcional|

## Origen de las distancias por carretera

`distancias\_carretera.csv` se generó **una sola vez** con:

```bash
python obtener\_carretera.py
```

Ese script consulta el servicio *table* de **OSRM** (motor de rutas sobre OpenStreetMap):
una sola petición devuelve la distancia de la ruta en coche entre cada par de capitales.
Por calles de sentido único, ida y vuelta pueden diferir unos metros; el programa usa la media
de ambos sentidos.

El CSV está incluido en el repositorio, así que **quien lo clone no necesita internet**.
Se puede volver a ejecutar `obtener\_carretera.py` para regenerarlo, pero el resultado puede
variar ligeramente si OpenStreetMap ha actualizado sus mapas.

## Hiperparámetros: `config.ini`

Todo se cambia en `config.ini`, sin tocar el código. Cada línea indica su valor por defecto.

* `distancias = carretera` o `haversine` (línea recta calculada desde las coordenadas).
* `optimo\_carretera\_km`: el óptimo exacto, solo para la columna "Dif. óptimo".
Se obtiene con `python optimo\_exacto.py`.
* Si escribes mal un nombre o un valor fuera de rango, el programa se detiene e indica la línea.

Las opciones de terminal tienen prioridad sobre `config.ini`:

|Opción|Efecto|
|-|-|
|`--distancias haversine`|Usa distancias en línea recta|
|`--seed 7`|Cambia la semilla aleatoria (misma semilla ⇒ mismo resultado)|
|`--inicio Sevilla`|Muestra el recorrido empezando en otra capital|
|`--modo puro` o `--puro`|ACO y GA clásicos, sin búsqueda local 2-opt|
|`--config otro.ini`|Usa otro archivo de configuración|

## Qué hace el programa, paso a paso

1. **Carga los datos**: 47 ciudades y la matriz `D\[i]\[j]` en km (por carretera o Haversine).
2. **Calcula una referencia voraz** (vecino más cercano) como punto de comparación.
3. **ACO**: en cada iteración, las hormigas construyen rutas eligiendo la siguiente ciudad con
probabilidad ∝ τ^α · (1/d)^β. La mejor ruta de la iteración se pule con 2-opt; la feromona se
evapora y se refuerza en las aristas de las buenas rutas (con refuerzo extra para la mejor global).
4. **GA**: población de rutas aleatorias; selección por torneo, cruce OX, mutación por inversión,
2-opt a una fracción de los hijos (GA memético), elitismo y descarte de clones.
5. **Resultados**: ruta tramo a tramo, tabla resumen, `resultados.csv` y `resultados.png`.

La gráfica dibuja líneas rectas entre ciudades: muestra el **orden** de visita, no el trazado
de las carreteras.

