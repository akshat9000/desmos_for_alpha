
import numpy as np, pandas as pd
from ..registry import register

def _cs_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True)

@register("rank", arity=[1], kind="cs", doc="cross-sectional rank at t")
def rank_fn(ctx, x):
    return _cs_rank(x)

@register("zscore", arity=[1], kind="cs", doc="cross-sectional zscore at t")
def zscore_fn(ctx, x):
    m = x.mean()
    sd = x.std(ddof=1)
    return (x - m) / (sd if sd and sd != 0 else np.nan)

@register("scale", arity=range(1,3), kind="cs", doc="scale to unit L1 or target a")
def scale_fn(ctx, x, a=1.0):
    a = float(a)
    denom = x.abs().sum()
    if denom and denom != 0:
        return x * (a / denom)
    return x
