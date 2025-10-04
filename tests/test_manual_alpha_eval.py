# tests/test_manual_alpha_eval.py

import pandas as pd
import pytest
from dsl.parser import parse_alpha
from dsl.eval import EvaluationContext, eval_node
import dsl.functions  # ensure registry loads

@pytest.fixture(scope="session")
def fields():
    # Load the market data you generated via scripts/gen_market_data.py
    field_names = ["returns", "close", "volume"]
    dfs = {name: pd.read_csv(f"data/{name}.csv", index_col=0, parse_dates=True)
           for name in field_names}
    return dfs

def test_rank_of_mean(fields):
    """Basic sanity test for alpha evaluation."""
    alpha = "rank(ts_mean(returns,5) - ts_mean(returns,20))"
    ast = parse_alpha(alpha)
    ctx = EvaluationContext(fields, fields["returns"].index[-1])
    result = eval_node(ctx, ast)
    # Should produce one value per symbol between 0–1
    assert isinstance(result, pd.Series)
    assert result.between(0, 1).all()

def test_ts_corr(fields):
    alpha = "rank(ts_corr(close, volume, 20))"
    ast = parse_alpha(alpha)
    ctx = EvaluationContext(fields, fields["returns"].index[-1])
    result = eval_node(ctx, ast)
    assert not result.isna().all()
