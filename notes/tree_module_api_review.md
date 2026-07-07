# Tree Module API Review

## Overview
The `Tree` module implements a general-purpose `Tree` container where each node holds a **hashable value** and maintains **children in insertion order** (via an internal `dict`). Nodes are accessed and constructed primarily through bracket syntax (`t[key]`), which also auto-creates intermediate nodes on demand. This leads to a very terse, "builder-style" API for constructing trees. The root is a structural entry point — accessing `.value` on it raises `AttributeError`.

## Positives
- **Highly Pythonic and concise construction:** The `__getitem__` + auto-creation pattern (`t[a][b].add(c)`) is very expressive and fits well with Python’s mutable collection feel.
- **Rich Traversal Support:** Provides `bfs`, `dfs` (with `pre`, `in`, `post` orders), `leaves`, `branches`, `children`, and `siblings` iterators.
- **Efficient C-level internals:** Cython implementation with C++ `deque`, `PyObject*` pointers, and manual memory management (via `freelist`) ensures good performance.
- **Good Encapsulation:** The `Cursor` abstraction is a clean way to represent and manipulate paths through the tree.
- **Standard Protocols:** Implements `__len__`, `__contains__`, `__iter__`, `__bool__`, and pickling (`__reduce__`).

## Single-Class Architecture

The tree uses a **single-class design** where `Tree` serves as both the container and the node type:

- `t = Tree()` creates a *base Tree container* — it holds no value, only children
- `t.add(0)` makes node `0` a child of `t`
- `t.root` returns the first child, not `t` itself

**Pros:**
- Empty trees are representable (`Tree()`)
- No `Tree` vs `Node` class distinction — simpler API

**Cons:**
- `t.root` returns the first child, not `self` — unintuitive at first glance

**Alternative (value-mandatory):** `Tree(0)` would make the root hold a value, `t.root == self`, but empty trees become impossible.

The current design prioritizes flexibility (empty trees, single-class simplicity) over the intuition that "the tree I created is the root."

### The Value Question

The single-class design creates a conceptual tension: is the root a `Node`?

**Decision: "Every Tree is not a Node" (Raise approach).** Accessing `.value` on the root raises `AttributeError`. This enforces that the root is a `Tree` (structure) but not a `Node` (value-holder). The root is a structural entry point, not a value-bearing element — parallel to how an empty `Maybe` has no `.value`.

### Theoretical Alignment & Semantic Friction

The base container creates semantic friction with standard tree theory.

**Standard Tree Theory (Wikipedia, Cornell CS, GWU CSci 1112, ProofWiki):**
- A tree is either **empty**, or consists of a **root node** and subtrees
- The root is a node with no parent (in-degree = 0)
- All other nodes have exactly one parent
- Depth of a node = number of edges from root to that node
- Root has depth 0

**Current implementation behavior:**
```
Tree (base container, no value)
└── 0
    └── 1

t.depth = 0      # base container is root
t[0].depth = 1   # 1 edge from base container
t[0, 1].depth = 2
```

**The tension:** The base container is treated as a node for parent/child relationships (`t[0].parent = t`), but it has no value. Standard theory expects the root to be a "real" node (with data).

**Two possible interpretations:**

| | Base container = root (current) | Base container ≠ node |
|---|---|---|
| Root | `t` (no parent) | `t[0]` (no parent) |
| `t[0].parent` | `t` | `None` |
| `t[0].depth` | 1 | 0 |
| `t[0, 1].depth` | 2 | 1 |
| Empty tree | `Tree()` | `Tree()` |
| `len(t)` | 0 | 0 |

**Impact of choosing "Base container ≠ node":**
- `parents()` must skip base container
- All iterators must skip base container
- `__setitem__` planned behavior (accept Node as value) affected
- `root` property changes semantics

**Sources:**
- https://en.wikipedia.org/wiki/Tree_(data_structure)
- https://www.cs.cornell.edu/courses/cs2112/2022fa/lectures/trees/
- https://www2.seas.gwu.edu/~bell/csci1112/lectures/trees.pdf
- https://proofwiki.org/wiki/Definition:Rooted_Tree

## Grafting (Subtree Insertion Semantics)

When inserting a subtree from one tree into another (`t[key] = other_tree[node]`), the key question is: **does the inserted node remain linked to the source tree?**

**"Grafting"** = attaching a branch/subtree from one tree onto another (botanical metaphor).

### Two possible behaviors

| | Deep copy (independent) | Shallow copy (reference) |
|---|---|---|
| After insertion | Subtree is independent | Subtree shares state with source |
| Mutation in source | Does NOT affect target | DOES affect target |
| Memory | Duplicates nodes | Shared references |
| Lifetime | Independent | Tied to source |

### Recommendation: Deep copy by default

As an experienced Python developer, **deep copy (independent)** is the expected default:

1. **Predictability** — `other_tree["a"].add("z")` should not silently affect `my_tree["x"]`
2. **Lifetime independence** — If source tree is GC'd, inserted subtree survives
3. **No hidden coupling** — Shared mutable state across trees leads to subtle bugs
4. **Matches single-class design** — `t[key]` returns a `Tree`, inserted `Tree` should be independent

If reference sharing is needed, provide an explicit API:
- `my_tree["x"] = branch` → deep copy (independent)
- `my_tree.link("x", branch)` → shallow reference (shared)

## Missing Properties & Methods

Common tree operations not yet implemented:

| Property/Method | Description | Status |
|---|---|---|
| `is_leaf` | `len(self) == 0` | Missing |
| `is_root` | `self.parent is None` | Missing |
| `ancestors` | All ancestors (like `parents()` but may include self or have options) | Missing |
| `descendants` | All nodes below self (flattened) | Missing |
| `lca(other)` | Lowest common ancestor of two nodes | Missing — **most useful missing operation** |
| `path_to(other)` | Path (list of nodes) from self to other | Missing |
| `nodes_at(depth)` | All nodes at a specific depth | Missing |

**Note:** `width` was added but needs docstring clarification — it should return "the number of nodes at the same depth as this node."

## Negatives & API Inconsistencies
- **Inconsistent `add` Semantics:** The `add` method's `parent` parameter and its interaction with `Cursor` are complex. The fact that `t.add(x)` and `t[x].add(y)` works, but `t.add(x, cursor=...)` behaves differently, is confusing.
- **Missing/Incomplete API:**
    - `diameter` is not implemented.
    - `__invert__` (`~node`) for getting a cursor is unconventional.

## Recommendations
1. **Document Root Behavior:** The single-class design is sound but non-obvious. Add docstrings explaining that `Tree()` creates the root node and `root` returns the first child.
2. **Simplify `add`:** Re-evaluate the `parent` flag in `add`. It might be cleaner to have a dedicated `add_child` or `setdefault` style method.
3. **Implement/Remove Features:** Either implement `diameter` or remove the placeholder.
4. **Replace `__invert__` with `__neg__`:** Use `-node` instead of `~node` for getting a cursor. The minus sign has a directional connotation ("path to this node") and is less unconventional than `~` (bitwise NOT) for representing a path/location.
