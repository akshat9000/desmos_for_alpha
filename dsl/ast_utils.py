# dsl/ast_utils.py
from typing import Any, Dict
from .parser import Number, Name, UnaryOp, BinOp, Call

def ast_to_dict(node) -> Dict[str, Any]:
    if isinstance(node, Number):
        return {"type": "Number", "value": node.value}
    if isinstance(node, Name):
        return {"type": "Name", "name": node.name}
    if isinstance(node, UnaryOp):
        return {"type": "UnaryOp", "op": node.op, "operand": ast_to_dict(node.operand)}
    if isinstance(node, BinOp):
        return {"type": "BinOp", "op": node.op, "left": ast_to_dict(node.left), "right": ast_to_dict(node.right)}
    if isinstance(node, Call):
        return {"type": "Call", "name": node.name, "args": [ast_to_dict(a) for a in node.args]}
    return {"type": "Unknown", "repr": repr(node)}

def ast_to_pretty(node, indent: str = "  ") -> str:
    lines = []
    def rec(n, depth=0, label=None):
        pad = indent * depth
        pre = f"{label}: " if label else ""
        if isinstance(n, Number):
            lines.append(f"{pad}{pre}Number({n.value})")
        elif isinstance(n, Name):
            lines.append(f"{pad}{pre}Name({n.name})")
        elif isinstance(n, UnaryOp):
            lines.append(f"{pad}{pre}UnaryOp({n.op})")
            rec(n.operand, depth+1, "operand")
        elif isinstance(n, BinOp):
            lines.append(f"{pad}{pre}BinOp({n.op})")
            rec(n.left, depth+1, "left")
            rec(n.right, depth+1, "right")
        elif isinstance(n, Call):
            lines.append(f"{pad}{pre}Call({n.name})")
            for i, a in enumerate(n.args):
                rec(a, depth+1, f"arg[{i}]")
        else:
            lines.append(f"{pad}{pre}{type(n).__name__}")
    rec(node)
    return "\n".join(lines)
