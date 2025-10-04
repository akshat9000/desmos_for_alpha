# Desmos-for-Alphas (Starter Repo)

A minimal DSL + interpreter to parse and evaluate WorldQuant-style alpha expressions over time-series and cross-sectional data.

## Features (v0)
- Lark-based parser with arithmetic, logical ops, function calls
- Time-series functions: `delay`, `ts_mean`, `ts_std`, `ts_sum`, `ts_rank`
- Cross-sectional functions: `rank`, `zscore`, `scale`
- Safe math: `sdiv`
- Evaluation engine with a simple `EvaluationContext`
- FastAPI service exposing `/functions`, `/parse`, `/evaluate`

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

### Try it in Python

```python
import pandas as pd, numpy as np
from dsl.parser import parse_alpha
from dsl.eval import EvaluationContext, eval_node

# toy data
dates = pd.date_range("2024-01-01", periods=30, freq="B")
symbols = ["AAPL","MSFT","GOOG"]
rng = np.random.default_rng(0)
retn = pd.DataFrame(rng.normal(0, 0.01, (len(dates), len(symbols))), index=dates, columns=symbols)

fields = {"returns": retn}
alpha_src = "rank(ts_mean(returns, 5) - ts_mean(returns, 10))"

ast = parse_alpha(alpha_src)
ctx = EvaluationContext(fields, dates[-1])
signal_today = eval_node(ctx, ast)
print(signal_today)
```

### HTTP example

- `GET /functions` — list registry
- `POST /parse` — `{"alpha": "rank(ts_mean(returns,5))"}`
- `POST /evaluate` —
```json
{
  "alpha": "rank(ts_mean(returns,5) - ts_mean(returns,10))",
  "date": "2024-02-12",
  "fields": ["returns"]
}
```

## Structure

```
desmos_for_alphas/
  app/
    main.py
  dsl/
    __init__.py
    parser.py
    eval.py
    registry.py
    functions/
      __init__.py
      time_series.py
      cross_sectional.py
      safe_math.py
  tests/
    test_parse.py
    test_eval_basics.py
  data/
    example_returns.csv
  requirements.txt
  README.md
```

## Notes

- For time-windowed functions, we compute using the underlying DataFrame and the current `t`.
- We attach `_field_name` to Series returned by identifiers so function implementations can find their source DataFrame.
- This is a teaching/starter repo; harden and optimize before production (memoization, vectorized evaluation across dates, precomputed rollings, etc.).
