# Track J: Software Engineering Optimization – Experimental Summary

## Environment & Platform Configuration
- **Python Version**: 3.12.10
- **NumPy Version**: 2.5.4
- **SciPy Version**: 1.18.1
- **Platform / OS**: Windows-11-10.0.26200-SP0
- **Quick Execution Flag**: True
- **Random Seed Management**: Explicit seeds across all stochastic selections

## Codebase Under Test Metrics
- **Code Under Test (CUT) Non-Comment Lines**: 1644
- **Total Non-Test Compiler Lines**: 2582

### Codebase Line Counts by Module
| file | lines |
| --- | --- |
| cc_lang.py | 465 |
| cc_ir.py | 291 |
| cc_passes.py | 376 |
| cc_regalloc.py | 286 |
| cc_vm.py | 226 |
| TOTAL_CUT | 1644 |
| TOTAL_ALL_COMPILER | 2582 |

## J0: Baseline Profiling & Test Execution
- **Total Tests in Universe**: 38
- **Baseline Median Full-Suite Runtime**: 0.6672 s
- **Passing Tests**: 38/38
- **Per-Test Cost (min / median / max)**: 0.00148 s / 0.02409 s / 0.38733 s
- **Top 10 Slowest Tests Runtime Share**: 60.10%

### Top 15 Functions by Cumulative Execution Time (cProfile)
| function | file_line | ncalls | tottime | cumtime |
| --- | --- | --- | --- | --- |
| run_ir | cc_ir.py:296 | 228 | 0.497 | 0.7468 |
| run_machine | cc_vm.py:161 | 38 | 0.1222 | 0.2416 |
| optimize_all | cc_passes.py:500 | 38 | 4.91e-05 | 0.1596 |
| optimize | cc_passes.py:469 | 38 | 0.001117 | 0.1595 |
| dce | cc_passes.py:361 | 125 | 0.01599 | 0.148 |
| live_after_each_instruction | cc_ir.py:243 | 235 | 0.01872 | 0.1212 |
| build_cfg | cc_ir.py:111 | 610 | 0.02542 | 0.1124 |
| <built-in method builtins.isinstance> | ~:0 | 1488385 | 0.1094 | 0.1098 |
| <built-in method builtins.len> | ~:0 | 1445751 | 0.09833 | 0.09833 |
| compute_local_def_use | cc_ir.py:98 | 15813 | 0.03314 | 0.09694 |
| eval_op | cc_lang.py:50 | 484817 | 0.08596 | 0.08596 |
| get_def_use | cc_ir.py:54 | 74985 | 0.05472 | 0.07259 |
| read_operand | cc_vm.py:181 | 216690 | 0.05131 | 0.06589 |
| const_fold_prop | cc_passes.py:55 | 212 | 0.01151 | 0.06097 |
| compute_liveness | cc_ir.py:185 | 273 | 0.01644 | 0.04806 |

### Code Coverage Breakdown
| file | executable_lines | covered_lines | line_coverage_pct | covered_arcs |
| --- | --- | --- | --- | --- |
| cc_lang.py | 391 | 236 | 60.36 | 254 |
| cc_ir.py | 256 | 206 | 80.47 | 260 |
| cc_passes.py | 299 | 233 | 77.93 | 299 |
| cc_regalloc.py | 233 | 89 | 38.2 | 125 |
| cc_vm.py | 181 | 139 | 76.8 | 163 |
| TOTAL | 1360 | 903 | 66.4 | 1101 |

- Output Figure: `j0_test_cost_distribution.png`

## J1: Test Suite Minimization (Weighted Set Cover)
Evaluates full suite against random-until-cover, greedy heuristic, and exact 0/1 ILP minimization.
- **Kill Matrix Execution**: partial: 0 of 20 mutants completed

| coverage_kind | method | num_tests | summed_cost | actual_runtime | runtime_reduction_pct | coverage_preserved_pct | failing_tests | mutation_score_pct | optimal | solve_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| all | full_suite | 38 | 1.436 | 1.661 | 0 | 100 | 0 | 100 | True | 0 |
| lines | random_until_cover(mean_N=30.6) | 31 | 1.154 | 1.476 | 11.15 | 100 | 0 | 100 | False | 0 |
| lines | greedy | 9 | 0.1384 | 0.1864 | 88.78 | 100 | 0 | 100 | False | 0.00406 |
| lines | ilp | 7 | 0.1108 | 0.1511 | 90.9 | 100 | 0 | 100 | True | 0.06579 |
| arcs | random_until_cover(mean_N=30.6) | 31 | 1.154 | 1.334 | 19.7 | 100 | 0 | 100 | False | 0 |
| arcs | greedy | 10 | 0.2166 | 0.3748 | 77.44 | 100 | 0 | 100 | False | 0.01303 |
| arcs | ilp | 8 | 0.1889 | 0.2968 | 82.13 | 100 | 0 | 100 | True | 0.06217 |

- Output Figure: `j1_minimization_comparison.png`

## J2: Test Prioritization
Compares cumulative line coverage accumulation over time for greedy additional coverage, cost-ascending, and random orders.

| strategy | normalized_auc |
| --- | --- |
| greedy_additional | 0.9974 |
| cost_ascending | 0.9967 |
| random_order(mean_over_20_seeds) | 0.9826 |

- Output Figure: `j2_prioritization_curves.png`

## J3: Fault-Injection & Mutation Testing
Evaluates whether minimized test suites preserve mutant killing capability.

- **Mutation Matrix Status**: partial: 0 of 20 mutants completed
- **Total Injected Mutants**: 20
- **Completed Mutants Evaluated**: 0
- **Detectable Mutants by Full Suite**: 0

> **Note on Fault Injection Proxy**: Fault injection in this benchmark modifies the instruction list output of individual optimization passes. This operates as an empirical proxy for fault-detection ability; structural coverage and fault-detection capability are not theoretically identical.

| method | tests_kept | detectable_killed | detectable_missed | mutation_score_pct | missed_mutants |
| --- | --- | --- | --- | --- | --- |
| full | 38 | 0 | 0 | 100 | None |
| greedy_lines | 9 | 0 | 0 | 100 | None |
| ilp_lines | 7 | 0 | 0 | 100 | None |
| greedy_arcs | 10 | 0 | 0 | 100 | None |
| ilp_arcs | 8 | 0 | 0 | 100 | None |

## Verification Section
- **No verification failures**