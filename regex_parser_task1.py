"""
=============================================================
TASK 1 — REGEX PARSER
=============================================================
Converts a raw regex string into an Augmented Syntax Tree
(AST) ready for DFA construction via the direct method.

Pipeline:
  raw string
    → tokenize()       (lexer)
    → insert_concat()  (add explicit · operator)
    → to_postfix()     (shunting-yard)
    → build_ast()      (stack-based tree builder)
    → augment()        (append # end-marker, number leaves)

Public API:
  parse_regex(src: str) -> ASTNode
=============================================================
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
import copy


# ─────────────────────────────────────────────
# Token types
# ─────────────────────────────────────────────
class TT:
    CHAR    = "CHAR"
    STAR    = "STAR"
    PLUS    = "PLUS"
    QUEST   = "QUEST"
    OR      = "OR"
    CONCAT  = "CONCAT"
    LPAREN  = "LPAREN"
    RPAREN  = "RPAREN"
    EPS     = "EPS"


@dataclass
class Token:
    type: str
    value: Optional[str] = None   # only set for CHAR tokens

    def __repr__(self):
        return f"Token({self.type}{', ' + repr(self.value) if self.value else ''})"


# ─────────────────────────────────────────────
# AST node types
# ─────────────────────────────────────────────
@dataclass
class ASTNode:
    """
    kind in {'leaf', 'eps', 'star', 'concat', 'or'}

    Leaf nodes carry:
      symbol : str          the character (or '#' for end-marker)
      pos    : int | None   leaf position number (set during augmentation)

    Internal nodes carry:
      left, right : ASTNode | None   children
      child       : ASTNode | None   used by 'star'
    """
    kind:   str
    symbol: Optional[str]    = None
    pos:    Optional[int]    = None
    left:   Optional[ASTNode] = field(default=None, repr=False)
    right:  Optional[ASTNode] = field(default=None, repr=False)
    child:  Optional[ASTNode] = field(default=None, repr=False)

    def __repr__(self):
        if self.kind == "leaf":
            return f"Leaf({self.symbol!r}, pos={self.pos})"
        if self.kind == "eps":
            return "ε"
        kids = []
        if self.left:  kids.append(f"left={self.left!r}")
        if self.right: kids.append(f"right={self.right!r}")
        if self.child: kids.append(f"child={self.child!r}")
        return f"{self.kind.upper()}({', '.join(kids)})"


# ─────────────────────────────────────────────
# STEP 1 — Lexer / Tokenizer
# ─────────────────────────────────────────────
def tokenize(src: str) -> List[Token]:
    """
    Read the regex string character by character and emit Token objects.
    Supported:
      a-z A-Z 0-9 _ -   → CHAR
      *                 → STAR
      +                 → PLUS
      ?                 → QUEST
      |                 → OR
      ( )               → LPAREN / RPAREN
      ε  or  eps        → EPS (empty string literal)
    Whitespace is silently skipped.
    """
    if not src or not src.strip():
        raise ValueError("Input regex is empty.")

    tokens: List[Token] = []
    i = 0
    while i < len(src):
        c = src[i]

        if c == " ":
            i += 1
            continue

        if src[i:i+3] == "eps":
            tokens.append(Token(TT.EPS))
            i += 3
        elif c == "ε":
            tokens.append(Token(TT.EPS))
            i += 1
        elif c == "*":
            tokens.append(Token(TT.STAR))
            i += 1
        elif c == "+":
            tokens.append(Token(TT.PLUS))
            i += 1
        elif c == "?":
            tokens.append(Token(TT.QUEST))
            i += 1
        elif c == "|":
            tokens.append(Token(TT.OR))
            i += 1
        elif c == "(":
            tokens.append(Token(TT.LPAREN))
            i += 1
        elif c == ")":
            tokens.append(Token(TT.RPAREN))
            i += 1
        elif c.isalnum() or c in ("_", "-"):
            tokens.append(Token(TT.CHAR, c))
            i += 1
        else:
            raise ValueError(f"Unexpected character '{c}' at index {i}.")

    return tokens


# ─────────────────────────────────────────────
# STEP 2 — Insert explicit concatenation
# ─────────────────────────────────────────────
# A · B is implied wherever a "right-operand-starter" follows a
# "left-operand-ender" without an explicit binary operator.
_LEFT_OK  = {TT.CHAR, TT.EPS, TT.STAR, TT.PLUS, TT.QUEST, TT.RPAREN}
_RIGHT_OK = {TT.CHAR, TT.EPS, TT.LPAREN}

def insert_concat(tokens: List[Token]) -> List[Token]:
    """
    Insert explicit CONCAT tokens where concatenation is implied.
    Example:  a b  →  a · b
              a* b →  a* · b
              a(b) →  a · (b)
    """
    result: List[Token] = []
    for i, tok in enumerate(tokens):
        result.append(tok)
        if i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if tok.type in _LEFT_OK and nxt.type in _RIGHT_OK:
                result.append(Token(TT.CONCAT))
    return result


# ─────────────────────────────────────────────
# STEP 3 — Shunting-yard → postfix
# ─────────────────────────────────────────────
# Precedence: unary (*, +, ?) > concat (·) > alternation (|)
_PREC: dict[str, int] = {
    TT.OR:     1,
    TT.CONCAT: 2,
    TT.STAR:   3,
    TT.PLUS:   3,
    TT.QUEST:  3,
}
_UNARY = {TT.STAR, TT.PLUS, TT.QUEST}  # right-associative

def to_postfix(tokens: List[Token]) -> List[Token]:
    """
    Dijkstra's shunting-yard algorithm.
    Returns tokens in postfix (RPN) order, respecting operator precedence
    and parentheses.
    """
    output: List[Token] = []
    ops:    List[Token] = []

    for tok in tokens:
        if tok.type in (TT.CHAR, TT.EPS):
            output.append(tok)

        elif tok.type in _PREC:
            # Pop operators with higher (or equal left-assoc) precedence
            while (ops and
                   ops[-1].type != TT.LPAREN and
                   ops[-1].type in _PREC and
                   (_PREC[ops[-1].type] > _PREC[tok.type] or
                    (_PREC[ops[-1].type] == _PREC[tok.type] and
                     tok.type not in _UNARY))):
                output.append(ops.pop())
            ops.append(tok)

        elif tok.type == TT.LPAREN:
            ops.append(tok)

        elif tok.type == TT.RPAREN:
            while ops and ops[-1].type != TT.LPAREN:
                output.append(ops.pop())
            if not ops:
                raise ValueError('Mismatched parentheses: extra ")".')
            ops.pop()  # discard the matching LPAREN

    while ops:
        top = ops.pop()
        if top.type == TT.LPAREN:
            raise ValueError('Mismatched parentheses: unclosed "(".')
        output.append(top)

    return output


# ─────────────────────────────────────────────
# STEP 4 — Build AST from postfix
# ─────────────────────────────────────────────
def build_ast(postfix: List[Token]) -> ASTNode:
    """
    Process the postfix token list using a stack.
    Unary operators (*, +, ?) consume one node.
    Binary operators (|, ·) consume two nodes.

    Desugaring:
      a+  →  a · a*          (one-or-more)
      a?  →  a | ε           (zero-or-one)
    """
    if not postfix:
        raise ValueError("Empty expression — nothing to parse.")

    stack: List[ASTNode] = []

    for tok in postfix:
        if tok.type == TT.CHAR:
            stack.append(ASTNode(kind="leaf", symbol=tok.value))

        elif tok.type == TT.EPS:
            stack.append(ASTNode(kind="eps"))

        elif tok.type == TT.STAR:
            if not stack:
                raise ValueError("Operator '*' has no operand.")
            child = stack.pop()
            stack.append(ASTNode(kind="star", child=child))

        elif tok.type == TT.PLUS:
            # a+ = a · a*
            if not stack:
                raise ValueError("Operator '+' has no operand.")
            child = stack.pop()
            star_copy = ASTNode(kind="star", child=copy.deepcopy(child))
            stack.append(ASTNode(kind="concat", left=child, right=star_copy))

        elif tok.type == TT.QUEST:
            # a? = a | ε
            if not stack:
                raise ValueError("Operator '?' has no operand.")
            child = stack.pop()
            stack.append(ASTNode(kind="or", left=child, right=ASTNode(kind="eps")))

        elif tok.type == TT.CONCAT:
            if len(stack) < 2:
                raise ValueError("Concatenation operator needs two operands.")
            right = stack.pop()
            left  = stack.pop()
            stack.append(ASTNode(kind="concat", left=left, right=right))

        elif tok.type == TT.OR:
            if len(stack) < 2:
                raise ValueError("Alternation operator '|' needs two operands.")
            right = stack.pop()
            left  = stack.pop()
            stack.append(ASTNode(kind="or", left=left, right=right))

    if len(stack) != 1:
        raise ValueError("Invalid regex: could not reduce to a single tree.")

    return stack[0]


# ─────────────────────────────────────────────
# STEP 5 — Augment and number leaves
# ─────────────────────────────────────────────
def _number_leaves(node: Optional[ASTNode], counter: list) -> None:
    """
    DFS traversal: assign sequential position numbers to every leaf node.
    counter is a one-element list used as a mutable integer reference.
    """
    if node is None:
        return
    if node.kind == "leaf":
        counter[0] += 1
        node.pos = counter[0]
        return
    _number_leaves(node.left,  counter)
    _number_leaves(node.right, counter)
    _number_leaves(node.child, counter)


def augment(tree: ASTNode) -> ASTNode:
    """
    1. Wrap tree in  (tree) · #   to add the end-marker.
    2. Number all leaf nodes left-to-right starting from 1.
    Returns the augmented root node.
    """
    end_marker = ASTNode(kind="leaf", symbol="#")
    augmented  = ASTNode(kind="concat", left=tree, right=end_marker)
    _number_leaves(augmented, [0])
    return augmented


# ─────────────────────────────────────────────
# PUBLIC API  (Task 1 deliverable)
# ─────────────────────────────────────────────
def parse_regex(src: str) -> ASTNode:
    """
    parse_regex(src) -> AugmentedSyntaxTree

    Full pipeline:
      tokenize → insert_concat → to_postfix → build_ast → augment

    Raises ValueError with a descriptive message on any error.
    """
    tokens   = tokenize(src)
    tokens   = insert_concat(tokens)
    postfix  = to_postfix(tokens)
    tree     = build_ast(postfix)
    return augment(tree)


# ─────────────────────────────────────────────
# Pretty-printer (for debugging / display)
# ─────────────────────────────────────────────
def print_ast(node: Optional[ASTNode], prefix: str = "", is_last: bool = True) -> None:
    """Recursively print the AST in a tree-drawing style."""
    if node is None:
        return
    connector  = "└── " if is_last else "├── "
    child_pfx  = prefix + ("    " if is_last else "│   ")

    if node.kind == "leaf":
        sym = "'#'(end)" if node.symbol == "#" else f"'{node.symbol}'"
        print(f"{prefix}{connector}LEAF[{node.pos}] {sym}")
    elif node.kind == "eps":
        print(f"{prefix}{connector}ε")
    else:
        print(f"{prefix}{connector}{node.kind.upper()}")
        children = [c for c in (node.left, node.right, node.child) if c is not None]
        for i, child in enumerate(children):
            print_ast(child, child_pfx, i == len(children) - 1)
