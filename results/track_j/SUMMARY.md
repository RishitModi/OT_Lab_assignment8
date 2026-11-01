# Track J: Software Engineering Optimization – Experimental Summary

## Environment & Platform Configuration
- **Python Version**: 3.12.10
- **NumPy Version**: 2.5.4
- **SciPy Version**: 1.18.1
- **Platform / OS**: Windows-11-10.0.26200-SP0
- **Quick Execution Flag**: False
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
- **Total Tests in Universe**: 158
- **Baseline Median Full-Suite Runtime**: 6.1621 s
- **Passing Tests**: 158/158
- **Per-Test Cost (min / median / max)**: 0.00083 s / 0.03013 s / 0.32686 s
- **Top 10 Slowest Tests Runtime Share**: 23.98%

### Top 15 Functions by Cumulative Execution Time (cProfile)
| function | file_line | ncalls | tottime | cumtime |
| --- | --- | --- | --- | --- |
| run_ir | cc_ir.py:296 | 948 | 1.882 | 2.828 |
| optimize_all | cc_passes.py:500 | 158 | 0.0006639 | 2.36 |
| optimize | cc_passes.py:469 | 158 | 0.0192 | 2.36 |
| dce | cc_passes.py:361 | 550 | 0.2361 | 2.2 |
| live_after_each_instruction | cc_ir.py:243 | 1138 | 0.2881 | 1.792 |
| build_cfg | cc_ir.py:111 | 2788 | 0.3934 | 1.64 |
| compute_local_def_use | cc_ir.py:98 | 71980 | 0.465 | 1.374 |
| get_def_use | cc_ir.py:54 | 342132 | 0.7912 | 1.042 |
| run_machine | cc_vm.py:161 | 158 | 0.4635 | 0.916 |
| const_fold_prop | cc_passes.py:55 | 942 | 0.1651 | 0.8832 |
| compute_liveness | cc_ir.py:185 | 1296 | 0.2146 | 0.662 |
| compile_to_ir | cc_lang.py:530 | 158 | 0.005754 | 0.5464 |
| <built-in method builtins.isinstance> | ~:0 | 2185790 | 0.5376 | 0.5431 |
| cse | cc_passes.py:251 | 550 | 0.1196 | 0.5223 |
| build_live_ranges | cc_regalloc.py:67 | 158 | 0.1706 | 0.4921 |

### Code Coverage Breakdown
| file | executable_lines | covered_lines | line_coverage_pct | covered_arcs |
| --- | --- | --- | --- | --- |
| cc_lang.py | 391 | 236 | 60.36 | 254 |
| cc_ir.py | 256 | 206 | 80.47 | 260 |
| cc_passes.py | 299 | 235 | 78.6 | 303 |
| cc_regalloc.py | 233 | 89 | 38.2 | 125 |
| cc_vm.py | 181 | 139 | 76.8 | 163 |
| TOTAL | 1360 | 905 | 66.54 | 1105 |

- Output Figure: `j0_test_cost_distribution.png`

## Verification Section
### Failed Experiment Exceptions
#### Experiment `INTERRUPTED`
```python
KeyboardInterrupt received.
```