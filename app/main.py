
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import pandas as pd, numpy as np
from dsl.registry import list_functions
from dsl.parser import parse_alpha
from dsl.eval import EvaluationContext, eval_node
from dsl.analyzer import analyze
import dsl.functions  # register all

app = FastAPI(title="Desmos-for-Alphas DSL")

class ParseBody(BaseModel):
    alpha: str

class EvalBody(BaseModel):
    alpha: str
    date: str
    fields: List[str] = []  # names required (for validation later)

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
    # Toy in-memory data generator for demo
    # In production, load from your DB or files.
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    symbols = ["AAPL","MSFT","GOOG","AMZN"]
    rng = np.random.default_rng(42)
    fields = {
        "returns": pd.DataFrame(rng.normal(0,0.01,(len(dates), len(symbols))), index=dates, columns=symbols),
        "close": pd.DataFrame(100+np.cumsum(rng.normal(0,1,(len(dates), len(symbols))), axis=0), index=dates, columns=symbols),
        "volume": pd.DataFrame(rng.integers(1e5, 2e6, size=(len(dates), len(symbols))), index=dates, columns=symbols),
    }
    if body.date not in dates.astype(str).tolist():
        raise HTTPException(status_code=400, detail="Requested date not in demo dataset range")
    t = pd.Timestamp(body.date)

    try:
        ast = parse_alpha(body.alpha)
        ctx = EvaluationContext(fields, t)
        out = eval_node(ctx, ast)
        if hasattr(out, "to_dict"):
            return {"date": body.date, "result": out.to_dict()}
        return {"date": body.date, "result": float(out)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/evaluate_series")
def evaluate_series_api(body: EvalBody):
    from engine.backtest_loop import evaluate_series
    fields = {name: pd.read_csv(f"data/{name}.csv", index_col=0, parse_dates=True)
              for name in ["returns","close","volume"]}
    out = evaluate_series(body.alpha, fields)
    return {"dates": out.index.strftime("%Y-%m-%d").tolist(),
            "columns": out.columns.tolist(),
            "values": out.values.tolist()}
