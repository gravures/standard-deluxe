# Copyright (c) 2025 - Gilles Coissac
# This file is part of bunu program.
#
# bunu is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# bunu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bunu. If not, see <https://www.gnu.org/licenses/>
#
# distutils: language = c++

from cpython cimport bool
from cpython.tuple cimport (
    PyTuple_New,
    _PyTuple_Resize,
    PyTuple_SetItem,
    PyTuple_SET_ITEM,
    PyTuple_GET_ITEM,
    PyTuple_Pack,
)
from cpython.dict cimport PyDict_Next, PyDict_GetItem, PyDict_Size
from cpython.ref cimport PyObject
from libcpp.deque cimport deque as Stack
cimport cython

from typing import ClassVar
from collections import deque


__all__ = ("Cursor", "Tree")


@cython.freelist(6)
@cython.final
cdef class Cursor:
    cdef tuple _values
    cdef Py_ssize_t _size

    def __cinit__(self, *keys):
        cdef list values
        values = []

        for obj in keys:
            if obj.__hash__ is None:
                raise TypeError("Cursor's values should be hashable")
            if isinstance(obj, Cursor):
                for item in obj:
                    values.append(item)
            else:
                values.append(obj)
        self._values = tuple(values)
        self._size = len(values)

    def __len__(self):
        return self._size

    def __contains__(self, value):
        return value in self._values

    def __iter__(self):
        yield from self._values

    def __getitem__(self, index):
        try:
            if isinstance(index, slice):
                return Cursor(*self._values.__getitem__(index))
            return self._values.__getitem__(index)
        except IndexError:
            raise IndexError("Cursor index out of range")

    def __eq__(self, value):
        return self._values == value

    def __hash__(self):
        return hash(self._values)

    def __repr__(self):
        return f"Cursor{self._values}"

    def __getstate__(self):
        return { "values": self._values }

    def __setstate__(self, dict state):
        self._values = state["value"]

    def __reduce__(self):
        return (Cursor.__new__, (Cursor,), self.__getstate__(), None, None, None)


cdef inline (int, int) _slice(Tree node, object slice_ = None) noexcept:
    return (
        (node._depth() + (slice_.start or 0), slice_.stop or node._height())
        if isinstance(slice_, slice)
        else (0, slice_) if isinstance(slice_, int)
        else (0, node._height())
    )


cdef inline Py_ssize_t sz_max(Py_ssize_t a, Py_ssize_t b) noexcept:
    return a if a > b else b


cdef enum Nodes:
    All
    Leaves
    Branches


cdef class _iterator:
    cdef Tree tree

    def __iter__(self):
        return self

    def __reversed__(self):
        return reversed(tuple(self))

    def __repr__(self):
        return f"{self._name_}(<Tree at {hex(id(self.tree))}>)"


cdef class _CHILD(_iterator):
    cdef object generator
    _name_: ClassVar[str] = "ChildrenIterator"

    def __cinit__(self, Tree node, bint siblings = False):
        self.tree = node
        if siblings:
            self.generator = self._siblings()
        else:
            self.generator = self._children()

    def __next__(self):
        return next(self.generator)

    def _children(self):
        cdef Py_ssize_t pos = 0
        cdef PyObject* value
        while PyDict_Next(self.tree._children, &pos, &value, NULL):
            yield <object> value

    def _siblings(self):
        if self.tree.parent is None:
            yield from ()
            return

        cdef Py_ssize_t pos = 0
        cdef PyObject* value
        cdef PyObject* node

        while PyDict_Next(self.tree.parent._children, &pos, &value, &node):
            if <object> node is not self.tree:
                yield <object> value


@cython.freelist(2)
cdef class _BFS(_iterator):
    cdef Tree node
    cdef Stack[PyObject*] stack, nodes
    cdef int start, stop
    cdef Nodes kind

    _name_: ClassVar[str] = "BfsIterator"

    def __cinit__(self, Tree node, Nodes kind, object depth = None):
        cdef PyObject* value
        cdef Py_ssize_t pos = 0

        self.tree = node
        self.node = node
        self.start, self.stop = _slice(node, depth)
        self.kind = kind

        while PyDict_Next(node._children, &pos, NULL, &value):
            self.stack.push_back(value)
        self.nodes.clear()

    def __next__(self):
        if self.stack.empty():
            raise StopIteration

        cdef PyObject* value
        cdef Py_ssize_t pos = 0

        self.node = <Tree> self.stack.back()
        self.stack.pop_back()

        if PyDict_Size(self.node._children) != 0:
            if self.node._depth() < self.stop:
                while PyDict_Next(self.node._children, &pos, NULL, &value):
                    self.nodes.push_front(value)
                self.stack.insert(self.stack.begin(), self.nodes.begin(), self.nodes.end())
                self.nodes.clear()
            if self.node.depth >= self.start and self.kind is not Nodes.Leaves:
                return self.node.value
            else:
                self.__next__()

        if self.node._depth() >= self.start and self.kind is not Nodes.Branches:
            return self.node.value
        self.__next__()

    # def _bfs(self, Nodes kind, object depth = None):
    #     cdef Tree node = self
    #     cdef PyObject* value
    #     cdef Stack[PyObject*] stack, nodes
    #     cdef Py_ssize_t pos = 0
    #     cdef int start, stop

    #     while PyDict_Next(node._children, &pos, NULL, &value):
    #         stack.push_back(value)
    #     start, stop = _slice(self, depth)

    #     while not stack.empty():
    #         node = <Tree> stack.back()
    #         stack.pop_back()

    #         if PyDict_Size(node._children) != 0:
    #             if node._depth() < stop:
    #                 nodes.clear()
    #                 pos = 0
    #                 while PyDict_Next(node._children, &pos, NULL, &value):
    #                     nodes.push_front(value)
    #                 stack.insert(stack.begin(), nodes.begin(), nodes.end())
    #             if node.depth >= start and kind is not Nodes.Leaves:
    #                 yield node.value
    #             continue

    #         if node._depth() >= start and kind is not Nodes.Branches:
    #             yield node.value


@cython.freelist(2)
cdef class _DFS((_iterator)):
    # NOTE: source https://en.wikipedia.org/wiki/Tree_traversal#Arbitrary_trees
    #
    # To traverse arbitrary trees (not necessarily binary trees)
    # with depth-first search, perform the following operations at each node:
    #     1. If the current node is empty then return.
    #     2. Visit the current node for pre-order traversal.
    #     3. For each i from 1 to the current node's number of subtrees - 1,
    #        or from the latter to the former for reverse traversal, do:
    #         a. Recursively traverse the current node's i-th subtree.
    #         b. Visit the current node for in-order traversal.
    #     4. Recursively traverse the current node's last subtree.
    #     5. Visit the current node for post-order traversal.
    cdef object generator
    _name_: ClassVar[str] = "DfsIterator"

    def __init__(self, Tree tree, object order, bool reverse):
        self.tree = tree

        if order == "in":
            self.generator = self._in(tree, reverse)
        elif order == "post":
            self.generator = self._post(tree, reverse)
        else:
            self.generator = self._pre(tree, reverse)

    def __next__(self):
        return next(self.generator)

    def _in(self, Tree tree, bint reverse):
        if PyDict_Size(tree._children) == 0:
            return

        cdef Tree node, peek
        cdef PyObject* tmp
        cdef Py_ssize_t pos
        cdef Stack[PyObject*] stack, r_stack, nodes

        node = tree

        while True:
            while PyDict_Size(node._children) != 0:
                pos = 0
                while PyDict_Next(node._children, &pos, NULL, &tmp):
                    _ = nodes.push_back(tmp) if reverse else nodes.push_front(tmp)
                if PyDict_Size(node._children) > 1:
                    r_stack.push_back(nodes.front())
                    nodes.pop_front()
                stack.insert(stack.end(), nodes.begin(), nodes.end())
                nodes.clear()
                stack.push_front(<PyObject*> node)
                node = <Tree> stack.back()
                stack.pop_back()
            yield node.value  # leaf node

            peek = <Tree> stack.back()
            if peek is tree:
                if not r_stack.empty():
                    node = <Tree> r_stack.back()
                    r_stack.pop_back()
                    peek = <Tree> stack.front()
                    if peek is not tree:
                        stack.pop_front()
                        yield peek.value
                    continue
                break

            node = <Tree> stack.back()
            stack.pop_back()

    def _post(self, Tree tree, bint reverse):
        if PyDict_Size(tree._children) == 0:
            return

        cdef Tree node, peek
        cdef PyObject* tmp
        cdef Py_ssize_t pos
        cdef Stack[PyObject*] stack, r_stack, nodes

        node = tree

        while True:
            while PyDict_Size(node._children) != 0:
                pos = 0
                while PyDict_Next(node._children, &pos, NULL, &tmp):
                    _ = nodes.push_back(tmp) if reverse else nodes.push_front(tmp)
                if PyDict_Size(node._children) > 1:
                    r_stack.push_back(nodes.front())
                    nodes.pop_front()
                stack.insert(stack.end(), nodes.begin(), nodes.end())
                nodes.clear()
                stack.push_front(<PyObject*> node)
                node = <Tree> stack.back()
                stack.pop_back()
            yield node.value  # leaf node

            peek = <Tree> stack.back()
            if peek is tree:
                if not r_stack.empty():
                    # visit exhausted traversed nodes
                    while not stack.empty():
                        peek = <Tree> stack.front()
                        if peek._depth() < (<Tree> r_stack.back())._depth():
                            break
                        yield peek.value
                        stack.pop_front()
                    node = <Tree> r_stack.back()
                    r_stack.pop_back()
                    continue

                while not stack.empty():
                    peek = <Tree> stack.front()
                    if peek is tree:
                        break
                    yield peek.value
                    stack.pop_front()
                break

            node = <Tree> stack.back()
            stack.pop_back()

    def _pre(self, Tree tree, bint reverse):
        if PyDict_Size(tree._children) == 0:
            return

        cdef Tree node, peek
        cdef PyObject* tmp
        cdef Py_ssize_t pos
        cdef Stack[PyObject*] stack, nodes

        node = tree
        pos = 0
        while PyDict_Next(node._children, &pos, NULL, &tmp):
            _ = nodes.push_back(tmp) if reverse else nodes.push_front(tmp)
        stack.insert(stack.end(), nodes.begin(), nodes.end())
        nodes.clear()

        while not stack.empty():
            node = <Tree> stack.back()
            stack.pop_back()
            yield node.value
            if PyDict_Size(node._children) == 0:
                continue

            pos = 0
            while PyDict_Next(node._children, &pos, NULL, &tmp):
                _ = nodes.push_back(tmp) if reverse else nodes.push_front(tmp)
            stack.insert(stack.end(), nodes.begin(), nodes.end())
            nodes.clear()


@cython.freelist(12)
cdef class Tree:
    """A General Tree datatype.

    Implements: Container, Iterable, Sized, Collection.
    """
    cdef dict _children
    cdef tuple _parents
    cdef readonly Tree parent
    cdef readonly object value
    cdef PyObject* _empty_ptr

    Cursor: ClassVar[type] = Cursor
    _empty_: ClassVar[dict] = {}

    @property
    def __hash__(self):
        return None

    @property
    def __reversed__(self):
        return None

    @classmethod
    def __class_getitem__(cls, keys):
        # TODO: investigate around this trick, test number of args
        return Tree

    def __cinit__(self, *args, **kwds):
        self.value = None
        self.parent = None
        self._parents = None

        # NOTE: dummy `singleton' dict for new empty Tree nodes.
        self._empty_ptr = <PyObject*> Tree._empty_
        self._children = Tree._empty_

    def __init__(self, *args, **kwds):
        """Initialize self.  See help(type(self)) for accurate signature."""
        if args or kwds:
            raise ValueError("Tree doesn't take any arguments")

    @staticmethod
    cdef Tree _new_node(object value, Tree parent):
        if parent is None:
            raise TypeError("Tree internal error!")

        if value.__hash__ is None:
            raise TypeError("Tree node value should be hashable")

        cdef Tree node = Tree.__new__(Tree)
        node.value = value
        node.parent = parent
        return node

    @cython.inline
    cdef void _ensure_children(self) noexcept:
        if <PyObject*> self._children is self._empty_ptr:
            self._children = {}

    cdef tuple parents(self):
        if self._parents is not None:
            return self._parents

        cdef Tree node
        cdef Stack[PyObject*] stack
        cdef Py_ssize_t i = 0
        cdef PyObject* ref

        node = self.parent
        while node is not None:
            stack.push_front(<PyObject*> node)
            node = node.parent

        self._parents = PyTuple_New(stack.size())
        for ref in stack:
            PyTuple_SET_ITEM(self._parents, i, <object> ref)
            i += 1

        return self._parents

    cdef Cursor _cursor(self):
        cdef Stack[PyObject*] stack
        cdef PyObject* ref
        cdef Cursor cursor = Cursor.__new__(Cursor)
        cdef Tree node = self

        while node.parent is not None:
            stack.push_front(<PyObject*> node.value)
            node = node.parent

        cursor._values = tuple(<object> ref for ref in stack)
        return cursor

    def __invert__(self):
        """Returns this node's `Cursor`.

        Cursor is a tuple like object, values of `Cursor` represents
        a path to the node from the Tree's `root`.
        """
        return self._cursor()

    def __matmul__(self, args) -> Tree.Cursor[_VT]:
        """Returns a new `Cursor`."""
        return Cursor(args) if not isinstance(args, tuple) else Cursor(*args)

    @property
    def root(self):
        """Top `Tree`'s node."""
        return (
            None
            if self.parent is not None
            else next(iter(self._children.values()))
            if self._children
            else None
        )

    cdef inline Py_ssize_t _depth(self) noexcept:
        return len(self.parents())

    @property
    def depth(self):
        """Number of nodes from `Tree`'s `root` to self."""
        return self._depth()

    cdef Py_ssize_t _height(self):
        if PyDict_Size(self._children) == 0:
            return 0

        cdef Tree node = self
        cdef PyObject* value
        cdef Stack[PyObject*] stack
        cdef Py_ssize_t height = 0, pos = 0

        while PyDict_Next(node._children, &pos, NULL, &value):
            stack.push_front(value)

        while not stack.empty():
            node = <Tree> stack.back()
            stack.pop_back()
            height = sz_max(height, node._depth())
            pos = 0
            while PyDict_Next(node._children, &pos, NULL, &value):
                stack.push_front(value)

        return height - self._depth()

    @property
    def height(self):
        """Number of nodes from self to the deepest contained `leaf` node."""
        return self._height()

    @property
    def diameter(self):
        # FIXME: missing implementation
        raise NotImplementedError

    def __len__(self):
        """Returns the total of self contained nodes."""
        cdef Tree node
        cdef Stack[PyObject*] stack
        cdef Py_ssize_t size, pos
        cdef PyObject* value

        size = PyDict_Size(self._children)
        pos = 0
        while PyDict_Next(self._children, &pos, NULL, &value):
            stack.push_front(value)

        while not stack.empty():
            node = <Tree> stack.back()
            stack.pop_back()
            size += PyDict_Size(node._children)
            pos = 0
            while PyDict_Next(node._children, &pos, NULL, &value):
                stack.push_front(value)
        return size

    def __contains__(self, object value):
        return value in self._bfs(Nodes.All, None)

    cdef Tree _get_node_at_cursor(self, object cursor, bint parent):
        cdef Tree node = self
        cdef PyObject* ref

        if isinstance(cursor, Cursor):
            for value in cursor:
                if (ref := PyDict_GetItem(node._children, value)) is NULL:
                    if parent:
                        self._ensure_children()
                        node._children[value] = Tree._new_node(value, node)
                        node = node._children[value]
                    else:
                        raise KeyError(value)
                else:
                    node = <Tree> ref
        else:
            if (ref := PyDict_GetItem(node._children, cursor)) is NULL:
                if parent:
                    self._ensure_children()
                    node = Tree._new_node(cursor, node)
                    node._children[cursor] = node
                else:
                    raise KeyError(cursor)
            else:
                node = <Tree> ref
        return node

    cpdef add(self, object value, Cursor cursor=None, bool parent=False):
        cdef Tree node
        node = self._get_node_at_cursor(cursor, parent) if cursor is not None else self
        if value not in node._children:
            if node.parent is None:
                node._children.clear()
            self._ensure_children()
            node._children[value] = Tree._new_node(value, node)

    def __setitem__(self, object key, object value):
        self.add(value, key, parent=False)

    def __getitem__(self, object value):
        return self._get_node_at_cursor(value, parent=False)

    def __delitem__(self, object value):
        cdef Tree node = self._get_node_at_cursor(value, parent=False)
        del node.parent._children[node.value]

    cpdef clear(self):
        """Removes all self contained nodes."""
        self._children.clear()

    def children(self):
        """Returns an `Iterator` over children node's value."""
        return _CHILD(self, False)

    def siblings(self):
        """Returns an `Iterator` over sibling node's value."""
        return _CHILD(self, True)

    def dfs(self, object order="pre", bool reverse=False):
        """Returns an `Iterator` over self contained node's value in a depth first traversal order."""
        return _DFS(self, order, reverse)

    def __iter__(self):
        """Returns an `Iterator` over self contained node's value in a bfs traversal oder."""
        return _BFS(self, Nodes.All, None)

    def bfs(self):
        """Returns an `Iterator` over self contained node's value in a bfs traversal oder."""
        return _BFS(self, Nodes.All, None)

    def leaves(self, object depth = None):
        """Returns an `Iterator` over leaf node's values."""
        return _BFS(self, Nodes.Leaves, depth)

    def branches(self, object depth = None):
        """Returns an `Iterator` over branche node's values."""
        return _BFS(self, Nodes.Branches, depth)

    def __bool__(self) -> bool:
        return PyDict_Size(self._children) != 0

    def __str__(self):
        return str(self.value)

    def __repr__(self) -> str:
        # FIXME: * bad indent when called on Node
        #        * leaves begin with ' ,'
        cdef Tree node

        stack: deque[Tree[_VT]] = deque(reversed(self._children.values()))
        tab = "  "
        start: int = self.depth
        prev_depth: int = start - 1
        name = f"[{self.value}]" if self.parent is not None else ""
        string: deque[str] = deque((f"{self.__class__.__name__}{name}(",))
        expand = self.height > 3

        while stack:
            node = stack.pop()
            size = len(stack)
            depth = node._depth() - start

            if depth == prev_depth:  # siblings
                string += ", "
                indent = ""
            elif depth <= prev_depth - 1:  # back from children
                string += "}, \n" if expand else "}, "
                indent = tab * (depth + 1)
            else:
                indent = "\n" + (tab * (prev_depth + 2))

            string += f"{indent}{node.value!r}: {{"  # print value
            # string += f"{node.value!r}: {{"  # print value
            stack.extend(reversed(node._children.values()))

            if not len(stack) - size:  # empty node
                string += "}"
            prev_depth = depth

        for d in range(prev_depth, 0, -1):  # closes remaining nodes
            string += f"}}\n{tab * d}" if expand else "}}"
        string += ")"

        return "".join(string)

    def __getstate__(self):
        return { "parent": self.parent, "value": self.value, "children": self._children }

    def __setstate__(self, dict state):
        cdef dict children
        self.value = state["value"]
        self.parent = state["parent"]
        children = state["children"]
        if PyDict_Size(children) > 0:
            self._children = children

    def __reduce__(self):
        return (Tree.__new__, (Tree,), self.__getstate__(), None, None, None)



def test():
    t = Tree()
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
