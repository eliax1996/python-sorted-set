"""Benchmark for treap.Set insertion performance.

Measures insertion time across exponentially growing set sizes to verify
O(log n) behaviour. Prints a table with:
  n  |  total (µs)  |  µs/op  |  log2(n)  |  µs/op / log2(n)

Expected: µs/op / log2(n) should be roughly constant if insertion is O(log n).
"""

import math
import random
from time import perf_counter

from treap import Set


def benchmark_insertion(
    sizes: list[int],
    samples_per_size: int = 5,
    seed: int = 42,
) -> list[dict[str, float]]:
    """Benchmark insertion of *n* elements into a treap.

    Returns a list of dicts with keys:
      n, total_us, us_per_op, ops_per_s, log2n, us_per_op_per_log2n.
    """
    rng = random.Random(seed)
    results: list[dict[str, float]] = []

    for n in sizes:
        times: list[float] = []
        for _ in range(samples_per_size):
            elements = rng.sample(range(max(n * 10, 100)), n)

            s: Set[int] = Set()
            t0 = perf_counter()
            for x in elements:
                s.add(x)
            elapsed = perf_counter() - t0
            times.append(elapsed)

        avg_total = sum(times) / len(times)
        total_us = avg_total * 1_000_000
        us_per_op = total_us / n
        ops_per_s = n / avg_total
        log2n = math.log2(n) if n > 1 else 1.0
        us_per_op_per_log2n = us_per_op / log2n if log2n > 0 else 0.0

        results.append(
            {
                "n": n,
                "total_us": total_us,
                "us_per_op": us_per_op,
                "ops_per_s": ops_per_s,
                "log2n": log2n,
                "us_per_op_per_log2n": us_per_op_per_log2n,
            }
        )

    return results


def print_benchmark_table(results: list[dict[str, float]]) -> None:
    """Print a formatted benchmark table."""
    header = (
        f"{'n':>8}  {'total (µs)':>12}  {'µs/op':>10}  "
        f"{'log2(n)':>8}  {'µs/op / log2(n)':>16}"
    )
    sep = "-" * len(header)
    lines = ["\n── Treap Insertion Benchmark ──", "", header, sep]

    for r in results:
        lines.append(
            f"{int(r['n']):>8}  {r['total_us']:>10.2f}µs  "
            f"{r['us_per_op']:>8.3f}µs  "
            f"{r['log2n']:>8.2f}  "
            f"{r['us_per_op_per_log2n']:>12.3f}µs"
        )

    lines.append(sep)
    lines.append("If µs/op / log2(n) is roughly constant → insertion is O(log n).\n")
    print("\n".join(lines))


def test_benchmark_insertion() -> None:
    """Benchmark insertion performance across multiple sizes.

    Verifies that growth is sub-linear (consistent with O(log n)).
    """
    sizes = [10, 50, 100, 500, 1_000, 5_000, 10_000, 50_000, 100_000]
    results = benchmark_insertion(sizes, samples_per_size=3)

    print_benchmark_table(results)

    # Sanity: no size should take > 10s
    for r in results:
        time_s = r["total_us"] / 1_000_000
        assert time_s < 10.0, f"n={int(r['n'])} took {time_s:.2f}s, exceeds 10s limit"

    # O(log n) check: µs/op should grow sub-linearly with n.
    # Specifically, (µs/op at n=N) / (µs/op at n=small) should be < 5x
    # for a 2000x increase in n if it's truly O(log n).
    if len(results) >= 3:
        small_us_op = results[1]["us_per_op"]  # skip n=10 (startup noise)
        large_us_op = results[-1]["us_per_op"]
        ratio = large_us_op / small_us_op if small_us_op > 0 else 1.0
        # For O(log n): going from n=50 (log2=5.6) to n=100k (log2=16.6)
        # the µs/op should increase at most ~3x. Allow 5x for noise.
        assert ratio < 5.0, (
            f"µs/op grew {ratio:.1f}x from n={int(results[1]['n'])} "
            f"(µs/op={small_us_op:.3f}) to n={int(results[-1]['n'])} "
            f"(µs/op={large_us_op:.3f}). "
            f"Expected O(log n) — at most ~3x for this range."
        )


def test_benchmark_small() -> None:
    """Quick sanity: 1000 insertions completes in reasonable time."""
    s: Set[int] = Set()
    t0 = perf_counter()
    for i in range(1000):
        s.add(i)
    elapsed = perf_counter() - t0

    assert elapsed < 2.0, f"1000 insertions took {elapsed:.2f}s, expected < 2s"
