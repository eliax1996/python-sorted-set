"""Statistical tests for the FeistelPermuter's mixing quality."""

from feistel import FeistelPermuter


def test_permutation_bijection() -> None:
    """Every output appears exactly once across all inputs (it's a permutation)."""
    permuter = FeistelPermuter(seed=42, rounds=4, bits=16)
    n = 1 << 16
    seen = [0] * n

    for x in range(n):
        y = permuter.random_index(x)
        seen[y] += 1

    # every slot should be hit exactly once
    assert all(count == 1 for count in seen), "Not a permutation!"


def test_no_fixed_points() -> None:
    """Fewer than 1% of inputs should map to themselves (random permutation)."""
    permuter = FeistelPermuter(seed=42, rounds=4, bits=16)
    n = 1 << 16
    fixed = sum(1 for x in range(n) if permuter.random_index(x) == x)

    # expected fixed points for random permutation ≈ 1, allow some slack
    assert fixed < n // 100, f"Too many fixed points: {fixed}/{n}"


def test_avalanche_single_bit() -> None:
    """Flipping one input bit should flip ~50% of output bits."""
    permuter = FeistelPermuter(seed=42, rounds=4, bits=16)
    n = 1 << 16
    total_flipped = 0
    trials = 0

    for x in range(0, n, 137):  # sample every 137th for speed
        y1 = permuter.random_index(x)
        for bit in range(16):
            y2 = permuter.random_index(x ^ (1 << bit))
            diff = y1 ^ y2
            total_flipped += diff.bit_count()
            trials += 1

    avg_flipped = total_flipped / trials
    assert 6 <= avg_flipped <= 10, f"Expected ~8 flipped bits, got {avg_flipped:.2f}"


def test_avalanche_neighbour() -> None:
    """Consecutive inputs should produce wildly different outputs."""
    permuter = FeistelPermuter(seed=42, rounds=4, bits=16)
    n = 1 << 16
    total_flipped = 0
    trials = 0

    for x in range(0, n - 1, 137):
        y1 = permuter.random_index(x)
        y2 = permuter.random_index(x + 1)
        diff = y1 ^ y2
        total_flipped += diff.bit_count()
        trials += 1

    avg_flipped = total_flipped / trials
    assert 6 <= avg_flipped <= 10, f"Expected ~8 flipped bits, got {avg_flipped:.2f}"
