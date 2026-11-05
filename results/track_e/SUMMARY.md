# Track E: Courier Route Optimization - Case Study Summary

## Environment and Run Metadata

- **Operating System / Platform:** Windows-11-10.0.26200-SP0
- **Python Version:** 3.15.1
- **NumPy Version:** 2.5.2
- **SciPy Version:** 1.18.1
- **Mode:** Quick mode
- **Total Runtime:** 16.92 seconds

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
| 8 | order received | 46.47 | 5.384 | 0.0004152 | 0.0001066 |
| 8 | nearest neighbour | 8.497 | 8.497 | 4.29e-05 | 5.8e-06 |
| 8 | nearest neighbour + 2-opt | 0 | 0 | 0.0001522 | 3.225e-05 |
| 8 | simulated annealing | 7.699e-15 | 7.699e-15 | 0.5029 | 6.43e-05 |
| 8 | Held-Karp | 0 | 0 | 0.02649 | 0.001576 |
| 8 | ILP | 7.699e-15 | 7.699e-15 | 1.013 | 0.5076 |
| 10 | order received | 84.76 | 4.352 | 0.0002935 | 9.45e-06 |
| 10 | nearest neighbour | 13.39 | 9.722 | 4.515e-05 | 1.501e-07 |
| 10 | nearest neighbour + 2-opt | 0.8471 | 0.8471 | 0.0001627 | 3.6e-06 |
| 10 | simulated annealing | 0 | 0 | 0.5037 | 0.000296 |
| 10 | Held-Karp | 0 | 0 | 0.1396 | 0.0004565 |
| 10 | ILP | 0 | 0 | 0.7881 | 0.5127 |

**Evidence for Assignment Question 1:** Across benchmark instances, the current order-received baseline exceeds the provably optimal tour by a mean of 65.62% (standard deviation: 19.76%).

- Aggregate CSV: `e1_aggregated.csv`
- Comparative Plot: `e1_exact_comparison.png`

## Experiment E2: Heuristic Scalability Benchmarks

Empirical scaling analysis of fast heuristic algorithms across problem instances ranging from n = 20 to n = 200 delivery stops, measured in distance gap relative to the best-discovered route and wall-clock execution time.

| n | method | mean_gap_percent | std_gap_percent | mean_runtime_s | std_runtime_s |
| --- | --- | --- | --- | --- | --- |
| 20 | order received | 211.8 | 69.9 | 0.000162 | 2.265e-05 |
| 20 | nearest neighbour | 2.013 | 2.013 | 0.0005975 | 0.0004924 |
| 20 | nearest neighbour + 2-opt | 1.966 | 1.966 | 0.0008892 | 0.0004105 |
| 20 | random start + 2-opt | 5.277 | 4.81 | 0.005302 | 0.001287 |
| 20 | simulated annealing | 0 | 0 | 0.3016 | 0.001359 |
| 50 | order received | 468 | 56.09 | 0.0001635 | 8e-06 |
| 50 | nearest neighbour | 24.01 | 10.46 | 0.0005599 | 5.55e-05 |
| 50 | nearest neighbour + 2-opt | 5.648 | 4.834 | 0.0205 | 0.006734 |
| 50 | random start + 2-opt | 0.6723 | 0.5669 | 0.1182 | 0.01673 |
| 50 | simulated annealing | 0 | 0 | 0.3027 | 0.0009583 |

- Aggregate CSV: `e2_aggregated.csv`
- Solution Gap Plot: `e2_scaling_gap.png`
- Runtime Scaling Plot: `e2_scaling_runtime.png`

## Experiment E3: Anytime Convergence and Spatial Route Inspection

Evaluation of the anytime objective improvement curve during Simulated Annealing local search, alongside side-by-side planar route visualizations contrasting chaotic baseline dispatching against clustered, optimized tours.

- Evaluated size: n=50, seed=0
- Nearest Neighbour length: 119.16 km
- Nearest Neighbour + 2-opt length: 105.80 km
- Simulated Annealing best length: 104.44 km
- Trajectory samples captured: 134

- Anytime Convergence Curve: `e3_anytime_curve.png`
- Route Map Figure: `e3_map_comparison.png`
- Trace CSV: `e3_sa_trace.csv`

## Experiment E4: Hyperparameter Sensitivity Analysis

Sensitivity analysis of Simulated Annealing performance under variations in the initial temperature parameter T0 (scaled relative to mean edge distance) and geometric cooling rate alpha.

| t0_factor | alpha | mean_length_km | std_length_km |
| --- | --- | --- | --- |
| 0.01 | 0.999 | 158.8 | 8.263 |
| 0.01 | 0.9995 | 155.9 | 8.39 |
| 0.01 | 1 | 157.5 | 8.265 |
| 0.1 | 0.999 | 161.9 | 5.646 |
| 0.1 | 0.9995 | 165.7 | 2.911 |
| 0.1 | 1 | 172.2 | 6.848 |
| 1 | 0.999 | 171 | 5.666 |
| 1 | 0.9995 | 173.6 | 8.302 |
| 1 | 1 | 173.6 | 8.302 |

- Sensitivity CSV: `e4_sensitivity.csv`
- Parameter Surface Plot: `e4_sensitivity.png`

## Verification and Correctness Section

No verification failures
