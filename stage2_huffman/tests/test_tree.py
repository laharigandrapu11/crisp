
from __future__ import annotations

import pytest

from huffman.tree import HuffmanTree, Node, NYT_SYMBOL, INTERNAL


class TestInitialState:
    def test_root_is_nyt(self):
        t = HuffmanTree()
        assert t.root.is_nyt
        assert t.root.symbol == NYT_SYMBOL
        assert t.root.weight == 0

    def test_nyt_equals_root_initially(self):
        t = HuffmanTree()
        assert t.nyt is t.root

    def test_symbols_map_empty_initially(self):
        t = HuffmanTree()
        assert t.symbols_map == {}

    def test_initial_root_has_max_number(self):
        t = HuffmanTree()
        assert t.root.number == HuffmanTree.MAX_NODES

    def test_empty_tree_is_valid(self):
        HuffmanTree().validate_invariants()


class TestSplitNyt:
    def test_split_creates_two_children(self):
        t = HuffmanTree()
        leaf = t.split_nyt(97)
        assert t.root.left is not None
        assert t.root.right is not None
        assert t.root.left.is_leaf
        assert t.root.right.is_leaf

    def test_split_makes_old_nyt_internal(self):
        t = HuffmanTree()
        t.split_nyt(97)
        assert t.root.symbol == INTERNAL

    def test_split_new_leaf_has_correct_symbol(self):
        t = HuffmanTree()
        leaf = t.split_nyt(97)
        assert leaf.symbol == 97
        assert not leaf.is_nyt

    def test_split_new_nyt_is_lower_numbered(self):
        t = HuffmanTree()
        leaf = t.split_nyt(97)
        new_nyt = t.nyt
        assert new_nyt.number < leaf.number

    def test_split_registers_symbol(self):
        t = HuffmanTree()
        leaf = t.split_nyt(97)
        assert t.symbols_map[97] is leaf

    def test_split_updates_nyt_pointer(self):
        t = HuffmanTree()
        old_nyt = t.nyt
        t.split_nyt(97)
        assert t.nyt is not old_nyt
        assert t.nyt.is_nyt

    def test_split_plus_update_preserves_invariants(self):
        from huffman import vitter
        t = HuffmanTree()
        for byte in [65, 66, 67, 68]:
            new_leaf = t.split_nyt(byte)
            vitter.vitter_update(t, new_leaf)
            t.validate_invariants()


class TestPathFromRoot:
    def test_root_has_empty_path(self):
        t = HuffmanTree()
        assert t.path_from_root(t.root) == ""

    def test_left_child_is_zero(self):
        t = HuffmanTree()
        t.split_nyt(97)
        assert t.path_from_root(t.root.left) == "0"

    def test_right_child_is_one(self):
        t = HuffmanTree()
        t.split_nyt(97)
        assert t.path_from_root(t.root.right) == "1"

    def test_deeper_path(self):
        t = HuffmanTree()
        t.split_nyt(97)
        t.split_nyt(98)         
        leaf_98 = t.symbols_map[98]
        assert t.path_from_root(leaf_98) == "01"


class TestSwap:
    def test_swap_exchanges_numbers(self):
        t = HuffmanTree()
        t.split_nyt(97)
        t.split_nyt(98)
        a = t.symbols_map[97]
        b = t.symbols_map[98]
        n_a_before, n_b_before = a.number, b.number
        t.swap(a, b)
        assert a.number == n_b_before
        assert b.number == n_a_before

    def test_swap_exchanges_parents(self):
        t = HuffmanTree()
        t.split_nyt(97)
        t.split_nyt(98)
        a = t.symbols_map[97]        
        b = t.symbols_map[98]        
        pa_before, pb_before = a.parent, b.parent
        t.swap(a, b)
        assert a.parent is pb_before
        assert b.parent is pa_before

    def test_swap_preserves_children(self):
        t = HuffmanTree()
        t.split_nyt(97)
        t.split_nyt(98)
        internal = t.root.left       
        leaf_a = t.symbols_map[97]
        l_before, r_before = internal.left, internal.right
        t.swap(internal, leaf_a)
        assert internal.left is l_before
        assert internal.right is r_before

    def test_swap_self_is_noop(self):
        t = HuffmanTree()
        t.split_nyt(97)
        leaf = t.symbols_map[97]
        num_before = leaf.number
        t.swap(leaf, leaf)
        assert leaf.number == num_before

    def test_swap_refuses_parent_child(self):
        t = HuffmanTree()
        t.split_nyt(97)
        leaf = t.symbols_map[97]
        root = t.root
        n_before = leaf.number
        t.swap(root, leaf)           
        assert leaf.number == n_before
        t.swap(leaf, root)           
        assert leaf.number == n_before


class TestBlockSearch:
    def test_leader_of_only_node_is_itself(self):
        t = HuffmanTree()
        t.split_nyt(97)
        leaf = t.symbols_map[97]
        assert t.find_typed_leader(leaf) is leaf

    def test_leader_is_highest_numbered(self):
        t = HuffmanTree()
        t.split_nyt(97)
        t.split_nyt(98)
        t.split_nyt(99)
        nyt = t.nyt
        leaf_97 = t.symbols_map[97]
        leaf_98 = t.symbols_map[98]
        leaf_99 = t.symbols_map[99]
        leader = t.find_typed_leader(nyt)
        assert leader is not nyt
        assert leader.weight == 0
        assert leader.is_leaf

    def test_typed_distinguishes_leaves_from_internals(self):
        t = HuffmanTree()
        t.split_nyt(97)
        nyt = t.nyt
        leaf_leader = t.find_highest_in_block(
            weight=0, is_leaf=True, exclude_a=nyt, exclude_b=nyt.parent,
        )
        assert leaf_leader is not None
        assert leaf_leader.is_leaf

        internal_leader = t.find_highest_in_block(
            weight=0, is_leaf=False, exclude_a=nyt, exclude_b=nyt.parent,
        )
        assert internal_leader is None

    def test_exclude_parent(self):
        t = HuffmanTree()
        t.split_nyt(97)
        leaf = t.symbols_map[97]
        nyt = t.find_highest_in_block(
            weight=0, is_leaf=True, exclude_a=leaf, exclude_b=leaf.parent,
        )
        assert nyt is t.nyt
