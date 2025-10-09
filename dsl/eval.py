
import numpy as np, pandas as pd
from .registry import get_fn
from .parser import Number, Name, BinOp, UnaryOp, Call

def _as_series_like(a, ref_index):
    if isinstance(a, pd.Series):
        return a
    return pd.Series(float(a), index=ref_index)

OPS = {
    '+': lambda a,b: a + b,
    '-': lambda a,b: a - b,
    '*': lambda a,b: a * b,
    '/': lambda a,b: a / b,
    '%': lambda a,b: a % b,
    '^': lambda a,b: np.power(a, b),
    '==': lambda a,b: (a == b).astype(float),
    '!=': lambda a,b: (a != b).astype(float),
    '>': lambda a,b: (a > b).astype(float),
    '>=': lambda a,b: (a >= b).astype(float),
    '<': lambda a,b: (a < b).astype(float),
    '<=': lambda a,b: (a <= b).astype(float),
    '&&': lambda a,b: ((truthy(a)) & (truthy(b))).astype(float),
    '||': lambda a,b: ((truthy(a)) | (truthy(b))).astype(float),
}

def truthy(x):
    if isinstance(x, pd.Series):
        return x.fillna(0.0) != 0.0
    return bool(x)

class EvaluationContext:
    def __init__(self, fields: dict[str, pd.DataFrame], t):
        self.fields = fields
        self.t = t
        self._cache = {}

    def series(self, field_name: str) -> pd.Series:
        if field_name not in self.fields:
            raise KeyError(f"Unknown identifier '{field_name}'")
        df = self.fields[field_name]
        try:
            s = df.loc[self.t].copy()
        except KeyError:
            raise KeyError(f"Date {self.t} not found in field '{field_name}' index")
        # Attach field reference so functions can find DF:
        setattr(s, "_field_name", field_name)
        return s


def _node_key(node):
    from .parser import Number, Name, BinOp, UnaryOp, Call
    if isinstance(node, Number): return ("num", node.value)
    if isinstance(node, Name): return ("name", node.name)
    if isinstance(node, UnaryOp): return ("un", node.op, _node_key(node.operand))
    if isinstance(node, BinOp): return ("bin", node.op, _node_key(node.left), _node_key(node.right))
    if isinstance(node, Call): return ("call", node.name, tuple(_node_key(a) for a in node.args))
    raise TypeError


def eval_node(ctx: EvaluationContext, node):
    k = _node_key(node)
    if k in ctx._cache:
        return ctx._cache[k]
    import pandas as pd
    if isinstance(node, Number):
        return node.value
    if isinstance(node, Name):
        return ctx.series(node.name)
    if isinstance(node, UnaryOp):
        val = eval_node(ctx, node.operand)
        if node.op == '+': return val
        if node.op == '-': return -val
        if node.op == '!':
            if isinstance(val, pd.Series):
                return (~truthy(val)).astype(float)
            return float(not truthy(val))
        raise ValueError(f"Unknown unary op {node.op}")
    if isinstance(node, BinOp):
        a = eval_node(ctx, node.left)
        b = eval_node(ctx, node.right)
        # align series if needed
        if hasattr(a, "index") and hasattr(b, "index"):
            a, b = a.align(b, join="outer")
        elif hasattr(a, "index"):
            b = _as_series_like(b, a.index)
        elif hasattr(b, "index"):
            a = _as_series_like(a, b.index)
        return OPS[node.op](a, b)
    if isinstance(node, Call):
        spec = get_fn(node.name)
        argc = len(node.args)
        allowed = list(spec.arity) if not isinstance(spec.arity, range) else list(range(spec.arity.start, spec.arity.stop))
        if argc not in allowed:
            raise AssertionError(f"{node.name} expects {allowed}, got {argc}")
        args = [eval_node(ctx, arg) for arg in node.args]
        out = spec.impl(ctx, *args)
    ctx._cache[k] = out
    return out
    # raise TypeError(f"Unknown node {type(node)}")
