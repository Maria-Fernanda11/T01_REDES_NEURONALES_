# Datos y metodología de peajes

## Archivos de entrada
- `distancias_km.csv`: matriz de distancias de 47 capitales recibida del usuario; metadata ORS Matrix API v2, perfil `driving-car`.
- `tiempos_horas.csv`: matriz de tiempos ORS recibida, conservada para trazabilidad; este modelo utiliza distancias y una velocidad media asumida.
- `coordenadas.csv`: coordenadas de las capitales.
- `metadatos_ors.csv`: metadatos aportados para la consulta ORS.
- `peajes_sinteticos_eur.csv`: matriz simétrica de peajes sintéticos, utilizada igual para 2020 y 2026.

## Cómo se construyó la matriz sintética
No se dispone de peajes reales desglosados por cada ruta de cada pareja de capitales. Para no inventar tarifas específicas de trayectos, se construyó una aproximación de escenario:
1. Se supone que el 20% de la distancia de cada par corresponde a tramos de autopista de peaje.
2. Se toma como tarifa de referencia para vehículo ligero sin TAG 0,0927 €/km (tarifa publicada para 2025 en autopistas SEITT) y se aplica el aumento del 2% previsto para 2026: 0,094554 €/km.
3. Tarifa efectiva sintética = 20% × 0,094554 = **0.018911 €/km**.
4. Peaje sintético de cada pareja = distancia por carretera × tarifa efectiva.
5. La misma matriz se aplica a 2020 y 2026, tal como decidió el grupo, para aislar parcialmente otros cambios del escenario.
6. Se fija la salida a las **12:00** para todos los viajes. En esta aproximación no se modelan variaciones horarias de las tarifas; la hora de salida queda documentada como supuesto común.

## Limitaciones que deben aparecer en el informe
- **Esto NO es una matriz de peajes reales observados.** Es una matriz sintética construida a partir de un supuesto de proporción de kilómetros de peaje y una tarifa oficial de referencia SEITT. La tarifa SEITT no es la tarifa universal de todas las autopistas de España.
- El 20% es un supuesto de modelización, no una estadística oficial de la proporción de kilómetros de cada trayecto que usan autopistas de peaje.
- No identifica autopistas ni estaciones de entrada/salida concretas, ni calcula los peajes reales por carretera.
- Usar la misma matriz para 2020 y 2026 facilita la comparación, pero no refleja la evolución histórica de la red ni de las tarifas.
- No se recibió una matriz histórica de distancias de 2020; el código reutiliza la matriz ORS entregada (2026) en ambos escenarios, identificando el escenario 2020 como proxy.
