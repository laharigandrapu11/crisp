from __future__ import annotations
from typing import Optional

NYT_SYMBOL = -1
INTERNAL   = -2


class Node:
    __slots__ = ("weight", "number", "symbol", "parent", "left", "right")

    def __init__(
        self,
        weight: int = 0,
        number: int = 0,
        symbol: int = NYT_SYMBOL,
        parent: Optional["Node"] = None,
        left:   Optional["Node"] = None,
        right:  Optional["Node"] = None,
    ) -> None:
        self.weight = weight
        self.number = number
        self.symbol = symbol
        self.parent = parent
        self.left   = left
        self.right  = right

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    @property
    def is_nyt(self) -> bool:
        return self.symbol == NYT_SYMBOL

    def __repr__(self) -> str:
        sym = "NYT" if self.is_nyt else ("INT" if self.symbol == INTERNAL else str(self.symbol))
        return f"Node(#{self.number} w={self.weight} sym={sym})"


class HuffmanTree:
    MAX_NODES = 511  # 256 leaves + 255 internal nodes

    def __init__(self) -> None:
        self._current_number = self.MAX_NODES
        self.root = Node(weight=0, number=self._current_number, symbol=NYT_SYMBOL)
        self.nyt  = self.root
        self.symbols_map: dict[int, Node] = {}

    def path_from_root(self, node: Node) -> str:
        """Returns '' for root — handles the first-symbol NYT edge case."""
        bits: list[str] = []
        current = node
        while current.parent is not None:
            parent = current.parent
            bits.append("0" if parent.left is current else "1")
            current = current.parent
        bits.reverse()
        return "".join(bits)

    def find_highest_in_block(
        self,
        weight: int,
        is_leaf: bool,
        exclude_a: Optional[Node] = None,
        exclude_b: Optional[Node] = None,
    ) -> Optional[Node]:
        """Core primitive for Vitter's update — finds typed block leader."""
        best: Optional[Node] = None
        stack: list[Node] = [self.root]
        while stack:
            n = stack.pop()
            if n is not exclude_a and n is not exclude_b:
                if n.weight == weight and n.is_leaf == is_leaf:
                    if best is None or n.number > best.number:
                        best = n
            if n.left is not None:
                stack.append(n.left)
            if n.right is not None:
                stack.append(n.right)
        return best

    def find_typed_leader(self, node: Node) -> Node:
        """Highest-numbered node in node's (weight, is_leaf) block. Returns node if already leader."""
        best = self.find_highest_in_block(
            weight=node.weight,
            is_leaf=node.is_leaf,
            exclude_a=node,
            exclude_b=node.parent,
        )
        if best is None or best.number < node.number:
            return node
        return best

    def swap(self, a: Node, b: Node) -> None:
        """Swap tree positions of a and b — each node keeps its own subtree."""
        if a is b:
            return
        if a is b.parent or b is a.parent:
            return

        pa, pb = a.parent, b.parent
        assert pa is not None and pb is not None, "cannot swap root"

        if pa.left is a:
            pa.left = b
        else:
            pa.right = b
        if pb.left is b:
            pb.left = a
        else:
            pb.right = a

        a.parent, b.parent = pb, pa
        a.number, b.number = b.number, a.number

    def split_nyt(self, symbol: int) -> Node:
        """
        Expand NYT into internal node with two children:
            left  = new NYT  (lower number)
            right = new leaf (higher number)
        Leaf gets higher number so leaves-before-internal holds after updates.
        """
        old_nyt = self.nyt

        new_leaf = Node(weight=0, number=self._current_number - 1, symbol=symbol,    parent=old_nyt)
        new_nyt  = Node(weight=0, number=self._current_number - 2, symbol=NYT_SYMBOL, parent=old_nyt)
        self._current_number -= 2

        old_nyt.left   = new_nyt
        old_nyt.right  = new_leaf
        old_nyt.symbol = INTERNAL

        self.nyt = new_nyt
        self.symbols_map[symbol] = new_leaf
        return new_leaf

    def collect_nodes(self) -> list[Node]:
        nodes: list[Node] = []
        stack: list[Node] = [self.root]
        while stack:
            n = stack.pop()
            nodes.append(n)
            if n.left is not None:
                stack.append(n.left)
            if n.right is not None:
                stack.append(n.right)
        return nodes

    def validate_invariants(self) -> None:
        """Assert all 6 Vitter invariants. Call after every encode step in tests."""
        nodes = self.collect_nodes()

        for n in nodes:
            if n.is_leaf:
                assert n.left is None and n.right is None, f"{n!r} has partial children"
            else:
                assert n.left is not None and n.right is not None, f"{n!r} missing child"
                assert n.left.parent is n, f"{n!r}.left.parent mismatch"
                assert n.right.parent is n, f"{n!r}.right.parent mismatch"

        for n in nodes:
            if not n.is_leaf:
                assert n.weight == n.left.weight + n.right.weight, \
                    f"{n!r} weight != sum of children"

        numbers = [n.number for n in nodes]
        assert len(numbers) == len(set(numbers)), "duplicate node numbers"

        nodes_sorted = sorted(nodes, key=lambda n: n.number)
        for i in range(1, len(nodes_sorted)):
            prev, curr = nodes_sorted[i - 1], nodes_sorted[i]
            assert prev.weight <= curr.weight, \
                f"sibling property violated: #{prev.number} w={prev.weight} > #{curr.number} w={curr.weight}"

        weight_classes: dict[int, list[Node]] = {}
        for n in nodes:
            weight_classes.setdefault(n.weight, []).append(n)
        for w, group in weight_classes.items():
            max_leaf_num = max((n.number for n in group if n.is_leaf), default=-1)
            min_int_num  = min((n.number for n in group if not n.is_leaf), default=10**9)
            assert max_leaf_num < min_int_num, \
                f"Vitter invariant violated at weight {w}: max leaf #{max_leaf_num} >= min internal #{min_int_num}"

    def print_tree(self) -> None:
        from collections import deque
        q: deque[tuple[Optional[Node], int]] = deque([(self.root, 0)])
        while q:
            node, depth = q.popleft()
            if node is None:
                continue
            sym = "NYT" if node.is_nyt else ("INT" if node.symbol == INTERNAL else f"sym={node.symbol}")
            print("  " * depth + f"#{node.number} w={node.weight} [{sym}]")
            q.append((node.left,  depth + 1))
            q.append((node.right, depth + 1))
