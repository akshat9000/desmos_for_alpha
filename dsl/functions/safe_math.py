
import numpy as np, pandas as pd
from ..registry import register

@register("sdiv", arity=[2], kind="scalar", doc="safe divide; returns 0 where denom==0 or NaN")
def sdiv(ctx, a, b):
    if isinstance(a, pd.Series) or isinstance(b, pd.Series):
        a = a if isinstance(a, pd.Series) else pd.Series(float(a), index=b.index)
        b = b if isinstance(b, pd.Series) else pd.Series(float(b), index=a.index)
        out = pd.Series(index=a.index, dtype=float)
        mask = (b == 0) | b.isna()
        out[~mask] = a[~mask] / b[~mask]
        out[mask] = 0.0
        return out
    return 0.0 if (b == 0 or np.isnan(b)) else a / b
