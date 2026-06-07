"""Deep property-based tests for treap.Set covering treap invariants.

Tests verify:
- BST invariant: left descendants < node < right descendants for all nodes
- Heap invariant: Feistel priority of parent >= priority of children (max-heap)
- In-order traversal yields sorted elements (structural BST check)
- Membership correctness against Python's built-in set
- No phantom elements (strict containment match)
- Structural stability under duplicate additions
- Height is bounded (O(log n) expected for treaps with random priorities)
"""

from hypothesis import given
from hypothesis import strategies as st

from feistel import FeistelPermuter
from treap import Set

# Recreate the same permuter used by the treap for priority computation
PERMUTER = FeistelPermuter(seed=667, rounds=4, bits=32)
SENTINEL = -1


# ── Invariant checkers ────────────────────────────────────────────────────────


def _check_bst_invariant(treap: Set[int]) -> bool:
    """Every node's left subtree contains only smaller values, right only larger."""

    def _check(node: int, lo: int | None, hi: int | None) -> bool:
        if node == SENTINEL:
            return True
        val = treap.binary_vector[node]
        if lo is not None and val <= lo:
            return False
        if hi is not None and val >= hi:
            return False
        return _check(treap.left_children[node], lo, val) and _check(
            treap.right_children[node], val, hi
        )

    return _check(treap.root, None, None)


def _check_heap_invariant(treap: Set[int]) -> bool:
    """Every parent has priority >= children (max-heap by Feistel priority)."""

    def _check(node: int) -> bool:
        if node == SENTINEL:
            return True
        prio = PERMUTER.random_index(treap.binary_vector[node])

        left = treap.left_children[node]
        right = treap.right_children[node]

        if left != SENTINEL:
            left_prio = PERMUTER.random_index(treap.binary_vector[left])
            if prio < left_prio:
                return False
        if right != SENTINEL:
            right_prio = PERMUTER.random_index(treap.binary_vector[right])
            if prio < right_prio:
                return False

        return _check(left) and _check(right)

    return _check(treap.root)


def _check_no_duplicates_in_vector(treap: Set[int]) -> bool:
    """No duplicate values are stored in the binary vector."""
    seen: set[int] = set()
    for node in range(len(treap.binary_vector)):
        val = treap.binary_vector[node]
        if val in seen:
            return False
        seen.add(val)
    return True


def _inorder_values(treap: Set[int]) -> list[int]:
    """Return elements in in-order traversal order."""
    result: list[int] = []

    def _walk(node: int) -> None:
        if node == SENTINEL:
            return
        _walk(treap.left_children[node])
        result.append(treap.binary_vector[node])
        _walk(treap.right_children[node])

    _walk(treap.root)
    return result


def _height(treap: Set[int]) -> int:
    """Return the height of the treap (max depth from root to leaf)."""

    def _depth(node: int) -> int:
        if node == SENTINEL:
            return 0
        return 1 + max(
            _depth(treap.left_children[node]),
            _depth(treap.right_children[node]),
        )

    return _depth(treap.root) - 1 if len(treap.binary_vector) > 0 else 0


def _count_nodes(treap: Set[int]) -> int:
    """Count reachable nodes from the root (should match unique elements)."""

    def _count(node: int) -> int:
        if node == SENTINEL:
            return 0
        return (
            1 + _count(treap.left_children[node]) + _count(treap.right_children[node])
        )

    return _count(treap.root) if len(treap.binary_vector) > 0 else 0


# ── BST Invariant ─────────────────────────────────────────────────────────────


@given(st.lists(st.integers(), max_size=200))
def test_bst_invariant(elements: list[int]) -> None:
    """After adding elements, the BST ordering property holds throughout the tree."""
    s: Set[int] = Set()
    for x in elements:
        s.add(x)

    assert _check_bst_invariant(s), "BST invariant violated after sequential adds"


@given(st.lists(st.integers(), max_size=100))
def test_bst_invariant_after_repeated_adds(elements: list[int]) -> None:
    """Adding duplicate elements doesn't break the BST invariant."""
    s: Set[int] = Set()
    for x in elements:
        s.add(x)
    for x in elements:
        s.add(x)

    assert _check_bst_invariant(s), "BST invariant violated after duplicate adds"


@given(st.lists(st.integers(), max_size=200))
def test_inorder_sorted(elements: list[int]) -> None:
    """In-order traversal yields elements in strictly increasing order."""
    s: Set[int] = Set()
    for x in elements:
        s.add(x)

    ordered = _inorder_values(s)
    unique_sorted = sorted(set(elements))

    assert ordered == unique_sorted, (
        f"In-order traversal mismatch. Got {ordered}, expected {unique_sorted}"
    )


# ── Heap Invariant ────────────────────────────────────────────────────────────


@given(st.lists(st.integers(), max_size=200))
def test_heap_invariant(elements: list[int]) -> None:
    """The treap maintains a max-heap by Feistel priority: parent >= children."""
    s: Set[int] = Set()
    for x in elements:
        s.add(x)

    assert _check_heap_invariant(s), "Heap invariant (max-heap) violated"


@given(st.lists(st.integers(), max_size=100))
def test_heap_invariant_after_duplicates(elements: list[int]) -> None:
    """Duplicate adds preserve the heap invariant."""
    s: Set[int] = Set()
    for x in elements:
        s.add(x)
    for x in elements:
        s.add(x)

    assert _check_heap_invariant(s), "Heap invariant violated after duplicate adds"


# ── Both invariants simultaneously ────────────────────────────────────────────


@given(st.lists(st.integers(), max_size=200))
def test_treap_invariants_both(elements: list[int]) -> None:
    """Both BST and heap invariants hold simultaneously after any sequence of adds."""
    s: Set[int] = Set()
    for x in elements:
        s.add(x)

    assert _check_bst_invariant(s), "BST invariant violated"
    assert _check_heap_invariant(s), "Heap invariant violated"


@given(st.lists(st.integers(), max_size=100))
def test_treap_invariants_random_order(elements: list[int]) -> None:
    """Invariants hold regardless of insertion order."""
    import random

    s: Set[int] = Set()
    shuffled = list(elements)
    random.shuffle(shuffled)
    for x in shuffled:
        s.add(x)

    assert _check_bst_invariant(s), "BST invariant violated with shuffled insertion"
    assert _check_heap_invariant(s), "Heap invariant violated with shuffled insertion"


# ── Membership correctness ────────────────────────────────────────────────────


@given(st.lists(st.integers(), max_size=200))
def test_membership_matches_set(elements: list[int]) -> None:
    """__contains__ matches Python's built-in set for every probed element."""
    s: Set[int] = Set()
    py_set: set[int] = set()

    for x in elements:
        s.add(x)
        py_set.add(x)

    for probe in elements:
        assert (probe in s) == (probe in py_set), (
            f"Mismatch for probe={probe}: treap={probe in s}, set={probe in py_set}"
        )


@given(st.lists(st.integers(), max_size=200), st.integers())
def test_membership_random_probe(elements: list[int], probe: int) -> None:
    """__contains__ matches Python set for arbitrary probes."""
    s: Set[int] = Set()
    py_set: set[int] = set()

    for x in elements:
        s.add(x)
        py_set.add(x)

    assert (probe in s) == (probe in py_set)


@given(st.lists(st.integers(), max_size=200))
def test_no_phantom_elements(elements: list[int]) -> None:
    """Elements never in the set are not contained."""
    s: Set[int] = Set()

    for x in elements:
        s.add(x)

    if elements:
        min_val = min(elements)
        max_val = max(elements)
        # probe values between and beyond the range
        for offset in range(-5, 0):
            assert (min_val + offset) not in s
        for offset in range(1, 6):
            assert (max_val + offset) not in s


# ── No duplicates in vector ───────────────────────────────────────────────────


@given(st.lists(st.integers(), max_size=200))
def test_no_duplicates_stored(elements: list[int]) -> None:
    """The binary vector never contains duplicates."""
    s: Set[int] = Set()
    for x in elements:
        s.add(x)

    assert _check_no_duplicates_in_vector(s), "Duplicate values found in binary vector"


@given(st.lists(st.integers(), max_size=200))
def test_reachable_nodes_match_unique_count(elements: list[int]) -> None:
    """The number of reachable nodes equals the number of unique elements added."""
    s: Set[int] = Set()
    for x in elements:
        s.add(x)

    unique_count = len(set(elements))
    reachable = _count_nodes(s)

    assert reachable == unique_count, (
        f"Reachable nodes ({reachable}) != unique elements ({unique_count})"
    )


# ── Structural stability ──────────────────────────────────────────────────────


@given(st.lists(st.integers(), max_size=100))
def test_duplicate_adds_no_structure_change(elements: list[int]) -> None:
    """Adding already-present elements doesn't change the tree structure.

    We snapshot the tree structure after the first round of adds, then verify
    it's identical after adding the same elements again.
    """
    s: Set[int] = Set()
    for x in elements:
        s.add(x)

    # Snapshot
    snapshot_left = list(s.left_children)
    snapshot_right = list(s.right_children)
    snapshot_val = list(s.binary_vector)
    snapshot_root = s.root

    # Add again
    for x in elements:
        s.add(x)

    assert s.root == snapshot_root, "Root changed after duplicate adds"
    assert s.left_children == snapshot_left, (
        "Left children changed after duplicate adds"
    )
    assert s.right_children == snapshot_right, (
        "Right children changed after duplicate adds"
    )
    assert s.binary_vector == snapshot_val, "Binary vector changed after duplicate adds"


# ── Height ────────────────────────────────────────────────────────────────────


@given(st.lists(st.integers(), min_size=10, max_size=500, unique=True))
def test_height_is_logarithmic(elements: list[int]) -> None:
    """Height is O(log n) for random priorities — at most 20x log2(n) as a sanity bound.

    For a treap with random priorities, expected height is ~4.3 log2(n).
    We use a generous upper bound of 10 * log2(n) to catch catastrophic imbalance.
    """
    import math

    s: Set[int] = Set()
    for x in elements:
        s.add(x)

    n = len(set(elements))
    h = _height(s)

    if n > 0:
        max_height = max(20, int(10 * math.log2(n) + 5))
        assert h <= max_height, (
            f"Height {h} exceeds bound {max_height} for n={n} "
            f"(expected ~{4.3 * math.log2(n):.1f})"
        )


@given(st.lists(st.integers(), min_size=1, max_size=100, unique=True))
def test_single_node_height(elements: list[int]) -> None:
    """A set with one element has height 0 (just the root)."""
    if not elements:
        return
    s: Set[int] = Set()
    s.add(elements[0])
    assert _height(s) == 0, "Single-element treap should have height 0"


@given(st.lists(st.integers(), min_size=3, max_size=100, unique=True))
def test_height_never_exceeds_n(elements: list[int]) -> None:
    """Height is never worse than O(n) — sanity bound: height < n."""
    s: Set[int] = Set()
    for x in elements:
        s.add(x)

    n = len(set(elements))
    h = _height(s)
    assert h < n, f"Height {h} >= n={n} — degenerate tree!"
