"""Property-based tests for treap.Set against Python's built-in set."""

from hypothesis import given
from hypothesis import strategies as st

from treap import Set


@given(st.lists(st.integers()))
def test_contains_matches_set(elements: list[int]) -> None:
    """After adding the same elements, both sets match on __contains__."""
    treap_set: Set[int] = Set()
    py_set: set[int] = set()

    for x in elements:
        treap_set.add(x)
        py_set.add(x)

    for probe in elements:
        assert (probe in treap_set) == (probe in py_set)


@given(st.lists(st.integers()), st.integers())
def test_contains_unknown_matches_set(elements: list[int], probe: int) -> None:
    """Contains for arbitrary probes matches Python set behaviour."""
    treap_set: Set[int] = Set()
    py_set: set[int] = set()

    for x in elements:
        treap_set.add(x)
        py_set.add(x)

    assert (probe in treap_set) == (probe in py_set)


@given(st.lists(st.integers()))
def test_contains_after_duplicate_adds(elements: list[int]) -> None:
    """Adding the same elements again doesn't change containment."""
    treap_set: Set[int] = Set()

    for x in elements:
        treap_set.add(x)

    # add them a second time
    for x in elements:
        treap_set.add(x)

    for probe in elements:
        assert probe in treap_set


@given(st.integers())
def test_single_element(x: int) -> None:
    """A set with one element contains it and doesn't contain others."""
    treap_set: Set[int] = Set()
    treap_set.add(x)

    assert x in treap_set
    assert (x + 1) not in treap_set
    assert (x - 1) not in treap_set


@given(st.lists(st.integers()))
def test_empty_set_contains_nothing(elements: list[int]) -> None:
    """An empty set contains nothing, even after adding and removing nothing."""
    treap_set: Set[int] = Set()

    for probe in elements:
        assert probe not in treap_set


@given(st.lists(st.integers()))
def test_binary_vector_grows(elements: list[int]) -> None:
    """Adding many elements doesn't crash — vector grows as needed."""
    treap_set: Set[int] = Set()

    for x in elements:
        treap_set.add(x)

    for probe in elements:
        assert probe in treap_set
