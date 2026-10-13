"""
tsp_bio.py — TSP cerrado de las 47 capitales de la España peninsular
resuelto con Colonia de Hormigas (ACO) y Algoritmo Genético (GA).

USO (un solo comando):
    python tsp_bio.py                       # usa los hiperparámetros de config.ini
    python tsp_bio.py --modo puro           # ACO y GA clásicos, sin búsqueda local (comparación)
    python tsp_bio.py --seed 7              # otra semilla (misma semilla ⇒ mismo resultado)
    python tsp_bio.py --config otro.ini     # otro archivo de configuración
    python tsp_bio.py --distancias haversine  # línea recta en vez de carretera

DISTANCIAS:
    - carretera (por defecto): distancias_km.csv. Es ASIMÉTRICA (ida ≠ vuelta), así
      que el programa tiene en cuenta el sentido en que se recorre cada tramo.
      Con 'simetrizar = si' en config.ini se usa la media de ida y vuelta.
    - haversine: línea recta calculada desde coordenadas.csv.

HIPERPARÁMETROS:
    Todos se editan en config.ini, sin tocar este archivo. Prioridad:
    opciones de terminal  >  config.ini  >  valores por defecto (PASO 4).

REQUISITOS:
    - Python 3.8+ y, en la misma carpeta: datos_tsp.py, config.ini,
      coordenadas.csv y distancias_km.csv.
    - Solo librería estándar.
    - Opcional: matplotlib → se guarda además resultados.png (mapas + convergencia).

SALIDAS:
    - Consola: progreso, ruta de cada algoritmo tramo a tramo y tabla resumen.
    - resultados.csv: orden de visita de cada algoritmo.
    - resultados.png: gráfica (solo si matplotlib está instalado).

ESTRUCTURA
    Paso 0. Utilidades comunes (longitud, vecino más cercano, 2-opt y Or-opt).
    Paso 1. Colonia de Hormigas (ACO).
    Paso 2. Algoritmo Genético (GA).
    Paso 3. Presentación de resultados.
    Paso 4. Programa principal.
"""
import argparse
import configparser
import csv
import os
import random
import sys
import time

try:    # ejecutado como parte del paquete (python -m punto_2.parte_1.tsp_bio, PyCharm…)
    from .datos_tsp import CAPITALES, CIUDADES, cargar_distancias, es_simetrica
except ImportError:    # ejecutado directamente (python tsp_bio.py)
    from datos_tsp import CAPITALES, CIUDADES, cargar_distancias, es_simetrica

# Matriz de distancias activa (km). Se asigna en main() según config.ini.
# D[i][j] = distancia DE i HACIA j. Con datos por carretera puede ser
# D[i][j] != D[j][i] (matriz asimétrica), así que el SENTIDO del recorrido importa.
D = cargar_distancias("haversine")
SIMETRICA = True

N = len(CIUDADES)  # 47 nodos


# ═════════════════════════════════════════════════════════════════════════════
# PASO 0. UTILIDADES COMUNES
# ═════════════════════════════════════════════════════════════════════════════
def longitud(ruta):
    """Longitud total (km) del ciclo cerrado.
    Con i = 0, ruta[i-1] es ruta[-1]: así se suma el regreso a la ciudad inicial."""
    return sum(D[ruta[i - 1]][ruta[i]] for i in range(len(ruta)))


def vecino_mas_cercano(inicio=0):
    """Heurística voraz: ir siempre a la ciudad no visitada más cercana.
    Sirve como referencia y para escalar la feromona inicial del ACO."""
    ruta, libres = [inicio], set(range(N)) - {inicio}
    while libres:
        sig = min(libres, key=lambda j: D[ruta[-1]][j])
        ruta.append(sig)
        libres.remove(sig)
    return ruta


def _sumas_acumuladas(ruta):
    """adelante[k] = km de ruta[0]→…→ruta[k];  atras[k] = ese mismo trozo recorrido al revés."""
    adelante, atras = [0.0] * N, [0.0] * N
    for k in range(1, N):
        adelante[k] = adelante[k - 1] + D[ruta[k - 1]][ruta[k]]
        atras[k] = atras[k - 1] + D[ruta[k]][ruta[k - 1]]
    return adelante, atras


def dos_opt(ruta):
    """Búsqueda local 2-opt: si cambiar dos tramos por otros dos acorta la ruta,
    se invierte el trozo intermedio. Se repite hasta que nada mejora.

        ... a → b → ... → c → d ...   ⇒   ... a → c → ... → b → d ...

    Con distancias ASIMÉTRICAS, el trozo b..c pasa a recorrerse AL REVÉS y su
    longitud cambia (ida ≠ vuelta). Por eso la ganancia incluye
    (coste del trozo al revés) − (coste del trozo hacia delante), que se obtiene
    al instante con sumas acumuladas en ambos sentidos."""
    ruta = ruta[:]
    adelante, atras = _sumas_acumuladas(ruta)
    mejora = True
    while mejora:
        mejora = False
        for i in range(N - 1):
            for j in range(i + 2, N if i > 0 else N - 1):  # tramos no adyacentes
                a, b = ruta[i], ruta[i + 1]
                c, d = ruta[j], ruta[(j + 1) % N]
                cambio_interior = (atras[j] - atras[i + 1]) - (adelante[j] - adelante[i + 1])
                if D[a][c] + D[b][d] - D[a][b] - D[c][d] + cambio_interior < -1e-9:
                    ruta[i + 1:j + 1] = reversed(ruta[i + 1:j + 1])
                    adelante, atras = _sumas_acumuladas(ruta)   # la ruta cambió
                    mejora = True
    return ruta


def or_opt(ruta):
    """Búsqueda local Or-opt: saca un trozo de 1, 2 o 3 ciudades consecutivas y lo
    reinserta en otro punto de la ruta SIN invertirlo.

        ... p → [s1 … sL] → q ... x → y ...   ⇒   ... p → q ... x → [s1 … sL] → y ...

    Como el trozo conserva su sentido, es la mejora natural cuando ida ≠ vuelta
    (2-opt, en cambio, obliga a recorrer un trozo al revés)."""
    ruta = ruta[:]
    mejora = True
    while mejora:
        mejora = False
        for L in (1, 2, 3):
            for i in range(N):
                trozo = [ruta[(i + t) % N] for t in range(L)]
                p, q = ruta[i - 1], ruta[(i + L) % N]
                s1, sL = trozo[0], trozo[-1]
                ahorro = D[p][s1] + D[sL][q] - D[p][q]          # lo que se ahorra al sacarlo
                resto = [c for c in ruta if c not in trozo]     # ruta sin el trozo (p → q)
                mejor_k, mejor_coste = None, ahorro - 1e-9
                for k in range(len(resto)):
                    x, y = resto[k], resto[(k + 1) % len(resto)]
                    if x == p:                                  # posición original
                        continue
                    coste = D[x][s1] + D[sL][y] - D[x][y]       # lo que cuesta meterlo entre x e y
                    if coste < mejor_coste:
                        mejor_k, mejor_coste = k, coste
                if mejor_k is not None:
                    ruta = resto[:mejor_k + 1] + trozo + resto[mejor_k + 1:]
                    mejora = True
    return ruta


def mejora_local(ruta):
    """Alterna 2-opt y Or-opt hasta que ninguno de los dos mejora la ruta."""
    L = longitud(ruta)
    while True:
        ruta = or_opt(dos_opt(ruta))
        nueva = longitud(ruta)
        if nueva > L - 1e-9:
            return ruta
        L = nueva


def rotar(ruta, inicio):
    """Reordena el ciclo para que empiece en 'inicio' (la longitud no cambia)."""
    k = ruta.index(inicio)
    return ruta[k:] + ruta[:k]


# ═════════════════════════════════════════════════════════════════════════════
# PASO 1. COLONIA DE HORMIGAS (ACO) — Ant System elitista (+ búsqueda local opcional)
# ═════════════════════════════════════════════════════════════════════════════
def aco(rng, n_hormigas=20, iteraciones=200, alpha=1.0, beta=3.0, rho=0.1,
        elitismo=5.0, busqueda_local=True, log_cada=50):
    """
    1.1 Feromona inicial τ0 = m / L_nn en todas las aristas
        (m = nº de hormigas, L_nn = longitud del vecino más cercano).
    1.2 Cada hormiga construye una ruta: desde la ciudad i elige la siguiente j
        (no visitada) con probabilidad ∝ τ_ij^α · η_ij^β, con η_ij = 1/d_ij.
    1.3 (Opcional) La mejor hormiga de la iteración se mejora con 2-opt + Or-opt.
    1.4 Evaporación: τ ← (1 − ρ)·τ.
    1.5 Depósito: cada ruta suma 1/L en sus aristas; la mejor ruta global
        suma 'elitismo'/L adicional (refuerzo elitista).
    Devuelve (mejor_ruta, mejor_longitud, historial, iteración_del_mejor).
    """
    # 1.1 Inicialización
    eta_b = [[0.0 if i == j else (1.0 / D[i][j]) ** beta for j in range(N)]
             for i in range(N)]  # η^β no cambia: se calcula una sola vez
    tau0 = n_hormigas / longitud(vecino_mas_cercano())
    tau = [[tau0] * N for _ in range(N)]

    mejor_ruta, mejor_L, it_mejor, historial = None, float("inf"), 0, []

    for it in range(1, iteraciones + 1):
        # Atractivo de cada arista en esta iteración: τ^α · η^β
        peso = [[(tau[i][j] ** alpha) * eta_b[i][j] for j in range(N)] for i in range(N)]

        # 1.2 Construcción de soluciones
        rutas = []
        for _ in range(n_hormigas):
            actual = rng.randrange(N)                 # ciudad de salida aleatoria
            ruta, libres = [actual], list(range(N))
            libres.remove(actual)
            while libres:
                pesos = [peso[actual][j] for j in libres]
                actual = rng.choices(libres, weights=pesos)[0]  # ruleta proporcional
                libres.remove(actual)
                ruta.append(actual)
            rutas.append((ruta, longitud(ruta)))

        # 1.3 Búsqueda local sobre la mejor hormiga de la iteración
        ruta_it, L_it = min(rutas, key=lambda x: x[1])
        if busqueda_local:
            ruta_it = mejora_local(ruta_it)
            L_it = longitud(ruta_it)
            rutas.append((ruta_it, L_it))             # la versión mejorada también deposita

        if L_it < mejor_L - 1e-9:
            mejor_ruta, mejor_L, it_mejor = ruta_it, L_it, it

        # 1.4 Evaporación
        for fila in tau:
            for j in range(N):
                fila[j] *= (1.0 - rho)

        # 1.5 Depósito: 1/L por cada ruta y e/L extra para la mejor global.
        # Con distancias asimétricas se refuerza solo el sentido recorrido (a → b);
        # con simétricas, ambos sentidos (a → b y b → a son el mismo tramo).
        depositos = [(ruta, 1.0 / L) for ruta, L in rutas]
        if elitismo > 0:
            depositos.append((mejor_ruta, elitismo / mejor_L))
        for ruta, dep in depositos:
            for k in range(N):
                a, b = ruta[k - 1], ruta[k]
                tau[a][b] += dep
                if SIMETRICA:
                    tau[b][a] += dep

        historial.append(mejor_L)
        if log_cada and it % log_cada == 0:
            print(f"   ACO  iteración  {it:>5}/{iteraciones}   mejor = {mejor_L:8.1f} km")

    return mejor_ruta, mejor_L, historial, it_mejor


# ═════════════════════════════════════════════════════════════════════════════
# PASO 2. ALGORITMO GENÉTICO (GA) — (+ búsqueda local opcional = GA memético)
# ═════════════════════════════════════════════════════════════════════════════
def cruce_ox(p1, p2, rng):
    """Order Crossover (OX): copia un tramo de p1 y completa con las ciudades
    restantes en el orden en que aparecen en p2 → nunca repite ciudades.

        p1 = [A B |C D E| F G]       hijo = [_ _ C D E _ _]
        p2 = [E G  B A F  D C]  →    hijo = [A F C D E G B]
    (p2 leído desde después del tramo: D C E G B A F → sin C D E: G B A F,
     colocadas en los huecos desde después del tramo: posiciones 6, 7, 1, 2)
    """
    i, j = sorted(rng.sample(range(N), 2))
    hijo = [None] * N
    hijo[i:j + 1] = p1[i:j + 1]
    usados = set(hijo[i:j + 1])
    resto = [c for c in p2[j + 1:] + p2[:j + 1] if c not in usados]
    for pos, c in zip(list(range(j + 1, N)) + list(range(i)), resto):
        hijo[pos] = c
    return hijo


def mutacion_inversion(ruta, rng):
    """Invierte un tramo aleatorio (un movimiento 2-opt al azar)."""
    i, j = sorted(rng.sample(range(N), 2))
    ruta[i:j + 1] = reversed(ruta[i:j + 1])


def torneo(poblacion, costes, k, rng):
    """Selección por torneo: de k individuos al azar gana el de menor longitud."""
    elegidos = rng.sample(range(len(poblacion)), k)
    return poblacion[min(elegidos, key=costes.__getitem__)]


def ga(rng, tam_poblacion=150, generaciones=500, p_cruce=0.9, p_mutacion=0.3,
       p_busqueda_local=0.05, n_elite=2, k_torneo=3, log_cada=100):
    """
    2.1 Población inicial: permutaciones aleatorias de las 47 ciudades.
    2.2 Evaluación: coste = longitud de la ruta (menor es mejor).
    2.3 Elitismo: las n_elite mejores pasan intactas.
    2.4 Selección de dos padres por torneo.
    2.5 Cruce OX con probabilidad p_cruce (si no, el hijo es copia de p1).
    2.6 Mutación por inversión con probabilidad p_mutacion.
    2.7 (Opcional) 2-opt + Or-opt al hijo con probabilidad p_busqueda_local (GA memético).
    2.8 Se descartan hijos repetidos para conservar la diversidad
        (evita la convergencia prematura: toda la población igual).
    Devuelve (mejor_ruta, mejor_longitud, historial, generación_del_mejor).
    """
    # 2.1 Población inicial
    poblacion = [rng.sample(range(N), N) for _ in range(tam_poblacion)]
    mejor_ruta, mejor_L, g_mejor, historial = None, float("inf"), 0, []

    for g in range(1, generaciones + 1):
        # 2.2 Evaluación
        costes = [longitud(r) for r in poblacion]
        orden = sorted(range(tam_poblacion), key=costes.__getitem__)
        if costes[orden[0]] < mejor_L - 1e-9:
            mejor_ruta, mejor_L, g_mejor = poblacion[orden[0]][:], costes[orden[0]], g

        # 2.3 Elitismo
        nueva = [poblacion[i][:] for i in orden[:n_elite]]
        vistos = {round(costes[i], 6) for i in orden[:n_elite]}  # huellas (longitudes) ya presentes

        # 2.4 – 2.8 Reproducción
        while len(nueva) < tam_poblacion:
            p1 = torneo(poblacion, costes, k_torneo, rng)
            p2 = torneo(poblacion, costes, k_torneo, rng)
            hijo = cruce_ox(p1, p2, rng) if rng.random() < p_cruce else p1[:]
            if rng.random() < p_mutacion:
                mutacion_inversion(hijo, rng)
            if rng.random() < p_busqueda_local:
                hijo = mejora_local(hijo)
            huella = round(longitud(hijo), 6)
            if huella in vistos:          # clon de alguien ya incluido → se descarta
                continue
            vistos.add(huella)
            nueva.append(hijo)
        poblacion = nueva

        historial.append(mejor_L)
        if log_cada and g % log_cada == 0:
            print(f"   GA   generación {g:>5}/{generaciones}   mejor = {mejor_L:8.1f} km")

    return mejor_ruta, mejor_L, historial, g_mejor


# ═════════════════════════════════════════════════════════════════════════════
# PASO 3. PRESENTACIÓN DE RESULTADOS
# ═════════════════════════════════════════════════════════════════════════════
def imprimir_ruta(titulo, ruta):
    """Recorrido tramo a tramo con distancia parcial y acumulada."""
    print(f"\n{titulo}")
    print(f"   {'#':>2}  {'Desde':<22} {'Hasta':<22} {'Tramo':>8} {'Acum.':>9}")
    acum = 0.0
    for k in range(N):
        a, b = ruta[k], ruta[(k + 1) % N]       # el último tramo regresa al inicio
        acum += D[a][b]
        print(f"   {k + 1:>2}  {CIUDADES[a]:<22} {CIUDADES[b]:<22} {D[a][b]:8.1f} {acum:9.1f}")


def guardar_csv(resultados, archivo="resultados.csv"):
    with open(archivo, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["algoritmo", "orden", "id", "ciudad", "longitud_total_km"])
        for nombre, ruta, L in resultados:
            for k, c in enumerate(ruta + [ruta[0]]):  # se repite el inicio: ciclo cerrado
                w.writerow([nombre, k, c, CIUDADES[c], f"{L:.2f}"])


def graficar(resultados, historiales, optimo=None, archivo="resultados.png"):
    """Mapa de cada ruta + curva de convergencia (requiere matplotlib).
    'optimo' (km) es opcional: si se conoce, se dibuja como línea de referencia."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # sin ventana: funciona también en servidores
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"(matplotlib no está instalado: se omite {archivo} → pip install matplotlib)")
        return

    colores = {"ACO": "#2a78d6", "GA": "#eb6834"}
    lon = [c[2] for c in CAPITALES]
    lat = [c[1] for c in CAPITALES]
    fig, ejes = plt.subplots(1, 3, figsize=(19, 6.5))

    for ax, (nombre, ruta, L) in zip(ejes[:2], resultados):
        ciclo = ruta + [ruta[0]]
        ax.plot([lon[c] for c in ciclo], [lat[c] for c in ciclo], "-",
                color=colores[nombre], lw=2, zorder=1)
        if not SIMETRICA:  # con ida ≠ vuelta el sentido importa: flecha en cada tramo
            for a, b in zip(ciclo, ciclo[1:]):
                xm, ym = (lon[a] + lon[b]) / 2, (lat[a] + lat[b]) / 2
                ax.annotate("", xy=(xm + (lon[b] - lon[a]) * 0.05, ym + (lat[b] - lat[a]) * 0.05),
                            xytext=(xm, ym), zorder=2,
                            arrowprops=dict(arrowstyle="-|>", color=colores[nombre], lw=0,
                                            mutation_scale=11))
        ax.scatter(lon, lat, s=36, color="#333333", edgecolor="white", linewidth=1.5, zorder=2)
        ax.scatter([lon[ruta[0]]], [lat[ruta[0]]], s=160, marker="*", color="#111111",
                   zorder=3, label=f"Salida: {CIUDADES[ruta[0]]}")
        for i, nom in enumerate(CIUDADES):
            ax.annotate(nom, (lon[i], lat[i]), fontsize=7, color="#444444",
                        xytext=(3, 3), textcoords="offset points")
        ax.set_title(f"{nombre}: {L:,.1f} km", fontsize=12)
        ax.set_aspect(1 / 0.76)  # corrige la deformación lon/lat a ~40° N (≈ 1/cos 40°)
        ax.set_xlabel("Longitud")
        ax.set_ylabel("Latitud")
        ax.legend(loc="lower right", frameon=False, fontsize=8)
        ax.grid(color="#e6e6e6", lw=0.6)

    ax = ejes[2]
    for nombre, hist in historiales.items():
        ax.plot(range(1, len(hist) + 1), hist, color=colores[nombre], lw=2, label=nombre)
    # Zoom cerca del mejor valor: la población aleatoria inicial del GA (~16 000 km)
    # aplastaría la curva y ocultaría la parte interesante
    base = optimo if optimo else min(L for _, _, L in resultados)
    if optimo:
        ax.axhline(optimo, color="#888888", lw=1, ls="--",
                   label=f"Óptimo exacto ({optimo:,.1f} km)")
    ax.set_ylim(base * 0.99, base * 1.12)
    ax.set_title("Convergencia: mejor longitud encontrada", fontsize=12)
    ax.set_xlabel("Iteración (ACO) / generación (GA)")
    ax.set_ylabel("km")
    ax.legend(frameon=False)
    ax.grid(color="#e6e6e6", lw=0.6)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)

    fig.tight_layout()
    fig.savefig(archivo, dpi=130)
    print(f"Gráfica guardada en {archivo}")


# ═════════════════════════════════════════════════════════════════════════════
# PASO 4. PROGRAMA PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════
# Valores por defecto: se usan si config.ini no existe o le falta alguna línea.
# El TIPO de cada valor (int, float, bool, str) sirve también para validar el archivo.
POR_DEFECTO = {
    "general": {
        "semilla": 42,
        "inicio": "Madrid",
        "modo": "hibrido",
        "distancias": "carretera",
        "simetrizar": False,
        # Óptimos exactos conocidos de cada matriz (programación lineal entera, DFJ).
        # Solo miden la diferencia con el óptimo; no intervienen en la búsqueda.
        # None = desconocido (se calcula con optimo_exacto.py y se escribe en config.ini).
        "optimo_carretera_km": None,
        "optimo_carretera_simetrizada_km": None,
        "optimo_haversine_km": None,
        "lineas_progreso": 6,
        "archivo_csv": "resultados.csv",
        "archivo_png": "resultados.png",
    },
    "aco": {"n_hormigas": 20, "iteraciones": 300, "alpha": 1.0, "beta": 5.0,
            "rho": 0.1, "elitismo": 5.0, "busqueda_local": True},
    "ga": {"tam_poblacion": 150, "generaciones": 200, "p_cruce": 0.9, "p_mutacion": 0.3,
           "p_busqueda_local": 0.05, "n_elite": 2, "k_torneo": 3},
}
VERDADERO = {"si", "sí", "true", "yes", "1"}
FALSO = {"no", "false", "0"}


def convertir(texto, ejemplo, donde):
    """Convierte el texto de config.ini al tipo del valor por defecto 'ejemplo'."""
    t = texto.strip()
    try:
        if isinstance(ejemplo, bool):           # bool antes que int: bool es subclase de int
            if t.lower() in VERDADERO | FALSO:
                return t.lower() in VERDADERO
            raise ValueError
        if isinstance(ejemplo, int):
            return int(t)
        if isinstance(ejemplo, float):
            return float(t.replace(",", "."))   # tolera la coma decimal
        return t
    except ValueError:
        tipo = {bool: "si/no", int: "entero", float: "número"}[type(ejemplo)]
        sys.exit(f"Error en {donde} = '{t}': se esperaba {tipo}.")


def cargar_config(ruta):
    """Lee config.ini y devuelve la configuración completa (con defaults)."""
    cfg = {sec: dict(vals) for sec, vals in POR_DEFECTO.items()}

    # Una ruta relativa se busca primero en la carpeta desde la que se ejecuta y,
    # si no está ahí, en la carpeta de este script. Así funciona aunque se lance
    # como "python carpeta/tsp_bio.py" o con el botón "Run" de un editor.
    if not os.path.isabs(ruta) and not os.path.exists(ruta):
        junto_al_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta)
        if os.path.exists(junto_al_script):
            ruta = junto_al_script
    if not os.path.exists(ruta):
        print("!" * 74)
        print(f"AVISO: no se encontró {ruta}. Se usan los valores por defecto.")
        print("!" * 74)
        return cfg

    ini = configparser.ConfigParser(inline_comment_prefixes=(";", "#"),
                                    empty_lines_in_values=False)
    ini.read(ruta, encoding="utf-8-sig")  # -sig: tolera el BOM que añade el Bloc de notas
    print(f"Configuración leída de: {os.path.abspath(ruta)}")

    for seccion in ini.sections():
        if seccion not in cfg and seccion != "puro":
            sys.exit(f"Error en {ruta}: sección desconocida [{seccion}].")

    def aplicar(seccion, clave, texto, origen):
        if clave not in cfg[seccion]:            # detecta erratas: 'n_hormiga', 'betta'...
            sys.exit(f"Error en {ruta} → {origen}: parámetro desconocido '{clave}'. "
                     f"Válidos en [{seccion}]: {', '.join(cfg[seccion])}")
        ejemplo = POR_DEFECTO[seccion][clave]
        if clave.startswith("optimo_"):           # número o "ninguno"
            if texto.strip().lower() in ("ninguno", "none", ""):
                cfg[seccion][clave] = None
                return
            ejemplo = 0.0
        cfg[seccion][clave] = convertir(texto, ejemplo, f"{ruta} → {origen}")

    for seccion in ("general", "aco", "ga"):
        if ini.has_section(seccion):
            for clave, texto in ini.items(seccion):
                aplicar(seccion, clave, texto, f"[{seccion}] {clave}")

    # Se guardan las sustituciones de [puro]; se aplican después si el modo es "puro"
    cfg["_puro"] = dict(ini.items("puro")) if ini.has_section("puro") else {}
    cfg["_aplicar"] = aplicar
    return cfg


def validar_config(cfg):
    """Comprueba rangos para dar un mensaje claro antes de ejecutar nada."""
    a, g, gen = cfg["aco"], cfg["ga"], cfg["general"]
    errores = []
    if gen["modo"] not in ("hibrido", "puro"):
        errores.append("[general] modo debe ser 'hibrido' o 'puro'")
    if gen["distancias"] not in ("carretera", "haversine"):
        errores.append("[general] distancias debe ser 'carretera' o 'haversine'")
    if gen["inicio"] not in CIUDADES:
        errores.append(f"[general] inicio: ciudad desconocida '{gen['inicio']}'")
    if a["n_hormigas"] < 1 or a["iteraciones"] < 1:
        errores.append("[aco] n_hormigas e iteraciones deben ser ≥ 1")
    if not 0 < a["rho"] <= 1:
        errores.append("[aco] rho debe estar en (0, 1]")
    if a["alpha"] < 0 or a["beta"] < 0 or a["elitismo"] < 0:
        errores.append("[aco] alpha, beta y elitismo deben ser ≥ 0")
    for p in ("p_cruce", "p_mutacion", "p_busqueda_local"):
        if not 0 <= g[p] <= 1:
            errores.append(f"[ga] {p} debe estar entre 0 y 1")
    if g["tam_poblacion"] < 2 or g["generaciones"] < 1:
        errores.append("[ga] tam_poblacion debe ser ≥ 2 y generaciones ≥ 1")
    if not 0 <= g["n_elite"] < g["tam_poblacion"]:
        errores.append("[ga] n_elite debe estar entre 0 y tam_poblacion − 1")
    if not 1 <= g["k_torneo"] <= g["tam_poblacion"]:
        errores.append("[ga] k_torneo debe estar entre 1 y tam_poblacion")
    if errores:
        sys.exit("Configuración no válida:\n  - " + "\n  - ".join(errores))


def main():
    global D, SIMETRICA
    ap = argparse.ArgumentParser(description="TSP 47 capitales: ACO vs GA")
    ap.add_argument("--config", default="config.ini", help="archivo de hiperparámetros")
    ap.add_argument("--seed", type=int, help="semilla (prioridad sobre config.ini)")
    ap.add_argument("--inicio", help="ciudad de salida para mostrar la ruta")
    ap.add_argument("--modo", choices=["hibrido", "puro"], help="hibrido (con búsqueda local) o puro")
    ap.add_argument("--puro", action="store_true", help="atajo de --modo puro")
    ap.add_argument("--distancias", choices=["carretera", "haversine"],
                    help="fuente de distancias (prioridad sobre config.ini)")
    args = ap.parse_args()

    # 4.1 Configuración: defaults → config.ini → opciones de terminal
    cfg = cargar_config(args.config)
    gen = cfg["general"]
    if args.seed is not None:
        gen["semilla"] = args.seed
    if args.inicio:
        gen["inicio"] = args.inicio
    if args.modo or args.puro:
        gen["modo"] = "puro" if args.puro else args.modo
    if args.distancias:
        gen["distancias"] = args.distancias
    if gen["modo"] == "puro":                     # sustituciones de la sección [puro]
        for clave, texto in cfg.get("_puro", {}).items():
            if "." not in clave or clave.split(".")[0] not in ("aco", "ga"):
                sys.exit(f"Error en [puro] {clave}: usa el formato aco.parametro o ga.parametro")
            sec, par = clave.split(".", 1)
            cfg["_aplicar"](sec, par, texto, f"[puro] {clave}")
    validar_config(cfg)

    p_aco, p_ga = dict(cfg["aco"]), dict(cfg["ga"])
    lineas = gen["lineas_progreso"]
    p_aco["log_cada"] = max(1, p_aco["iteraciones"] // lineas) if lineas > 0 else 0
    p_ga["log_cada"] = max(1, p_ga["generaciones"] // lineas) if lineas > 0 else 0
    # Matriz de distancias: todas las funciones (longitud, búsqueda local, ACO, GA) usan D
    try:
        D = cargar_distancias(gen["distancias"], sim=gen["simetrizar"])
    except (FileNotFoundError, ValueError, AssertionError) as e:
        sys.exit(f"Error al cargar las distancias: {e}")
    SIMETRICA = es_simetrica(D)
    variante = gen["distancias"] + ("_simetrizada" if gen["distancias"] == "carretera"
                                    and gen["simetrizar"] else "")
    optimo = gen[f"optimo_{variante}_km"]
    inicio = CIUDADES.index(gen["inicio"])
    semilla = gen["semilla"]

    # 4.2 Cabecera con la configuración efectiva (para que el experimento quede documentado)
    print("=" * 74)
    print(f" TSP cerrado · {N} capitales · distancias por {gen['distancias']} · "
          f"modo {gen['modo']} · semilla {semilla}")
    print("=" * 74)
    print("Matriz: " + ("simétrica (ida = vuelta)" if SIMETRICA
                        else "ASIMÉTRICA (ida ≠ vuelta: el sentido del recorrido importa)"))
    print("ACO: " + ", ".join(f"{k}={v}" for k, v in cfg["aco"].items()))
    print("GA : " + ", ".join(f"{k}={v}" for k, v in cfg["ga"].items()))
    L_nn = longitud(vecino_mas_cercano(inicio))
    print(f"\nReferencia voraz (vecino más cercano desde {gen['inicio']}): {L_nn:.1f} km")
    if optimo:
        print(f"Óptimo exacto de referencia:                           {optimo:.1f} km")

    # 4.3 Ejecución. Cada algoritmo usa su propio generador con la misma semilla → reproducible
    print(f"\n[1/2] Colonia de hormigas: {p_aco['n_hormigas']} hormigas, "
          f"{p_aco['iteraciones']} iteraciones")
    t = time.perf_counter()
    r_aco, L_aco, h_aco, k_aco = aco(random.Random(semilla), **p_aco)
    t_aco = time.perf_counter() - t

    print(f"\n[2/2] Algoritmo genético: población {p_ga['tam_poblacion']}, "
          f"{p_ga['generaciones']} generaciones")
    t = time.perf_counter()
    r_ga, L_ga, h_ga, k_ga = ga(random.Random(semilla), **p_ga)
    t_ga = time.perf_counter() - t

    filas = [("ACO", rotar(r_aco, inicio), L_aco, k_aco, t_aco),
             ("GA", rotar(r_ga, inicio), L_ga, k_ga, t_ga)]

    for nombre, ruta, L, _, _ in filas:
        imprimir_ruta(f"Ruta {nombre} — {L:.1f} km", ruta)

    # Tabla resumen
    print("\n" + "=" * 74)
    print(" RESUMEN")
    print("=" * 74)
    print(f"   {'Algoritmo':<10} {'Longitud':>11} {'Dif. óptimo':>12} {'Hallada en':>12} {'Tiempo':>8}")
    for nombre, _, L, k, seg in filas:
        dif = 100 * (L - optimo) / optimo if optimo else None
        dif = 0.0 if dif is not None and abs(dif) < 0.005 else dif   # evita "-0.00 %"
        gap = f"{dif:+10.2f} %" if dif is not None else f"{'—':>12}"
        hallada = ("iter. " if nombre == "ACO" else "gen. ") + str(k)
        print(f"   {nombre:<10} {L:8.1f} km {gap} {hallada:>12} {seg:6.1f} s")

    mejor = min(filas, key=lambda f: f[2])
    print(f"\n   Mejor recorrido ({mejor[0]}, {mejor[2]:.1f} km, "
          f"{100 * (L_nn - mejor[2]) / L_nn:.1f} % más corto que el vecino más cercano):")
    print("   " + " → ".join(CIUDADES[c] for c in mejor[1] + [mejor[1][0]]))

    # 4.4 Archivos de salida: las rutas relativas se guardan junto al script,
    # se ejecute desde la terminal o desde el botón "Run" de un editor
    carpeta = os.path.dirname(os.path.abspath(__file__))
    salida_csv = os.path.join(carpeta, gen["archivo_csv"])
    salida_png = os.path.join(carpeta, gen["archivo_png"])
    guardar_csv([(f[0], f[1], f[2]) for f in filas], salida_csv)
    print(f"\nRutas guardadas en {salida_csv}")
    graficar([(f[0], f[1], f[2]) for f in filas], {"ACO": h_aco, "GA": h_ga},
             optimo, salida_png)


if __name__ == "__main__":
    main()
