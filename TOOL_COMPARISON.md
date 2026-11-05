# Tool Comparison

Side-by-side comparison of two AI tools evaluated on an identical assignment task.

| Task | Tool | Correctness | Hallucinations | Speed | Prompt iterations needed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Weighted interval scheduling, function max_weight_schedule, identical task text, checked by tool_comparison/verify.py (504 test cases against brute force plus a 100000-job speed test) | Antigravity IDE with Claude Sonnet 5.5 | 504/504 passed | not recorded | answer time not recorded; verifier speed test 0.09 s for 100000 jobs | not recorded |
| Weighted interval scheduling, function max_weight_schedule, identical task text, checked by tool_comparison/verify.py (504 test cases against brute force plus a 100000-job speed test) | GitHub Copilot (model not recorded) | 504/504 passed | not recorded | answer time not recorded; verifier speed test 0.10 s for 100000 jobs | not recorded |

## Notes

Both tools received the same task text; the IDE additionally received an instruction not to run commands; both solutions passed all 504 verifier cases; the difference between 0.09 s and 0.10 s in the speed test is a single-run difference within timer noise, so no speed advantage is claimed for either tool; values written as "not recorded" were not measured; one task and one run per tool is a small sample, so any difference between the tools is anecdotal.

## Detailed Notes & Analysis
- **Tool A Observations:** 
- **Tool B Observations:** 
- **Summary & Recommendation:** 
