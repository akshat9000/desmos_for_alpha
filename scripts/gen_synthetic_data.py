import pandas as pd, numpy as np

def make_field(seed=0, n_days=200, n_symbols=6):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
    symbols = ["AAPL","MSFT","GOOG","AMZN","TSLA","NVDA"][:n_symbols]
    close = pd.DataFrame(100 + np.cumsum(rng.normal(0, 1, (n_days, n_symbols)), axis=0),
                         index=dates, columns=symbols)
    volume = pd.DataFrame(rng.integers(1e5, 5e6, (n_days, n_symbols)),
                          index=dates, columns=symbols)
    returns = close.pct_change().fillna(0)
    open_ = close * (1 + rng.normal(0, 0.002, close.shape))
    high = np.maximum(open_, close) * (1 + rng.normal(0, 0.001, close.shape))
    low  = np.minimum(open_, close) * (1 - rng.normal(0, 0.001, close.shape))

    return {
        "close": close,
        "open": open_,
        "high": high,
        "low": low,
        "volume": volume,
        "returns": returns,
    }

if __name__ == "__main__":
    fields = make_field()
    for name, df in fields.items():
        df.to_csv(f"data/{name}.csv")
    print("Synthetic data saved to ./data/*.csv")
