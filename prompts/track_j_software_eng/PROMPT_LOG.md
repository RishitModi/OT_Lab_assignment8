# Prompt Log: Track J: Software Engineering Optimization

## Entry 1
- Date: 01/11/26
- Tool and model version: 
- Original prompt: 
STRICT RULES FOR THIS TASK: Do NOT run any command, script, test, python, pip, git or shell command. Do NOT create scratch or test scripts anywhere. Do NOT install anything. Edit only files inside tracks/track_j_software_eng/ (including tests/), FAILURE_LOG.md and README.md (repository root), changing only what is described. Do not modify any file of tracks/track_f_compiler.

Problem: in the full run (158 tests) experiment J1 never finishes in kill_matrix (sj_suite.py): it runs every test under every mutant through all pipeline variants, and mutated programs can loop until the very large step limit of run_ir. Required changes:

A. sj_suite.py:
 (1) reference steps: compute once per test the dynamic step count of the unmutated unoptimised run (run_ir returns it) and cache it in a dict keyed by test name (also return it from the cost measurement if that is where it is computed).
 (2) While a mutant is active, every run_ir call (and the machine-code VM call, if any) must use step_limit = max(5000, 20 * reference_steps[test]). If the step limit is exceeded under a mutant, that counts as the test failing (the mutant is killed), unless the unmutated reference run itself exceeded its limit. Make sure the exception class used for the step limit is caught inside run_test and never propagates.
 (3) A mutant of pass P only runs the pipeline variants that contain P: the variant "P alone" and the variant "all passes"; skip the other single-pass variants and skip the register-machine variant under mutants (the unmutated suite still runs every variant). A mutant is killed by a test if either executed variant disagrees with the reference.
 (4) kill_matrix gets a deadline argument (a time.time() value) and a progress callback: after each mutant print "mutant i/N <name> done, killed by k tests, elapsed s"; check the deadline between mutants and between tests; if the deadline is exceeded stop and return the partial matrix together with a list of completed mutants and the flag partial = True.
 (5) Check that mutant installation and restoration happen in a try/finally and that a mutant never remains installed after kill_matrix returns (also after a KeyboardInterrupt).
B. run_all.py: add --max-minutes (default 10; quick mode default 3) which defines one global deadline used by kill_matrix; J1 and J3 must work with a partial kill matrix: mutation scores and the "not killed" tables are computed only over the completed mutants and the SUMMARY states "partial: k of N mutants completed" (otherwise "complete: N of N mutants"). Save the kill matrix as results/track_j/kill_matrix.csv immediately after it is computed. Print progress lines for the coverage collection and the minimisation steps. Keep everything else unchanged, including that SUMMARY.md is written in a finally block.
C. tests/test_selection.py: add (write only) a test that a mutant whose effect creates an infinite loop is reported as killed within the step budget and that the original pass is restored afterwards (use a tiny hand-made program and a hand-made mutated pass that turns "i = i + 1" into "i = i + 0" in a while loop).
D. FAILURE_LOG.md (repository root): keep every existing row exactly as it is and append one row with the next case number (the last existing case number plus 1): "J | The generated mutation-testing code ran every test under every mutant through all pipeline variants with a very large step limit; in the full run (158 tests, 20 mutants) the kill-matrix computation did not finish and was interrupted by the user (traceback inside the interpreter loop executing a mutated program); the quick run with 38 tests had finished. | Interrupting the run and reading the traceback location. | Step limit proportional to the reference run, only the variants a mutant can affect, a time guard with partial results and progress output. | Test-time cost must be estimated before scaling up: tests x mutants x variants x worst-case run length."
E. README.md (repository root), "AI Tools Register" table only: add or extend the single row for Antigravity IDE / Claude Sonnet 5.5 so that Tracks includes "J", Dates includes 2026-11-01, and Kind of work includes "debugging". Do not create duplicate rows and do not change anything else in README.md.
- AI response / relevant excerpt: 
- Revised prompt (if any): 
- Resulting commit link: 
- Verification note (done by the student): 
- Chat export / screenshot filename: 
