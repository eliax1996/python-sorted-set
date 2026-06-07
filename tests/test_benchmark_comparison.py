"""Comparison benchmark: treap vs stdlib vs sortedcontainers."""

import bisect
import random
from time import perf_counter

from sortedcontainers import SortedSet

from treap import Set as TreapSet


def bench_treap(elements: list[int]) -> float:
    s: TreapSet = TreapSet()
    t0 = perf_counter()
    for x in elements:
        s.add(x)
    return perf_counter() - t0


def bench_sortedcontainers(elements: list[int]) -> float:
    s: SortedSet = SortedSet()
    t0 = perf_counter()
    for x in elements:
        s.add(x)
    return perf_counter() - t0


def bench_bisect_list(elements: list[int]) -> float:
    lst: list[int] = []
    t0 = perf_counter()
    for x in elements:
        bisect.insort(lst, x)
    return perf_counter() - t0


def bench_builtin_set_sort(elements: list[int]) -> float:
    s: set[int] = set()
    t0 = perf_counter()
    for x in elements:
        s.add(x)
    sorted(s)
    return perf_counter() - t0


def run_comparison(sizes: list[int], samples: int = 3, seed: int = 42) -> None:
    rng = random.Random(seed)
    results: list[dict] = []

    for n in sizes:
        elements = rng.sample(range(n * 10), n)

        t_treap = bench_treap(elements)
        t_sc = bench_sortedcontainers(elements)
        t_bisect = bench_bisect_list(elements)

        results.append(
            {
                "n": n,
                "treap_us": t_treap * 1_000_000,
                "sc_us": t_sc * 1_000_000,
                "bisect_us": t_bisect * 1_000_000,
                "treap_per_op_us": t_treap * 1_000_000 / n,
                "sc_per_op_us": t_sc * 1_000_000 / n,
                "bisect_per_op_us": t_bisect * 1_000_000 / n,
                "treap_vs_sc": t_treap / t_sc if t_sc > 0 else float("inf"),
                "treap_vs_bisect": t_treap / t_bisect if t_bisect > 0 else float("inf"),
            }
        )

    # Print table
    header = (
        f"{'n':>8}  {'treap (µs)':>12}  {'sc (µs)':>12}  {'bisect (µs)':>14}  "
        f"{'treap/op':>9}  {'sc/op':>9}  {'bisect/op':>11}  "
        f"{'treap/sc':>9}  {'treap/bisect':>13}"
    )
    sep = "-" * len(header)
    print("\n── Sorted Set Comparison ──\n")
    print("  sc = sortedcontainers.SortedSet\n  bisect = bisect.insort into list\n")
    print(header)
    print(sep)
    for r in results:
        print(
            f"{int(r['n']):>8}  {r['treap_us']:>10.1f}µs  "
            f"{r['sc_us']:>10.1f}µs  {r['bisect_us']:>10.1f}µs  "
            f"{r['treap_per_op_us']:>7.3f}µs  {r['sc_per_op_us']:>7.3f}µs  "
            f"{r['bisect_per_op_us']:>7.3f}µs  "
            f"{r['treap_vs_sc']:>7.1f}x  {r['treap_vs_bisect']:>10.1f}x"
        )
    print(sep)
    print("\n  treap/sc  = how many times slower treap is vs sortedcontainers")
    print("  treap/bisect = how many times slower treap is vs bisect.insort")
    print("  (< 1 means treap is faster)\n")


def test_comparison() -> None:
    sizes = [100, 1_000, 10_000, 50_000]
    run_comparison(sizes, samples=1)


def test_comparison_large() -> None:
    """Benchmark at 5M elements (treap vs sortedcontainers only — bisect is O(n²))."""
    n = 5_000_000
    rng = random.Random(42)
    elements = rng.sample(range(n * 10), n)

    s: TreapSet = TreapSet()
    t0 = perf_counter()
    for x in elements:
        s.add(x)
    t_treap = perf_counter() - t0

    s2: SortedSet = SortedSet()
    t0 = perf_counter()
    for x in elements:
        s2.add(x)
    t_sc = perf_counter() - t0

    us_treap = t_treap / n * 1_000_000
    us_sc = t_sc / n * 1_000_000
    ratio = t_treap / t_sc

    print("\n── 5M Comparison (bisect skipped — would take ~45 min) ──\n")
    print(f"{'':>20} {'total':>10} {'µs/op':>10}")
    print(f"{'sortedcontainers':>20} {t_sc:>8.3f}s {us_sc:>8.3f}µs")
    print(f"{'treap':>20} {t_treap:>8.3f}s {us_treap:>8.3f}µs")
    print(f"\ntreap is {ratio:.1f}x slower than sortedcontainers at n=5M\n")

    assert t_treap < 120.0, f"treap took {t_treap:.1f}s, expected < 120s"
    assert t_sc < 30.0, f"sortedcontainers took {t_sc:.1f}s, expected < 30s"
