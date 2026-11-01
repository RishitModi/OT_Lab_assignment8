# Track E: Real-World Optimization Case Study

## Objective
Optimize courier dispatch routing in an urban delivery network to minimize total distance traveled in kilometers. The case study evaluates exact and heuristic combinatorial optimization paradigms across multiple problem scales, benchmarks anytime behavior against the baseline, and assesses empirical trade-offs between optimality guarantees and computational tractability.

## Baseline
The baseline represents the current operational process: the courier visits delivery stops strictly in the order the orders arrived (chronological arrival order, modeled as a random permutation of the delivery stops beginning and ending at the central depot).

## Formulation
### Mathematical Formulation
The courier route optimization problem is modeled as a symmetric Traveling Salesperson Problem (TSP) with a single depot (node 0) and $n$ delivery stops ($1, \dots, n$):

- **Decision variables:**
  - $x_{ij} \in \{0, 1\}$: Binary arc variable indicating whether the courier drives directly from node $i$ to node $j$ ($i \ne j$).
  - $u_i \in [1, n]$: Continuous auxiliary variables representing the visit sequence order for each delivery stop $i \in \{1, \dots, n\}$.
- **Objective function:**
  $$\min \sum_{i=0}^{n} \sum_{j=0, j \ne i}^{n} D_{ij} x_{ij}$$
  where $D_{ij}$ denotes the symmetric Euclidean distance in kilometers between node $i$ and node $j$.
- **Constraints:**
  - Out-degree constraints (each node is left exactly once):
    $$\sum_{j=0, j \ne i}^{n} x_{ij} = 1 \quad \forall i \in \{0, \dots, n\}$$
  - In-degree constraints (each node is entered exactly once):
    $$\sum_{i=0, i \ne j}^{n} x_{ij} = 1 \quad \forall j \in \{0, \dots, n\}$$
  - Miller-Tucker-Zemlin (MTZ) subtour elimination constraints:
    $$u_i - u_j + n x_{ij} \le n - 1 \quad \forall i \ne j \in \{1, \dots, n\}$$
  - Domain bounds:
    $$x_{ij} \in \{0, 1\}, \quad 1 \le u_i \le n \quad \forall i \in \{1, \dots, n\}$$

### Assumptions
- **Geography:** Planar 20 km $\times$ 20 km city territory with a centrally located depot at (10 km, 10 km).
- **Distances:** Symmetric Euclidean distance metric $D_{ij} = \|coords[i] - coords[j]\|_2$.
- **Fleet & Demand:** Single courier vehicle; all parcels fit into a single vehicle (unconstrained vehicle capacity); no customer delivery time windows.
- **Spatial distribution:** Synthetic customer stops generated from a mixture of 4 Gaussian spatial clusters (std = 2 km, clipped to city boundaries) comprising 80% of stops, combined with 20% uniform random stops.

### Metrics
- **Tour length (km):** Total round-trip distance computed independently of the optimization method via `tour_length(D, tour)`.
- **Optimality gap (%):** Relative percentage excess distance compared to the provably optimal tour (Held-Karp) or best-discovered tour:
  $$\text{Gap} (\%) = \frac{\text{Length} - \text{Reference}}{\text{Reference}} \times 100\%$$
- **Runtime (s):** Wall-clock execution time measured with `time.perf_counter()`.

## Strategy-Selection Table
| Method | Variable type | Problem size handled | Exact or heuristic | Hardware | Parallelism | Chapter 6 technique |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| order received (baseline) | permutation | any n | heuristic (baseline) | one CPU core | none | baseline |
| nearest neighbour | permutation | any n | heuristic | one CPU core | parallel over start nodes | greedy |
| 2-opt | permutation | up to a few thousand stops | heuristic reaching a local optimum | one CPU core | parallel restarts | local search |
| simulated annealing | permutation | any n | heuristic | one CPU core | parallel independent chains | stochastic search |
| Held-Karp | subsets of stops | n up to about 20 because memory grows as n * 2^n | exact | one CPU core with large memory | parallel over subsets of equal size | dynamic programming |
| ILP with MTZ | binary arc variables plus continuous order variables | up to about 15 to 30 stops in minutes with a general solver | exact | solver runs on CPU | solver-internal parallelism | ILP and branch-and-bound |

## Methods
1. **Order Received (Baseline):** Simulates the FIFO arrival sequence with no routing optimization.
2. **Nearest Neighbour:** Greedy heuristic that builds a tour by iteratively visiting the nearest unvisited node from the current location.
3. **2-opt Local Search:** First-improvement iterative improvement heuristic that evaluates edge reconnection moves in $O(1)$ time via delta evaluation and reverses intermediate subpaths.
4. **Simulated Annealing:** Metropolis stochastic local search with geometric cooling schedule ($T \leftarrow T \times \alpha$) over 2-opt neighborhood permutations, tracking the best-so-far solution.
5. **Held-Karp Dynamic Programming:** Exact subset dynamic programming algorithm vectorized across incoming nodes in NumPy, capped at $n \le 15$ delivery stops.
6. **Integer Linear Programming (ILP MTZ):** Exact branch-and-cut optimization using `scipy.optimize.milp` over $O(n^2)$ binary arc variables and continuous ordering variables.

## How to run
Execute the master benchmark pipeline:
```bash
python tracks/track_e_case_study/run_all.py [--quick]
```

Run automated pytest unit and invariant tests:
```bash
python -m pytest tracks/track_e_case_study/tests -q
```

## Results
<!-- Experimental outcomes, comparison tables, and plots saved in results/ -->

## Correctness check
<!-- Verification steps, assertions, unit tests, and theoretical invariants checked -->

## Limitations
<!-- Computational bottlenecks, approximations, assumptions, and failure modes -->
