
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from functools import lru_cache
import pandas as pd, numpy as np
from dsl.registry import list_functions
from dsl.parser import parse_alpha
from dsl.eval import EvaluationContext, eval_node
from dsl.analyzer import analyze
from dsl.ast_utils import ast_to_dict, ast_to_pretty
import dsl.functions  # register all

# add imports at top
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import pandas as pd, os

# after app = FastAPI(...)
WEB_DIR = os.path.join(os.path.dirname(__file__), "..", "web")
STATIC_DIR = os.path.join(WEB_DIR)  # we’ll mount the same dir for simplicity

app = FastAPI(title="Desmos-for-Alphas DSL")

# mount /static to /web for css/js
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

class ParseBody(BaseModel):
    alpha: str

class EvalBody(BaseModel):
    alpha: str
    date: Optional[str] = None
    fields: List[str] = []  # names required (for validation later)

class BacktestBody(BaseModel):
    alpha: str
    top_q: float = 0.2     # top 20% long
    bot_q: float = 0.2     # bottom 20% short
    cost_bps: float = 0.0  # per-side turnover cost in basis points (e.g., 5 = 5bps)
    neutralize: bool = True  # dollar-neutral long-short


@lru_cache(maxsize=64)
def _cached_signal(alpha: str):
    fields = load_fields()
    try:
        from engine.vectorized import evaluate_series_vectorized
        sig = evaluate_series_vectorized(alpha, fields)
    except Exception:
        from engine.backtest_loop import evaluate_series
        sig = evaluate_series(alpha, fields)
    # Return immutable (values) and index/cols, because DataFrames aren't hashable
    return (tuple(sig.index.astype(str)), tuple(sig.columns), sig.values.copy())


def load_fields():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    def read(name): 
        return pd.read_csv(os.path.join(data_dir, f"{name}.csv"), index_col=0, parse_dates=True)
    return {
        "returns": read("returns"),
        "close":   read("close"),
        "volume":  read("volume"),
    }

@app.get("/", response_class=HTMLResponse)
def playground():
    index_path = os.path.join(WEB_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()



@app.post("/backtest")
def backtest(body: BacktestBody):
    fields = load_fields()

    idx, cols, vals = _cached_signal(body.alpha)
    sig = pd.DataFrame(list(vals), index=pd.to_datetime(list(idx)), columns=list(cols))

    rets = fields["returns"].reindex(sig.index).reindex(columns=sig.columns)

    # 2) Build long/short weights each day by quantiles
    def make_weights(row):
        s = row.dropna()
        if s.empty:
            return pd.Series(0.0, index=row.index)
        lo = s.quantile(body.bot_q)
        hi = s.quantile(1.0 - body.top_q)
        long  = (row >= hi).astype(float)
        short = (row <= lo).astype(float) * -1.0
        w = long + short
        # neutralize & normalize (equal weight within long/short)
        if body.neutralize:
            n_long = (w > 0).sum()
            n_short = (w < 0).sum()
            if n_long > 0:  w[w > 0]  =  1.0 / n_long
            if n_short > 0: w[w < 0]  = -1.0 / n_short
        else:
            # scale to unit L1
            ssum = w.abs().sum()
            if ssum > 0: w = w / ssum
        return w.fillna(0.0)

    W = sig.apply(make_weights, axis=1)   # DataFrame of weights aligned to sig

    # 3) Turnover & costs
    turnover = (W.diff().abs().sum(axis=1)).fillna(0.0)  # per-day L1 change
    cost = (body.cost_bps / 1e4) * turnover              # cost fraction

    # 4) Daily P&L
    pnl = (W * rets).sum(axis=1).fillna(0.0)
    pnl_net = pnl - cost
    equity = (1.0 + pnl_net).cumprod()

    return {
        "dates": sig.index.strftime("%Y-%m-%d").tolist(),
        "equity": equity.values.tolist(),
        "pnl": pnl_net.values.tolist(),
        "columns": sig.columns.tolist(),
        "signals": sig.values.tolist(),       # for heatmap
        "turnover": turnover.values.tolist(),
    }


@app.get("/functions")
def functions():
    return {"functions": list_functions()}

@app.post("/parse")
def parse(body: ParseBody):
    try:
        ast = parse_alpha(body.alpha)
        meta = analyze(ast)
        return {
            "ok": True,
            "fields": sorted(meta.fields),
            "windows": {k: sorted(v) for k,v in meta.windows.items()},
            "functions": sorted(meta.functions),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/evaluate")
def evaluate(body: EvalBody):
    fields = load_fields()
    dates = next(iter(fields.values())).index
    t = pd.Timestamp(body.date) if body.date else dates[-1]

    try:
        ast = parse_alpha(body.alpha)
        ctx = EvaluationContext(fields, t)
        out = eval_node(ctx, ast)
        return {"date": t.strftime("%Y-%m-%d"), "result": out.to_dict() if hasattr(out, "to_dict") else float(out)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/evaluate_series")
def evaluate_series_api(body: EvalBody):
    from engine.backtest_loop import evaluate_series
    fields = load_fields()
    out = evaluate_series(body.alpha, fields)
    return {
        "dates": out.index.strftime("%Y-%m-%d").tolist(),
        "columns": out.columns.tolist(),
        "values": out.values.tolist(),
    }


@app.post("/evaluate_series_fast")
def evaluate_series_fast(body: EvalBody):
    fields = load_fields()
    try:
        from engine.vectorized import evaluate_series_vectorized
        out = evaluate_series_vectorized(body.alpha, fields)
    except Exception:
        from engine.backtest_loop import evaluate_series
        out = evaluate_series(body.alpha, fields)
    return {
        "dates": out.index.strftime("%Y-%m-%d").tolist(),
        "columns": out.columns.tolist(),
        "values": out.values.tolist(),
    }


@app.post("/ast")
def ast_view(body: ParseBody):
    try:
        ast = parse_alpha(body.alpha)
        return {
            "ok": True,
            "pretty": ast_to_pretty(ast),
            "tree": ast_to_dict(ast),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))