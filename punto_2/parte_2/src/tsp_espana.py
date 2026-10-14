#!/usr/bin/env python3
"""TSP 47 capitales: ACO y GA, comparación de escenarios 2016/2026 y GIF de rutas."""

from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
SCENARIOS = ("2016", "2026")


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


def aco(cost, ants=25, iterations=80, seed=20261008):
    rng = np.random.default_rng(seed)
    n = len(cost)
    pos = cost[cost > 0]
    eps = max(1e-9, float(pos.min()) if pos.size else 1)
    eta = 1 / np.maximum(cost, eps)
    np.fill_diagonal(eta, 0)
    tau = np.ones((n, n))
    best, bestv, hist = None, float("inf"), []
    for _ in range(iterations):
        tours = []
        for _a in range(ants):
            tour = [0]
            avail = set(range(1, n))
            while avail:
                i = tour[-1]
                js = np.array(sorted(avail))
                w = tau[i, js] * eta[i, js] ** 3
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
        tau *= 0.5
        for tour, val in tours:
            dep = 1 / max(val, 1e-9)
            for i in range(n):
                tau[tour[i], tour[(i + 1) % n]] += dep
        hist.append(bestv)
    return best, bestv, hist


def ga(cost, population=60, generations=150, mutation_rate=0.2, seed=20261008):
    rng = np.random.default_rng(seed)
    n = len(cost)

    def new():
        a = np.arange(1, n)
        rng.shuffle(a)
        return [0] + a.tolist()

    pop = [new() for _ in range(population)]
    best, bestv, hist = None, float("inf"), []

    def tournament():
        ids = rng.integers(0, len(pop), size=3)
        best_idx = min(ids, key=lambda idx: tour_cost(pop[int(idx)], cost))
        return pop[int(best_idx)][:]

    for _ in range(generations):
        vals = [tour_cost(t, cost) for t in pop]
        ix = int(np.argmin(vals))
        if vals[ix] < bestv:
            best, bestv = pop[ix][:], vals[ix]
        nxt = [best[:]]
        while len(nxt) < population:
            p1, p2 = tournament(), tournament()
            lo, hi = sorted(rng.choice(np.arange(1, n), size=2, replace=False))
            child = [None] * n
            child[0] = 0
            child[lo:hi + 1] = p1[lo:hi + 1]
            fill = [x for x in p2[1:] if x not in child]
            it = iter(fill)
            for j in range(1, n):
                if child[j] is None:
                    child[j] = next(it)
            if rng.random() < mutation_rate:
                i, k = sorted(rng.choice(np.arange(1, n), size=2, replace=False))
                child[i:k + 1] = child[i:k + 1][::-1]
            nxt.append(child)
        pop = nxt
        hist.append(bestv)
    return best, bestv, hist


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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", choices=["2016", "2026", "both"], default="both")
    p.add_argument("--algorithm", choices=["aco", "ga", "both"], default="both")
    p.add_argument("--seed", type=int, default=20261008)
    p.add_argument("--aco-ants", type=int, default=25)
    p.add_argument("--aco-iterations", type=int, default=80)
    p.add_argument("--ga-population", type=int, default=60)
    p.add_argument("--ga-generations", type=int, default=150)
    args = p.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)

    # Solo se admiten estas matrices exactas. No hay respaldo a nombres antiguos.
    distance_paths = {
        "2016": find_required_matrix("distancias_km_2016.csv"),
        "2026": find_required_matrix("distancias_km_2026.csv"),
    }
    toll_paths = {
        "2016": find_required_matrix("peajes_sinteticos_eur_2016.csv"),
        "2026": find_required_matrix("peajes_sinteticos_eur_2026.csv"),
    }

    params_path = DATA / "parametros.json"
    if not params_path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo obligatorio: {params_path}")
    params = json.loads(params_path.read_text(encoding="utf-8"))

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

    summaries = []
    scenarios = list(SCENARIOS) if args.scenario == "both" else [args.scenario]

    for sc in scenarios:
        out = RESULTS / sc
        out.mkdir(parents=True, exist_ok=True)
        names, D, T = matrices[sc]

        vh = float(params["hour_value_eur"][sc])
        speed = float(params["average_speed_kmh"][sc])
        fuelprice = float(params["fuel_price_eur_l"][sc])
        cons = float(params["consumption_l_100km"])
        time = D / speed
        fuel = D * (cons / 100) * fuelprice
        timecost = vh * time
        cost = timecost + fuel + T

        for fn, mat in [
            ("matriz_costos_eur.csv", cost),
            ("matriz_tiempos_estimados_h.csv", time),
            ("matriz_combustible_eur.csv", fuel),
            (f"matriz_peajes_sinteticos_eur_{sc}.csv", T),
        ]:
            pd.DataFrame(mat, index=names, columns=names).to_csv(out / fn, index_label="Capital")

        algos = ["aco", "ga"] if args.algorithm == "both" else [args.algorithm]
        for alg in algos:
            if alg == "aco":
                tour, val, hist = aco(cost, args.aco_ants, args.aco_iterations, args.seed)
            else:
                tour, val, hist = ga(cost, args.ga_population, args.ga_generations, seed=args.seed)

            route = [names[i] for i in tour] + [names[tour[0]]]
            pd.DataFrame(
                {"orden": range(1, len(route) + 1), "Capital": route}
            ).to_csv(out / f"ruta_{alg}.csv", index=False)
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
            save_route_gif(
                tour, names, coords_df, gif_path,
                f"Ruta TSP — {alg.upper()} — escenario {sc}"
            )
            summaries.append({
                "escenario": sc,
                "algoritmo": alg.upper(),
                "capitales": len(names),
                "semilla": args.seed,
                "salida": "12:00",
                "valor_hora_eur": vh,
                "velocidad_media_kmh_sup": speed,
                "combustible_eur_l": fuelprice,
                "consumo_l_100km": cons,
                "peaje_matriz_total_eur_suma_unica": float(T.sum() / 2),
                "costo_total_eur": val,
                "archivo_distancias": distance_paths[sc].name,
                "archivo_peajes": toll_paths[sc].name,
                "gif_ruta": str(gif_path.relative_to(ROOT)),
            })

    df = pd.DataFrame(summaries)
    df.to_csv(RESULTS / "resumen.csv", index=False)
    print("=== TSP ESPAÑA: EJECUCIÓN ===")
    print("Capitales:", len(matrices["2026"][0]), "| semilla:", args.seed, "| salida fijada: 12:00")
    print(df[[
        "escenario", "algoritmo", "valor_hora_eur", "costo_total_eur",
        "archivo_distancias", "archivo_peajes"
    ]].to_string(index=False))
    print("Resultados:", RESULTS)
    print("Se generó un GIF de ruta por cada combinación escenario-algoritmo.")


if __name__ == "__main__":
    main()
