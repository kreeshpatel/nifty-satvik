"""Count Daniel-Moskowitz (2016) 'panic states' in Nifty history — market data only, no trade outcome read.

Panic state (monthly): trailing 24-month Nifty return < 0 AND 126-day realised vol above its own
expanding 75th percentile (no lookahead). Run BEFORE any study of the book's behaviour in such states:
if the window holds one or two episodes, that study is underpowered by construction and spends no screen.

    python pipelines/diagnostics/count_panic_states.py
"""
from __future__ import annotations

import warnings

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")


def main() -> int:
    n = yf.download("^NSEI", start="2005-01-01", progress=False, auto_adjust=True)["Close"].squeeze()
    m = n.resample("ME").last()
    r24 = m / m.shift(24) - 1
    v = n.pct_change().rolling(126).std().resample("ME").last() * 252 ** 0.5
    panic = (r24 < 0) & (v > v.expanding(36).quantile(0.75))
    print("panic months:", [str(x.date())[:7] for x in panic[panic].index])
    tr = panic[(panic.index >= "2019-01-01") & (panic.index <= "2024-06-30")]
    print(f"train window panic months: {int(tr.sum())} of {len(tr)}")
    print(f"latest: 24m return {float(r24.iloc[-1]) * 100:.1f}% | 126d vol {float(v.iloc[-1]) * 100:.1f}% | "
          f"panic now: {bool(panic.iloc[-1])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
