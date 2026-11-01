# Track E: Courier Route Optimization - Case Study Summary

## Environment and Run Metadata

- **Operating System / Platform:** Windows-11-10.0.26200-SP0
- **Python Version:** 3.12.10
- **NumPy Version:** 2.5.4
- **SciPy Version:** 1.18.1
- **Mode:** Quick mode
- **Total Runtime:** 11.15 seconds

## Experiment E0: Strategy-Selection Table

Evaluation matrix contrasting discrete optimization paradigms across problem scale, computational complexity, memory bounds, hardware demands, and parallelization structures.

| Method | Variable type | Problem size handled | Exact or heuristic | Hardware | Parallelism | Chapter 6 technique |
| --- | --- | --- | --- | --- | --- | --- |
| order received (baseline) | permutation | any n | heuristic (baseline) | one CPU core | none | baseline |
| nearest neighbour | permutation | any n | heuristic | one CPU core | parallel over start nodes | greedy |
| 2-opt | permutation | up to a few thousand stops | heuristic reaching a local optimum | one CPU core | parallel restarts | local search |
| simulated annealing | permutation | any n | heuristic | one CPU core | parallel independent chains | stochastic search |
| Held-Karp | subsets of stops | n up to about 20 because memory grows as n * 2^n | exact | one CPU core with large memory | parallel over subsets of equal size | dynamic programming |
| ILP with MTZ | binary arc variables plus continuous order variables | up to about 15 to 30 stops in minutes with a general solver | exact | solver runs on CPU | solver-internal parallelism | ILP and branch-and-bound |

- Output CSV: `strategy_table.csv`

## Experiment E1: Exact Optimization and Evidence Comparison

Comparative benchmark of provably exact algorithms (Held-Karp dynamic programming and Miller-Tucker-Zemlin Integer Linear Programming) versus polynomial-time heuristics (order-received baseline, Nearest Neighbour, 2-opt local search, and Simulated Annealing).

| n | method | mean_gap_percent | std_gap_percent | mean_runtime_s | std_runtime_s |
| --- | --- | --- | --- | --- | --- |
| 8 | order received | 46.47 | 5.384 | 0.002935 | 0.002808 |
| 8 | nearest neighbour | 8.497 | 8.497 | 1.34e-05 | 7e-07 |
| 8 | nearest neighbour + 2-opt | 0 | 0 | 0.0002653 | 0.0002048 |
| 8 | simulated annealing | 7.699e-15 | 7.699e-15 | 0.5008 | 0.0003913 |
| 8 | Held-Karp | 0 | 0 | 0.005956 | 0.00088 |
| 8 | ILP | 7.699e-15 | 7.699e-15 | 0.3251 | 0.1563 |
| 10 | order received | 84.76 | 4.352 | 0.0001116 | 1.7e-06 |
| 10 | nearest neighbour | 13.39 | 9.722 | 1.36e-05 | 5.999e-07 |
| 10 | nearest neighbour + 2-opt | 0.8471 | 0.8471 | 4.71e-05 | 1.1e-06 |
| 10 | simulated annealing | 0 | 0 | 0.5006 | 6.89e-05 |
| 10 | Held-Karp | 0 | 0 | 0.02784 | 0.002145 |
| 10 | ILP | 0 | 0 | 0.2352 | 0.1552 |

**Evidence for Assignment Question 1:** Across benchmark instances, the current order-received baseline exceeds the provably optimal tour by a mean of 65.62% (standard deviation: 19.76%).

- Aggregate CSV: `e1_aggregated.csv`
- Comparative Plot: `e1_exact_comparison.png`

## Experiment E2: Heuristic Scalability Benchmarks

Empirical scaling analysis of fast heuristic algorithms across problem instances ranging from n = 20 to n = 200 delivery stops, measured in distance gap relative to the best-discovered route and wall-clock execution time.

| n | method | mean_gap_percent | std_gap_percent | mean_runtime_s | std_runtime_s |
| --- | --- | --- | --- | --- | --- |
| 20 | order received | 211.8 | 69.9 | 5.695e-05 | 8.75e-06 |
| 20 | nearest neighbour | 2.013 | 2.013 | 3.475e-05 | 7.499e-07 |
| 20 | nearest neighbour + 2-opt | 1.966 | 1.966 | 0.0001294 | 1.57e-05 |
| 20 | random start + 2-opt | 5.277 | 4.81 | 0.001667 | 0.0003313 |
| 20 | simulated annealing | 0 | 0 | 0.3007 | 3.905e-05 |
| 50 | order received | 468 | 56.09 | 0.000116 | 8.65e-06 |
| 50 | nearest neighbour | 24.01 | 10.46 | 0.0004089 | 1.65e-06 |
| 50 | nearest neighbour + 2-opt | 5.648 | 4.834 | 0.01232 | 0.00073 |
| 50 | random start + 2-opt | 0.6723 | 0.5669 | 0.05658 | 0.008086 |
| 50 | simulated annealing | 0 | 0 | 0.3018 | 0.0004949 |

- Aggregate CSV: `e2_aggregated.csv`
- Solution Gap Plot: `e2_scaling_gap.png`
- Runtime Scaling Plot: `e2_scaling_runtime.png`

## Experiment E3: Anytime Convergence and Spatial Route Inspection

Evaluation of the anytime objective improvement curve during Simulated Annealing local search, alongside side-by-side planar route visualizations contrasting chaotic baseline dispatching against clustered, optimized tours.

- Evaluated size: n=50, seed=0
- Nearest Neighbour length: 119.16 km
- Nearest Neighbour + 2-opt length: 105.80 km
- Simulated Annealing best length: 104.44 km
- Trajectory samples captured: 161

- Anytime Convergence Curve: `e3_anytime_curve.png`
- Route Map Figure: `e3_map_comparison.png`
- Trace CSV: `e3_sa_trace.csv`

## Experiment E4: Hyperparameter Sensitivity Analysis

Sensitivity analysis of Simulated Annealing performance under variations in the initial temperature parameter T0 (scaled relative to mean edge distance) and geometric cooling rate alpha.

| t0_factor | alpha | mean_length_km | std_length_km |
| --- | --- | --- | --- |
| 0.01 | 0.999 | 156.1 | 5.728 |
| 0.01 | 0.9995 | 153.6 | 8.236 |
| 0.01 | 1 | 154.9 | 8.147 |
| 0.1 | 0.999 | 160.2 | 5.939 |
| 0.1 | 0.9995 | 158.6 | 1.964 |
| 0.1 | 1 | 164.1 | 6.556 |
| 1 | 0.999 | 161.2 | 6.511 |
| 1 | 0.9995 | 158.2 | 5.682 |
| 1 | 1 | 173.6 | 8.302 |

- Sensitivity CSV: `e4_sensitivity.csv`
- Parameter Surface Plot: `e4_sensitivity.png`

## Verification and Correctness Section

No verification failures
