#!/usr/bin/env python3
"""
engine_smoke_test.py

Standalone script to sanity-check the Desmos-for-Alphas engine.

What it does:
1) Loads data from ./data (returns.csv, close.csv, volume.csv).
   - If not found, generates synthetic data in-memory (and can save to ./data with --save).
2) Evaluates a sample alpha across all dates × symbols.
3) Prints shape, head/tail, and a couple of parity checks vs pandas.
4) Optional: plot a single ticker's last-N signal values with --plot.

Usage examples:
    python engine_smoke_test.py
    python engine_smoke_test.py --alpha "rank(ts_mean(returns,5) - ts_mean(returns,20))"
    python engine_smoke_test.py --plot --ticker AAPL --last 150
    python engine_smoke_test.py --save   # if you generated synthetic data, save it under ./data
"""

import os
import argparse
import pandas as pd
import numpy as np

# Import your engine & DSL
from engine.backtest_loop import evaluate_series
from dsl.parser import parse_alpha
from dsl.eval import EvaluationContext, eval_node
import dsl.functions  # ensure registry is loaded


def load_fields_from_csv(data_dir="data"):
    required = ["returns", "close", "volume"]
    paths = {name: os.path.join(data_dir, f"{name}.csv") for name in required}
    if all(os.path.exists(p) for p in paths.values()):
        fields = {
            name: pd.read_csv(paths[name], index_col=0, parse_dates=True) for name in required
        }
        return fields, True
    return None, False


def gen_synthetic_fields(n_days=250, symbols=("AAPL","MSFT","GOOG","AMZN","TSLA","NVDA"), seed=42):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
    n = len(symbols)

    close = pd.DataFrame(100 + np.cumsum(rng.normal(0, 1, (n_days, n)), axis=0),
                         index=dates, columns=symbols)
    volume = pd.DataFrame(rng.integers(1e5, 5e6, (n_days, n)),
                          index=dates, columns=symbols)
    returns = close.pct_change().fillna(0.0)

    return {"close": close, "volume": volume, "returns": returns}


def save_fields_to_csv(fields, data_dir="data"):
    os.makedirs(data_dir, exist_ok=True)
    for name, df in fields.items():
        df.to_csv(os.path.join(data_dir, f"{name}.csv"))


def pandas_parity_checks(fields, t):
    """Return a dict of boolean results comparing DSL vs pandas for a couple of ops."""
    results = {}

    # ts_mean parity
    alpha = "ts_mean(returns, 5)"
    dsl = eval_node(EvaluationContext(fields, t), parse_alpha(alpha)).sort_index()
    pd_res = fields["returns"].rolling(5).mean().loc[t].sort_index()
    results["ts_mean==rolling_mean_5"] = bool((dsl.round(10) == pd_res.round(10)).all())

    # ts_std parity
    alpha = "ts_std(returns, 5)"
    dsl = eval_node(EvaluationContext(fields, t), parse_alpha(alpha)).sort_index()
    pd_res = fields["returns"].rolling(5).std(ddof=1).loc[t].sort_index()
    results["ts_std==rolling_std_5"] = bool((dsl.round(10) == pd_res.round(10)).all())

    # delay parity
    alpha = "delay(returns, 3)"
    dsl = eval_node(EvaluationContext(fields, t), parse_alpha(alpha)).sort_index()
    row = fields["returns"].index.get_loc(t)
    pd_res = fields["returns"].iloc[row-3].sort_index()
    results["delay_3_equals_shift"] = bool((dsl.round(10) == pd_res.round(10)).all())

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=str,
                    default="rank(ts_mean(returns,5) - ts_mean(returns,20))",
                    help="Alpha expression to evaluate across dates × symbols.")
    ap.add_argument("--data-dir", type=str, default="data", help="Directory containing CSVs.")
    ap.add_argument("--plot", action="store_true", help="Plot a single ticker's signal.")
    ap.add_argument("--ticker", type=str, default=None, help="Ticker to plot (default: first column).")
    ap.add_argument("--last", type=int, default=100, help="Last N points to plot.")
    ap.add_argument("--save", action="store_true",
                    help="If synthetic data is generated, save it to --data-dir.")
    args = ap.parse_args()

    fields, found = load_fields_from_csv(args.data_dir)
    if not found:
        print("⚠️  CSVs not found under ./data — generating synthetic data in-memory...")
        fields = gen_synthetic_fields()
        if args.save:
            print("💾 Saving synthetic data to ./data ...")
            save_fields_to_csv(fields, args.data_dir)

    # Evaluate full series
    print(f"\nEvaluating alpha:\n  {args.alpha}\n")
    sig = evaluate_series(args.alpha, fields)

    print("✅ Engine output shape (dates × symbols):", sig.shape)
    print("\nColumns (symbols):", list(sig.columns))
    print("\nTail of signal:")
    print(sig.tail())

    # Parity checks vs pandas for a few ops
    t = next(iter(fields.values())).index[-1]
    checks = pandas_parity_checks(fields, t)
    print("\nPandas parity checks @ last date", t.date(), ":")
    for k, v in checks.items():
        print(f"  {k:30s} -> {v}")

    # Optional plot
    if args.plot:
        try:
            import matplotlib.pyplot as plt
            col = args.ticker or sig.columns[0]
            window = sig.iloc[-args.last:][col]
            ax = window.plot(title=f"{col} — alpha signal (last {len(window)} points)")
            ax.set_xlabel("Date"); ax.set_ylabel("Signal")
            import matplotlib
            plt.tight_layout(); plt.show()
        except Exception as e:
            print("Plotting failed:", e)

    print("\nDone.")


if __name__ == "__main__":
    main()
