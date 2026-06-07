from collections.abc import Iterable, Iterator
from multiprocessing import Value
from re import A
from typing import Any, Generic, Protocol, Self, TypeVar, cast, runtime_checkable

from feistel import FeistelPermuter


@runtime_checkable
class Comparable(Protocol):
    def __lt__(self, other: Any, /) -> bool: ...
    def __eq__(self, other: Any, /) -> bool: ...
    def __gt__(self, other: Any, /) -> bool: ...


C = TypeVar("C", bound=Comparable)


class ReusableStack:
    def __init__(self) -> None:
        self.stack: list[int] = []
        self.pos = 0

    def append(self, elem: int) -> None:
        if self.pos >= len(self.stack):
            self.stack.append(elem)
            self.pos += 1
            return
        self.stack[self.pos] = elem
        self.pos += 1

    def __getitem__(self, index) -> int:
        return self.stack[index]

    def reset(self) -> None:
        self.pos = 0

    def __repr__(self) -> str:
        return repr(self.stack[0 : self.pos])


class Set(Generic[C]):
    """A set implemented using a treap (tree + heap).

    The left child will be smaller than the father, the right bigger.

    Elements must be mutually comparable via ``__gt__`` — this provides
    the total order that drives treap structure and iteration order.
    """

    SENTINEL: int = -1

    def __init__(self) -> None:
        # we need a root since the rotations can rotate also the root node, so is not always 0
        self.root = self.SENTINEL
        self.binary_vector: list[C] = []
        self.left_children: list[int] = [self.SENTINEL]
        self.right_children: list[int] = [self.SENTINEL]
        self.permuter = FeistelPermuter(seed=667, rounds=4, bits=32)

        # a stack that will be used to keep track of the traversed nodes in a recursive descend
        # it will be in average log2(len(self.binary_vector)) to store the traversed path
        self.traversed_stack = ReusableStack()

    # --- Basic operations ---

    def _add(self, elem: C) -> int:
        self.binary_vector.append(elem)
        self.left_children.append(self.SENTINEL)
        self.right_children.append(self.SENTINEL)
        return len(self.binary_vector) - 1

    def _fix_granfather(self, child: int, father: int, granfather: int | None) -> None:
        if granfather is None:
            self.root = child
        elif self.left_children[granfather] == father:
            self.left_children[granfather] = child
        elif self.right_children[granfather] == father:
            self.right_children[granfather] = child
        else:
            raise ValueError(f"Cannot find granfather of {father}")

    def rotate_right(self, child: int, father: int, granfather: int | None) -> None:
        child_right = self.right_children[child]

        self.right_children[child] = father
        self.left_children[father] = child_right

        self._fix_granfather(child, father, granfather)

    def rotate_left(self, child: int, father: int, granfather: int | None) -> None:
        child_left = self.left_children[child]

        self.left_children[child] = father
        self.right_children[father] = child_left

        self._fix_granfather(child, father, granfather)

    def add(self, elem: C) -> None:
        if len(self.binary_vector) == 0:
            self._add(elem)
            self.root = 0
            return

        self.traversed_stack.reset()

        ptr = self.root

        while True:
            self.traversed_stack.append(ptr)
            if self.binary_vector[ptr] == elem:
                # by definition a set shouldn't have duplicates
                return
            elif self.binary_vector[ptr] > elem:
                if self.left_children[ptr] == self.SENTINEL:
                    self.left_children[ptr] = self._add(elem)
                    ptr = self.left_children[ptr]
                    break
                ptr = self.left_children[ptr]
            else:
                if self.right_children[ptr] == self.SENTINEL:
                    self.right_children[ptr] = self._add(elem)
                    ptr = self.right_children[ptr]
                    break
                ptr = self.right_children[ptr]

        # now lets traverse in the reverse order the pointers
        # touched, if the random element is not
        child = ptr
        # pre-computed since is always the same node that traverse the tree
        monotonic_score_child = self.permuter.random_index(self.binary_vector[child])
        for i in range(self.traversed_stack.pos - 1, -1, -1):
            father = self.traversed_stack[i]
            granfather = self.traversed_stack[i - 1] if i - 1 >= 0 else None

            # random values monotonic stack check, lets rotate only if the heap is not a max heap
            # regarding the feistel network
            if monotonic_score_child <= self.permuter.random_index(self.binary_vector[father]):
                break

            if self.left_children[father] == child:
                # child is left child of.i
                self.rotate_right(
                    child,
                    father,
                    granfather,
                )
            elif self.right_children[father] == child:
                # child is right child of i
                self.rotate_left(
                    child,
                    father,
                    granfather,
                )
            else:
                raise ValueError(f"Implementation error, cannot find the child of {i}")

    def binary_treap(self) -> Iterable[int]:
        for num in self.binary_vector:
            # ignoring if for now, feistel can return a different element from a range no matter whats the domain
            # of the data; for now lets keep hardcoded for integers
            yield self.permuter.random_index(num)  # pyright: ignore[reportArgumentType]

        # todo: missing the heap based balancing

    def remove(self, elem: C) -> None: ...
    def discard(self, elem: C) -> None: ...
    def pop(self) -> C: ...
    def clear(self) -> None: ...

    # --- Membership & size ---

    def __contains__(self, elem: object) -> bool:
        if len(self.binary_vector) == 0:
            return False

        ptr = self.root
        while True:
            if self.binary_vector[ptr] == elem:
                return True
            elif self.binary_vector[ptr] > elem:
                ptr = self.left_children[ptr]
            else:
                ptr = self.right_children[ptr]

            if ptr == self.SENTINEL:
                return False

        return False

    def __len__(self) -> int: ...
    def isdisjoint(self, other: Iterable[C]) -> bool: ...
    def issubset(self, other: Iterable[C]) -> bool: ...
    def issuperset(self, other: Iterable[C]) -> bool: ...

    # --- Comparison operators ---

    def __eq__(self, other: object) -> bool: ...
    def __ne__(self, other: object) -> bool: ...
    def __le__(self, other: Iterable[C]) -> bool: ...
    def __lt__(self, other: Iterable[C]) -> bool: ...
    def __ge__(self, other: Iterable[C]) -> bool: ...
    def __gt__(self, other: Iterable[C]) -> bool: ...

    # --- Set operations: return new sets ---

    def union(self, *others: Iterable[C]) -> Self: ...
    def __or__(self, other: Iterable[C]) -> Self: ...
    def intersection(self, *others: Iterable[C]) -> Self: ...
    def __and__(self, other: Iterable[C]) -> Self: ...
    def difference(self, *others: Iterable[C]) -> Self: ...
    def __sub__(self, other: Iterable[C]) -> Self: ...
    def symmetric_difference(self, other: Iterable[C]) -> Self: ...
    def __xor__(self, other: Iterable[C]) -> Self: ...
    def copy(self) -> Self: ...

    # --- Set operations: in-place update ---

    def update(self, *others: Iterable[C]) -> None: ...
    def __ior__(self, other: Iterable[C]) -> Self: ...
    def intersection_update(self, *others: Iterable[C]) -> None: ...
    def __iand__(self, other: Iterable[C]) -> Self: ...
    def difference_update(self, *others: Iterable[C]) -> None: ...
    def __isub__(self, other: Iterable[C]) -> Self: ...
    def symmetric_difference_update(self, other: Iterable[C]) -> None: ...
    def __ixor__(self, other: Iterable[C]) -> Self: ...

    # --- Iteration & representation ---

    def __iter__(self) -> Iterator[C]: ...
    def __repr__(self) -> str: ...
