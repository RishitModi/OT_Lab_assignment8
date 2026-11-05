"""Test suite orchestration, coverage tracing via sys.settrace, and fault injection."""

from __future__ import annotations

import dis
from pathlib import Path
import sys
import time
import types
from typing import Any, Callable, NamedTuple, Sequence

# Ensure repository root, track F, and current folder are on sys.path
_TRACK_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
_TRACK_F = _REPO_ROOT / "tracks" / "track_f_compiler"

for _p in [str(_REPO_ROOT), str(_TRACK_ROOT), str(_TRACK_F)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cc_fuzz
import cc_ir
import cc_lang
import cc_passes
import cc_programs
import cc_regalloc
import cc_vm

from sj_util import median

# Code under test files (strictly the 5 core compiler modules)
CUT_FILENAMES: list[str] = [
    "cc_lang.py",
    "cc_ir.py",
    "cc_passes.py",
    "cc_regalloc.py",
    "cc_vm.py",
]
CUT_PATHS: list[Path] = [_TRACK_F / name for name in CUT_FILENAMES]


def count_lines() -> dict[str, Any]:
    """Count non-blank, non-comment lines of code under test and all compiler files.

    Returns
    -------
    dict[str, Any]
        Dictionary with per-file counts, code-under-test total, and full compiler total.
    """
    file_counts: dict[str, int] = {}
    for path in CUT_PATHS:
        count = 0
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        count += 1
        file_counts[path.name] = count

    cut_total = sum(file_counts.values())

    # Count all non-test .py files in tracks/track_f_compiler
    compiler_total = 0
    compiler_files: list[Path] = sorted(
        [p for p in _TRACK_F.glob("*.py") if not p.name.startswith("test_")]
    )
    for p in compiler_files:
        c = 0
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    c += 1
        compiler_total += c

    return {
        "file_counts": file_counts,
        "cut_total": cut_total,
        "compiler_total": compiler_total,
    }


def get_test_universe(n_fuzz: int = 150) -> list[tuple[str, str]]:
    """Build the test universe combining hand-crafted programs and fuzz programs.

    Parameters
    ----------
    n_fuzz : int
        Number of fuzz test programs to generate (seed 0..n_fuzz-1).

    Returns
    -------
    list[tuple[str, str]]
        List of (test_name, source_text) pairs.
    """
    tests: list[tuple[str, str]] = []

    # 1. Benchmark programs from cc_programs
    for name, src in cc_programs.PROGRAMS.items():
        tests.append((name, src))

    # 2. Fuzz programs
    cap = n_fuzz + 5
    steps = 0
    for seed in range(n_fuzz):
        steps += 1
        if steps > cap:
            break
        src = cc_fuzz.generate(seed)
        tests.append((f"fuzz_{seed}", src))

    return tests


REFERENCE_STEPS: dict[str, int] = {}
_ACTIVE_MUTANT_PASS: str | None = None

_PRISTINE_PASS_REGISTRY: dict[str, Any] = dict(cc_passes.PASS_REGISTRY)
_PRISTINE_ALL_PASSES: list[Any] = list(cc_passes.ALL_PASSES)
_PRISTINE_PASS_ATTRS: dict[str, Any] = {
    name: getattr(cc_passes, name)
    for name in ("const_fold_prop", "algebraic_strength_reduction", "cse", "dce")
    if hasattr(cc_passes, name)
}


def restore_pristine_passes() -> None:
    """Ensure all compiler optimization passes are restored to unmutated state."""
    global _ACTIVE_MUTANT_PASS
    _ACTIVE_MUTANT_PASS = None
    cc_passes.PASS_REGISTRY.clear()
    cc_passes.PASS_REGISTRY.update(_PRISTINE_PASS_REGISTRY)
    cc_passes.ALL_PASSES = list(_PRISTINE_ALL_PASSES)
    for name, fn in _PRISTINE_PASS_ATTRS.items():
        setattr(cc_passes, name, fn)


def get_reference_steps(test_name: str, source: str) -> int:
    """Return and cache dynamic instruction count of unmutated unoptimised run."""
    if test_name and test_name in REFERENCE_STEPS:
        return REFERENCE_STEPS[test_name]
    try:
        base_ir = cc_lang.compile_to_ir(source)
        _, steps, _ = cc_ir.run_ir(base_ir, step_limit=2_000_000)
    except Exception:
        steps = 0
    if test_name:
        REFERENCE_STEPS[test_name] = steps
    return steps


def run_test(
    source: str,
    mutant_pass: str | None = None,
    test_name: str | None = None,
    ref_steps: int | None = None,
) -> bool:
    """Execute compilation and VM pipeline and verify output equivalence.

    Reuses evaluation sequence: source -> unoptimised IR reference, each single pass,
    all passes, and k=3 register machine. While a mutant is active, evaluates only
    the mutant pass alone and all passes using step_limit = max(5000, 20 * ref_steps).

    Parameters
    ----------
    source : str
        Toy language program source code.
    mutant_pass : str | None, default=None
        Name of mutated pass if a mutant is active (defaults to _ACTIVE_MUTANT_PASS).
    test_name : str | None, default=None
        Optional test identifier to query cached reference steps.
    ref_steps : int | None, default=None
        Dynamic step count of unoptimised reference execution.

    Returns
    -------
    bool
        True if all executed variants match reference; False otherwise. Never raises.
    """
    ref_step_limit = 2_000_000
    try:
        base_ir = cc_lang.compile_to_ir(source)
    except Exception as e:
        base_exc = type(e)
        base_out: list[int] = []
        base_steps = 0
        ref_exceeded = False
    else:
        base_exc = None
        base_out = []
        base_steps = 0
        ref_exceeded = False
        try:
            base_out, base_steps, _ = cc_ir.run_ir(base_ir, step_limit=ref_step_limit)
        except cc_ir.StepLimitExceeded:
            base_exc = cc_ir.StepLimitExceeded
            ref_exceeded = True
        except Exception as e:
            base_exc = type(e)

    # Cache reference steps
    if test_name and test_name not in REFERENCE_STEPS and not ref_exceeded:
        REFERENCE_STEPS[test_name] = base_steps

    active_pname = mutant_pass if mutant_pass is not None else _ACTIVE_MUTANT_PASS

    if active_pname is not None:
        # A mutant is active:
        # Step limit = max(5000, 20 * reference_steps[test])
        effective_steps = ref_steps
        if effective_steps is None:
            if test_name and test_name in REFERENCE_STEPS:
                effective_steps = REFERENCE_STEPS[test_name]
            else:
                effective_steps = base_steps
        step_limit = max(5000, 20 * effective_steps)

        # Variant 1: "P alone"
        pfn = cc_passes.PASS_REGISTRY.get(active_pname, getattr(cc_passes, active_pname, None))
        if pfn is not None:
            try:
                p_ir = pfn(base_ir)
                p_out, _, _ = cc_ir.run_ir(p_ir, step_limit=step_limit)
                p_exc = None
            except cc_ir.StepLimitExceeded:
                if not ref_exceeded:
                    return False  # Exceeded step limit under mutant -> killed
                p_out = []
                p_exc = cc_ir.StepLimitExceeded
            except Exception as e:
                p_out = []
                p_exc = type(e)

            if p_exc != base_exc:
                return False
            if base_exc is None and p_out != base_out:
                return False

        # Variant 2: "all passes"
        try:
            opt_ir, _ = cc_passes.optimize_all(base_ir)
            opt_out, _, _ = cc_ir.run_ir(opt_ir, step_limit=step_limit)
            opt_exc = None
        except cc_ir.StepLimitExceeded:
            if not ref_exceeded:
                return False  # Exceeded step limit under mutant -> killed
            opt_out = []
            opt_exc = cc_ir.StepLimitExceeded
        except Exception as e:
            opt_ir = base_ir
            opt_out = []
            opt_exc = type(e)

        if opt_exc != base_exc:
            return False
        if base_exc is None and opt_out != base_out:
            return False

        return True

    # Unmutated run: run full pipeline across all variants
    # 1. Test each individual pass
    single_pass_names = [
        "const_fold_prop",
        "algebraic_strength_reduction",
        "cse",
        "dce",
    ]
    for pname in single_pass_names:
        pfn = cc_passes.PASS_REGISTRY.get(pname, getattr(cc_passes, pname))
        try:
            p_ir = pfn(base_ir)
            p_out, _, _ = cc_ir.run_ir(p_ir)
            p_exc = None
        except cc_ir.StepLimitExceeded:
            p_out = []
            p_exc = cc_ir.StepLimitExceeded
        except Exception as e:
            p_out = []
            p_exc = type(e)

        if p_exc != base_exc:
            return False
        if base_exc is None and p_out != base_out:
            return False

    # 2. Test "all" pass pipeline
    try:
        opt_ir, _ = cc_passes.optimize_all(base_ir)
        opt_out, _, _ = cc_ir.run_ir(opt_ir)
        opt_exc = None
    except cc_ir.StepLimitExceeded:
        opt_ir = base_ir
        opt_out = []
        opt_exc = cc_ir.StepLimitExceeded
    except Exception as e:
        opt_ir = base_ir
        opt_out = []
        opt_exc = type(e)

    if opt_exc != base_exc:
        return False
    if base_exc is None and opt_out != base_out:
        return False

    # 3. Test Register Machine code generation with ILP at k=3
    try:
        ranges = cc_regalloc.build_live_ranges(opt_ir)
        kept, spilled, _, _ = cc_regalloc.allocate_ilp(ranges, k=3)
        alloc = cc_regalloc.assign_physical_registers(ranges, kept, spilled, k=3)
        code = cc_vm.generate_code(opt_ir, alloc, k=3)
        m_out, _, _, _, _, _ = cc_vm.run_machine(code)
        m_exc = None
    except cc_ir.StepLimitExceeded:
        m_out = []
        m_exc = cc_ir.StepLimitExceeded
    except Exception as e:
        m_out = []
        m_exc = type(e)

    if m_exc != base_exc:
        return False
    if base_exc is None and m_out != base_out:
        return False

    return True


def executable_lines(file_path: str | Path) -> set[int]:
    """Find all executable line numbers in a Python file via dis.findlinestarts across nested code objects.

    Parameters
    ----------
    file_path : str | Path
        Path to Python source file.

    Returns
    -------
    set[int]
        Set of executable source line numbers.
    """
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as f:
        source = f.read()

    root_co = compile(source, str(path.resolve()), "exec")
    lines: set[int] = set()

    stack: list[types.CodeType] = [root_co]
    cap = 10000
    steps = 0
    while stack and steps < cap:
        steps += 1
        co = stack.pop()
        for _, lineno in dis.findlinestarts(co):
            lines.add(lineno)
        for const in co.co_consts:
            if isinstance(const, types.CodeType):
                stack.append(const)

    return lines


def collect_coverage(
    fn: Callable[[], Any],
    cut_paths: Sequence[Path] | None = None,
) -> tuple[set[tuple[int, int]], set[tuple[int, int, int]]]:
    """Collect statement (line) and branch (arc) coverage of code under test using sys.settrace.

    Parameters
    ----------
    fn : Callable[[], Any]
        Zero-argument function to execute under trace profiling.
    cut_paths : Sequence[Path] | None
        List of code-under-test paths (default CUT_PATHS).

    Returns
    -------
    tuple[set[tuple[int, int]], set[tuple[int, int, int]]]
        (lines covered as (file_index, line), arcs covered as (file_index, prev_line, line)).
    """
    targets = CUT_PATHS if cut_paths is None else list(cut_paths)
    resolved_map: dict[Path, int] = {p.resolve(): idx for idx, p in enumerate(targets)}

    covered_lines: set[tuple[int, int]] = set()
    covered_arcs: set[tuple[int, int, int]] = set()

    def global_trace(frame: types.FrameType, event: str, arg: Any) -> Any:
        try:
            fname = Path(frame.f_code.co_filename).resolve()
            f_idx = resolved_map.get(fname)
        except Exception:
            f_idx = None

        if f_idx is None:
            return None

        prev_line = -1

        def local_trace(lframe: types.FrameType, levent: str, larg: Any) -> Any:
            nonlocal prev_line
            if levent == "line":
                lineno = lframe.f_lineno
                covered_lines.add((f_idx, lineno))
                covered_arcs.add((f_idx, prev_line, lineno))
                prev_line = lineno
            elif levent == "call":
                prev_line = -1
            elif levent == "return":
                prev_line = -1
            return local_trace

        return local_trace

    old_trace = sys.gettrace()
    try:
        sys.settrace(global_trace)
        fn()
    finally:
        sys.settrace(None)

    return covered_lines, covered_arcs


def measure_test_cost(
    source: str,
    runs: int = 5,
    test_name: str | None = None,
    return_steps: bool = False,
) -> float | tuple[float, int]:
    """Measure untraced wall-clock runtime of run_test as the median of multiple runs.

    Parameters
    ----------
    source : str
        Program source code under test.
    runs : int
        Number of untraced executions to sample.
    test_name : str | None, default=None
        Optional name of the test to cache reference steps.
    return_steps : bool, default=False
        If True, returns (median_runtime, reference_steps).

    Returns
    -------
    float | tuple[float, int]
        Median execution duration in seconds (or tuple with reference steps).
    """
    times: list[float] = []
    cap = runs + 2
    steps = 0
    for _ in range(runs):
        steps += 1
        if steps > cap:
            break
        t0 = time.perf_counter()
        run_test(source, test_name=test_name)
        t1 = time.perf_counter()
        times.append(t1 - t0)

    med_time = median(times)
    ref_s = get_reference_steps(test_name or "", source)
    if return_steps:
        return med_time, ref_s
    return med_time


# ---------------------------------------------------------------------------
# Fault Injection / Mutation Operators
# ---------------------------------------------------------------------------

BINARY_OPS = {
    "add",
    "sub",
    "mul",
    "div",
    "mod",
    "shl",
    "shr",
    "and",
    "lt",
    "le",
    "gt",
    "ge",
    "eq",
    "ne",
}


def apply_mutation_op(
    instructions: list[cc_lang.Instruction],
    operator: str,
) -> list[cc_lang.Instruction]:
    """Apply a mutation operator to the instruction list.

    Operators:
    M1: swap first add with sub (or sub with add)
    M2: turn first mul into add
    M3: add 1 to the first integer constant operand of a binary instruction
    M4: delete the first mov instruction
    M5: turn first lt into le (or le into lt)

    If no site is found, leaves instructions unchanged.

    Parameters
    ----------
    instructions : list[Instruction]
        Input three-address instruction list.
    operator : str
        Operator identifier ("M1".."M5").

    Returns
    -------
    list[Instruction]
        Mutated instruction list.
    """
    mutated = list(instructions)
    cap = len(mutated) + 5
    steps = 0

    if operator == "M1":
        for i, (op, dst, a, b) in enumerate(mutated):
            steps += 1
            if steps > cap:
                break
            if op == "add":
                mutated[i] = ("sub", dst, a, b)
                break
            elif op == "sub":
                mutated[i] = ("add", dst, a, b)
                break

    elif operator == "M2":
        for i, (op, dst, a, b) in enumerate(mutated):
            steps += 1
            if steps > cap:
                break
            if op == "mul":
                mutated[i] = ("add", dst, a, b)
                break

    elif operator == "M3":
        for i, (op, dst, a, b) in enumerate(mutated):
            steps += 1
            if steps > cap:
                break
            if op in BINARY_OPS:
                if isinstance(a, int) and not isinstance(a, bool):
                    mutated[i] = (op, dst, a + 1, b)
                    break
                elif isinstance(b, int) and not isinstance(b, bool):
                    mutated[i] = (op, dst, a, b + 1)
                    break

    elif operator == "M4":
        for i, (op, dst, a, b) in enumerate(mutated):
            steps += 1
            if steps > cap:
                break
            if op == "mov":
                del mutated[i]
                break

    elif operator == "M5":
        for i, (op, dst, a, b) in enumerate(mutated):
            steps += 1
            if steps > cap:
                break
            if op == "lt":
                mutated[i] = ("le", dst, a, b)
                break
            elif op == "le":
                mutated[i] = ("lt", dst, a, b)
                break

    return mutated


class ActiveMutant:
    """Context manager replacing a pass function with a mutated version across registry and module."""

    def __init__(self, pass_name: str, operator: str) -> None:
        self.pass_name = pass_name
        self.operator = operator
        self.orig_fn = cc_passes.PASS_REGISTRY[pass_name]
        self.orig_all_passes = list(cc_passes.ALL_PASSES)
        self.orig_attr = getattr(cc_passes, pass_name)
        self.mutated_fn: Any = None

    def __enter__(self) -> ActiveMutant:
        global _ACTIVE_MUTANT_PASS
        _ACTIVE_MUTANT_PASS = self.pass_name
        orig = self.orig_fn
        op = self.operator

        def mutated_pass(ir: list[cc_lang.Instruction]) -> list[cc_lang.Instruction]:
            res = orig(ir)
            return apply_mutation_op(res, op)

        mutated_pass.__name__ = orig.__name__
        self.mutated_fn = mutated_pass

        # Update registry, pipeline, and module attribute
        cc_passes.PASS_REGISTRY[self.pass_name] = mutated_pass
        cc_passes.ALL_PASSES = [
            mutated_pass if p is orig else p for p in self.orig_all_passes
        ]
        setattr(cc_passes, self.pass_name, mutated_pass)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        global _ACTIVE_MUTANT_PASS
        try:
            # Restore original functions unconditionally
            cc_passes.PASS_REGISTRY[self.pass_name] = self.orig_fn
            cc_passes.ALL_PASSES = list(self.orig_all_passes)
            setattr(cc_passes, self.pass_name, self.orig_attr)
        finally:
            _ACTIVE_MUTANT_PASS = None


MUTANT_PASSES: list[str] = [
    "const_fold_prop",
    "algebraic_strength_reduction",
    "cse",
    "dce",
]
MUTANT_OPERATORS: list[str] = ["M1", "M2", "M3", "M4", "M5"]


def get_all_mutants() -> list[tuple[str, str]]:
    """Return all defined (pass_name, operator) mutant pairs."""
    return [
        (pname, op)
        for pname in MUTANT_PASSES
        for op in MUTANT_OPERATORS
    ]


class KillMatrixResult(NamedTuple):
    """Result returned by kill_matrix containing kill matrix and completion status."""
    matrix: dict[tuple[str, str], dict[str, bool]]
    completed_mutants: list[tuple[str, str]]
    partial: bool


def kill_matrix(
    tests: Sequence[tuple[str, str]],
    mutants: Sequence[tuple[str, str]],
    deadline: float | None = None,
    progress_callback: Callable[[int, int, str, int, float], None] | None = None,
) -> KillMatrixResult:
    """Compute test kill matrix K[m][t] = True when test t does not pass with mutant m active.

    Parameters
    ----------
    tests : Sequence[tuple[str, str]]
        List of (test_name, source) tests.
    mutants : Sequence[tuple[str, str]]
        List of (pass_name, operator) mutants.
    deadline : float | None, default=None
        Wall-clock deadline timestamp (via time.time()). If exceeded, execution halts gracefully.
    progress_callback : Callable | None, default=None
        Optional callback called after each mutant: fn(i, total, mutant_name, killed_count, elapsed_s).

    Returns
    -------
    KillMatrixResult
        Named tuple containing (matrix, completed_mutants, partial).
    """
    matrix: dict[tuple[str, str], dict[str, bool]] = {}
    completed_mutants: list[tuple[str, str]] = []
    is_partial = False
    t_start = time.time()
    total_mutants = len(mutants)

    # Pre-cache reference steps for all tests if not already cached
    for t_name, t_src in tests:
        if t_name not in REFERENCE_STEPS:
            get_reference_steps(t_name, t_src)

    try:
        m_cap = total_mutants + 5
        m_steps = 0
        for idx, m in enumerate(mutants, 1):
            m_steps += 1
            if m_steps > m_cap:
                break

            # Check deadline between mutants
            if deadline is not None and time.time() >= deadline:
                is_partial = True
                break

            pname, op = m
            m_name = f"{pname}:{op}"
            row: dict[str, bool] = {}
            interrupted = False

            with ActiveMutant(pname, op):
                t_cap = len(tests) + 5
                t_steps = 0
                for t_name, t_src in tests:
                    t_steps += 1
                    if t_steps > t_cap:
                        break

                    # Check deadline between tests
                    if deadline is not None and time.time() >= deadline:
                        interrupted = True
                        is_partial = True
                        break

                    ref_s = REFERENCE_STEPS.get(t_name)
                    passed = run_test(
                        t_src,
                        mutant_pass=pname,
                        test_name=t_name,
                        ref_steps=ref_s,
                    )
                    row[t_name] = not passed

            if interrupted:
                break

            matrix[m] = row
            completed_mutants.append(m)
            k = sum(1 for killed in row.values() if killed)
            elapsed = time.time() - t_start

            print(f"mutant {idx}/{total_mutants} {m_name} done, killed by {k} tests, elapsed {elapsed:.1f}s")
            if progress_callback is not None:
                try:
                    progress_callback(idx, total_mutants, m_name, k, elapsed)
                except Exception:
                    pass

    finally:
        # Guarantee mutant restoration unconditionally
        restore_pristine_passes()

    return KillMatrixResult(
        matrix=matrix,
        completed_mutants=completed_mutants,
        partial=is_partial,
    )

