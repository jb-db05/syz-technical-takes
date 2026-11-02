"""Deterministic indicator synthesis for Technical Takes.

The renderer (``render.py``) consumes a Bloomberg export with these columns and
uses the indicators *as exported* (it only ever recomputes MA/Bollinger when it
detects the zero-decimal export defect). When no Bloomberg export exists, this
module rebuilds that workbook from a bare OHLC feed so the renderer runs
unchanged. Every definition here matches BUILD_SPEC.md §Data rules exactly.

The one indicator the renderer can never recompute is the Bloomberg stochastic
``%DS(25)`` / ``%DSS(15)``. It was reverse-engineered from a real SPIEX export
(it reproduces both exported columns to ~1e-4, i.e. Excel's stored rounding):

    rawK(99) = 100 * (Close - min(Low, 99)) / (max(High, 99) - min(Low, 99))
    %DS(25)  = SMA( SMA(rawK(99), 25), 25 )     # 99-bar %K, double 25-bar smooth
    %DSS(15) = SMA( %DS(25), 15 )

Warm-up: %DS needs 99+25+25-3 = 146 bars, %DSS a further 14 -> 160. Do not
"simplify" these constants; they are fitted to the vendor series, not guessed.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

import openpyxl

# column headers the renderer's load() matches by name (order is irrelevant to it,
# but we keep the canonical Bloomberg order; the benchmark column is appended last).
HEADERS = [
    "Date", "Open", "High", "Low", "Close",
    "Moving Average(Simple,200,0)", "UBB(2)", "LBB(2)",
    "Moving Average(Simple,50,0)", "Maximum(100)", "Minimum(100)",
    "%DS(25)", "%DSS(15)",
]


def sma(v, n):
    out = []
    for i in range(len(v)):
        seg = v[i - n + 1:i + 1]
        out.append(sum(seg) / n if i >= n - 1 and all(x is not None for x in seg) else None)
    return out


def pstdev(v, n):
    """Population standard deviation (/n) -- matches render.py's stdev()."""
    out = []
    for i in range(len(v)):
        if i < n - 1:
            out.append(None); continue
        w = v[i - n + 1:i + 1]; m = sum(w) / n
        out.append((sum((z - m) ** 2 for z in w) / n) ** 0.5)
    return out


def rollmax(v, n):
    return [max(v[i - n + 1:i + 1]) if i >= n - 1 else None for i in range(len(v))]


def rollmin(v, n):
    return [min(v[i - n + 1:i + 1]) if i >= n - 1 else None for i in range(len(v))]


def stochastic(H, L, C):
    """The decoded Bloomberg %DS(25) / %DSS(15); see module docstring."""
    hh, ll = rollmax(H, 99), rollmin(L, 99)
    rawK = [None if hh[i] is None or hh[i] == ll[i]
            else 100 * (C[i] - ll[i]) / (hh[i] - ll[i]) for i in range(len(C))]
    ds = sma(sma(rawK, 25), 25)
    dss = sma(ds, 15)
    return ds, dss


def synthesize_workbook(bars, out_path, bench_bars=None, bench_name=None):
    """Write a Bloomberg-equivalent Sheet1 workbook the renderer can load.

    bars       : list of (date, open, high, low, close), ascending by date.
    bench_bars : same shape for the benchmark (or None for commodities/FX/rates).
    bench_name : e.g. "SPX" -> header "SPX Index - Last Price".
    Returns a small dict of the last-row values for logging / sanity checks.
    """
    dts = [b[0] for b in bars]
    O = [b[1] for b in bars]; H = [b[2] for b in bars]; L = [b[3] for b in bars]; C = [b[4] for b in bars]

    ma200 = sma(C, 200); ma50 = sma(C, 50)
    mid100 = sma(C, 100); sd100 = pstdev(C, 100)
    ubb = [m + 2 * s if m is not None and s is not None else None for m, s in zip(mid100, sd100)]
    lbb = [m - 2 * s if m is not None and s is not None else None for m, s in zip(mid100, sd100)]
    mx = rollmax(H, 100); mn = rollmin(L, 100)
    ds, dss = stochastic(H, L, C)

    bcol = None
    if bench_bars is not None:
        bench = {b[0]: b[4] for b in bench_bars}
        last = None; bcol = []
        for d in dts:                          # align by date, forward-fill gaps
            if d in bench:
                last = bench[d]
            bcol.append(last)

    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Sheet1"
    hdr = list(HEADERS)
    if bcol is not None:
        hdr.append(f"{bench_name} Index - Last Price")
    ws.append(hdr)
    r = lambda v, p: (round(v, p) if v is not None else None)
    for i in range(len(dts)):
        row = [dt.datetime(dts[i].year, dts[i].month, dts[i].day),
               r(O[i], 4), r(H[i], 4), r(L[i], 4), r(C[i], 4),
               r(ma200[i], 6), r(ubb[i], 6), r(lbb[i], 6), r(ma50[i], 6),
               r(mx[i], 4), r(mn[i], 4), r(ds[i], 6), r(dss[i], 6)]
        if bcol is not None:
            row.append(r(bcol[i], 4))
        ws.append(row)
    wb.save(out_path)
    return dict(n=len(dts), start=str(dts[0]), end=str(dts[-1]), last=C[-1],
                ma50=ma50[-1], ma200=ma200[-1], max100=mx[-1], min100=mn[-1],
                ds=ds[-1], dss=dss[-1], bench_last=(bcol[-1] if bcol else None))
