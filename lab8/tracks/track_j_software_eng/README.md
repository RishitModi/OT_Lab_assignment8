# Track J: Software Engineering Optimization

## Objective
Measure whether mathematical optimization (weighted set cover via 0/1 Integer Linear Programming and greedy heuristics) can significantly reduce regression test suite execution time and size while preserving 100% of structural code coverage (lines and branch arcs) and maintaining fault-detection effectiveness (mutation score). The code under test is the core compiler pipeline of Track F (>1000 lines).

## Baseline
<!-- Describe the baseline method or initial unoptimized benchmark -->

## Formulation
- **Decision variables:**
  $$x_t \in \{0, 1\} \quad \text{for each candidate test } t \in T$$
  where $x_t = 1$ if test $t$ is selected and retained in the minimized suite, and $x_t = 0$ if discarded.
- **Objective function:**
  Minimise total test execution cost (measured untraced wall-clock runtime):
  $$\min \sum_{t \in T} c_t \cdot x_t$$
  where $c_t > 0$ represents the empirical execution cost of test $t$.
- **Constraints (Weighted Set Cover):**
  Every structural code element $e \in E$ (lines or branch arcs exercised by the full suite) must be covered by at least one selected test:
  $$\sum_{t: e \in \text{cover}(t)} x_t \ge 1 \quad \forall e \in E$$

## Methods
- **Codebase Under Test:** The five core compiler modules of Track F (`cc_lang.py`, `cc_ir.py`, `cc_passes.py`, `cc_regalloc.py`, `cc_vm.py`), comprising an optimizing compiler codebase of over 1000 non-blank, non-comment lines.
- **Profile First, Then Optimise:** Baseline test execution is profiled using `cProfile` and traced with `sys.settrace` to measure individual test durations, identify runtime bottlenecks, and extract exact statement and branch coverage sets before optimization.
- **Minimization Algorithms:**
  - *Exact 0/1 ILP:* Solves the weighted set cover problem to provable mathematical optimality using `scipy.optimize.milp` over a sparse constraint matrix.
  - *Greedy Heuristic:* Iteratively selects tests maximizing cost-effectiveness (ratio of newly covered elements to test cost: $\frac{|\text{cover}(t) \cap U|}{c_t}$).
  - *Random Baseline:* Repeatedly samples tests in random order until full universe coverage is achieved (`select_random_until_cover`).
- **Test Prioritization:** Evaluates greedy additional coverage, cost-ascending, and random permutations via cumulative coverage progression curves and normalized Area Under the Curve (AUC).
- **Fault-Injection Validation:** Injects 20 pass output mutants (operators M1–M5 across 4 compiler passes) to evaluate empirical mutation scores of minimized suites.

## How to run
```bash
python tracks/track_j_software_eng/run_all.py [--quick]
python -m pytest tracks/track_j_software_eng/tests -q
```

## Results
All tables and figures are produced by python tracks/track_j_software_eng/run_all.py and listed in results/track_j/SUMMARY.md (the final results use the --quick configuration with 38 tests; results/track_j/SUMMARY_full_J0_only.md, if present, holds the baseline and profile of the 158-test universe: median full-suite runtime 6.16 s, 905 of 1360 executable lines covered). Code under test: 1644 non-blank non-comment lines of the Track F compiler. 38 tests, full suite: summed cost 1.44 s, runtime 1.66 s. Minimisation keeping all covered lines: random order needs 31 tests on average; greedy 9 tests (89 percent measured runtime reduction); exact ILP 7 tests (91 percent). Keeping all covered arcs: greedy 10 tests (77 percent), ILP 8 tests (82 percent). Coverage was preserved at 100 percent with no failing test. Prioritisation: normalised coverage-time area 0.997 for greedy additional coverage and cheapest-first, 0.983 for random orders. Fault-detection cost was not measured (mutation step incomplete).

## Correctness check
- All tests pass on the unmodified compiler (38 of 38, and 158 of 158 in the baseline run).
- Every selection covers 100 percent of the elements it was asked to cover and has no failing tests.
- ILP cost is at most greedy cost, which is at most the full-suite cost, in every row.
- Coverage is traced with sys.settrace (line and arc).

## Limitations
- The final results are for 38 tests, not 158.
- The fault-injection (mutation) experiment did not complete and its scores (100 percent over zero detectable mutants) are not valid (Failure Log cases 25 and 26), so the loss of fault-detection ability from minimisation is not measured.
- Coverage is not fault detection.
- Timings are single-machine wall-clock values with about 8 points of noise.
- The baseline runtime of J0 and J1 disagree (case 26).
- The selection must be recomputed when the code changes.
