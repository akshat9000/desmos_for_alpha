import pandas as pd
import numpy as np
import pytest
from engine.vectorized import evaluate_series_vectorized
from engine.backtest_loop import evaluate_series

@pytest.fixture(scope="session")
def fields():
    names = ["returns","close","volume"]
    return {n: pd.read_csv(f"data/{n}.csv", index_col=0, parse_dates=True) for n in names}

@pytest.mark.parametrize("alpha", [
    "ts_mean(returns,5)",
    "ts_std(returns,10)",
    "ts_sum(returns,7)",
    "delay(returns,3)",
    "rank(ts_mean(returns,5) - ts_mean(returns,20))",
    "zscore(decay_linear(returns,10))",
    "rank(ts_corr(close, volume, 20))",
    "sdiv(ts_mean(returns,5), ts_std(returns,5))"
])
def test_vectorized_matches_slow(fields, alpha):
    fast = evaluate_series_vectorized(alpha, fields)
    slow = evaluate_series(alpha, fields)
    assert fast.shape == slow.shape
    # allow tiny fp differences / early NaNs due to startup
    diff = (fast - slow).abs()
    # ignore rows where both are NaN
    mask = ~(fast.isna() & slow.isna())
    quantile = diff[mask].stack().quantile(0.999)
    assert (np.isnan(quantile) or quantile < 1e-6)
