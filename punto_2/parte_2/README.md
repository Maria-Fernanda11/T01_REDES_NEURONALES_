Punto 2 — TSP de las 47 capitales con costos (ACO y GA)
Se busca el orden de visita de las 47 capitales de provincia de la España peninsular
que minimiza el costo total del viaje (no solo la distancia), con dos algoritmos:
colonia de hormigas (ACO) y algoritmo genético (GA), en dos escenarios: 2016 y 2026.
Cómo ejecutarlo
Desde la raíz del repositorio:
```bash
cd punto_2/parte_2
pip install -r requirements.txt
python3 src/tsp_espana.py                    # 2016 y 2026, ACO y GA (~1,5 min)
python3 src/tsp_espana.py --scenario 2026    # demo rápida (~45 s)
python3 src/tsp_espana.py --sin-gif           # sin GIF, más rápido
```
En Windows, usa `python` en lugar de `python3`.
Modelo de costo
Costo de ir de la capital i a la j:
```
costo_ij = valor_hora × tiempo_ij + combustible_ij + peaje_ij

tiempo_ij      = km_ij / 80                       (horas)
combustible_ij = km_ij × consumo/100 × precio      (€)
peaje_ij       = matriz de peajes sintéticos       (€)
```
Supuestos
Velocidad media constante de 80 km/h en todos los tramos.
Peajes sintéticos (no son tarifas reales por trayecto); ver `data/README_DATOS.md`.
Vehículo: Toyota Corolla (consumo y fuente en `data/parametros.json`).
Parámetros: `config.ini`
Todos los parámetros se cambian en `config.ini` (en esta carpeta), sin tocar el código:
Sección	Qué controla
`[general]`	escenario, algoritmo, semilla, ciudad de inicio, generar GIF
`[costos]`	valor de la hora y precio del combustible por año, velocidad, consumo
`[aco]`	hormigas, iteraciones, alpha, beta, rho
`[ga]`	población, generaciones, probabilidad de mutación, tamaño del torneo
Si se escribe mal un nombre (`betta` en lugar de `beta`), el programa avisa y se detiene.
`data/parametros.json` documenta la procedencia de los datos (vehículo, modelo de peajes).
Opciones de terminal
Tienen prioridad sobre `config.ini` (útiles para pruebas rápidas):
Opción	Valores
`--config`	otro archivo de parámetros
`--scenario`	`2016`, `2026`, `both`
`--algorithm`	`aco`, `ga`, `both`
`--seed`	entero
`--inicio`	ciudad desde la que se muestra el recorrido
`--aco-ants`, `--aco-iterations`	entero
`--ga-population`, `--ga-generations`	entero
`--sin-gif`	no genera los GIF (más rápido)
Ejemplo: `python3 src/tsp_espana.py --scenario 2016 --algorithm ga --seed 7 --sin-gif`
Resultados (`results/`)
Por cada escenario (`results/2016/`, `results/2026/`):
Archivo	Contenido
`ruta_aco.csv`, `ruta_ga.csv`	Orden de visita tramo a tramo: km, horas, tiempo €, combustible €, peaje €, costo acumulado
`convergencia_*.csv` / `.png`	Mejor costo por iteración
`mapa_ruta_*.gif`	Ruta sobre el mapa
`matriz_costos_eur.csv`	Matriz de costos usada
`matriz_tiempos_estimados_h.csv`, `matriz_combustible_eur.csv`, `matriz_peajes_sinteticos_eur_*.csv`	Componentes del costo
Y `results/resumen.csv` con los totales (costo, km, horas y cada componente) y el orden
completo de las ciudades de cada combinación escenario-algoritmo.
En la terminal se muestra además el recorrido de cada algoritmo y una comparación
ACO vs GA que indica cuál es mejor (menor costo total) y por cuánto.
Estructura
```
parte_2/
├── README.md
├── config.ini               ← parámetros (editar aquí)
├── requirements.txt
├── src/tsp_espana.py        ← programa principal
├── data/                    ← datos de entrada (ver data/README_DATOS.md)
├── results/                 ← se regenera al ejecutar
└── recoleccion_datos/       ← scripts y docker-compose usados para obtener
                               las matrices con un servidor ORS local
```
La semilla fija garantiza que dos ejecuciones con los mismos parámetros dan el mismo resultado.