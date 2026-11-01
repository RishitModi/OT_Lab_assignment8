"""Unit tests and algorithmic invariant tests for Track E routing methods.

Tests exact optimality, mathematical invariants, tour validations, and smoke tests:
- Held-Karp matches brute-force permutation search (n = 6 on 3 seeds)
- ILP MTZ matches Held-Karp provable optimum (n = 8 on 2 seeds)
- Nearest Neighbour and 2-opt generate valid tours
- 2-opt monotonicity invariant (never lengthens tour)
- Hand-made square perimeter verification
- Simulated Annealing tour validity and monotonicity
- Smoke test dynamic pipeline runner via importlib
"""

from __future__ import annotations

import importlib.util
import itertools
import math
from pathlib import Path
import sys

# Ensure repository root and track root are placed on sys.path
_TRACK_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in [str(_REPO_ROOT), str(_TRACK_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import pytest

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


def test_held_karp_equals_brute_force_n6() -> None:
    """Verify Held-Karp dynamic programming against exhaustive brute-force for n = 6 across 3 seeds."""
    n = 6
    seeds = [10, 20, 30]

    for seed in seeds:
        inst = make_instance(n, seed)
        D = inst.D

        # 1. Exact Held-Karp
        hk_res = held_karp(D)
        assert is_valid_tour(hk_res["tour"], n), f"Held-Karp produced invalid tour on seed {seed}"
        hk_len = hk_res["length"]

        # 2. Exhaustive brute-force enumeration of all 6! = 720 permutations
        min_bf_len = float("inf")
        best_bf_tour: list[int] = []

        # Stops are 1 to 6
        stops = list(range(1, n + 1))
        cap_perms = 1000
        step = 0
        for perm in itertools.permutations(stops):
            step += 1
            if step > cap_perms:
                break
            cand_tour = [0] + list(perm) + [0]
            cand_len = tour_length(D, cand_tour)
            if cand_len < min_bf_len:
                min_bf_len = cand_len
                best_bf_tour = cand_tour

        # Held-Karp must equal brute-force optimal length within floating-point tolerance
        assert math.isclose(hk_len, min_bf_len, rel_tol=1e-6, abs_tol=1e-6), (
            f"Held-Karp length {hk_len:.6f} != brute-force optimum {min_bf_len:.6f} (seed {seed})"
        )


def test_ilp_equals_held_karp_n8() -> None:
    """Verify MTZ Integer Linear Programming matches Held-Karp for n = 8 across 2 seeds."""
    n = 8
    seeds = [42, 84]

    for seed in seeds:
        inst = make_instance(n, seed)
        D = inst.D

        hk_res = held_karp(D)
        ilp_res = ilp_mtz(D, time_limit_s=30.0)

        assert is_valid_tour(ilp_res["tour"], n), f"ILP tour invalid on seed {seed}"
        assert ilp_res["optimal"] is True, f"ILP did not report provable optimality on seed {seed}"

        # Invariant: Held-Karp length equals ILP objective and tour length
        assert math.isclose(hk_res["length"], ilp_res["length"], rel_tol=1e-5, abs_tol=1e-5), (
            f"HK length {hk_res['length']:.6f} != ILP length {ilp_res['length']:.6f} (seed {seed})"
        )
        assert math.isclose(hk_res["length"], ilp_res["objective"], rel_tol=1e-5, abs_tol=1e-5), (
            f"HK length {hk_res['length']:.6f} != ILP objective {ilp_res['objective']:.6f} (seed {seed})"
        )


def test_nearest_neighbour_and_two_opt_valid_tours() -> None:
    """Verify Nearest Neighbour and 2-opt return structurally valid tours."""
    n = 12
    inst = make_instance(n, seed=99)
    D = inst.D

    nn_res = nearest_neighbour(D, start=0)
    assert is_valid_tour(nn_res["tour"], n), "Nearest Neighbour tour failed validity check"

    two_opt_res = two_opt(D, nn_res["tour"], max_passes=200)
    assert is_valid_tour(two_opt_res["tour"], n), "2-opt tour failed validity check"


def test_two_opt_never_lengthens_tour() -> None:
    """Verify 2-opt monotonicity invariant: output length is never strictly greater than input."""
    n = 15
    for seed in [1, 2, 3]:
        inst = make_instance(n, seed=seed)
        D = inst.D

        # Test from arbitrary order-received tour
        init_tour = order_received_tour(n, seed=seed)
        init_len = tour_length(D, init_tour)

        opt_res = two_opt(D, init_tour, max_passes=200)
        assert opt_res["length"] <= init_len + 1e-9, (
            f"2-opt lengthened tour from {init_len:.6f} to {opt_res['length']:.6f} (seed {seed})"
        )

        # Test from Nearest Neighbour tour
        nn_res = nearest_neighbour(D, start=0)
        nn_opt = two_opt(D, nn_res["tour"], max_passes=200)
        assert nn_opt["length"] <= nn_res["length"] + 1e-9, (
            f"2-opt lengthened NN tour from {nn_res['length']:.6f} to {nn_opt['length']:.6f} (seed {seed})"
        )


def test_handmade_square_perimeter() -> None:
    """Verify tour_length on a 10 km x 10 km square equals the perimeter (40 km)."""
    # Depot 0 at (0, 0), stop 1 at (0, 10), stop 2 at (10, 10), stop 3 at (10, 0)
    coords = np.array([
        [0.0, 0.0],    # Depot
        [0.0, 10.0],   # Stop 1
        [10.0, 10.0],  # Stop 2
        [10.0, 0.0],   # Stop 3
    ], dtype=np.float64)

    delta = coords[:, np.newaxis, :] - coords[np.newaxis, :, :]
    D = np.hypot(delta[:, :, 0], delta[:, :, 1])

    tour_explicit = [0, 1, 2, 3, 0]
    expected_perimeter = 40.0
    computed_len = tour_length(D, tour_explicit)

    assert math.isclose(computed_len, expected_perimeter, rel_tol=1e-9, abs_tol=1e-9), (
        f"Square perimeter computed as {computed_len:.6f}, expected {expected_perimeter:.6f}"
    )

    # Test implicit closed tour format [0, 1, 2, 3]
    tour_implicit = [0, 1, 2, 3]
    assert math.isclose(tour_length(D, tour_implicit), expected_perimeter, rel_tol=1e-9, abs_tol=1e-9)


def test_simulated_annealing_validity_and_monotonicity() -> None:
    """Verify Simulated Annealing returns a valid tour not worse than its starting tour."""
    n = 15
    inst = make_instance(n, seed=77)
    D = inst.D

    nn_res = nearest_neighbour(D, start=0)
    sa_res = simulated_annealing(
        D,
        nn_res["tour"],
        seed=123,
        time_limit_s=0.2,
        alpha=0.999,
    )

    assert is_valid_tour(sa_res["tour"], n), "Simulated Annealing produced an invalid tour"
    assert sa_res["length"] <= nn_res["length"] + 1e-9, (
        f"SA length {sa_res['length']:.6f} worse than start {nn_res['length']:.6f}"
    )


def test_smoke_run_all(tmp_path: Path) -> None:
    """Smoke test loading run_all via importlib and running quick mode into tmp_path."""
    run_all_path = Path(__file__).resolve().parents[1] / "run_all.py"
    spec = importlib.util.spec_from_file_location("track_e_run_all", run_all_path)
    assert spec is not None, "Failed to create spec for track_e_run_all"
    assert spec.loader is not None, "Loader missing for track_e_run_all"

    mod = importlib.util.module_from_spec(spec)
    sys.modules["track_e_run_all"] = mod
    spec.loader.exec_module(mod)

    # Execute quick mode
    exit_code = mod.main(["--quick", "--out", str(tmp_path)])
    assert exit_code == 0, f"run_all pipeline failed with exit code {exit_code}"

    # Assert outputs exist
    summary_path = tmp_path / "SUMMARY.md"
    assert summary_path.exists(), "SUMMARY.md was not generated in quick mode"

    csv_files = list(tmp_path.glob("*.csv"))
    assert len(csv_files) > 0, "No CSV files produced by run_all in quick mode"

    png_files = list(tmp_path.glob("*.png"))
    assert len(png_files) > 0, "No PNG plots produced by run_all in quick mode"

