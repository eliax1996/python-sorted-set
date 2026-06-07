# python-sorted-set

Python's standard library has no sorted set (or tree set) — `set` is a hash
set, unordered by design. While `sortedcontainers` exists, I wanted to
understand what makes a sorted set tick **from scratch**.

This is my study of the **treap** (tree + heap), a probabilistic data structure
that combines a **BST** (binary search tree) with a **max-heap** to maintain
sorted order with O(log n) expected operations.

## How it works

A treap is a BST where every node carries a **random priority**. The tree is
ordered by key (BST property: left < node < right), but balanced by priority
(heap property: parent priority >= children). Insertions use rotations to
restore both invariants. The result: the tree stays balanced **in expectation**
without any rebalancing logic — just random priorities.

### Priorities via Feistel network

Instead of storing a random value per node, I derive the priority from the
value itself using a **Feistel permutation network**. This is a deterministic,
bijective function that maps each value to a pseudo-random index in `[0, 2ⁿ)`.
Since the permutation is a bijection, no two values collide on priority, and
the mapping is deterministic — no need to store per-node randomness.

> **Note:** The current Feistel network only works with integers. But the
> underlying principle extends to any data structure: if you can design a
> bijection between your data type and a fixed set of bits, the network
> shuffles those bits and maps the result back to a valid object. Every bit
> sequence projects to another random bit sequence in the same space — no two
> distinct inputs map to the same output, and every output value in the domain
> is covered. This is what makes it a **permutation** over the entire space:
> bijection + surjection onto the codomain.

### Data structure: array-backed tree

The tree is stored in three parallel arrays:

```
binary_vector[i]  → the value at node i
left_children[i]  → index of the left child (or -1 sentinel)
right_children[i] → index of the right child
```

This is similar to how a binary heap is stored, but with explicit child
pointers (indices) instead of the implicit `2i+1` / `2i+2` formula — because
treap rotations rewrite parent-child relationships, which the implicit layout
can't express.

Initially I tried the **implicit array layout** (heap-style: left at `2i+1`,
right at `2i+2`). Mid-implementation I realised that rotations would need to
move entire subtrees — O(n) per rotation, defeating the purpose. So I migrated
to the explicit offset-based representation above, where a rotation is just
swapping a few indices: O(1).

## How to run

```bash
uv run pytest tests/ -q
```

This runs 41 tests: 23 existing + 17 property-based invariant tests + 1 benchmark.

To see the benchmark table:

```bash
uv run pytest tests/test_benchmark_set.py -v -s
```

Expected output:

```
── Treap Insertion Benchmark ──

       n    total (µs)       µs/op   log2(n)   µs/op / log2(n)
      10       42.34µs     4.234µs      3.32         1.275µs
      50      215.34µs     4.307µs      5.64         0.763µs
     100      502.00µs     5.020µs      6.64         0.756µs
     500     2665.15µs     5.330µs      8.97         0.595µs
    1000     5592.67µs     5.593µs      9.97         0.561µs
    5000    31015.10µs     6.203µs     12.29         0.505µs
   10000    63713.03µs     6.371µs     13.29         0.479µs
   50000   351386.61µs     7.028µs     15.61         0.450µs
  100000   758683.15µs     7.587µs     16.61         0.457µs
```

The key column is **µs/op / log₂(n)** — if it's roughly constant (here it stays
between 0.45 and 0.76), insertion is O(log n). The per-insertion time goes from
4.3µs (n=50) to 7.6µs (n=100k) — less than 2x slower for 2000x more elements.

### How it compares

| n | metric | treap | sortedcontainers | bisect.insort |
|---|---|---|---|---|
| 1,000 | µs/op | 5.48 | 0.39 | 0.16 |
| | vs treap | — | 14.0× faster | 34.9× faster |
| 50,000 | µs/op | 7.09 | 0.61 | 2.29 |
| | vs treap | — | 11.7× faster | **3.1× slower** |
| **5,000,000** | µs/op | **13.91** | **1.94** | **536.41** |
| | total | **69.6s** | **9.7s** | **44.7 min** |
| | vs treap | — | 7.2× faster | **38.6× slower** |

Key takeaways:

- **sortedcontainers** (C B-tree) is consistently ~7–14× faster — expected for
  a pure-Python learning implementation vs an optimised C extension.
- **bisect.insort** into a list starts fast at small n (cheap array shifts), but
  O(n) per insertion catches up brutally. By 5M elements it takes **45 minutes**
  vs **70 seconds** for the treap.
- Both the treap and sortedcontainers scale O(log n). The treap's µs/op / log₂(n)
  stays between 0.39 and 0.63 across all sizes; sortedcontainers stays between
  0.03 and 0.09. The gap is a constant factor from Python overhead (function
  calls, attribute access, Feistel permutation) vs C with a cache-friendly
  B-tree layout.
- For a from-scratch Python implementation, beating bisect by **38×** at 5M
  while matching its asymptotic behaviour is the win.

## What's implemented

| Operation | Status |
|---|---|
| `add` | ✅ |
| `__contains__` | ✅ |
| `remove`, `discard`, `pop`, `clear` | ❌ stubs |
| `__len__` | ❌ stub |
| `__iter__` | ❌ stub |
| Set operations (`union`, `intersection`, etc.) | ❌ stubs |

The basic API is in place; the rest are structural stubs waiting to be filled.
This was a learning project, not a production library.

## How it was built

The implementation was done **by hand** as a deliberate study exercise — writing
the rotations, debugging the pointer logic, working through the invariants.
The property-based tests (using [Hypothesis](https://hypothesis.readthedocs.io/))
were **assisted by AI** to ensure deep coverage: BST invariants, heap invariants,
membership correctness across thousands of random inputs.

Project structure:

```
treap/
├── treap.py       # the Set implementation
├── feistel.py     # Feistel permutation network for priorities
├── pytests        # project config
├── tests/
│   ├── test_set.py               # basic membership tests
│   ├── test_set_invariants.py    # property-based invariant tests
│   ├── test_benchmark_set.py     # insertion benchmark
│   ├── test_feistel.py           # Feistel property tests
│   └── test_permuter.py          # Feistel permutation tests
└── README.md
```
