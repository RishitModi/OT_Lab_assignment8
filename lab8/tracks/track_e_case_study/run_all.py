"""Master Benchmark and Evaluation Script for Track E: Courier Route Optimization.

Usage:
    python tracks/track_e_case_study/run_all.py [--quick] [--out results/track_e]

Experiments:
    E0: Strategy-Selection Table across Chapter 6 paradigms
    E1: Exact Optimization and Heuristic Evidence (Held-Karp vs ILP vs Heuristics)
    E2: Empirical Scaling of Fast Heuristics (up to n = 200 stops)
    E3: Anytime Convergence Behavior and Spatial Route Inspection
    E4: Simulated Annealing Hyperparameter Sensitivity (T0 and cooling schedule)
"""

from __future__ import annotations

import argparse
from pathlib import Path
import platform
import sys
import time
import traceback
from typing import Any, Sequence

# Ensure repository root and current track directory are present on sys.path
_TRACK_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in [str(_REPO_ROOT), str(_TRACK_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy

from rp_instances import (
    is_valid_tour,
    make_instance,
    order_received_tour,
    tour_length,
)
from rp_methods import (
    held_karp,
    ilp_mtz,
    nearest_neighbour,
    simulated_annealing,
    two_opt,
)
from rp_util import to_markdown, write_csv


# ---------------------------------------------------------------------------
# Experiment E0: Strategy-Selection Table
# ---------------------------------------------------------------------------


def run_experiment_e0(out_dir: Path) -> dict[str, Any]:
    """Generate the Chapter 6 strategy-selection comparison table."""
    columns = [
        "Method",
        "Variable type",
        "Problem size handled",
        "Exact or heuristic",
        "Hardware",
        "Parallelism",
        "Chapter 6 technique",
    ]
    rows = [
        {
            "Method": "order received (baseline)",
            "Variable type": "permutation",
            "Problem size handled": "any n",
            "Exact or heuristic": "heuristic (baseline)",
            "Hardware": "one CPU core",
            "Parallelism": "none",
            "Chapter 6 technique": "baseline",
        },
        {
            "Method": "nearest neighbour",
            "Variable type": "permutation",
            "Problem size handled": "any n",
            "Exact or heuristic": "heuristic",
            "Hardware": "one CPU core",
            "Parallelism": "parallel over start nodes",
            "Chapter 6 technique": "greedy",
        },
        {
            "Method": "2-opt",
            "Variable type": "permutation",
            "Problem size handled": "up to a few thousand stops",
            "Exact or heuristic": "heuristic reaching a local optimum",
            "Hardware": "one CPU core",
            "Parallelism": "parallel restarts",
            "Chapter 6 technique": "local search",
        },
        {
            "Method": "simulated annealing",
            "Variable type": "permutation",
            "Problem size handled": "any n",
            "Exact or heuristic": "heuristic",
            "Hardware": "one CPU core",
            "Parallelism": "parallel independent chains",
            "Chapter 6 technique": "stochastic search",
        },
        {
            "Method": "Held-Karp",
            "Variable type": "subsets of stops",
            "Problem size handled": "n up to about 20 because memory grows as n * 2^n",
            "Exact or heuristic": "exact",
            "Hardware": "one CPU core with large memory",
            "Parallelism": "parallel over subsets of equal size",
            "Chapter 6 technique": "dynamic programming",
        },
        {
            "Method": "ILP with MTZ",
            "Variable type": "binary arc variables plus continuous order variables",
            "Problem size handled": "up to about 15 to 30 stops in minutes with a general solver",
            "Exact or heuristic": "exact",
            "Hardware": "solver runs on CPU",
            "Parallelism": "solver-internal parallelism",
            "Chapter 6 technique": "ILP and branch-and-bound",
        },
    ]

    csv_path = out_dir / "strategy_table.csv"
    write_csv(csv_path, rows, columns)
    md_table = to_markdown(rows, columns)

    return {
        "rows": rows,
        "columns": columns,
        "md_table": md_table,
        "csv_path": str(csv_path.name),
    }


# ---------------------------------------------------------------------------
# Experiment E1: Exact Optimization & Heuristic Evidence
# ---------------------------------------------------------------------------


def run_experiment_e1(
    out_dir: Path,
    quick: bool,
    verification_failures: list[str],
) -> dict[str, Any]:
    """Benchmark exact methods against heuristics and quantify the baseline gap."""
    n_values = [8, 10] if quick else [8, 10, 12, 14]
    seeds = [0, 1] if quick else [0, 1, 2, 3, 4]

    instance_rows: list[dict[str, Any]] = []
    order_gaps_all: list[float] = []

    # Map method names for consistent tracking
    methods_order = [
        "order received",
        "nearest neighbour",
        "nearest neighbour + 2-opt",
        "simulated annealing",
        "Held-Karp",
        "ILP",
    ]

    for n in n_values:
        for seed in seeds:
            inst = make_instance(n, seed)
            coords, D = inst.coords, inst.D

            # 1. Exact Held-Karp
            hk_res = held_karp(D)
            opt_len = hk_res["length"]

            # Tour validation for Held-Karp
            if not is_valid_tour(hk_res["tour"], n):
                verification_failures.append(f"E1: Held-Karp tour invalid (n={n}, seed={seed})")
            if abs(tour_length(D, hk_res["tour"]) - opt_len) > 1e-9:
                verification_failures.append(f"E1: Held-Karp length discrepancy (n={n}, seed={seed})")

            # 2. Exact ILP MTZ
            ilp_time_limit = 10.0 if quick else 30.0
            ilp_res = ilp_mtz(D, time_limit_s=ilp_time_limit)

            # Tour validation for ILP
            if not is_valid_tour(ilp_res["tour"], n):
                verification_failures.append(f"E1: ILP tour invalid (n={n}, seed={seed})")
            if abs(tour_length(D, ilp_res["tour"]) - ilp_res["length"]) > 1e-9:
                verification_failures.append(f"E1: ILP length discrepancy (n={n}, seed={seed})")

            # Invariant check: Held-Karp equals ILP objective when optimal
            if ilp_res["optimal"]:
                if abs(opt_len - ilp_res["objective"]) > 1e-5:
                    verification_failures.append(
                        f"E1: HK length {opt_len:.6f} != ILP obj {ilp_res['objective']:.6f} (n={n}, seed={seed})"
                    )

            # 3. Order received baseline
            t_or_start = time.perf_counter()
            or_tour = order_received_tour(n, seed)
            or_time = time.perf_counter() - t_or_start
            or_len = tour_length(D, or_tour)
            if not is_valid_tour(or_tour, n):
                verification_failures.append(f"E1: order received tour invalid (n={n}, seed={seed})")

            # 4. Nearest Neighbour
            nn_res = nearest_neighbour(D, start=0)
            if not is_valid_tour(nn_res["tour"], n):
                verification_failures.append(f"E1: NN tour invalid (n={n}, seed={seed})")
            if abs(tour_length(D, nn_res["tour"]) - nn_res["length"]) > 1e-9:
                verification_failures.append(f"E1: NN length discrepancy (n={n}, seed={seed})")

            # 5. NN + 2-opt
            two_opt_res = two_opt(D, nn_res["tour"], max_passes=200)
            if not is_valid_tour(two_opt_res["tour"], n):
                verification_failures.append(f"E1: 2-opt tour invalid (n={n}, seed={seed})")
            if abs(tour_length(D, two_opt_res["tour"]) - two_opt_res["length"]) > 1e-9:
                verification_failures.append(f"E1: 2-opt length discrepancy (n={n}, seed={seed})")
            # Invariant check: 2-opt never lengthens starting tour
            if two_opt_res["length"] > nn_res["length"] + 1e-9:
                verification_failures.append(
                    f"E1: 2-opt length {two_opt_res['length']} > start NN {nn_res['length']} (n={n}, seed={seed})"
                )

            # 6. Simulated Annealing from NN
            sa_res = simulated_annealing(
                D,
                nn_res["tour"],
                seed=seed + 100,
                time_limit_s=0.5,
                alpha=0.9995,
            )
            if not is_valid_tour(sa_res["tour"], n):
                verification_failures.append(f"E1: SA tour invalid (n={n}, seed={seed})")
            if abs(tour_length(D, sa_res["tour"]) - sa_res["length"]) > 1e-9:
                verification_failures.append(f"E1: SA length discrepancy (n={n}, seed={seed})")

            # Compile method results for instance
            eval_data = [
                ("order received", or_len, or_time, None),
                ("nearest neighbour", nn_res["length"], nn_res["runtime_s"], None),
                ("nearest neighbour + 2-opt", two_opt_res["length"], nn_res["runtime_s"] + two_opt_res["runtime_s"], None),
                ("simulated annealing", sa_res["length"], sa_res["runtime_s"], None),
                ("Held-Karp", hk_res["length"], hk_res["runtime_s"], None),
                ("ILP", ilp_res["length"], ilp_res["runtime_s"], ilp_res["optimal"]),
            ]

            for m_name, m_len, m_time, m_opt in eval_data:
                # Invariant check: no heuristic shorter than optimum
                if m_len < opt_len - 1e-8:
                    verification_failures.append(
                        f"E1: Heuristic {m_name} length {m_len:.6f} < optimum {opt_len:.6f} (n={n}, seed={seed})"
                    )

                gap_pct = 100.0 * (m_len - opt_len) / opt_len
                if m_name == "order received":
                    order_gaps_all.append(gap_pct)

                instance_rows.append({
                    "n": n,
                    "seed": seed,
                    "method": m_name,
                    "length_km": m_len,
                    "gap_to_optimum_percent": gap_pct,
                    "runtime_s": m_time,
                    "ilp_optimal": m_opt,
                })

    # Save per-instance CSV
    inst_cols = ["n", "seed", "method", "length_km", "gap_to_optimum_percent", "runtime_s", "ilp_optimal"]
    write_csv(out_dir / "e1_instances.csv", instance_rows, inst_cols)

    # Compute aggregated metrics (mean and std of gap and runtime per n and method)
    agg_rows: list[dict[str, Any]] = []
    agg_cols = ["n", "method", "mean_gap_percent", "std_gap_percent", "mean_runtime_s", "std_runtime_s"]

    for n in n_values:
        for m in methods_order:
            subset = [r for r in instance_rows if r["n"] == n and r["method"] == m]
            gaps = [r["gap_to_optimum_percent"] for r in subset]
            times = [r["runtime_s"] for r in subset]
            agg_rows.append({
                "n": n,
                "method": m,
                "mean_gap_percent": float(np.mean(gaps)),
                "std_gap_percent": float(np.std(gaps)),
                "mean_runtime_s": float(np.mean(times)),
                "std_runtime_s": float(np.std(times)),
            })

    write_csv(out_dir / "e1_aggregated.csv", agg_rows, agg_cols)

    # Plot bar chart of mean gap per method and n
    fig, ax = plt.subplots(figsize=(10, 6))
    heuristic_methods = [
        "order received",
        "nearest neighbour",
        "nearest neighbour + 2-opt",
        "simulated annealing",
    ]
    x_indices = np.arange(len(n_values))
    width = 0.18

    for idx, method in enumerate(heuristic_methods):
        method_gaps = [
            next(r["mean_gap_percent"] for r in agg_rows if r["n"] == n and r["method"] == method)
            for n in n_values
        ]
        offset = (idx - 1.5) * width
        ax.bar(x_indices + offset, method_gaps, width, label=method)

    ax.set_xlabel("Number of delivery stops (n)")
    ax.set_ylabel("Mean optimality gap (%)")
    ax.set_title("E1: Heuristic Optimality Gap vs Provably Optimal Route")
    ax.set_xticks(x_indices)
    ax.set_xticklabels([f"n={n}" for n in n_values])
    ax.grid(True, linestyle="--", alpha=0.5, axis="y")
    ax.legend()
    fig.tight_layout()
    fig_path = out_dir / "e1_exact_comparison.png"
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    mean_baseline_gap = float(np.mean(order_gaps_all))
    std_baseline_gap = float(np.std(order_gaps_all))

    return {
        "agg_rows": agg_rows,
        "agg_cols": agg_cols,
        "md_table": to_markdown(agg_rows, agg_cols),
        "mean_baseline_gap": mean_baseline_gap,
        "std_baseline_gap": std_baseline_gap,
        "csv_path": "e1_aggregated.csv",
        "fig_path": "e1_exact_comparison.png",
    }


# ---------------------------------------------------------------------------
# Experiment E2: Scaling of the Heuristics
# ---------------------------------------------------------------------------


def run_experiment_e2(
    out_dir: Path,
    quick: bool,
    verification_failures: list[str],
) -> dict[str, Any]:
    """Benchmark heuristic scalability and solution quality up to n = 200 stops."""
    n_values = [20, 50] if quick else [20, 50, 100, 200]
    seeds = [0, 1] if quick else [0, 1, 2, 3, 4]
    sa_time_limit = 0.3 if quick else 2.0

    methods = [
        "order received",
        "nearest neighbour",
        "nearest neighbour + 2-opt",
        "random start + 2-opt",
        "simulated annealing",
    ]

    instance_rows: list[dict[str, Any]] = []

    for n in n_values:
        for seed in seeds:
            inst = make_instance(n, seed)
            coords, D = inst.coords, inst.D

            # 1. Order received
            t0 = time.perf_counter()
            or_tour = order_received_tour(n, seed)
            or_time = time.perf_counter() - t0
            or_len = tour_length(D, or_tour)

            # 2. Nearest neighbour
            nn_res = nearest_neighbour(D, start=0)

            # 3. NN + 2-opt
            two_opt_res = two_opt(D, nn_res["tour"], max_passes=200)

            # 4. Random start + 2-opt
            t0_rnd2opt = time.perf_counter()
            rnd_tour = order_received_tour(n, seed + 500)
            rnd_2opt_res = two_opt(D, rnd_tour, max_passes=200)
            rnd_2opt_time = (time.perf_counter() - t0_rnd2opt) + rnd_2opt_res["runtime_s"]

            # 5. Simulated Annealing from NN
            sa_res = simulated_annealing(
                D,
                nn_res["tour"],
                seed=seed + 200,
                time_limit_s=sa_time_limit,
                alpha=0.9995,
            )

            # Validity and invariant checks
            for name, tour_cand, len_cand in [
                ("order received", or_tour, or_len),
                ("nearest neighbour", nn_res["tour"], nn_res["length"]),
                ("nearest neighbour + 2-opt", two_opt_res["tour"], two_opt_res["length"]),
                ("random start + 2-opt", rnd_2opt_res["tour"], rnd_2opt_res["length"]),
                ("simulated annealing", sa_res["tour"], sa_res["length"]),
            ]:
                if not is_valid_tour(tour_cand, n):
                    verification_failures.append(f"E2: {name} produced invalid tour (n={n}, seed={seed})")
                if abs(tour_length(D, tour_cand) - len_cand) > 1e-9:
                    verification_failures.append(f"E2: {name} length discrepancy (n={n}, seed={seed})")

            # Reference length: shortest tour found by any method on this instance
            cand_lengths = [
                or_len,
                nn_res["length"],
                two_opt_res["length"],
                rnd_2opt_res["length"],
                sa_res["length"],
            ]
            ref_length = min(cand_lengths)

            instance_data = [
                ("order received", or_len, or_time),
                ("nearest neighbour", nn_res["length"], nn_res["runtime_s"]),
                ("nearest neighbour + 2-opt", two_opt_res["length"], nn_res["runtime_s"] + two_opt_res["runtime_s"]),
                ("random start + 2-opt", rnd_2opt_res["length"], rnd_2opt_time),
                ("simulated annealing", sa_res["length"], sa_res["runtime_s"]),
            ]

            for m_name, m_len, m_time in instance_data:
                gap_pct = 100.0 * (m_len - ref_length) / ref_length
                instance_rows.append({
                    "n": n,
                    "seed": seed,
                    "method": m_name,
                    "length_km": m_len,
                    "gap_to_best_percent": gap_pct,
                    "runtime_s": m_time,
                })

    # Save CSV
    inst_cols = ["n", "seed", "method", "length_km", "gap_to_best_percent", "runtime_s"]
    write_csv(out_dir / "e2_scaling.csv", instance_rows, inst_cols)

    # Aggregated table
    agg_rows: list[dict[str, Any]] = []
    agg_cols = ["n", "method", "mean_gap_percent", "std_gap_percent", "mean_runtime_s", "std_runtime_s"]

    for n in n_values:
        for m in methods:
            subset = [r for r in instance_rows if r["n"] == n and r["method"] == m]
            gaps = [r["gap_to_best_percent"] for r in subset]
            times = [r["runtime_s"] for r in subset]
            agg_rows.append({
                "n": n,
                "method": m,
                "mean_gap_percent": float(np.mean(gaps)),
                "std_gap_percent": float(np.std(gaps)),
                "mean_runtime_s": float(np.mean(times)),
                "std_runtime_s": float(np.std(times)),
            })

    write_csv(out_dir / "e2_aggregated.csv", agg_rows, agg_cols)

    # Plot 1: Gap vs n per method
    fig, ax = plt.subplots(figsize=(9, 5))
    for m in methods:
        gaps = [next(r["mean_gap_percent"] for r in agg_rows if r["n"] == n and r["method"] == m) for n in n_values]
        ax.plot(n_values, gaps, marker="o", linewidth=2, label=m)

    ax.set_xlabel("Number of delivery stops (n)")
    ax.set_ylabel("Mean gap to best discovered route (%)")
    ax.set_title("E2: Scalability Comparison - Solution Gap vs Scale (n)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig_gap_path = out_dir / "e2_scaling_gap.png"
    fig.savefig(fig_gap_path, dpi=150)
    plt.close(fig)

    # Plot 2: Runtime vs n (log y)
    fig, ax = plt.subplots(figsize=(9, 5))
    for m in methods:
        times = [next(r["mean_runtime_s"] for r in agg_rows if r["n"] == n and r["method"] == m) for n in n_values]
        ax.plot(n_values, times, marker="s", linewidth=2, label=m)

    ax.set_yscale("log")
    ax.set_xlabel("Number of delivery stops (n)")
    ax.set_ylabel("Mean runtime (seconds, log scale)")
    ax.set_title("E2: Scalability Comparison - Wall-clock Runtime vs Scale (n)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig_time_path = out_dir / "e2_scaling_runtime.png"
    fig.savefig(fig_time_path, dpi=150)
    plt.close(fig)

    return {
        "agg_rows": agg_rows,
        "agg_cols": agg_cols,
        "md_table": to_markdown(agg_rows, agg_cols),
        "csv_path": "e2_aggregated.csv",
        "fig_gap_path": "e2_scaling_gap.png",
        "fig_time_path": "e2_scaling_runtime.png",
    }


# ---------------------------------------------------------------------------
# Experiment E3: Anytime Behavior & Route Inspection
# ---------------------------------------------------------------------------


def run_experiment_e3(
    out_dir: Path,
    quick: bool,
    verification_failures: list[str],
) -> dict[str, Any]:
    """Evaluate anytime convergence trajectory and render spatial route inspection map."""
    n_sa = 50 if quick else 100
    seed_sa = 0
    time_limit_sa = 1.0 if quick else 5.0

    inst_sa = make_instance(n_sa, seed_sa)
    D_sa = inst_sa.D

    nn_res = nearest_neighbour(D_sa, start=0)
    two_opt_res = two_opt(D_sa, nn_res["tour"], max_passes=200)

    sa_res = simulated_annealing(
        D_sa,
        nn_res["tour"],
        seed=seed_sa + 42,
        time_limit_s=time_limit_sa,
        alpha=0.9995,
    )

    trace = sa_res["trace"]
    if not trace:
        verification_failures.append("E3: SA trace is empty")

    # Save SA trace CSV
    trace_rows = [{"elapsed_s": t, "best_length_km": l} for t, l in trace]
    write_csv(out_dir / "e3_sa_trace.csv", trace_rows, ["elapsed_s", "best_length_km"])

    # Figure 1: Anytime curve
    fig, ax = plt.subplots(figsize=(9, 5))
    times = [t for t, _ in trace]
    lengths = [l for _, l in trace]
    ax.plot(times, lengths, label="Simulated Annealing (best-so-far)", color="#1f77b4", linewidth=2)

    ax.axhline(nn_res["length"], color="#d62728", linestyle="--", label=f"Nearest Neighbour ({nn_res['length']:.2f} km)")
    ax.axhline(two_opt_res["length"], color="#2ca02c", linestyle="--", label=f"NN + 2-opt ({two_opt_res['length']:.2f} km)")
    ax.axhline(sa_res["length"], color="#9467bd", linestyle=":", label=f"Best found ({sa_res['length']:.2f} km)")

    ax.set_xlabel("Elapsed time (seconds)")
    ax.set_ylabel("Tour length (km)")
    ax.set_title(f"E3: Anytime Convergence Profile (n={n_sa}, seed={seed_sa})")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig_curve_path = out_dir / "e3_anytime_curve.png"
    fig.savefig(fig_curve_path, dpi=150)
    plt.close(fig)

    # Figure 2: Spatial Route Map Inspection (n = 50, seed = 0)
    inst_map = make_instance(50, 0)
    coords_map = inst_map.coords
    D_map = inst_map.D

    or_map_tour = order_received_tour(50, 0)
    or_map_len = tour_length(D_map, or_map_tour)

    nn_map_res = nearest_neighbour(D_map, start=0)
    opt_map_res = two_opt(D_map, nn_map_res["tour"], max_passes=200)
    opt_map_len = opt_map_res["length"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: Order-received baseline
    ax1 = axes[0]
    ax1.scatter(coords_map[1:, 0], coords_map[1:, 1], c="#1f77b4", s=30, label="Delivery stops")
    ax1.scatter(coords_map[0, 0], coords_map[0, 1], c="#d62728", marker="s", s=100, label="Depot (node 0)")
    tour_coords_or = coords_map[or_map_tour]
    ax1.plot(tour_coords_or[:, 0], tour_coords_or[:, 1], c="#ff7f0e", alpha=0.7, linewidth=1.2, label="Tour path")
    ax1.set_title(f"Baseline: Order Received ({or_map_len:.2f} km)")
    ax1.set_xlabel("X (km)")
    ax1.set_ylabel("Y (km)")
    ax1.set_xlim(-0.5, 20.5)
    ax1.set_ylim(-0.5, 20.5)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right")

    # Panel 2: Optimized route (NN + 2-opt)
    ax2 = axes[1]
    ax2.scatter(coords_map[1:, 0], coords_map[1:, 1], c="#1f77b4", s=30, label="Delivery stops")
    ax2.scatter(coords_map[0, 0], coords_map[0, 1], c="#d62728", marker="s", s=100, label="Depot (node 0)")
    tour_coords_opt = coords_map[opt_map_res["tour"]]
    ax2.plot(tour_coords_opt[:, 0], tour_coords_opt[:, 1], c="#2ca02c", alpha=0.8, linewidth=1.5, label="Optimized path")
    ax2.set_title(f"Optimized: Nearest Neighbour + 2-opt ({opt_map_len:.2f} km)")
    ax2.set_xlabel("X (km)")
    ax2.set_ylabel("Y (km)")
    ax2.set_xlim(-0.5, 20.5)
    ax2.set_ylim(-0.5, 20.5)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc="upper right")

    fig.suptitle("E3: Spatial Comparison of Courier Trajectories (n=50, seed=0)", fontsize=14)
    fig.tight_layout()
    fig_map_path = out_dir / "e3_map_comparison.png"
    fig.savefig(fig_map_path, dpi=150)
    plt.close(fig)

    return {
        "n": n_sa,
        "seed": seed_sa,
        "nn_len": nn_res["length"],
        "two_opt_len": two_opt_res["length"],
        "sa_best_len": sa_res["length"],
        "trace_samples": len(trace),
        "fig_curve_path": "e3_anytime_curve.png",
        "fig_map_path": "e3_map_comparison.png",
        "csv_path": "e3_sa_trace.csv",
    }


# ---------------------------------------------------------------------------
# Experiment E4: Simulated Annealing Sensitivity
# ---------------------------------------------------------------------------


def run_experiment_e4(
    out_dir: Path,
    quick: bool,
    verification_failures: list[str],
) -> dict[str, Any]:
    """Measure hyperparameter sensitivity across initial temperature and cooling rate."""
    n = 100
    seeds = [0, 1] if quick else [0, 1, 2, 3, 4]
    time_limit_sa = 0.2 if quick else 1.0

    t0_factors = [0.01, 0.1, 1.0]
    alphas = [0.999, 0.9995, 0.99995]

    results_table: list[dict[str, Any]] = []

    for t0_factor in t0_factors:
        for alpha in alphas:
            lengths: list[float] = []
            for seed in seeds:
                inst = make_instance(n, seed)
                coords, D = inst.coords, inst.D

                mean_edge = float(np.sum(D) / (D.shape[0] * (D.shape[0] - 1)))
                t0_val = t0_factor * mean_edge

                nn_res = nearest_neighbour(D, start=0)
                sa_res = simulated_annealing(
                    D,
                    nn_res["tour"],
                    seed=seed + 300,
                    time_limit_s=time_limit_sa,
                    t0=t0_val,
                    alpha=alpha,
                )

                if not is_valid_tour(sa_res["tour"], n):
                    verification_failures.append(f"E4: invalid tour (t0_factor={t0_factor}, alpha={alpha}, seed={seed})")

                lengths.append(sa_res["length"])

            results_table.append({
                "t0_factor": t0_factor,
                "alpha": alpha,
                "mean_length_km": float(np.mean(lengths)),
                "std_length_km": float(np.std(lengths)),
            })

    columns = ["t0_factor", "alpha", "mean_length_km", "std_length_km"]
    write_csv(out_dir / "e4_sensitivity.csv", results_table, columns)

    # Plot sensitivity heatmap / curves
    fig, ax = plt.subplots(figsize=(9, 5))
    for factor in t0_factors:
        pts = [r for r in results_table if r["t0_factor"] == factor]
        x_vals = [r["alpha"] for r in pts]
        y_vals = [r["mean_length_km"] for r in pts]
        ax.plot(x_vals, y_vals, marker="o", linewidth=2, label=f"t0 factor = {factor}")

    ax.set_xlabel("Cooling multiplier (alpha)")
    ax.set_ylabel("Mean tour length (km)")
    ax.set_title("E4: Simulated Annealing Parameter Sensitivity (n=100)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig_path = out_dir / "e4_sensitivity.png"
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)

    return {
        "results_table": results_table,
        "columns": columns,
        "md_table": to_markdown(results_table, columns),
        "csv_path": "e4_sensitivity.csv",
        "fig_path": "e4_sensitivity.png",
    }


# ---------------------------------------------------------------------------
# Main Pipeline Runner and Markdown Generator
# ---------------------------------------------------------------------------


def run_pipeline(out_dir: Path, quick: bool = False) -> int:
    """Execute complete Track E experimental pipeline and synthesize SUMMARY.md."""
    out_dir.mkdir(parents=True, exist_ok=True)
    t_pipeline_start = time.perf_counter()

    failed_experiments: dict[str, str] = {}
    verification_failures: list[str] = []

    e0_data: dict[str, Any] | None = None
    e1_data: dict[str, Any] | None = None
    e2_data: dict[str, Any] | None = None
    e3_data: dict[str, Any] | None = None
    e4_data: dict[str, Any] | None = None

    print(f"Starting Track E evaluation (quick={quick}, out={out_dir})")

    # E0: Strategy selection table
    try:
        print("--> Running E0: Strategy selection table...")
        e0_data = run_experiment_e0(out_dir)
    except Exception:
        failed_experiments["E0"] = traceback.format_exc()
        print(f"E0 failed:\n{failed_experiments['E0']}", file=sys.stderr)

    # E1: Evidence and exact comparison
    try:
        print("--> Running E1: Exact optimization and baseline comparison...")
        e1_data = run_experiment_e1(out_dir, quick, verification_failures)
    except Exception:
        failed_experiments["E1"] = traceback.format_exc()
        print(f"E1 failed:\n{failed_experiments['E1']}", file=sys.stderr)

    # E2: Scalability of heuristics
    try:
        print("--> Running E2: Heuristic scalability benchmarks...")
        e2_data = run_experiment_e2(out_dir, quick, verification_failures)
    except Exception:
        failed_experiments["E2"] = traceback.format_exc()
        print(f"E2 failed:\n{failed_experiments['E2']}", file=sys.stderr)

    # E3: Anytime convergence and spatial tour inspection
    try:
        print("--> Running E3: Anytime convergence and route mapping...")
        e3_data = run_experiment_e3(out_dir, quick, verification_failures)
    except Exception:
        failed_experiments["E3"] = traceback.format_exc()
        print(f"E3 failed:\n{failed_experiments['E3']}", file=sys.stderr)

    # E4: Hyperparameter sensitivity
    try:
        print("--> Running E4: Hyperparameter sensitivity analysis...")
        e4_data = run_experiment_e4(out_dir, quick, verification_failures)
    except Exception:
        failed_experiments["E4"] = traceback.format_exc()
        print(f"E4 failed:\n{failed_experiments['E4']}", file=sys.stderr)

    # Synthesize SUMMARY.md inside finally block
    try:
        pipeline_duration = time.perf_counter() - t_pipeline_start
        summary_lines: list[str] = []

        summary_lines.append("# Track E: Courier Route Optimization - Case Study Summary\n")
        summary_lines.append("## Environment and Run Metadata\n")
        summary_lines.append(f"- **Operating System / Platform:** {platform.platform()}")
        summary_lines.append(f"- **Python Version:** {platform.python_version()}")
        summary_lines.append(f"- **NumPy Version:** {np.__version__}")
        summary_lines.append(f"- **SciPy Version:** {scipy.__version__}")
        summary_lines.append(f"- **Mode:** {'Quick mode' if quick else 'Full mode'}")
        summary_lines.append(f"- **Total Runtime:** {pipeline_duration:.2f} seconds\n")

        # E0 Section
        summary_lines.append("## Experiment E0: Strategy-Selection Table\n")
        summary_lines.append(
            "Evaluation matrix contrasting discrete optimization paradigms across problem scale, "
            "computational complexity, memory bounds, hardware demands, and parallelization structures.\n"
        )
        if e0_data is not None:
            summary_lines.append(e0_data["md_table"] + "\n")
            summary_lines.append(f"- Output CSV: `{e0_data['csv_path']}`\n")
        else:
            summary_lines.append("*Experiment E0 failed to execute.*\n")

        # E1 Section
        summary_lines.append("## Experiment E1: Exact Optimization and Evidence Comparison\n")
        summary_lines.append(
            "Comparative benchmark of provably exact algorithms (Held-Karp dynamic programming and "
            "Miller-Tucker-Zemlin Integer Linear Programming) versus polynomial-time heuristics "
            "(order-received baseline, Nearest Neighbour, 2-opt local search, and Simulated Annealing).\n"
        )
        if e1_data is not None:
            summary_lines.append(e1_data["md_table"] + "\n")
            summary_lines.append(
                f"**Evidence for Assignment Question 1:** Across benchmark instances, the current order-received "
                f"baseline exceeds the provably optimal tour by a mean of {e1_data['mean_baseline_gap']:.2f}% "
                f"(standard deviation: {e1_data['std_baseline_gap']:.2f}%).\n"
            )
            summary_lines.append(f"- Aggregate CSV: `{e1_data['csv_path']}`")
            summary_lines.append(f"- Comparative Plot: `{e1_data['fig_path']}`\n")
        else:
            summary_lines.append("*Experiment E1 failed to execute.*\n")

        # E2 Section
        summary_lines.append("## Experiment E2: Heuristic Scalability Benchmarks\n")
        summary_lines.append(
            "Empirical scaling analysis of fast heuristic algorithms across problem instances "
            "ranging from n = 20 to n = 200 delivery stops, measured in distance gap relative "
            "to the best-discovered route and wall-clock execution time.\n"
        )
        if e2_data is not None:
            summary_lines.append(e2_data["md_table"] + "\n")
            summary_lines.append(f"- Aggregate CSV: `{e2_data['csv_path']}`")
            summary_lines.append(f"- Solution Gap Plot: `{e2_data['fig_gap_path']}`")
            summary_lines.append(f"- Runtime Scaling Plot: `{e2_data['fig_time_path']}`\n")
        else:
            summary_lines.append("*Experiment E2 failed to execute.*\n")

        # E3 Section
        summary_lines.append("## Experiment E3: Anytime Convergence and Spatial Route Inspection\n")
        summary_lines.append(
            "Evaluation of the anytime objective improvement curve during Simulated Annealing local search, "
            "alongside side-by-side planar route visualizations contrasting chaotic baseline dispatching "
            "against clustered, optimized tours.\n"
        )
        if e3_data is not None:
            summary_lines.append(
                f"- Evaluated size: n={e3_data['n']}, seed={e3_data['seed']}\n"
                f"- Nearest Neighbour length: {e3_data['nn_len']:.2f} km\n"
                f"- Nearest Neighbour + 2-opt length: {e3_data['two_opt_len']:.2f} km\n"
                f"- Simulated Annealing best length: {e3_data['sa_best_len']:.2f} km\n"
                f"- Trajectory samples captured: {e3_data['trace_samples']}\n"
            )
            summary_lines.append(f"- Anytime Convergence Curve: `{e3_data['fig_curve_path']}`")
            summary_lines.append(f"- Route Map Figure: `{e3_data['fig_map_path']}`")
            summary_lines.append(f"- Trace CSV: `{e3_data['csv_path']}`\n")
        else:
            summary_lines.append("*Experiment E3 failed to execute.*\n")

        # E4 Section
        summary_lines.append("## Experiment E4: Hyperparameter Sensitivity Analysis\n")
        summary_lines.append(
            "Sensitivity analysis of Simulated Annealing performance under variations in the initial "
            "temperature parameter T0 (scaled relative to mean edge distance) and geometric cooling rate alpha.\n"
        )
        if e4_data is not None:
            summary_lines.append(e4_data["md_table"] + "\n")
            summary_lines.append(f"- Sensitivity CSV: `{e4_data['csv_path']}`")
            summary_lines.append(f"- Parameter Surface Plot: `{e4_data['fig_path']}`\n")
        else:
            summary_lines.append("*Experiment E4 failed to execute.*\n")

        # Verification Section
        summary_lines.append("## Verification and Correctness Section\n")
        all_ran = (len(failed_experiments) == 0) and (
            e0_data is not None
            and e1_data is not None
            and e2_data is not None
            and e3_data is not None
            and e4_data is not None
        )

        if all_ran and len(verification_failures) == 0:
            summary_lines.append("No verification failures\n")
        else:
            summary_lines.append(f"Recorded failures: {len(verification_failures) + len(failed_experiments)}\n")
            if failed_experiments:
                summary_lines.append("### Failed Experiments:\n")
                for exp_name, tb in failed_experiments.items():
                    summary_lines.append(f"#### Experiment {exp_name} Error:\n```\n{tb}\n```\n")
            if verification_failures:
                summary_lines.append("### Invariant Violation Messages:\n")
                for vf in verification_failures:
                    summary_lines.append(f"- {vf}")
                summary_lines.append("")

        summary_file = out_dir / "SUMMARY.md"
        summary_file.write_text("\n".join(summary_lines), encoding="utf-8")
        print(f"Generated {summary_file}")

    except KeyboardInterrupt:
        raise
    except Exception as exc:
        print(f"Failed while writing SUMMARY.md: {exc}", file=sys.stderr)
        traceback.print_exc()

    # Determine process exit code
    if failed_experiments or verification_failures:
        print(f"Completed with failures (failed_exps={len(failed_experiments)}, checks={len(verification_failures)})")
        return 1

    print("Completed successfully with no verification failures.")
    return 0


def main(args: list[str] | None = None) -> int:
    """CLI entrypoint for running Track E benchmark suite."""
    parser = argparse.ArgumentParser(description="Track E: Courier Route Optimization Benchmark Suite")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run lightweight quick mode (under 40 seconds)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="results/track_e",
        help="Target output directory for CSV, PNG, and SUMMARY.md (default: results/track_e)",
    )
    parsed = parser.parse_args(args)
    return run_pipeline(out_dir=Path(parsed.out), quick=parsed.quick)


if __name__ == "__main__":
    sys.exit(main())

