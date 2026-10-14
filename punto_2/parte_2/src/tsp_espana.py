#!/usr/bin/env python3
"""TSP de las 47 capitales con costos: ACO y GA, escenarios 2016/2026 y GIF de rutas.

Ejecución:   python3 src/tsp_espana.py
Parámetros:  config.ini (junto a este README)  ·  opciones de terminal (--help)
Prioridad:   terminal  >  config.ini  >  valores por defecto
"""

from pathlib import Path
import argparse
import configparser
import json
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter


ROOT = Path(__file__).resolve().parents[1]     # .../punto_2/parte_2
DATA = ROOT / "data"
RESULTS = ROOT / "results"
SCENARIOS = ("2016", "2026")


# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN (config.ini)
# ═════════════════════════════════════════════════════════════════════════════
# Valores por defecto: si una línea falta en config.ini se usa el de aquí.
# El tipo del valor por defecto (int, float, bool, str) indica cómo leer el texto.
POR_DEFECTO = {
    "general": {
        "escenario": "both",       # 2016 | 2026 | both
        "algoritmo": "both",       # aco | ga | both
        "semilla": 20261008,
        "inicio": "Madrid",        # solo cambia desde dónde se MUESTRA el ciclo
        "generar_gif": True,
    },
    "costos": {
        "valor_hora_2016": 19.77,          # €/h
        "valor_hora_2026": 26.18,
        "precio_combustible_2016": 1.17,   # €/L
        "precio_combustible_2026": 1.799,
        "velocidad_kmh": 80.0,             # supuesto: velocidad constante
        "consumo_l_100km": 4.7,            # Toyota Corolla (ver data/parametros.json)
    },
    "aco": {
        "n_hormigas": 25,
        "iteraciones": 80,
        "alpha": 1.0,     # peso de la feromona
        "beta": 3.0,      # peso de la heurística 1/costo
        "rho": 0.5,       # evaporación
    },
    "ga": {
        "tam_poblacion": 60,
        "generaciones": 150,
        "p_mutacion": 0.2,
        "k_torneo": 3,
    },
}
VERDADERO, FALSO = {"si", "sí", "true", "1", "yes"}, {"no", "false", "0"}


def convertir(texto, ejemplo, donde):
    """Convierte el texto del .ini al tipo del valor por defecto."""
    t = texto.strip()
    try:
        if isinstance(ejemplo, bool):              # bool antes que int (bool es subclase de int)
            if t.lower() in VERDADERO | FALSO:
                return t.lower() in VERDADERO
            raise ValueError
        if isinstance(ejemplo, int):
            return int(t)
        if isinstance(ejemplo, float):
            return float(t.replace(",", "."))      # tolera la coma decimal
        return t
    except ValueError:
        tipo = {bool: "si/no", int: "entero", float: "número"}[type(ejemplo)]
        sys.exit(f"Error en {donde} = '{t}': se esperaba {tipo}.")


def cargar_config(ruta):
    """Lee config.ini sobre los valores por defecto. Avisa de erratas en los nombres."""
    cfg = {sec: dict(vals) for sec, vals in POR_DEFECTO.items()}
    ruta = Path(ruta)
    if not ruta.is_absolute() and not ruta.exists():
        ruta = ROOT / ruta                          # una ruta relativa se busca también en parte_2/
    if not ruta.exists():
        print(f"AVISO: no se encontró {ruta}. Se usan los valores por defecto.")
        return cfg

    ini = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
    ini.read(ruta, encoding="utf-8-sig")            # -sig: tolera el BOM del Bloc de notas
    print(f"Configuración leída de: {ruta}")
    for sec in ini.sections():
        if sec not in cfg:
            sys.exit(f"Error en {ruta}: sección desconocida [{sec}].")
        for clave, texto in ini.items(sec):
            if clave not in cfg[sec]:               # detecta erratas: 'betta', 'n_hormiga'...
                sys.exit(f"Error en {ruta} → [{sec}]: parámetro desconocido '{clave}'. "
                         f"Válidos: {', '.join(cfg[sec])}")
            cfg[sec][clave] = convertir(texto, POR_DEFECTO[sec][clave], f"[{sec}] {clave}")
    return cfg


def validar_config(cfg, ciudades):
    g, a, ga_, c = cfg["general"], cfg["aco"], cfg["ga"], cfg["costos"]
    err = []
    if g["escenario"] not in ("2016", "2026", "both"):
        err.append("[general] escenario debe ser 2016, 2026 o both")
    if g["algoritmo"] not in ("aco", "ga", "both"):
        err.append("[general] algoritmo debe ser aco, ga o both")
    if g["inicio"] not in ciudades:
        err.append(f"[general] inicio: ciudad desconocida '{g['inicio']}'")
    if a["n_hormigas"] < 1 or a["iteraciones"] < 1:
        err.append("[aco] n_hormigas e iteraciones deben ser ≥ 1")
    if not 0 < a["rho"] <= 1:
        err.append("[aco] rho debe estar en (0, 1]")
    if ga_["tam_poblacion"] < 2 or ga_["generaciones"] < 1:
        err.append("[ga] tam_poblacion ≥ 2 y generaciones ≥ 1")
    if not 0 <= ga_["p_mutacion"] <= 1:
        err.append("[ga] p_mutacion debe estar entre 0 y 1")
    if not 1 <= ga_["k_torneo"] <= ga_["tam_poblacion"]:
        err.append("[ga] k_torneo debe estar entre 1 y tam_poblacion")
    if c["velocidad_kmh"] <= 0:
        err.append("[costos] velocidad_kmh debe ser > 0")
    if err:
        sys.exit("Errores en la configuración:\n  - " + "\n  - ".join(err))


# ═════════════════════════════════════════════════════════════════════════════
# DATOS
# ═════════════════════════════════════════════════════════════════════════════
def read_matrix(path):
    """Lee una matriz CSV con columna inicial Capital y mismo orden en filas/columnas."""
    df = pd.read_csv(path)
    if "Capital" not in df.columns:
        raise ValueError(f"La matriz debe tener una columna llamada 'Capital': {path}")
    names = df["Capital"].astype(str).tolist()
    cols = list(df.columns[1:])
    if cols != names:
        raise ValueError(
            f"Filas/columnas desalineadas en {path}. "
            "Deben tener el mismo orden de capitales."
        )
    m = df.iloc[:, 1:].to_numpy(float)
    if m.shape != (len(names), len(names)) or not np.isfinite(m).all():
        raise ValueError(f"Matriz inválida: {path}")
    if (m < 0).any():
        raise ValueError(f"La matriz contiene distancias/costes negativos: {path}")
    np.fill_diagonal(m, 0)
    return names, m


def find_required_matrix(filename):
    """Lee exclusivamente el nombre de archivo indicado; no usa nombres alternativos."""
    path = DATA / filename
    if not path.is_file():
        raise FileNotFoundError(
            f"No se encontró el archivo obligatorio: {path}\n"
            "El programa solo admite los archivos de matriz definidos para 2016 y 2026."
        )
    return path


def tour_cost(tour, cost):
    return float(sum(cost[tour[i], tour[(i + 1) % len(tour)]] for i in range(len(tour))))


# ═════════════════════════════════════════════════════════════════════════════
# ALGORITMOS
# ═════════════════════════════════════════════════════════════════════════════
def aco(cost, ants=25, iterations=80, seed=20261008, alpha=1.0, beta=3.0, rho=0.5):
    """Ant System: p_ij ∝ tau_ij^alpha · (1/c_ij)^beta ;  tau ← (1-rho)·tau + Σ 1/C_k."""
    rng = np.random.default_rng(seed)
    n = len(cost)
    pos = cost[cost > 0]
    eps = max(1e-9, float(pos.min()) if pos.size else 1)
    eta = 1 / np.maximum(cost, eps)                 # heurística: tramos baratos atraen
    np.fill_diagonal(eta, 0)
    tau = np.ones((n, n))                           # feromona inicial
    best, bestv, hist = None, float("inf"), []
    for _ in range(iterations):
        tours = []
        for _a in range(ants):
            tour = [0]
            avail = set(range(1, n))
            while avail:
                i = tour[-1]
                js = np.array(sorted(avail))
                w = tau[i, js] ** alpha * eta[i, js] ** beta   # regla de transición
                if not np.isfinite(w).all() or w.sum() <= 0:
                    nxt = int(rng.choice(js))
                else:
                    nxt = int(rng.choice(js, p=w / w.sum()))
                tour.append(nxt)
                avail.remove(nxt)
            val = tour_cost(tour, cost)
            tours.append((tour, val))
            if val < bestv:
                best, bestv = tour[:], val
        tau *= (1 - rho)                            # evaporación
        for tour, val in tours:                     # depósito: más feromona a rutas baratas
            dep = 1 / max(val, 1e-9)
            for i in range(n):
                tau[tour[i], tour[(i + 1) % n]] += dep
        hist.append(bestv)
    return best, bestv, hist


def ga(cost, population=60, generations=150, mutation_rate=0.2, seed=20261008, k=3):
    """GA: torneo de tamaño k, cruce OX, mutación por inversión, élite de 1."""
    rng = np.random.default_rng(seed)
    n = len(cost)

    def new():
        a = np.arange(1, n)
        rng.shuffle(a)
        return [0] + a.tolist()

    pop = [new() for _ in range(population)]
    best, bestv, hist = None, float("inf"), []

    def tournament():                               # gana la ruta más barata de k al azar
        ids = rng.integers(0, len(pop), size=k)
        best_idx = min(ids, key=lambda idx: tour_cost(pop[int(idx)], cost))
        return pop[int(best_idx)][:]

    for _ in range(generations):
        vals = [tour_cost(t, cost) for t in pop]
        ix = int(np.argmin(vals))
        if vals[ix] < bestv:
            best, bestv = pop[ix][:], vals[ix]
        nxt = [best[:]]                             # elitismo: la mejor pasa intacta
        while len(nxt) < population:
            p1, p2 = tournament(), tournament()
            lo, hi = sorted(rng.choice(np.arange(1, n), size=2, replace=False))
            child = [None] * n                      # cruce OX
            child[0] = 0
            child[lo:hi + 1] = p1[lo:hi + 1]
            fill = [x for x in p2[1:] if x not in child]
            it = iter(fill)
            for j in range(1, n):
                if child[j] is None:
                    child[j] = next(it)
            if rng.random() < mutation_rate:        # mutación por inversión
                i, kk = sorted(rng.choice(np.arange(1, n), size=2, replace=False))
                child[i:kk + 1] = child[i:kk + 1][::-1]
            nxt.append(child)
        pop = nxt
        hist.append(bestv)
    return best, bestv, hist


# ═════════════════════════════════════════════════════════════════════════════
# PRESENTACIÓN DEL ORDEN DE LAS CIUDADES
# ═════════════════════════════════════════════════════════════════════════════
def rotar(tour, inicio):
    """Mismo ciclo, empezando en la ciudad 'inicio' (el costo no cambia)."""
    k = tour.index(inicio)
    return tour[k:] + tour[:k]


def tabla_ruta(tour, names, D, H, F, T, C):
    """Una fila por tramo: desde, hasta, km, horas y cada componente del costo."""
    filas, acum = [], 0.0
    n = len(tour)
    for k in range(n):
        a, b = tour[k], tour[(k + 1) % n]           # el último tramo regresa al inicio
        acum += C[a, b]
        filas.append({
            "orden": k + 1, "desde": names[a], "hasta": names[b],
            "km": D[a, b], "horas": H[a, b],
            "tiempo_eur": C[a, b] - F[a, b] - T[a, b],
            "combustible_eur": F[a, b], "peaje_eur": T[a, b],
            "costo_eur": C[a, b], "costo_acumulado_eur": acum,
        })
    return pd.DataFrame(filas)


def corto(nombre, w=24):
    """Recorta nombres largos solo para la pantalla (el CSV guarda el nombre completo)."""
    return nombre if len(nombre) <= w else nombre[:w - 1] + "…"


def imprimir_ruta(titulo, df):
    w = min(24, max(12, int(df["desde"].str.len().max())))
    print(f"\n{titulo}")
    print(f"   {'#':>2}  {'Desde':<{w}}  {'Hasta':<{w}} {'km':>7} {'horas':>6} "
          f"{'Tramo €':>8} {'Acum. €':>9}")
    for r in df.itertuples():
        print(f"   {r.orden:>2}  {corto(r.desde, w):<{w}}  {corto(r.hasta, w):<{w}} {r.km:7.1f} {r.horas:6.2f} "
              f"{r.costo_eur:8.2f} {r.costo_acumulado_eur:9.2f}")


def totales(df):
    return {
        "km": df["km"].sum(), "horas": df["horas"].sum(),
        "tiempo_eur": df["tiempo_eur"].sum(), "combustible_eur": df["combustible_eur"].sum(),
        "peaje_eur": df["peaje_eur"].sum(), "costo_total_eur": df["costo_eur"].sum(),
    }


def comparar(sc, res):
    """Tabla ACO vs GA de un escenario y cuál es mejor (menor costo total)."""
    print(f"\nCOMPARACIÓN — escenario {sc}")
    print(f"   {'Algoritmo':<10} {'Costo total €':>14} {'km':>9} {'horas':>7} "
          f"{'Tiempo €':>9} {'Combust. €':>11} {'Peajes €':>9}")
    for alg, t in res.items():
        print(f"   {alg:<10} {t['costo_total_eur']:14.2f} {t['km']:9.1f} {t['horas']:7.1f} "
              f"{t['tiempo_eur']:9.2f} {t['combustible_eur']:11.2f} {t['peaje_eur']:9.2f}")
    if len(res) == 2:
        (a1, t1), (a2, t2) = sorted(res.items(), key=lambda x: x[1]["costo_total_eur"])
        dif = t2["costo_total_eur"] - t1["costo_total_eur"]
        print(f"   → Mejor: {a1}. Cuesta {dif:.2f} € menos que {a2} "
              f"({100 * dif / t2['costo_total_eur']:.1f} % más barato) "
              f"y recorre {t2['km'] - t1['km']:.1f} km menos.")


# ═════════════════════════════════════════════════════════════════════════════
# GIF
# ═════════════════════════════════════════════════════════════════════════════
def save_route_gif(route_indices, names, coords_df, output_path, title):
    """Crea un GIF que dibuja progresivamente la ruta sobre las coordenadas geográficas."""
    required_cols = {"Capital", "Longitud", "Latitud"}
    if not required_cols.issubset(coords_df.columns):
        raise ValueError("coordenadas.csv debe tener las columnas Capital, Longitud y Latitud.")
    coords = coords_df.copy()
    coords["Capital"] = coords["Capital"].astype(str)
    coords = coords.set_index("Capital")
    missing = [names[i] for i in route_indices if names[i] not in coords.index]
    if missing:
        raise ValueError("Faltan coordenadas para estas capitales: " + ", ".join(missing))

    route_names = [names[i] for i in route_indices] + [names[route_indices[0]]]
    lon = np.array([float(coords.loc[x, "Longitud"]) for x in route_names])
    lat = np.array([float(coords.loc[x, "Latitud"]) for x in route_names])
    all_lon = coords["Longitud"].astype(float).to_numpy()
    all_lat = coords["Latitud"].astype(float).to_numpy()

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.scatter(all_lon, all_lat, s=18, zorder=2)
    for city in coords.index:
        ax.annotate(
            city,
            (float(coords.loc[city, "Longitud"]), float(coords.loc[city, "Latitud"])),
            fontsize=5,
            xytext=(2, 2),
            textcoords="offset points",
        )
    line, = ax.plot([], [], linewidth=1.6, marker="o", markersize=2.5, zorder=3)
    progress = ax.text(
        0.02, 0.02, "", transform=ax.transAxes, fontsize=9,
        bbox=dict(facecolor="white", alpha=0.8, edgecolor="none")
    )
    ax.set_title(title)
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(alpha=0.2)
    ax.set_xlim(all_lon.min() - 0.6, all_lon.max() + 0.6)
    ax.set_ylim(all_lat.min() - 0.4, all_lat.max() + 0.4)
    fig.tight_layout()

    def update(frame):
        end = min(frame + 1, len(lon))
        line.set_data(lon[:end], lat[:end])
        if end > 1:
            progress.set_text(
                f"Tramo {min(frame, len(route_indices))}/{len(route_indices)}: "
                f"{route_names[end - 2]} → {route_names[end - 1]}"
            )
        else:
            progress.set_text(f"Inicio: {route_names[0]}")
        return line, progress

    anim = FuncAnimation(fig, update, frames=len(route_names), interval=220, blit=False, repeat=True)
    anim.save(output_path, writer=PillowWriter(fps=4))
    plt.close(fig)


# ═════════════════════════════════════════════════════════════════════════════
# PROGRAMA PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════
def main():
    # Las opciones de terminal valen None si no se escriben: así no pisan config.ini.
    p = argparse.ArgumentParser(description="TSP 47 capitales con costos (ACO y GA).")
    p.add_argument("--config", default=str(ROOT / "config.ini"),
                   help="archivo de parámetros (por defecto: parte_2/config.ini)")
    p.add_argument("--scenario", choices=["2016", "2026", "both"])
    p.add_argument("--algorithm", choices=["aco", "ga", "both"])
    p.add_argument("--seed", type=int)
    p.add_argument("--inicio", help="ciudad desde la que se muestra el recorrido")
    p.add_argument("--aco-ants", type=int)
    p.add_argument("--aco-iterations", type=int)
    p.add_argument("--ga-population", type=int)
    p.add_argument("--ga-generations", type=int)
    p.add_argument("--sin-gif", action="store_true", help="no generar los GIF (más rápido)")
    args = p.parse_args()

    cfg = cargar_config(args.config)
    for valor, sec, clave in [
        (args.scenario, "general", "escenario"), (args.algorithm, "general", "algoritmo"),
        (args.seed, "general", "semilla"), (args.inicio, "general", "inicio"),
        (args.aco_ants, "aco", "n_hormigas"), (args.aco_iterations, "aco", "iteraciones"),
        (args.ga_population, "ga", "tam_poblacion"), (args.ga_generations, "ga", "generaciones"),
    ]:
        if valor is not None:                       # la terminal tiene prioridad
            cfg[sec][clave] = valor
    if args.sin_gif:
        cfg["general"]["generar_gif"] = False

    gen, cst, pa, pg = cfg["general"], cfg["costos"], cfg["aco"], cfg["ga"]
    RESULTS.mkdir(parents=True, exist_ok=True)

    # Solo se admiten estas matrices exactas. No hay respaldo a nombres antiguos.
    distance_paths = {sc: find_required_matrix(f"distancias_km_{sc}.csv") for sc in SCENARIOS}
    toll_paths = {sc: find_required_matrix(f"peajes_sinteticos_eur_{sc}.csv") for sc in SCENARIOS}

    coords_path = DATA / "coordenadas.csv"
    if not coords_path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo obligatorio: {coords_path}")
    coords_df = pd.read_csv(coords_path)

    matrices = {}
    for sc in SCENARIOS:
        names, D = read_matrix(distance_paths[sc])
        toll_names, T = read_matrix(toll_paths[sc])
        if names != toll_names:
            raise ValueError(f"El orden de capitales difiere entre distancias y peajes del escenario {sc}.")
        matrices[sc] = (names, D, T)

    validar_config(cfg, matrices["2026"][0])
    print("=== TSP ESPAÑA: EJECUCIÓN ===")
    print(f"Capitales: {len(matrices['2026'][0])} | semilla: {gen['semilla']} | salida fijada: 12:00")
    print(f"ACO: {pa['n_hormigas']} hormigas, {pa['iteraciones']} iter., alpha={pa['alpha']}, "
          f"beta={pa['beta']}, rho={pa['rho']}")
    print(f"GA : población {pg['tam_poblacion']}, {pg['generaciones']} gen., "
          f"p_mutación={pg['p_mutacion']}, torneo k={pg['k_torneo']}")

    summaries = []
    scenarios = list(SCENARIOS) if gen["escenario"] == "both" else [gen["escenario"]]
    algos = ["aco", "ga"] if gen["algoritmo"] == "both" else [gen["algoritmo"]]

    for sc in scenarios:
        out = RESULTS / sc
        out.mkdir(parents=True, exist_ok=True)
        names, D, T = matrices[sc]

        # ── Matriz de costos: C = vh·tiempo + combustible + peaje ────────────
        vh = cst[f"valor_hora_{sc}"]
        speed = cst["velocidad_kmh"]
        fuelprice = cst[f"precio_combustible_{sc}"]
        cons = cst["consumo_l_100km"]
        time = D / speed                            # supuesto: velocidad constante
        fuel = D * (cons / 100) * fuelprice
        timecost = vh * time
        cost = timecost + fuel + T

        print(f"\n{'=' * 78}\nESCENARIO {sc}: valor hora {vh} €/h · combustible {fuelprice} €/L · "
              f"{cons} L/100 km · {speed} km/h\n{'=' * 78}")

        for fn, mat in [
            ("matriz_costos_eur.csv", cost),
            ("matriz_tiempos_estimados_h.csv", time),
            ("matriz_combustible_eur.csv", fuel),
            (f"matriz_peajes_sinteticos_eur_{sc}.csv", T),
        ]:
            pd.DataFrame(mat, index=names, columns=names).to_csv(out / fn, index_label="Capital")

        res_sc = {}
        for alg in algos:
            if alg == "aco":
                tour, val, hist = aco(cost, pa["n_hormigas"], pa["iteraciones"], gen["semilla"],
                                      pa["alpha"], pa["beta"], pa["rho"])
            else:
                tour, val, hist = ga(cost, pg["tam_poblacion"], pg["generaciones"],
                                     pg["p_mutacion"], gen["semilla"], pg["k_torneo"])

            # ── Orden de las ciudades, tramo a tramo, desde la ciudad de inicio ──
            tour = rotar(tour, names.index(gen["inicio"]))
            df_ruta = tabla_ruta(tour, names, D, time, fuel, T, cost)
            imprimir_ruta(f"RUTA {alg.upper()} — escenario {sc} — {val:.2f} €", df_ruta)
            df_ruta.round(3).to_csv(out / f"ruta_{alg}.csv", index=False)
            tot = totales(df_ruta)
            res_sc[alg.upper()] = tot

            pd.DataFrame(
                {"iteracion": range(1, len(hist) + 1), "mejor_costo_eur": hist}
            ).to_csv(out / f"convergencia_{alg}.csv", index=False)

            fig, ax = plt.subplots(figsize=(9, 4.5))
            ax.plot(range(1, len(hist) + 1), hist)
            ax.set_xlabel("Iteración/generación")
            ax.set_ylabel("Mejor costo (€)")
            ax.set_title(f"Convergencia {alg.upper()} — escenario {sc}")
            fig.tight_layout()
            fig.savefig(out / f"convergencia_{alg}.png", dpi=140)
            plt.close(fig)

            gif_path = out / f"mapa_ruta_{alg}.gif"
            if gen["generar_gif"]:
                save_route_gif(tour, names, coords_df, gif_path,
                               f"Ruta TSP — {alg.upper()} — escenario {sc}")
            summaries.append({
                "escenario": sc,
                "algoritmo": alg.upper(),
                "capitales": len(names),
                "semilla": gen["semilla"],
                "salida": "12:00",
                "valor_hora_eur": vh,
                "velocidad_media_kmh_sup": speed,
                "combustible_eur_l": fuelprice,
                "consumo_l_100km": cons,
                **{k: round(v, 3) for k, v in tot.items()},
                "orden_ciudades": " → ".join([names[i] for i in tour] + [names[tour[0]]]),
                "archivo_distancias": distance_paths[sc].name,
                "archivo_peajes": toll_paths[sc].name,
                "gif_ruta": str(gif_path.relative_to(ROOT)) if gen["generar_gif"] else "",
            })
        comparar(sc, res_sc)

    df = pd.DataFrame(summaries)
    df.to_csv(RESULTS / "resumen.csv", index=False)
    print(f"\n{'=' * 78}\nRESUMEN")
    print(df[["escenario", "algoritmo", "valor_hora_eur", "costo_total_eur", "km", "horas"]]
          .to_string(index=False))
    print("\nResultados:", RESULTS)
    print("  ruta_<alg>.csv  → orden de las ciudades tramo a tramo")
    print("  resumen.csv     → totales y orden completo de cada algoritmo")


if __name__ == "__main__":
    main()
