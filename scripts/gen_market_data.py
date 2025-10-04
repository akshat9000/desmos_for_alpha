"""
scripts/gen_market_data.py

Downloads historical OHLCV data for a list of tickers via Yahoo Finance,
computes daily returns, and saves each field as a CSV under ./data/.

Usage:
    python scripts/gen_market_data.py
"""

import os
import pandas as pd
import yfinance as yf
from datetime import datetime

# ---------------- CONFIG ---------------- #
TICKERS = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "NVDA"]
START_DATE = "2023-01-01"
END_DATE = datetime.today().strftime("%Y-%m-%d")
DATA_DIR = "data"

# ---------------------------------------- #
os.makedirs(DATA_DIR, exist_ok=True)

print(f"Downloading OHLCV data for {len(TICKERS)} tickers...")
data = yf.download(TICKERS, start=START_DATE, end=END_DATE, group_by="ticker", auto_adjust=True, threads=True)

# Each field (Open, High, Low, Close, Volume) is stored per ticker
fields = {}
for field in ["Open", "High", "Low", "Close", "Volume"]:
    df = pd.concat({t: data[t][field] for t in TICKERS}, axis=1)
    df.columns = TICKERS
    fields[field.lower()] = df

# Compute daily returns (percent change of close)
returns = fields["close"].pct_change().fillna(0)
fields["returns"] = returns

# Save each field as CSV
for name, df in fields.items():
    path = os.path.join(DATA_DIR, f"{name}.csv")
    df.to_csv(path)
    print(f"✅ Saved {name}.csv with shape {df.shape}")

print("\nAll files saved in ./data/")
print(f"Fields: {list(fields.keys())}")
print(f"Date range: {fields['close'].index.min().date()} → {fields['close'].index.max().date()}")
