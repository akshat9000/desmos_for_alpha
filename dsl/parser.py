
from lark import Lark, Transformer, v_args

GRAMMAR = r"""
?start: expr
?expr: or_expr
?or_expr: and_expr ("||" and_expr)*
?and_expr: cmp_expr ("&&" cmp_expr)*
?cmp_expr: add_expr (("=="|"!="|">"|">="|"<"|"<=") add_expr)*
?add_expr: mul_expr (("+"|"-") mul_expr)*
?mul_expr: pow_expr (("*"|"/"|"%") pow_expr)*
?pow_expr: unary_expr ("^" unary_expr)*
?unary_expr: ("+"|"-"|"!") unary_expr
           | atom
?atom: NUMBER        -> number
     | NAME          -> name
     | func_call
     | "(" expr ")"
func_call: NAME "(" [args] ")"
args: expr ("," expr)*
NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
NUMBER: /(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?/
%ignore /[ \t\r\n]+/
"""

parser = Lark(GRAMMAR, start="start", parser="lalr")

class Node: ...
class Number(Node):
    def __init__(self, value): self.value = value
class Name(Node):
    def __init__(self, name): self.name = name
class BinOp(Node):
    def __init__(self, op, left, right): self.op, self.left, self.right = op, left, right
class UnaryOp(Node):
    def __init__(self, op, operand): self.op, self.operand = op, operand
class Call(Node):
    def __init__(self, name, args): self.name, self.args = name, args

@v_args(inline=True)
class ASTBuilder(Transformer):
    def number(self, tok): return Number(float(tok))
    def name(self, tok): return Name(str(tok))

    def func_call(self, name, *rest):
        args = rest[0] if rest else []
        return Call(str(name), list(args))

    def args(self, *xs): return list(xs)

    def or_expr(self, a, *rest):
        n = a
        for b in rest: n = BinOp("||", n, b)
        return n

    def and_expr(self, a, *rest):
        n = a
        for b in rest: n = BinOp("&&", n, b)
        return n

    def cmp_expr(self, a, *pairs):
        # Lark gives tokens and nodes interleaved; we fold left-assoc
        n = a
        it = iter(pairs)
        for op, b in zip(it, it):  # pairs of (op, expr) via zip over step-2
            n = BinOp(str(op), n, b)
        return n

    def add_expr(self, a, *rest):
        n = a
        it = iter(rest)
        for op, b in zip(it, it):
            n = BinOp(str(op), n, b)
        return n

    def mul_expr(self, a, *rest):
        n = a
        it = iter(rest)
        for op, b in zip(it, it):
            n = BinOp(str(op), n, b)
        return n

    def pow_expr(self, a, *rest):
        n = a
        for b in rest:
            n = BinOp("^", n, b)
        return n

    def unary_expr(self, *args):
        if len(args) == 1:
            return args[0]
        op, operand = args[0], args[1]
        return UnaryOp(str(op), operand)

def parse_alpha(src: str) -> Node:
    tree = parser.parse(src)
    return ASTBuilder().transform(tree)
