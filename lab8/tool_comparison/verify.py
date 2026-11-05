"""Usage: python tool_comparison/verify.py path/to/solution.py"""
import importlib.util, itertools, random, sys, time

def load(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def conflict(a, b):
    return a[0] < b[1] and b[0] < a[1]

def brute(jobs):
    best = 0
    for mask in range(1 << len(jobs)):
        ch = [i for i in range(len(jobs)) if mask >> i & 1]
        if all(not conflict(jobs[a], jobs[b]) for a, b in itertools.combinations(ch, 2)):
            best = max(best, sum(jobs[i][2] for i in ch))
    return best

def check(fn, jobs):
    original = list(jobs)
    value, chosen = fn(jobs)
    if jobs != original:
        return "input was mutated"
    if list(chosen) != sorted(set(chosen)) or any(not 0 <= i < len(jobs) for i in chosen):
        return "indices not sorted, distinct and valid"
    if any(conflict(jobs[a], jobs[b]) for a, b in itertools.combinations(chosen, 2)):
        return "conflicting jobs chosen"
    if sum(jobs[i][2] for i in chosen) != value:
        return "reported weight != sum of chosen weights"
    opt = brute(jobs)
    if value != opt:
        return f"not optimal: got {value}, optimum {opt}"
    return None

if __name__ == "__main__":
    fn = load(sys.argv[1]).max_weight_schedule
    rng = random.Random(0)
    fails, first = 0, None
    cases = [[], [(0, 1, 5)], [(0, 2, 3), (0, 2, 3)], [(0, 2, 4), (2, 4, 4), (1, 3, 9)]]
    for _ in range(500):
        n = rng.randint(0, 10)
        cases.append([(s := rng.randint(0, 20), s + rng.randint(1, 8), rng.randint(1, 20)) for _ in range(n)])
    for jobs in cases:
        try:
            msg = check(fn, list(jobs))
        except Exception as e:
            msg = f"exception {type(e).__name__}: {e}"
        if msg:
            fails += 1
            first = first or (msg, jobs)
    print(f"correctness: {len(cases) - fails}/{len(cases)} passed")
    if first:
        print("first failure:", first)
    big = [(s := rng.randint(0, 10**6), s + rng.randint(1, 1000), rng.randint(1, 100)) for _ in range(100000)]
    t = time.perf_counter(); fn(big)
    print(f"speed: 100000 jobs in {time.perf_counter() - t:.2f} s")