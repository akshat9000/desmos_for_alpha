
import pandas as pd, numpy as np
from dsl.parser import parse_alpha
from dsl.eval import EvaluationContext, eval_node
import dsl.functions  # noqa

def toy():
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    syms = ["A","B","C"]
    rng = np.random.default_rng(0)
    retn = pd.DataFrame(rng.normal(0, 0.01, (len(dates), len(syms))), index=dates, columns=syms)
    return {"returns": retn}, dates

def test_rank_tsmean_basic():
    fields, dates = toy()
    alpha = "rank(ts_mean(returns,5) - ts_mean(returns,10))"
    ast = parse_alpha(alpha)
    ctx = EvaluationContext(fields, dates[-1])
    res = eval_node(ctx, ast)
    assert set(res.index) == set(fields["returns"].columns)
    assert (res >= 0).all() and (res <= 1).all()

def test_delay_equals_shift():
    fields, dates = toy()
    ast = parse_alpha("delay(returns, 3)")
    ctx = EvaluationContext(fields, dates[-1])
    out = eval_node(ctx, ast)
    # compare with manual shift in DF
    df = fields["returns"]
    row = df.index.get_loc(dates[-1])
    assert out.equals(df.iloc[row-3])
