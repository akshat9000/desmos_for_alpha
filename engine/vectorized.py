import pandas as pd
import numpy as np
from typing import Dict
from dsl.parser import parse_alpha, Number, Name, UnaryOp, BinOp, Call

_BIN = {
    '+': lambda a,b: a + b,
    '-': lambda a,b: a - b,
    '*': lambda a,b: a * b,
    '/': lambda a,b: a / b,
    '%': lambda a,b: a % b,
    '^': lambda a,b: np.power(a, b),
    '==': lambda a,b: (a == b).astype(float),
    '!=': lambda a,b: (a != b).astype(float),
    '>':  lambda a,b: (a >  b).astype(float),
    '>=': lambda a,b: (a >= b).astype(float),
    '<':  lambda a,b: (a <  b).astype(float),
    '<=': lambda a,b: (a <= b).astype(float),
    '&&': lambda a,b: (truthy(a) & truthy(b)).astype(float),
    '||': lambda a,b: (truthy(a) | truthy(b)).astype(float),
}

def truthy(x):
    if isinstance(x, (pd.Series, pd.DataFrame)):
        return x.fillna(0.0) != 0.0
    return bool(x)

def _align(a, b):
    if isinstance(a, pd.DataFrame) and isinstance(b, pd.DataFrame):
        return a.align(b, join="outer")
    if isinstance(a, pd.DataFrame):
        if isinstance(b, (int,float,np.floating)):
            b = pd.DataFrame(b, index=a.index, columns=a.columns)
        elif isinstance(b, pd.Series) and b.index.equals(a.index):
            b = pd.DataFrame({c: b for c in a.columns})
        elif isinstance(b, pd.Series):
            b = pd.DataFrame(b, index=a.index, columns=a.columns)
        return a, b
    if isinstance(b, pd.DataFrame):
        B, A = _align(b, a)
        return A, B
    return a, b

def _decay_linear(df: pd.DataFrame, n: int):
    base_w = np.arange(1, n+1, dtype=float)
    base_w /= base_w.sum()

    def wdot(x):
        arr = np.asarray(x, dtype=float)
        m = len(arr)

        # Trim to current window length, then normalize to sum=1 for this length
        w = base_w[-m:]
        w = w / w.sum()

        # Match pandas .sum(skipna=True): NaNs contribute 0, and we DO NOT
        # re-normalize weights after dropping NaNs.
        # (This mirrors: window.mul(w[:, None]).sum(axis=0))
        arr = np.nan_to_num(arr, nan=0.0)

        return float(np.dot(arr, w))

    # Reduced-window semantics like slow engine: min_periods=1
    return df.rolling(n, min_periods=1).apply(wdot, raw=True)

def _cs_rank(df: pd.DataFrame) -> pd.DataFrame:
    return df.rank(axis=1, pct=True)

def _cs_zscore(df: pd.DataFrame) -> pd.DataFrame:
    mu = df.mean(axis=1)
    sd = df.std(axis=1, ddof=1).replace(0, np.nan)
    return df.sub(mu, axis=0).div(sd, axis=0)

def _cs_scale(df: pd.DataFrame, a: float=1.0) -> pd.DataFrame:
    denom = df.abs().sum(axis=1).replace(0, np.nan)
    return df.mul(a, axis=0).div(denom, axis=0)

# ts_rank (reduced window)
def _ts_rank_last(df: pd.DataFrame, n: int) -> pd.DataFrame:
    def rank_last(col: pd.Series):
        return col.rolling(n, min_periods=1).apply(
            lambda w: (pd.Series(w).le(pd.Series(w).iloc[-1])).sum() / pd.Series(w).notna().sum(),
            raw=False
        )
    return df.apply(rank_last)

def _ts_corr(x: pd.DataFrame, y: pd.DataFrame, n: int) -> pd.DataFrame:
    x, y = x.align(y, join='inner')
    win = n

    Sx  = x.rolling(win, min_periods=2).sum()
    Sy  = y.rolling(win, min_periods=2).sum()
    Sxy = (x*y).rolling(win, min_periods=2).sum()
    Sxx = (x*x).rolling(win, min_periods=2).sum()
    Syy = (y*y).rolling(win, min_periods=2).sum()
    m   = x.rolling(win, min_periods=2).count()

    cov_num = Sxy - (Sx*Sy)/m
    varx    = Sxx - (Sx*Sx)/m
    vary    = Syy - (Sy*Sy)/m
    denom   = (varx * vary).where((varx>0) & (vary>0))
    corr    = cov_num / np.sqrt(denom)
    return corr

def evaluate_series_vectorized(alpha_src: str, fields: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Vectorized evaluation across all dates for supported subset:
      arithmetic/logic/comparisons, delay, ts_mean/std/sum, ts_rank, ts_corr,
      decay_linear, rank, zscore, scale, sdiv.
    Returns DataFrame (dates×symbols). Raises NotImplementedError for unsupported
    functions so callers can fallback to the slow per-date engine.
    """
    ast = parse_alpha(alpha_src)

    def walk(node):
        if isinstance(node, Number):
            return float(node.value)
        if isinstance(node, Name):
            if node.name not in fields:
                raise KeyError(f"Unknown field '{node.name}'")
            return fields[node.name]
        if isinstance(node, UnaryOp):
            v = walk(node.operand)
            if isinstance(v, (int,float,np.floating)):
                if node.op == '+': return +v
                if node.op == '-': return -v
                if node.op == '!': return 0.0 if v!=0 else 1.0
            if node.op == '+': return v
            if node.op == '-': return -v
            if node.op == '!': return (~truthy(v)).astype(float)
            raise ValueError(f"Unsupported unary {node.op}")
        if isinstance(node, BinOp):
            a = walk(node.left); b = walk(node.right)
            a, b = _align(a, b)
            if node.op not in _BIN:
                raise ValueError(f"Unsupported op {node.op}")
            return _BIN[node.op](a, b)
        if isinstance(node, Call):
            name = node.name.lower()
            args = [walk(a) for a in node.args]

            # time-series
            if name == "ts_mean": return args[0].rolling(int(args[1]), min_periods=1).mean()
            if name == "ts_sum":  return args[0].rolling(int(args[1]), min_periods=1).sum()
            if name == "ts_std":  return args[0].rolling(int(args[1]), min_periods=2).std(ddof=1)
            if name == "delay":   return args[0].shift(int(args[1]))
            if name == "decay_linear": return _decay_linear(args[0], int(args[1]))
            if name == "ts_rank": return _ts_rank_last(args[0], int(args[1]))
            if name == "ts_corr": return _ts_corr(args[0], args[1], int(args[2]))

            # cross-sectional
            if name == "rank":   return _cs_rank(args[0])
            if name == "zscore": return _cs_zscore(args[0])
            if name == "scale":
                a = float(args[1]) if len(args) > 1 and not isinstance(args[1], (pd.DataFrame, pd.Series)) else 1.0
                return _cs_scale(args[0], a=a)

            # safe divide
            if name == "sdiv":
                a, b = _align(args[0], args[1])
                if isinstance(a, pd.DataFrame) and isinstance(b, pd.DataFrame):
                    out = a.copy()
                    mask = (b == 0) | b.isna()
                    out[~mask] = a[~mask] / b[~mask]
                    out[mask] = 0.0
                    return out
                return 0.0 if (isinstance(b, (int,float)) and b == 0) else a / b

            raise NotImplementedError(f"Function '{name}' not yet vectorized")

        raise TypeError(f"Unknown node {type(node)}")

    res = walk(ast)
    if isinstance(res, pd.Series):
        res = res.to_frame()
    if not isinstance(res, pd.DataFrame):
        base = next(iter(fields.values()))
        res = pd.DataFrame(res, index=base.index, columns=base.columns)
    return res
