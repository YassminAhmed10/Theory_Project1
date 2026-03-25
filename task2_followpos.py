from task1_parser import RegexNode, parse_regex

def assign_positions(root: RegexNode) -> dict[int, RegexNode]:
    pos_map: dict[int, RegexNode] = {}
    counter = [0]

    def _walk(node: RegexNode):
        if node is None:
            return
        if node.ntype in (RegexNode.CHAR, RegexNode.END):
            counter[0] += 1
            node.pos = counter[0]
            pos_map[node.pos] = node
        else:
            _walk(node.left)
            _walk(node.right)

    _walk(root)
    return pos_map

def compute_nullable_first_last(node: RegexNode) -> None:
    if node is None:
        return

    compute_nullable_first_last(node.left)
    compute_nullable_first_last(node.right)

    nt = node.ntype

    if nt in (RegexNode.CHAR, RegexNode.END):
        node.nullable = False
        node.firstpos = {node.pos}
        node.lastpos  = {node.pos}

    elif nt == RegexNode.UNION:
        node.nullable = node.left.nullable or node.right.nullable
        node.firstpos = node.left.firstpos | node.right.firstpos
        node.lastpos  = node.left.lastpos  | node.right.lastpos

    elif nt == RegexNode.CONCAT:
        node.nullable = node.left.nullable and node.right.nullable
        if node.left.nullable:
            node.firstpos = node.left.firstpos | node.right.firstpos
        else:
            node.firstpos = node.left.firstpos
        if node.right.nullable:
            node.lastpos = node.left.lastpos | node.right.lastpos
        else:
            node.lastpos = node.right.lastpos

    elif nt == RegexNode.STAR:
        node.nullable = True
        node.firstpos = node.left.firstpos
        node.lastpos  = node.left.lastpos

    elif nt == RegexNode.PLUS:
        node.nullable = node.left.nullable
        node.firstpos = node.left.firstpos
        node.lastpos  = node.left.lastpos

    elif nt == RegexNode.QUEST:
        node.nullable = True
        node.firstpos = node.left.firstpos
        node.lastpos  = node.left.lastpos

    else:
        raise ValueError(f"Unknown node type: {nt!r}")

def compute_followpos(root: RegexNode,
                      pos_map: dict[int, RegexNode]) -> dict[int, set[int]]:
    followpos: dict[int, set[int]] = {p: set() for p in pos_map}

    def _walk(node: RegexNode):
        if node is None:
            return

        if node.ntype == RegexNode.CONCAT:
            for i in node.left.lastpos:
                followpos[i] |= node.right.firstpos

        elif node.ntype in (RegexNode.STAR, RegexNode.PLUS):
            for i in node.left.lastpos:
                followpos[i] |= node.left.firstpos

        _walk(node.left)
        _walk(node.right)

    _walk(root)
    return followpos

def annotate_tree(root: RegexNode):
    pos_map = assign_positions(root)
    compute_nullable_first_last(root)
    fp = compute_followpos(root, pos_map)
    return pos_map, fp

def followpos_table_str(followpos: dict[int, set[int]],
                        pos_map:   dict[int, RegexNode]) -> str:
    lines = ["pos | symbol | followpos"]
    lines.append("-" * 35)
    for p in sorted(followpos):
        sym = pos_map[p].value
        fp  = sorted(followpos[p])
        lines.append(f"  {p:2d} |   {sym!r:5s} | {fp}")
    return "\n".join(lines)

if __name__ == "__main__":
    pattern = "(aa|b)*a"
    root    = parse_regex(pattern)
    pos_map, followpos = annotate_tree(root)

    print(f"Pattern : {pattern!r}")
    print(f"Root firstpos : {sorted(root.firstpos)}")
    print()
    print(followpos_table_str(followpos, pos_map))