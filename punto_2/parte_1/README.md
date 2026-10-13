# TSP · 47 capitales de la España peninsular · ACO vs GA

Problema del vendedor viajero (ruta cerrada) sobre las 47 capitales de provincia peninsulares,
resuelto con **Colonia de Hormigas (ACO)** y **Algoritmo Genético (GA)** en Python puro,
usando **distancias reales por carretera**.

## Ejecución

```bash
git clone https://github.com/TU_USUARIO/TU_REPO.git
cd TU_REPO/punto_2/parte_1
python tsp_bio.py
```

Requisitos: Python 3.8+. No hace falta instalar nada ni tener internet.
Opcional: `pip install matplotlib` para generar también `resultados.png`.

## Archivos

| Archivo | Para qué | ¿Necesario? |
|---|---|---|
| `tsp_bio.py` | Programa principal: ACO, GA, búsqueda local y resultados | ✅ |
| `datos_tsp.py` | Lee y valida los dos CSV de datos | ✅ |
| `coordenadas.csv` | Capital, longitud y latitud de las 47 capitales | ✅ |
| `distancias_km.csv` | Matriz 47×47 de distancias por carretera (fila = origen, columna = destino) | ✅ |
| `config.ini` | Hiperparámetros (sin él se usan los valores por defecto) | Recomendado |
| `optimo_exacto.py` | Calcula el óptimo exacto para comparar (requiere numpy y scipy) | ❌ Opcional |

## Datos

La matriz por carretera es **asimétrica**: ir de A a B no siempre mide lo mismo que volver
de B a A. El programa respeta el sentido de cada tramo, así que el recorrido óptimo tiene
una dirección concreta (el mismo recorrido al revés es más largo). Con `simetrizar = si` en
`config.ini` se usa la media de ida y vuelta, para comparar.

| Variante | Óptimo exacto |
|---|---|
| Carretera, con sentido (por defecto) | 6207,7 km |
| Carretera, media ida/vuelta | 6240,0 km |
| Línea recta (Haversine) | 4795,8 km |

## Hiperparámetros: `config.ini`

Todo se cambia en `config.ini`, sin tocar el código. Cada línea indica su valor por defecto.

- `distancias = carretera` o `haversine` (línea recta calculada desde las coordenadas); `simetrizar = no` o `si`.
- `optimo_carretera_km`: el óptimo exacto, solo para la columna "Dif. óptimo".
  Se obtiene con `python optimo_exacto.py`.
- Si escribes mal un nombre o un valor fuera de rango, el programa se detiene e indica la línea.

Las opciones de terminal tienen prioridad sobre `config.ini`:

| Opción | Efecto |
|---|---|
| `--distancias haversine` | Usa distancias en línea recta |
| `--seed 7` | Cambia la semilla aleatoria (misma semilla ⇒ mismo resultado) |
| `--inicio Sevilla` | Muestra el recorrido empezando en otra capital |
| `--modo puro` o `--puro` | ACO y GA clásicos, sin búsqueda local 2-opt |
| `--config otro.ini` | Usa otro archivo de configuración |

## Qué hace el programa, paso a paso

1. **Carga los datos**: 47 ciudades y la matriz `D[i][j]` en km (por carretera o Haversine).
2. **Calcula una referencia voraz** (vecino más cercano) como punto de comparación.
3. **ACO**: en cada iteración, las hormigas construyen rutas eligiendo la siguiente ciudad con
   probabilidad ∝ τ^α · (1/d)^β. La mejor ruta de la iteración se pule con 2-opt; la feromona se
   evapora y se refuerza en las aristas de las buenas rutas (con refuerzo extra para la mejor global).
4. **GA**: población de rutas aleatorias; selección por torneo, cruce OX, mutación por inversión,
   2-opt a una fracción de los hijos (GA memético), elitismo y descarte de clones.
5. **Resultados**: ruta tramo a tramo, tabla resumen, `resultados.csv` y `resultados.png`.

La gráfica dibuja líneas rectas entre ciudades: muestra el **orden** de visita, no el trazado
de las carreteras.
