import numpy as np, pandas as pd
from ..registry import register

def _get_df_from_series(ctx, x: pd.Series) -> pd.DataFrame:
    field = getattr(x, "_field_name", None)
    if field is None:
        raise ValueError("Series is missing _field_name; ensure it originated from an identifier")
    if field not in ctx.fields:
        raise KeyError(f"Field '{field}' not in context")
    return ctx.fields[field]

def _row_slice(df: pd.DataFrame, t, n: int) -> pd.DataFrame:
    end = df.index.get_loc(t) + 1
    start = max(0, end - n)
    return df.iloc[start:end]

@register("delay", arity=range(2,3), kind="ts", doc="delay(x,n): return x(t-n)")
def delay(ctx, x, n):
    n = int(n)
    df = _get_df_from_series(ctx, x)
    row = df.index.get_loc(ctx.t)
    if row - n < 0:
        return pd.Series(index=df.columns, dtype=float)
    out = df.iloc[row - n].copy()
    setattr(out, "_field_name", getattr(x, "_field_name", None))
    return out

@register("ts_mean", arity=range(2,3), kind="ts", doc="rolling mean over last n (inclusive)")
def ts_mean(ctx, x, n):
    n = int(n)
    df = _get_df_from_series(ctx, x)
    window = _row_slice(df, ctx.t, n)
    out = window.mean()
    setattr(out, "_field_name", getattr(x, "_field_name", None))
    return out

@register("ts_std", arity=range(2,3), kind="ts", doc="rolling std over last n (inclusive)")
def ts_std(ctx, x, n):
    n = int(n)
    df = _get_df_from_series(ctx, x)
    window = _row_slice(df, ctx.t, n)
    out = window.std(ddof=1)
    setattr(out, "_field_name", getattr(x, "_field_name", None))
    return out

@register("ts_sum", arity=range(2,3), kind="ts", doc="rolling sum over last n (inclusive)")
def ts_sum(ctx, x, n):
    n = int(n)
    df = _get_df_from_series(ctx, x)
    window = _row_slice(df, ctx.t, n)
    out = window.sum()
    setattr(out, "_field_name", getattr(x, "_field_name", None))
    return out

@register("ts_rank", arity=range(2,3), kind="ts", doc="rank of last value within past n, per symbol")
def ts_rank(ctx, x, n):
    n = int(n)
    df = _get_df_from_series(ctx, x)
    window = _row_slice(df, ctx.t, n)
    last = window.iloc[-1]
    # proportion of values <= last (per column)
    ranks = (window.le(last, axis=1)).sum() / window.notna().sum()
    out = ranks.astype(float)
    setattr(out, "_field_name", getattr(x, "_field_name", None))
    return out


@register("ts_corr", arity=range(3,4), kind="ts", doc="rolling Pearson correlation of x,y over n")
def ts_corr(ctx, x, y, n):
    n = int(n)
    dfx = _get_df_from_series(ctx, x)
    dfy = _get_df_from_series(ctx, y)
    dfx, dfy = dfx.align(dfy, join="inner", axis=1)
    window_x = _row_slice(dfx, ctx.t, n)
    window_y = _row_slice(dfy, ctx.t, n)
    cov = ((window_x - window_x.mean()) * (window_y - window_y.mean())).sum() / (len(window_x) - 1)
    sx = window_x.std(ddof=1)
    sy = window_y.std(ddof=1)
    out = cov / (sx * sy)
    return out
