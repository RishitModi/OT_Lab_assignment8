# Tool Comparison: Weighted Interval Scheduling

Side-by-side comparison of Antigravity IDE (Claude Sonnet 5.5) and GitHub Copilot on an identical coding task.

---

## Files

| File | Description |
| :--- | :--- |
| `verify.py` | The checker script: runs 504 correctness cases against a brute-force reference and a 100 000-job speed test |
| `antigravity/solution.py` | Solution produced by Antigravity IDE with Claude Sonnet 5.5 |
| `copilot/solution.py` | Solution produced by GitHub Copilot (model not recorded) |

---

## Task Text (given identically to both tools)

> Write a Python module solution.py with a function max_weight_schedule(jobs). jobs is a list of (start, end, weight) tuples of integers with start < end and weight > 0. Two jobs conflict if their open intervals overlap, i.e. a.start < b.end and b.start < a.end (a job that ends exactly when another starts does not conflict). Return (best_total_weight, chosen_indices) where chosen_indices is a sorted list of indices into the input list. Requirements: O(n log n) time using dynamic programming and binary search; do not mutate the input; handle an empty list (return (0, [])) and duplicate jobs; standard library only.

The Antigravity IDE additionally received the instruction: *Do NOT run any command, script, test, python, pip, git or shell command.*

---

## Running the Verifier

```
python tool_comparison/verify.py tool_comparison/<tool>/solution.py
```

Replace `<tool>` with `antigravity` or `copilot`.

---

## Notes

`verify.py` was written in a Claude chat (claude.ai) and **not** in the IDE.

