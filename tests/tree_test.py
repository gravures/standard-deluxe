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
