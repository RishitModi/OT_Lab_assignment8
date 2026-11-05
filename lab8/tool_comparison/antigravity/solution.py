"""
Weighted Interval Scheduling problem solved via Dynamic Programming and Binary Search.
"""

from bisect import bisect_right
from typing import List, Tuple


def max_weight_schedule(jobs: List[Tuple[int, int, int]]) -> Tuple[int, List[int]]:
    """
    Finds the maximum weight subset of mutually non-overlapping jobs.

    Parameters:
        jobs: List of (start, end, weight) tuples of integers with start < end
              and weight > 0. Two jobs conflict if their open intervals overlap,
              i.e. a.start < b.end and b.start < a.end. A job that ends exactly
              when another starts does not conflict.

    Returns:
        (best_total_weight, chosen_indices):
            best_total_weight: Maximum total weight of compatible jobs.
            chosen_indices: Sorted list of 0-based indices into the input list `jobs`.

    Complexity:
        Time: O(n log n) where n is the number of jobs.
        Space: O(n) auxiliary space.
    """
    if not jobs:
        return (0, [])

    n = len(jobs)

    # Store (start, end, weight, original_index) without mutating the input list
    indexed_jobs = sorted(
        ((job[0], job[1], job[2], idx) for idx, job in enumerate(jobs)),
        key=lambda item: item[1],
    )

    # Sorted list of end times for binary search
    end_times = [item[1] for item in indexed_jobs]

    # dp[i] stores the optimal weight considering a subset of the first i sorted jobs (1-indexed)
    dp = [0] * (n + 1)
    parent = [0] * (n + 1)
    took = [False] * (n + 1)

    for i in range(1, n + 1):
        start, end, weight, _ = indexed_jobs[i - 1]

        # Find the latest compatible job among indexed_jobs[0 ... i - 2]
        # A previous job p is compatible if its end time <= start of current job
        p = bisect_right(end_times, start, 0, i - 1) - 1

        take_weight = weight + dp[p + 1]
        skip_weight = dp[i - 1]

        if take_weight > skip_weight:
            dp[i] = take_weight
            parent[i] = p + 1
            took[i] = True
        else:
            dp[i] = skip_weight
            parent[i] = i - 1
            took[i] = False

    best_total_weight = dp[n]

    # Backtrack to reconstruct the chosen job indices
    chosen_indices = []
    curr = n
    while curr > 0:
        if took[curr]:
            chosen_indices.append(indexed_jobs[curr - 1][3])
            curr = parent[curr]
        else:
            curr = parent[curr]

    chosen_indices.sort()
    return (best_total_weight, chosen_indices)

