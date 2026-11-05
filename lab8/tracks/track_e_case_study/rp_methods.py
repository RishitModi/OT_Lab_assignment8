"""Optimization methods for Track E: Courier Route Optimization.

Implements five exact and heuristic TSP routing algorithms:
1. Nearest Neighbour (Greedy heuristic)
2. 2-opt (Local search with first-improvement delta evaluation)
3. Simulated Annealing (Metropolis stochastic local search with geometric cooling)
4. Held-Karp (Exact Dynamic Programming over vertex subsets, vectorized in NumPy)
5. ILP with MTZ constraints (Exact Integer Linear Programming via scipy.optimize.milp)
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path
import sys
import time
from typing import Any, Sequence

# Ensure repository root and current track directory are present on sys.path
_TRACK_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in [str(_REPO_ROOT), str(_TRACK_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import scipy.sparse
from scipy.optimize import Bounds, LinearConstraint, milp

from rp_instances import is_valid_tour, tour_length


def nearest_neighbour(D: np.ndarray, start: int = 0) -> dict[str, Any]:
    """Greedy Nearest Neighbour construction heuristic for TSP.

    Optimisation logic:
    Begins at depot node (start) and iteratively moves to the closest unvisited
    node according to Euclidean distance matrix D until all stops are visited,
    subsequently returning to the depot.

    Parameters
    ----------
    D : np.ndarray
        Symmetric distance matrix of shape (n + 1, n + 1).
    start : int, default=0
        Starting depot index.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        - tour: list[int], closed tour [0, s_1, ..., s_n, 0].
        - length: float, total tour distance in km.
        - runtime_s: float, wall-clock execution time in seconds.
    """
    t_start = time.perf_counter()
    n_nodes = D.shape[0]

    visited = [False] * n_nodes
    visited[start] = True
    tour = [start]
    current = start

    # Explicit loop bound: visit remaining (n_nodes - 1) stops
    for _ in range(n_nodes - 1):
        best_dist = float("inf")
        best_node = -1
        # Greedy selection over unvisited nodes
        for node in range(n_nodes):
            if not visited[node] and D[current, node] < best_dist:
                best_dist = float(D[current, node])
                best_node = node

        if best_node == -1:
            # Fallback if graph is disconnected or numerical anomalies occur
            break
        visited[best_node] = True
        tour.append(best_node)
        current = best_node

    # Complete the cycle back to depot start
    tour.append(start)

    runtime_s = time.perf_counter() - t_start
    length = tour_length(D, tour)

    return {
        "tour": tour,
        "length": length,
        "runtime_s": runtime_s,
    }


def two_opt(
    D: np.ndarray,
    tour: Sequence[int],
    max_passes: int = 200,
    time_limit_s: float | None = None,
) -> dict[str, Any]:
    """First-improvement 2-opt local search with O(1) delta evaluation.

    Optimisation logic:
    Considers removing two non-adjacent edges (u, v) and (w, z) and reconnecting
    them as (u, w) and (v, z) by inverting the intermediate sub-tour segment.
    In a symmetric metric TSP, internal sub-tour distances remain unchanged,
    so candidate moves are evaluated in O(1) time via:
        delta = (D[u, w] + D[v, z]) - (D[u, v] + D[w, z])
    Adopts the first improving move encountered (delta < 0), restarts scanning,
    and terminates at a local optimum, the pass cap, or the time guard.
    Guaranteed never to return a worse tour than the initial input.

    Parameters
    ----------
    D : np.ndarray
        Distance matrix of shape (n + 1, n + 1).
    tour : Sequence[int]
        Initial tour starting and ending at node 0.
    max_passes : int, default=200
        Maximum passes through all candidate edge pairs.
    time_limit_s : float | None, default=None
        Maximum wall-clock time in seconds before stopping search.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        - tour: list[int], optimized tour.
        - length: float, tour distance in km.
        - runtime_s: float, wall-clock time in seconds.
        - improving_moves: int, number of accepted 2-opt swaps.
    """
    t_start = time.perf_counter()

    current_tour = list(tour)
    if current_tour[-1] != current_tour[0]:
        current_tour.append(current_tour[0])

    initial_length = tour_length(D, current_tour)
    best_tour = list(current_tour)
    best_length = initial_length

    improving_moves = 0
    num_nodes = len(current_tour) - 1  # n + 1 nodes (stops at indices 1..n)

    pass_count = 0
    while pass_count < max_passes:
        pass_count += 1
        if time_limit_s is not None and (time.perf_counter() - t_start) >= time_limit_s:
            break

        improved = False
        # Sweep edge 1: (tour[i-1], tour[i]) for i in 1..n
        for i in range(1, num_nodes):
            if time_limit_s is not None and (time.perf_counter() - t_start) >= time_limit_s:
                break
            u = current_tour[i - 1]
            v = current_tour[i]

            # Sweep edge 2: (tour[j], tour[j+1]) for j in i+1..n
            for j in range(i + 1, num_nodes):
                w = current_tour[j]
                z = current_tour[j + 1]

                # Delta evaluation in O(1)
                delta = (D[u, w] + D[v, z]) - (D[u, v] + D[w, z])
                if delta < -1e-11:
                    # First improvement: invert segment from i to j inclusive
                    current_tour[i : j + 1] = current_tour[i : j + 1][::-1]
                    improving_moves += 1
                    improved = True
                    break

            if improved:
                break

        if not improved:
            # Reached a 2-optimal local optimum
            break

    # Guard against floating-point drift: recompute exact tour length
    final_length = tour_length(D, current_tour)
    if final_length > initial_length:
        current_tour = best_tour
        final_length = best_length

    runtime_s = time.perf_counter() - t_start
    return {
        "tour": current_tour,
        "length": final_length,
        "runtime_s": runtime_s,
        "improving_moves": improving_moves,
    }


def simulated_annealing(
    D: np.ndarray,
    tour: Sequence[int],
    seed: int,
    time_limit_s: float,
    t0: float | None = None,
    alpha: float = 0.9995,
) -> dict[str, Any]:
    """Simulated Annealing metaheuristic using 2-opt neighborhood moves.

    Optimisation logic:
    Stochastic local search using the Metropolis criterion. At each iteration,
    a random 2-opt move is evaluated in O(1). If delta < 0, the move is accepted.
    If delta >= 0, it is accepted with probability exp(-delta / T).
    Temperature cools geometrically: T <- T * alpha after every candidate move.
    Runs until the wall-clock time limit expires (polled every 256 moves).
    Maintains the best-so-far tour seen during the entire chain.

    Parameters
    ----------
    D : np.ndarray
        Distance matrix of shape (n + 1, n + 1).
    tour : Sequence[int]
        Initial tour starting and ending at node 0.
    seed : int
        Random seed for stochastic decisions.
    time_limit_s : float
        Wall-clock runtime limit in seconds.
    t0 : float | None, default=None
        Initial temperature. If None, initialized to 0.1 * mean edge length.
    alpha : float, default=0.9995
        Geometric cooling schedule multiplier per move.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        - tour: list[int], best tour found.
        - length: float, best tour length in km.
        - runtime_s: float, elapsed time in seconds.
        - trace: list[tuple[float, float]], list of (elapsed_s, best_length).
        - moves: int, total evaluated moves.
    """
    t_start = time.perf_counter()
    rng = np.random.default_rng(seed)

    curr_tour = list(tour)
    if curr_tour[-1] != curr_tour[0]:
        curr_tour.append(curr_tour[0])

    curr_len = tour_length(D, curr_tour)
    best_tour = list(curr_tour)
    best_len = curr_len

    n_nodes = D.shape[0]
    n_stops = n_nodes - 1

    # Determine initial temperature T0
    if t0 is None:
        mean_edge = float(np.sum(D) / (n_nodes * (n_nodes - 1))) if n_nodes > 1 else 1.0
        T = 0.1 * mean_edge
    else:
        T = float(t0)
    T = max(T, 1e-6)

    trace: list[tuple[float, float]] = [(0.0, best_len)]
    sample_interval = max(time_limit_s / 200.0, 1e-4)
    last_sample_time = 0.0

    move_count = 0
    max_moves = 50_000_000  # Explicit iteration cap

    while move_count < max_moves:
        move_count += 1

        # Check time guard every 256 moves to minimize timing overhead
        if move_count % 256 == 0:
            elapsed = time.perf_counter() - t_start
            if elapsed - last_sample_time >= sample_interval and len(trace) < 200:
                trace.append((elapsed, best_len))
                last_sample_time = elapsed
            if elapsed >= time_limit_s:
                break

        # Pick two distinct stop indices uniformly from 1..n_stops
        i = int(rng.integers(1, n_stops + 1))
        j = int(rng.integers(1, n_stops + 1))
        if i == j:
            continue
        if i > j:
            i, j = j, i

        # Delta evaluation of 2-opt reversal
        u = curr_tour[i - 1]
        v = curr_tour[i]
        w = curr_tour[j]
        z = curr_tour[j + 1]

        delta = (D[u, w] + D[v, z]) - (D[u, v] + D[w, z])

        # Metropolis criterion
        if delta < 0.0 or rng.random() < math.exp(-delta / max(T, 1e-12)):
            curr_tour[i : j + 1] = curr_tour[i : j + 1][::-1]
            curr_len += delta

            if curr_len < best_len - 1e-11:
                best_tour = list(curr_tour)
                best_len = curr_len

        # Geometric cooling per move
        T *= alpha

    final_elapsed = time.perf_counter() - t_start
    if len(trace) < 200:
        trace.append((final_elapsed, best_len))

    # Recompute best tour length to prevent any floating-point drift
    recomputed_best = tour_length(D, best_tour)
    if recomputed_best > tour_length(D, tour):
        best_tour = list(tour)
        recomputed_best = tour_length(D, tour)

    # Downsample trace to at most 200 samples if needed
    if len(trace) > 200:
        sample_indices = np.round(np.linspace(0, len(trace) - 1, 200)).astype(int)
        trace = [trace[idx] for idx in sample_indices]

    return {
        "tour": best_tour,
        "length": recomputed_best,
        "runtime_s": final_elapsed,
        "trace": trace,
        "moves": move_count,
    }


def held_karp(D: np.ndarray) -> dict[str, Any]:
    """Exact Held-Karp dynamic programming algorithm for TSP.

    Optimisation logic:
    Finds the provably optimal TSP tour over subsets of stops using dynamic
    programming:
        C(S, j) = min_{k in S, k != j} [ C(S \\ {j}, k) + D[k, j] ]
    where S is a subset of stops containing j, and C(S, j) is the minimum cost
    of a path from depot 0 through all nodes in S ending at j.
    Vectorized across incoming predecessor nodes in NumPy for performance.
    Bounded to n <= 15 delivery stops to cap memory usage strictly at O(n 2^n).

    Parameters
    ----------
    D : np.ndarray
        Distance matrix of shape (n + 1, n + 1).

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        - tour: list[int], provably optimal tour.
        - length: float, optimal tour length in km.
        - runtime_s: float, execution time in seconds.
    """
    t_start = time.perf_counter()
    n_nodes = D.shape[0]
    n = n_nodes - 1  # Number of delivery stops

    if n > 15:
        raise ValueError(f"Held-Karp supports up to n <= 15 stops; got n={n}")

    if n == 0:
        return {"tour": [0, 0], "length": 0.0, "runtime_s": time.perf_counter() - t_start}

    if n == 1:
        length = float(D[0, 1] + D[1, 0])
        return {"tour": [0, 1, 0], "length": length, "runtime_s": time.perf_counter() - t_start}

    # DP table: dp[mask, j] = min cost to visit subset 'mask' ending at stop j (1..n)
    num_subsets = 1 << n
    dp = np.full((num_subsets, n + 1), np.inf, dtype=np.float64)
    parent = np.zeros((num_subsets, n + 1), dtype=np.int32)

    # Base cases: subsets of size 1 (direct arc from depot 0)
    for j in range(1, n + 1):
        mask = 1 << (j - 1)
        dp[mask, j] = D[0, j]
        parent[mask, j] = 0

    # Inductive step: iterate over subset sizes s = 2 to n
    for s in range(2, n + 1):
        for subset in itertools.combinations(range(1, n + 1), s):
            mask = 0
            for node in subset:
                mask |= (1 << (node - 1))

            # Vectorized evaluation for each destination node j in subset
            for j in subset:
                prev_mask = mask ^ (1 << (j - 1))
                candidates = [k for k in subset if k != j]
                # Vectorized cost evaluation over predecessor nodes
                cand_costs = dp[prev_mask, candidates] + D[candidates, j]
                best_cand_idx = int(np.argmin(cand_costs))
                dp[mask, j] = cand_costs[best_cand_idx]
                parent[mask, j] = candidates[best_cand_idx]

    # Return to depot 0 from full subset of all stops
    full_mask = (1 << n) - 1
    stops_array = np.arange(1, n + 1)
    return_costs = dp[full_mask, stops_array] + D[stops_array, 0]
    best_last_idx = int(np.argmin(return_costs))
    best_last_stop = int(stops_array[best_last_idx])
    opt_length = float(return_costs[best_last_idx])

    # Reconstruct optimal tour by backtracking through parent pointers
    path = [best_last_stop]
    curr = best_last_stop
    mask = full_mask
    for _ in range(n - 1):
        prev = int(parent[mask, curr])
        mask ^= (1 << (curr - 1))
        curr = prev
        path.append(curr)

    path.reverse()
    tour = [0] + path + [0]

    runtime_s = time.perf_counter() - t_start
    return {
        "tour": tour,
        "length": opt_length,
        "runtime_s": runtime_s,
    }


def ilp_mtz(D: np.ndarray, time_limit_s: float = 30.0) -> dict[str, Any]:
    """Exact Integer Linear Programming (ILP) with Miller-Tucker-Zemlin constraints.

    Optimisation logic:
    Formulates the TSP as an integer program solved via branch-and-bound in
    scipy.optimize.milp:
        Minimise sum_{i != j} D_ij x_ij
        Subject to:
            sum_{j != i} x_ij = 1  for all i  (out-degree)
            sum_{i != j} x_ij = 1  for all j  (in-degree)
            u_i - u_j + n * x_ij <= n - 1  for all i != j in {1..n} (subtour elimination)
            x_ij in {0, 1},  u_i in [1, n] continuous.
    The continuous auxiliary variables u_i enforce a total ordering on the
    delivery stops visited after depot 0, preventing disconnected sub-cycles.

    Parameters
    ----------
    D : np.ndarray
        Distance matrix of shape (n + 1, n + 1).
    time_limit_s : float, default=30.0
        Solver wall-clock time limit in seconds.

    Returns
    -------
    dict[str, Any]
        Dictionary with keys:
        - tour: list[int], extracted tour.
        - length: float, tour distance in km.
        - runtime_s: float, solver execution time.
        - optimal: bool, True if status == 0 (provably optimal).
        - status: int, solver status code.
        - objective: float, solver objective value.
        - mip_gap: float | None, optimality gap reported by solver.
    """
    t_start = time.perf_counter()
    N = D.shape[0]
    n = N - 1  # Number of delivery stops

    # Arc indexing for binary decision variables x_ij (i != j)
    arc_to_idx: dict[tuple[int, int], int] = {}
    idx_to_arc: list[tuple[int, int]] = []
    arc_idx = 0
    for i in range(N):
        for j in range(N):
            if i != j:
                arc_to_idx[(i, j)] = arc_idx
                idx_to_arc.append((i, j))
                arc_idx += 1

    num_arcs = N * (N - 1)
    num_vars = num_arcs + n  # x_ij arcs plus u_i continuous ordering variables

    # Objective coefficients c: minimise total distance
    c = np.zeros(num_vars, dtype=np.float64)
    for (i, j), k in arc_to_idx.items():
        c[k] = float(D[i, j])
    # Auxiliary u_i variables have zero cost in objective

    # Variable types: 1 for integer/binary x_ij, 0 for continuous u_i
    integrality = np.zeros(num_vars, dtype=np.uint8)
    integrality[:num_arcs] = 1

    # Variable bounds: x_ij in [0, 1], u_i in [1, n]
    lb = np.zeros(num_vars, dtype=np.float64)
    ub = np.ones(num_vars, dtype=np.float64)
    lb[num_arcs:] = 1.0
    ub[num_arcs:] = float(n)
    bounds = Bounds(lb=lb, ub=ub)

    # Build constraint matrix A in COO format
    row_ind: list[int] = []
    col_ind: list[int] = []
    data: list[float] = []
    lhs: list[float] = []
    rhs: list[float] = []
    constraint_idx = 0

    # 1. Out-degree: sum_{j != i} x_ij = 1 for all nodes i
    for i in range(N):
        for j in range(N):
            if i != j:
                row_ind.append(constraint_idx)
                col_ind.append(arc_to_idx[(i, j)])
                data.append(1.0)
        lhs.append(1.0)
        rhs.append(1.0)
        constraint_idx += 1

    # 2. In-degree: sum_{i != j} x_ij = 1 for all nodes j
    for j in range(N):
        for i in range(N):
            if i != j:
                row_ind.append(constraint_idx)
                col_ind.append(arc_to_idx[(i, j)])
                data.append(1.0)
        lhs.append(1.0)
        rhs.append(1.0)
        constraint_idx += 1

    # 3. MTZ subtour elimination: u_i - u_j + n * x_ij <= n - 1 for i, j in 1..n, i != j
    for i in range(1, N):
        u_i_idx = num_arcs + (i - 1)
        for j in range(1, N):
            if i != j:
                u_j_idx = num_arcs + (j - 1)
                x_ij_idx = arc_to_idx[(i, j)]

                row_ind.append(constraint_idx)
                col_ind.append(u_i_idx)
                data.append(1.0)

                row_ind.append(constraint_idx)
                col_ind.append(u_j_idx)
                data.append(-1.0)

                row_ind.append(constraint_idx)
                col_ind.append(x_ij_idx)
                data.append(float(n))

                lhs.append(-np.inf)
                rhs.append(float(n - 1))
                constraint_idx += 1

    A = scipy.sparse.csc_matrix(
        (data, (row_ind, col_ind)),
        shape=(constraint_idx, num_vars),
        dtype=np.float64,
    )
    constraints = LinearConstraint(A, lhs, rhs)

    # Solve via SciPy MILP interface
    options = {"time_limit": float(time_limit_s)}
    res = milp(
        c=c,
        integrality=integrality,
        bounds=bounds,
        constraints=constraints,
        options=options,
    )

    runtime_s = time.perf_counter() - t_start
    is_optimal = bool(res.status == 0)

    # Extract tour from solved arc variables
    tour = [0]
    if res.x is not None:
        sol_x = res.x[:num_arcs]
        next_nodes: dict[int, int] = {}
        for (i, j), k in arc_to_idx.items():
            if sol_x[k] > 0.5:
                next_nodes[i] = j

        curr = 0
        cap_traversal = N + 5
        steps = 0
        while steps < cap_traversal:
            steps += 1
            nxt = next_nodes.get(curr, None)
            if nxt is None:
                break
            tour.append(nxt)
            if nxt == 0:
                break
            curr = nxt

    # If extraction did not produce a valid tour, fallback gracefully to nearest neighbour
    if not is_valid_tour(tour, n):
        fallback = nearest_neighbour(D, start=0)
        tour = fallback["tour"]

    calc_len = tour_length(D, tour)
    obj_val = float(res.fun) if res.fun is not None else calc_len
    mip_gap = getattr(res, "mip_gap", None)

    return {
        "tour": tour,
        "length": calc_len,
        "runtime_s": runtime_s,
        "optimal": is_optimal,
        "status": int(res.status),
        "objective": obj_val,
        "mip_gap": float(mip_gap) if mip_gap is not None else None,
    }

