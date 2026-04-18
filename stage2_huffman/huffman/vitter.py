from __future__ import annotations
from .tree import HuffmanTree, Node


def _vitter_update_one(tree: HuffmanTree, node: Node) -> Node:
    typed_leader = tree.find_typed_leader(node)
    if typed_leader is not node:
        tree.swap(node, typed_leader)

    if node.is_leaf:
        slide_target = tree.find_highest_in_block(
            weight=node.weight, is_leaf=False, exclude_a=node, exclude_b=node.parent,
        )
    else:
        slide_target = tree.find_highest_in_block(
            weight=node.weight + 1, is_leaf=True, exclude_a=node, exclude_b=node.parent,
        )

    pre_slide_parent = node.parent
    internal_slide_happened = False

    if slide_target is not None and slide_target.number > node.number:
        if not node.is_leaf:
            internal_slide_happened = True
        tree.swap(node, slide_target)

    node.weight += 1

    if internal_slide_happened:
        return pre_slide_parent
    return node.parent


def vitter_update(tree: HuffmanTree, start: Node) -> None:
    current = start
    while current is not tree.root:
        current = _vitter_update_one(tree, current)
    tree.root.weight += 1


def encode(data: bytes) -> tuple[str, int]:
    tree = HuffmanTree()
    bits: list[str] = []

    for byte in data:
        leaf = tree.symbols_map.get(byte)
        if leaf is not None:
            bits.append(tree.path_from_root(leaf))
            vitter_update(tree, leaf)
        else:
            bits.append(tree.path_from_root(tree.nyt))
            bits.append(format(byte, "08b"))
            new_leaf = tree.split_nyt(byte)
            vitter_update(tree, new_leaf)

    bit_string = "".join(bits)
    return bit_string, len(bit_string)


def decode(bits: str) -> bytes:
    tree = HuffmanTree()
    output: list[int] = []
    pos = 0
    n = len(bits)

    while pos < n:
        if tree.nyt is tree.root:
            if pos + 8 > n:
                break
            byte = int(bits[pos:pos + 8], 2)
            pos += 8
            output.append(byte)
            new_leaf = tree.split_nyt(byte)
            vitter_update(tree, new_leaf)
            continue

        current = tree.root
        while not current.is_leaf:
            if pos >= n:
                break
            bit = bits[pos]
            pos += 1
            current = current.left if bit == "0" else current.right

        if not current.is_leaf:
            break

        if current.is_nyt:
            if pos + 8 > n:
                break
            byte = int(bits[pos:pos + 8], 2)
            pos += 8
            output.append(byte)
            new_leaf = tree.split_nyt(byte)
            vitter_update(tree, new_leaf)
        else:
            byte = current.symbol
            output.append(byte)
            vitter_update(tree, current)

    return bytes(output)


def compress(text: str) -> tuple[bytes, int, int]:
    from .bitpack import bits_to_bytes
    data = text.encode("utf-8")
    bit_string, total_bits = encode(data)
    return bits_to_bytes(bit_string), len(data), total_bits


def compress_with_tree(text: str) -> tuple[bytes, int, int, HuffmanTree]:
    from .bitpack import bits_to_bytes

    data = text.encode("utf-8")
    tree = HuffmanTree()
    bits: list[str] = []

    for byte in data:
        leaf = tree.symbols_map.get(byte)
        if leaf is not None:
            bits.append(tree.path_from_root(leaf))
            vitter_update(tree, leaf)
        else:
            bits.append(tree.path_from_root(tree.nyt))
            bits.append(format(byte, "08b"))
            new_leaf = tree.split_nyt(byte)
            vitter_update(tree, new_leaf)

    bit_string = "".join(bits)
    raw_bytes = bits_to_bytes(bit_string)
    return raw_bytes, len(data), len(bit_string), tree


def decompress(raw_data: bytes) -> str:
    from .bitpack import bytes_to_bits
    return decode(bytes_to_bits(raw_data)).decode("utf-8")
