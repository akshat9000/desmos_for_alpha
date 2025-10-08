
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd, numpy as np
from dsl.registry import list_functions
from dsl.parser import parse_alpha
from dsl.eval import EvaluationContext, eval_node
from dsl.analyzer import analyze
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
