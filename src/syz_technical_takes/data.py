"""Daily OHLC feed for Technical Takes.

Keyless Yahoo v8 chart endpoint (dev licence — same provenance caveat as the
newsletter's yfinance use: swap for a licensed feed before production). Isolated
here so the rest of the package never touches the network or the provider.

Returns bars as (date, open, high, low, close) ascending, holidays/nulls dropped.
"""
from __future__ import annotations

import datetime as dt
import time
from typing import Optional

import requests

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")
_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")


def fetch_ohlc(yahoo_symbol: str, years: int = 5, retries: int = 4):
    """Fetch ~`years` of daily OHLC for a Yahoo symbol. Raises on total failure."""
    rng = f"{max(years, 1)}y"
    last_err = None
    for host in _HOSTS:
        url = f"https://{host}/v8/finance/chart/{yahoo_symbol}"
        for attempt in range(retries):
            try:
                r = requests.get(url, params={"range": rng, "interval": "1d"},
                                 headers={"User-Agent": _UA, "Accept": "application/json"},
                                 timeout=45)
                if r.status_code == 200 and len(r.content) > 2000:
                    return _parse(r.json(), yahoo_symbol)
                last_err = f"HTTP {r.status_code}"
            except Exception as e:                      # network / JSON errors -> retry
                last_err = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)
    raise RuntimeError(f"could not fetch {yahoo_symbol}: {last_err}")


def _parse(j, symbol):
    res = j.get("chart", {}).get("result")
    if not res:
        err = j.get("chart", {}).get("error")
        raise RuntimeError(f"{symbol}: empty chart result ({err})")
    r = res[0]
    ts = r.get("timestamp") or []
    q = r["indicators"]["quote"][0]
    meta = r.get("meta", {})
    bars = []
    for i, t in enumerate(ts):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if None in (o, h, l, c):
            continue
        d = dt.datetime.fromtimestamp(t, dt.timezone.utc).date()
        bars.append((d, o, h, l, c))
    bars.sort(key=lambda x: x[0])
    if not bars:
        raise RuntimeError(f"{symbol}: no usable OHLC rows")
    return dict(symbol=meta.get("symbol", symbol), currency=meta.get("currency"),
                bars=bars)
