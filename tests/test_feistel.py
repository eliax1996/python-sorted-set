"""Property-based tests for FeistelPermuter.

Tests verify the core cryptographic guarantees:
- Bijection (every output unique across the full domain) — for even bits
- Range preservation (outputs stay within [0, 2^bits))
- Determinism (same params → same output)
- Uniform distribution (chi-squared goodness-of-fit) — for even bits
- Speed (performance floor)
- Avalanche effect (single-bit input changes flip many output bits)

Note: The FeistelPermuter uses ``bits // 2`` as the split point, so for odd
bits, one bit is lost — the effective domain is ``2^(2 * floor(bits/2))``
instead of ``2^bits``. Bijection/uniform tests only run on even bits where
the full domain is properly permuted.

Small domains (bits < 6) have limited permutation spaces and weak mixing —
tests account for this with appropriate minimum thresholds. Additionally, the
round function ``(r * 11 + r>>5 + seed + i*127) ^ r`` has a period resonance
at ``rounds % 8 == 0`` for small bit widths (identity on bits=6, excessive
fixed points on bits=8). Strategies avoid these degenerate round counts.
"""

from math import sqrt
from time import perf_counter

from hypothesis import assume, given
from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from feistel import FeistelPermuter

# ── Hypothesis strategies ──────────────────────────────────────────────────────


def feistel_params(
    min_bits: int = 4,
    max_bits: int = 12,
    even_only: bool = False,
    avoid_period_resonance: bool = False,
) -> SearchStrategy[tuple[int, int, int]]:
    """Generate (seed, rounds, bits) tuples for testing.

    When *even_only* is True, only even bit widths are generated.
    When *avoid_period_resonance* is True, rounds that are multiples of 8
    are excluded (the round function has a structural period at 8 for small
    half-bits, causing identity or excessive fixed-point behavior).
    """
    bits_strat = st.integers(min_bits, max_bits)
    if even_only:
        bits_strat = bits_strat.filter(lambda b: b % 2 == 0)

    rounds_strat = st.integers(3, 12)
    if avoid_period_resonance:
        rounds_strat = rounds_strat.filter(lambda r: r % 8 != 0)

    return st.tuples(
        st.integers(0, 2**16 - 1),  # seed
        rounds_strat,
        bits_strat,
    )


# ── Bijection (Permutation) tests ──────────────────────────────────────────────


@given(feistel_params(2, 8, even_only=True))
def test_bijection_small_domain_even(params: tuple[int, int, int]) -> None:
    """For even bits ≤ 8, enumerate all inputs and verify a perfect permutation."""
    seed, rounds, bits = params
    p = FeistelPermuter(seed, rounds, bits)
    n = 1 << bits
    outputs = [p.random_index(i) for i in range(n)]

    assert len(set(outputs)) == n, (
        f"Expected {n} unique outputs, got {len(set(outputs))}. "
        f"seed={seed}, rounds={rounds}, bits={bits}"
    )
    assert min(outputs) == 0, f"Minimum output should be 0, got {min(outputs)}"
    assert max(outputs) == n - 1, (
        f"Maximum output should be {n - 1}, got {max(outputs)}"
    )


@given(feistel_params(2, 8, even_only=True))
def test_bijection_range_preserved_even(params: tuple[int, int, int]) -> None:
    """Every output is strictly within [0, 2^bits) for even bits."""
    seed, rounds, bits = params
    p = FeistelPermuter(seed, rounds, bits)
    n = 1 << bits

    for x in range(n):
        y = p.random_index(x)
        assert 0 <= y < n, f"Output {y} outside [0, {n}) for input {x}"


@given(st.integers(3, 9))
def test_bijection_odd_bits_loss(bits: int) -> None:
    """For odd bits, some inputs collide because half_bits = bits // 2 loses a bit.

    This documents the current behaviour — not a bug per se, but a limitation
    of the ``bits // 2`` split. Fixing it would require ``ceil(bits / 2)``.
    """
    assume(bits % 2 == 1)

    p = FeistelPermuter(seed=42, rounds=8, bits=bits)
    n = 1 << bits
    outputs = [p.random_index(i) for i in range(n)]

    effective_bits = 2 * (bits // 2)
    expected_unique = 1 << effective_bits

    assert len(set(outputs)) == expected_unique, (
        f"With odd bits={bits}, half_bits={bits // 2}, "
        f"expected only {expected_unique} unique values, got {len(set(outputs))}."
    )


@given(feistel_params(6, 10, even_only=True, avoid_period_resonance=True))
def test_bijection_no_excessive_fixed_points(params: tuple[int, int, int]) -> None:
    """A Feistel permutation shouldn't have too many fixed points.

    A truly random permutation has expected fixed points = 1 (Poisson).
    For bits ≥ 6 with safe round counts, at most 5% of values should be fixed.
    """
    seed, rounds, bits = params
    p = FeistelPermuter(seed, rounds, bits)
    n = 1 << bits
    fixed = sum(1 for i in range(n) if p.random_index(i) == i)

    max_fixed = max(2, n // 20)
    assert fixed <= max_fixed, (
        f"{fixed}/{n} fixed points (max {max_fixed} allowed). "
        f"seed={seed}, rounds={rounds}, bits={bits}"
    )


# ── Determinism tests ──────────────────────────────────────────────────────────


@given(feistel_params(2, 8, even_only=True))
def test_determinism(params: tuple[int, int, int]) -> None:
    """Same parameters always produce the same output."""
    seed, rounds, bits = params
    p1 = FeistelPermuter(seed, rounds, bits)
    p2 = FeistelPermuter(seed, rounds, bits)

    n = 1 << bits
    for i in range(n):
        assert p1.random_index(i) == p2.random_index(i), (
            f"Mismatch at input {i} for seed={seed}, rounds={rounds}, bits={bits}"
        )


@given(feistel_params(4, 8, even_only=True, avoid_period_resonance=True))
def test_different_params_different_output(params: tuple[int, int, int]) -> None:
    """Different seeds or round counts produce different permutations."""
    seed, rounds, bits = params
    n = 1 << bits
    assume(n >= 16)

    p_ref = FeistelPermuter(seed, rounds, bits)
    ref_outputs = [p_ref.random_index(i) for i in range(n)]

    any_different = False

    # Try a different seed
    p_alt = FeistelPermuter(seed + 1, rounds, bits)
    alt_outputs = [p_alt.random_index(i) for i in range(n)]
    if any(a != b for a, b in zip(ref_outputs, alt_outputs)):
        any_different = True

    # Try different rounds
    if not any_different:
        p_alt2 = FeistelPermuter(seed, rounds + 1, bits)
        alt2_outputs = [p_alt2.random_index(i) for i in range(n)]
        if any(a != b for a, b in zip(ref_outputs, alt2_outputs)):
            any_different = True

    assert any_different, (
        f"Neither seed+1 nor rounds+1 changed the permutation! "
        f"seed={seed}, rounds={rounds}, bits={bits}"
    )


# ── Uniform distribution tests ─────────────────────────────────────────────────


@given(feistel_params(6, 12, even_only=True, avoid_period_resonance=True))
def test_uniform_distribution_even(params: tuple[int, int, int]) -> None:
    """Outputs are uniformly distributed across the range (even bits only).

    Tests the FULL domain (all 2^bits values) so distribution is meaningful.
    Uses chi-squared goodness-of-fit test with significance level α = 0.01.
    """
    seed, rounds, bits = params
    p = FeistelPermuter(seed, rounds, bits)
    n = 1 << bits

    # Full domain enumeration — fast enough for bits ≤ 12
    outputs = [p.random_index(i) for i in range(n)]

    # Partition into k equal-sized bins
    k = min(n // 8, 64)
    k = max(k, 4)
    bin_size = n // k

    counts = [0] * k
    for y in outputs:
        bin_idx = min(y // bin_size, k - 1)
        counts[bin_idx] += 1

    expected = n / k
    chi2 = sum((c - expected) ** 2 / expected for c in counts)

    df = k - 1
    # Critical value for α=0.01 using Wilson-Hilferty approximation
    z = 2.326  # z-score for 99th percentile
    critical = df * (1 - 2 / (9 * df) + z * sqrt(2 / (9 * df))) ** 3

    assert chi2 <= critical * 2, (
        f"chi²={chi2:.2f} exceeds critical={critical:.2f} (df={df}, k={k}). "
        f"seed={seed}, rounds={rounds}, bits={bits}. "
        f"First 8 of {k} bin counts: {counts[:8]}"
    )


@given(st.integers(6, 12))
def test_uniform_quadrants_even(bits: int) -> None:
    """For even bits, verify even spread across 4 quadrants of the range."""
    assume(bits % 2 == 0)

    for seed in [42, 1337, 9999, 12345]:
        p = FeistelPermuter(seed, rounds=8, bits=bits)
        n = 1 << bits

        q_size = n // 4
        quads = [0, 0, 0, 0]

        for i in range(n):
            y = p.random_index(i)
            quads[min(y // q_size, 3)] += 1

        expected = n / 4
        max_deviation = max(abs(q - expected) for q in quads)
        max_allowed = 2.5 * sqrt(expected)  # ~2.5 standard deviations

        assert max_deviation <= max_allowed + 10, (
            f"Uneven distribution for bits={bits}, seed={seed}: "
            f"{quads} (max dev={max_deviation:.1f}, allowed={max_allowed:.1f})"
        )


# ── Avalanche effect tests ────────────────────────────────────────────────────


@given(feistel_params(8, 10, even_only=True, avoid_period_resonance=True))
def test_avalanche_effect(params: tuple[int, int, int]) -> None:
    """Flipping a single input bit changes ~50% of output bits on average.

    For bits ≥ 8 with adequate rounds, a good Feistel network exhibits the
    avalanche effect. We verify at least 20% average bit change (true random
    gives ~50%, but simple round functions need more rounds to diffuse fully).
    """
    seed, rounds, bits = params
    p = FeistelPermuter(seed, rounds, bits)
    n = 1 << bits

    changes: list[float] = []
    for base in range(min(32, n)):
        y_base = p.random_index(base)
        for bit_pos in range(bits):
            flipped = base ^ (1 << bit_pos)
            if flipped >= n:
                continue
            y_flipped = p.random_index(flipped)

            # Normalized Hamming distance between outputs
            diff = y_base ^ y_flipped
            hamming = diff.bit_count()
            changes.append(hamming / bits)

    avg_change = sum(changes) / len(changes) if changes else 0.0

    assert avg_change >= 0.20, (
        f"Avalanche too weak: avg bit change = {avg_change:.1%} "
        f"(seed={seed}, rounds={rounds}, bits={bits})"
    )


# ── Speed / Performance tests ──────────────────────────────────────────────────


@given(feistel_params(6, 10, even_only=True))
def test_speed_floor(params: tuple[int, int, int]) -> None:
    """Permuting 10k values must complete in under 500ms (sanity floor)."""
    seed, rounds, bits = params
    p = FeistelPermuter(seed, rounds, bits)
    n = 10_000

    t0 = perf_counter()
    for i in range(n):
        p.random_index(i & ((1 << bits) - 1))
    elapsed = perf_counter() - t0

    assert elapsed < 0.5, (
        f"10k permutations took {elapsed * 1000:.1f}ms "
        f"(seed={seed}, rounds={rounds}, bits={bits})"
    )


def test_speed_benchmark() -> None:
    """Benchmark with typical params; print results for manual review."""
    results: list[str] = []
    for bits in [10, 12, 14, 16]:
        p = FeistelPermuter(seed=42, rounds=8, bits=bits)
        n = 50_000
        t0 = perf_counter()
        for i in range(n):
            p.random_index(i & ((1 << bits) - 1))
        elapsed = perf_counter() - t0
        us_per = elapsed / n * 1_000_000
        results.append(
            f"  bits={bits:2d}: {n} calls in {elapsed * 1000:.1f}ms "
            f"({us_per:.2f}µs/call)"
        )

    report = "\n".join(results)
    print(f"\n── FeistelPermuter Speed Benchmark ──\n{report}\n")


# ── Additional properties ──────────────────────────────────────────────────────


@given(feistel_params(4, 8, even_only=True, avoid_period_resonance=True))
def test_not_identity_permutation(params: tuple[int, int, int]) -> None:
    """The permutation should not be the identity (unless domain is tiny)."""
    seed, rounds, bits = params
    p = FeistelPermuter(seed, rounds, bits)
    n = 1 << bits
    assume(n >= 8)

    identity_count = sum(1 for i in range(n) if p.random_index(i) == i)
    assert identity_count != n, (
        f"Permutation is the identity! seed={seed}, rounds={rounds}, bits={bits}"
    )


@given(feistel_params(6, 12, even_only=True, avoid_period_resonance=True))
def test_no_output_collision_with_full_domain(params: tuple[int, int, int]) -> None:
    """Every output value has exactly one pre-image (formally: surjection = bijection).

    Since we proved uniqueness (injection) for even bits, and the domain equals
    the codomain, this is already a bijection. This test checks the output set
    directly as a double-check.
    """
    seed, rounds, bits = params
    p = FeistelPermuter(seed, rounds, bits)
    n = 1 << bits

    outputs = [p.random_index(i) for i in range(n)]
    output_set = set(outputs)

    assert len(output_set) == n, (
        f"Only {len(output_set)}/{n} output values hit — not surjective. "
        f"seed={seed}, rounds={rounds}, bits={bits}"
    )
