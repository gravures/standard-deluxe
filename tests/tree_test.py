from __future__ import annotations

import pytest
from deluxe.tree import Tree


@pytest.fixture
def binary_tree_height_3() -> Tree[int]:
    t = Tree[int]()
    t.add(0)
    t[0].add(1)
    t[0].add(2)
    t[0][1].add(3)
    t[0][1].add(4)
    t[0][2].add(5)
    t[0][2].add(6)
    t[0][1][3].add(7)
    t[0][1][3].add(8)
    t[0][1][4].add(9)
    t[0][1][4].add(10)
    t[0][2][5].add(11)
    t[0][2][5].add(12)
    t[0][2][6].add(13)
    t[0][2][6].add(14)
    return t


def test_bfs(binary_tree_height_3: Tree[int]):
    tree = binary_tree_height_3
    assert list[int](tree.bfs()) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]


def test_dfs_pre(binary_tree_height_3: Tree[int]):
    tree = binary_tree_height_3
    assert list[int](tree.dfs(order="pre")) == [0, 1, 3, 7, 8, 4, 9, 10, 2, 5, 11, 12, 6, 13, 14]


def test_dfs_in(binary_tree_height_3: Tree[int]):
    tree = binary_tree_height_3
    assert list[int](tree.dfs(order="in")) == [7, 3, 8, 1, 9, 4, 10, 0, 11, 5, 12, 2, 13, 6, 14]


def test_dfs_post(binary_tree_height_3: Tree[int]):
    tree = binary_tree_height_3
    assert list[int](tree.dfs(order="post")) == [7, 8, 3, 9, 10, 4, 1, 11, 12, 5, 13, 14, 6, 2, 0]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def empty_tree() -> Tree[int]:
    return Tree[int]()


@pytest.fixture
def single_node_tree() -> Tree[int]:
    t = Tree[int]()
    t.add(0)
    return t


@pytest.fixture
def chain_012() -> Tree[int]:
    t = Tree[int]()
    t.add(0)
    t[0].add(1)
    t[0][1].add(2)
    return t


# ============================================================================
# Theory: root
# - Base container is NOT a node, t[0] is the root
# - Root has no parent (in-degree = 0)
# - root returns the first child, not the base container
# ============================================================================


def test_root_empty_tree(empty_tree: Tree[int]):
    """Empty tree has no root."""
    assert empty_tree.root is None


def test_root_single_node(single_node_tree: Tree[int]):
    """Root of single-node tree is t[0]."""
    t = single_node_tree
    assert t.root is t[0]


def test_root_child_returns_root(single_node_tree: Tree[int]):
    """root of a child returns the root (t[0]), not the base container."""
    t = single_node_tree
    assert t[0].root is t[0]


def test_root_intermediate(chain_012: Tree[int]):
    """root of intermediate node returns t[0]."""
    t = chain_012
    assert t[0][1].root is t[0]
    assert t[0][1][2].root is t[0]


# ============================================================================
# Theory: parent
# - Base container is NOT a node
# - Root (t[0]) has parent = None
# - Other nodes have parent = their direct ancestor
# ============================================================================


def test_parent_of_root(single_node_tree: Tree[int]):
    """Root node has no parent."""
    t = single_node_tree
    assert t[0].parent is None


def test_parent_of_child(chain_012: Tree[int]):
    """Child's parent is its direct ancestor."""
    t = chain_012
    assert t[0][1].parent is t[0]
    assert t[0][1][2].parent is t[0][1]


# ============================================================================
# Theory: parents
# - Base container is NOT in the parents chain
# - Root (t[0]) has empty parents ()
# - Others have parents from t[0] down to direct parent
# ============================================================================


def test_parents_of_root(single_node_tree: Tree[int]):
    """Root node has empty parents."""
    t = single_node_tree
    assert t[0].parents() == ()


def test_parents_of_child(chain_012: Tree[int]):
    """Child's parents exclude base container."""
    t = chain_012
    assert t[0][1].parents() == (t[0],)
    assert t[0][1][2].parents() == (t[0], t[0][1])


# ============================================================================
# Theory: depth
# - Depth = number of edges from root to node
# - Root (t[0]) has depth 0
# - Empty tree has depth 0
# ============================================================================


def test_depth_empty_tree(empty_tree: Tree[int]):
    """Empty tree has depth 0."""
    assert empty_tree.depth == 0


def test_depth_root(single_node_tree: Tree[int]):
    """Root node has depth 0."""
    t = single_node_tree
    assert t[0].depth == 0


def test_depth_chain(chain_012: Tree[int]):
    """Depth is number of edges from root."""
    t = chain_012
    assert t[0].depth == 0
    assert t[0][1].depth == 1
    assert t[0][1][2].depth == 2


def test_depth_binary_tree(binary_tree_height_3: Tree[int]):
    """Depth varies by level."""
    t = binary_tree_height_3
    assert t[0].depth == 0
    assert t[0][1].depth == 1
    assert t[0][2].depth == 1
    assert t[0][1][3].depth == 2
    assert t[0][1][7].depth == 3


# ============================================================================
# Theory: height
# - Height = number of edges from node to deepest leaf
# - Leaf has height 0
# - Empty tree has height -1 (convention)
# ============================================================================


def test_height_empty_tree(empty_tree: Tree[int]):
    """Empty tree has height -1."""
    assert empty_tree.height == -1


def test_height_leaf(single_node_tree: Tree[int]):
    """Single leaf node has height 0."""
    t = single_node_tree
    assert t[0].height == 0


def test_height_chain(chain_012: Tree[int]):
    """Height is distance to deepest leaf."""
    t = chain_012
    assert t[0][1][2].height == 0
    assert t[0][1].height == 1
    assert t[0].height == 2


def test_height_binary_tree(binary_tree_height_3: Tree[int]):
    """Height is longest path to leaf."""
    t = binary_tree_height_3
    # Leaves: 7,8,9,10,11,12,13,14
    assert t[0][1][3][7].height == 0
    assert t[0][2][6][14].height == 0
    # Level 2: 3,4,5,6
    assert t[0][1][3].height == 1
    assert t[0][2][6].height == 1
    # Level 1: 1,2
    assert t[0][1].height == 2
    assert t[0][2].height == 2
    # Root: 0
    assert t[0].height == 3


# ============================================================================
# Theory: consistency
# - height(node) = max(depth(leaf)) - depth(node)
# - root.height = tree height (longest root-to-leaf path)
# ============================================================================


def test_height_consistency(binary_tree_height_3: Tree[int]):
    """height = max descendant depth - self depth."""
    t = binary_tree_height_3
    leaves = [
        t[0][1][3][7],
        t[0][1][3][8],
        t[0][1][4][9],
        t[0][1][4][10],
        t[0][2][5][11],
        t[0][2][5][12],
        t[0][2][6][13],
        t[0][2][6][14],
    ]
    max_leaf_depth = max(leaf.depth for leaf in leaves)
    for node in [t[0], t[0][1], t[0][2], t[0][1][3], t[0][1][3][7]]:
        expected = max_leaf_depth - node.depth
        assert node.height == expected
