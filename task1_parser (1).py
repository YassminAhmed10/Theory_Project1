class RegexNode:
    CHAR   = "CHAR"
    CONCAT = "CONCAT"
    UNION  = "UNION"
    STAR   = "STAR"
    PLUS   = "PLUS"
    QUEST  = "QUEST"
    END    = "END"

    def __init__(self, ntype, value=None, left=None, right=None):
        self.ntype  = ntype
        self.value  = value
        self.left   = left
        self.right  = right
        self.pos       = None
        self.nullable  = False
        self.firstpos  = set()
        self.lastpos   = set()

    def __repr__(self):
        if self.ntype == RegexNode.CHAR:
            return f"CHAR({self.value!r})"
        if self.ntype == RegexNode.END:
            return "END(#)"
        return f"{self.ntype}(left={self.left}, right={self.right})"

def _tokenise(pattern: str) -> list[str]:
    tokens = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if ch == "\\":
            i += 1
            if i < len(pattern):
                tokens.append(pattern[i])
        else:
            tokens.append(ch)
        i += 1
    return tokens

_OPERATORS   = set("|*+?()")
_UNARY_POST  = set("*+?")
_LEFT_CONCAT = set("*+?)") | set("abcdefghijklmnopqrstuvwxyz"
                                  "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                                  "0123456789")
_RIGHT_CONCAT = set("(")   | set("abcdefghijklmnopqrstuvwxyz"
                                  "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                                  "0123456789")

def _insert_concat(tokens: list[str]) -> list[str]:
    result = []
    for i, tok in enumerate(tokens):
        result.append(tok)
        if i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if (tok not in set("|(") and nxt not in set("|*+?)")):
                result.append(".")
    return result

class _Parser:
    def __init__(self, tokens: list[str]):
        self._tokens = tokens
        self._pos    = 0

    def _peek(self) -> str | None:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _consume(self, expected: str | None = None) -> str:
        tok = self._tokens[self._pos]
        if expected is not None and tok != expected:
            raise SyntaxError(
                f"Expected {expected!r} but got {tok!r} "
                f"at position {self._pos}"
            )
        self._pos += 1
        return tok

    def parse_expr(self) -> RegexNode:
        node = self.parse_term()
        while self._peek() == "|":
            self._consume("|")
            right = self.parse_term()
            node = RegexNode(RegexNode.UNION, left=node, right=right)
        return node

    def parse_term(self) -> RegexNode:
        node = self.parse_factor()
        while self._peek() == ".":
            self._consume(".")
            right = self.parse_factor()
            node = RegexNode(RegexNode.CONCAT, left=node, right=right)
        return node

    def parse_factor(self) -> RegexNode:
        node = self.parse_atom()
        while self._peek() in _UNARY_POST:
            op = self._consume()
            ntype = {
                "*": RegexNode.STAR,
                "+": RegexNode.PLUS,
                "?": RegexNode.QUEST,
            }[op]
            node = RegexNode(ntype, left=node)
        return node

    def parse_atom(self) -> RegexNode:
        tok = self._peek()
        if tok is None:
            raise SyntaxError("Unexpected end of expression")
        if tok == "(":
            self._consume("(")
            node = self.parse_expr()
            self._consume(")")
            return node
        if tok in _OPERATORS:
            raise SyntaxError(f"Unexpected operator {tok!r} at position {self._pos}")
        self._consume()
        return RegexNode(RegexNode.CHAR, value=tok)

def parse_regex(pattern: str) -> RegexNode:
    if not pattern.strip():
        raise ValueError("Regular expression cannot be empty.")

    tokens = _tokenise(pattern)
    tokens = _insert_concat(tokens)

    parser  = _Parser(tokens)
    tree    = parser.parse_expr()

    if parser._pos != len(parser._tokens):
        remaining = "".join(parser._tokens[parser._pos:])
        raise SyntaxError(f"Unexpected characters at end: {remaining!r}")

    end_marker = RegexNode(RegexNode.END, value="#")
    root       = RegexNode(RegexNode.CONCAT, left=tree, right=end_marker)
    return root

def tree_to_dict(node: RegexNode) -> dict:
    if node is None:
        return None
    d = {
        "type"  : node.ntype,
        "value" : node.value,
        "pos"   : node.pos,
        "left"  : tree_to_dict(node.left),
        "right" : tree_to_dict(node.right),
    }
    return d

if __name__ == "__main__":
    patterns = ["(aa|b)*a", "ab*c", "(a|b)+", "a?b", "(ab|cd)*e"]
    for p in patterns:
        root = parse_regex(p)
        print(f"Pattern: {p!r:20s}  →  root type: {root.ntype}")