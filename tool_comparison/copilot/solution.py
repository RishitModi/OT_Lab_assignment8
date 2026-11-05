"""Weighted interval scheduling using dynamic programming and binary search."""

from bisect import bisect_right


def max_weight_schedule(jobs):
    """Return the maximum weight and sorted original indices of compatible jobs."""
    if not jobs:
        return 0, []

    ordered = sorted(
        (start, end, weight, index)
        for index, (start, end, weight) in enumerate(jobs)
    )
    ordered.sort(key=lambda job: job[1])
    end_times = [job[1] for job in ordered]

    best = [0] * (len(ordered) + 1)
    took = [False] * (len(ordered) + 1)
    predecessor = [0] * (len(ordered) + 1)

    for position, (start, _, weight, _) in enumerate(ordered, start=1):
        previous = bisect_right(end_times, start, 0, position - 1)
        take_weight = best[previous] + weight

        if take_weight > best[position - 1]:
            best[position] = take_weight
            took[position] = True
            predecessor[position] = previous
        else:
            best[position] = best[position - 1]
            predecessor[position] = position - 1

    chosen = []
    position = len(ordered)
    while position:
        if took[position]:
            chosen.append(ordered[position - 1][3])
        position = predecessor[position]

    chosen.sort()
    return best[-1], chosen
