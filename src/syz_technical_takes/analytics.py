"""Verdict-driving analytics for Technical Takes.

Reads the synthesized workbook and returns one JSON object with every number the
§7 verdict grid needs: 200-day slope, 50/200 cross, the 100-day band-break signal
(computed exactly as render.build_chart2 does, so page 1 and page 2 agree), the
latest swing high/low, breakout/breakdown candidate levels, relative-strength
slope, and a mechanical verdict HINT. The hint is advisory — the model (or the
analyst subagent) forms the actual discretionary verdict and writes the prose.
"""
from __future__ import annotations

import datetime as dt
import openpyxl


def _sma(v, w):
    out = []
    for i in range(len(v)):
        seg = v[i - w + 1:i + 1]
        out.append(sum(seg) / w if i >= w - 1 and all(x is not None for x in seg) else None)
    return out


def analyze(workbook_path):
    wb = openpyxl.load_workbook(workbook_path, data_only=True)
    ws = wb["Sheet1"]
    hdr = [c.value for c in ws[1]]
    rows = [r for r in ws.iter_rows(min_row=2, values_only=True)
            if r[0] and all(r[i] is not None for i in (1, 2, 3, 4))]
    rows.sort(key=lambda r: r[0])
    has_bench = len(hdr) >= 14 and hdr[13] is not None

    D = [r[0].date() if hasattr(r[0], "date") else r[0] for r in rows]
    H = [r[2] for r in rows]; L = [r[3] for r in rows]; C = [r[4] for r in rows]
    ma200 = [r[5] for r in rows]; ma50 = [r[8] for r in rows]
    mx = [r[9] for r in rows]; mn = [r[10] for r in rows]
    ds = [r[11] for r in rows]; dss = [r[12] for r in rows]
    ubb = [r[6] for r in rows]; lbb = [r[7] for r in rows]
    n = len(rows)
    iso = lambda d: d.isoformat()

    def slope(a, k):
        return round(a[-1] - a[-1 - k], 4) if a[-1] is not None and a[-1 - k] is not None else None

    # --- 50/200 cross (most recent, daily) ---
    cross = None
    for i in range(1, n):
        if None in (ma50[i], ma200[i], ma50[i - 1], ma200[i - 1]):
            continue
        if (ma50[i - 1] - ma200[i - 1]) <= 0 < (ma50[i] - ma200[i]):
            cross = {"type": "golden", "date": iso(D[i])}
        if (ma50[i - 1] - ma200[i - 1]) >= 0 > (ma50[i] - ma200[i]):
            cross = {"type": "death", "date": iso(D[i])}

    # --- 100-day band-break signal (render.build_chart2 logic) ---
    xs = [i for i in range(n) if mx[i] is not None and mn[i] is not None]
    up_break = max((i for i in xs if H[i] >= mx[i] - 1e-9), default=None)
    dn_break = max((i for i in xs if L[i] <= mn[i] + 1e-9), default=None)
    if up_break is None and dn_break is None:
        touch = None
    elif dn_break is None or (up_break is not None and up_break > dn_break):
        touch = "upper"
    else:
        touch = "lower"
    band = {
        "last_band_broken": touch,
        "last_bar_momentum": ("up" if (len(ma200) > 5 and ma200[-1] is not None
                              and ma200[-6] is not None and ma200[-1] > ma200[-6]) else "down"),
        "upper_break_date": iso(D[up_break]) if up_break is not None else None,
        "upper_break_level": mx[up_break] if up_break is not None else None,
        "lower_break_date": iso(D[dn_break]) if dn_break is not None else None,
        "lower_break_level": mn[dn_break] if dn_break is not None else None,
    }
    badge = ("POSITIVE" if band["last_band_broken"] == "upper" and band["last_bar_momentum"] == "up"
             else "NEGATIVE" if band["last_band_broken"] == "lower" and band["last_bar_momentum"] == "down"
             else "MIXED")

    # --- swing structure (last 100-day window) ---
    win = range(n - 100, n)
    hi_i = max(win, key=lambda i: H[i]); lo_i = min(win, key=lambda i: L[i])
    lo60 = min(range(max(0, n - 60), n), key=lambda i: L[i])
    hi60 = max(range(max(0, n - 60), n), key=lambda i: H[i])

    out = {
        "dates": {"start": iso(D[0]), "end": iso(D[-1]), "bars": n},
        "last": C[-1], "ma50": ma50[-1], "ma200": ma200[-1],
        "price_above_ma50": C[-1] > ma50[-1], "price_above_ma200": C[-1] > ma200[-1],
        "ma50_above_ma200": ma50[-1] > ma200[-1],
        "ma200_slope_5_20_40": [slope(ma200, 5), slope(ma200, 20), slope(ma200, 40)],
        "ma50_slope_5_20_40": [slope(ma50, 5), slope(ma50, 20), slope(ma50, 40)],
        "cross_50_200": cross, "cross_spread_now": round(ma50[-1] - ma200[-1], 4),
        "high_100d": {"level": mx[-1], "made": iso(D[hi_i])},
        "low_100d": {"level": mn[-1], "made": iso(D[lo_i])},
        "last_vs_100d_high_pct": round(100 * (C[-1] / mx[-1] - 1), 2),
        "last_vs_100d_low_pct": round(100 * (C[-1] / mn[-1] - 1), 2),
        "swing_low_60d": {"level": L[lo60], "date": iso(D[lo60])},
        "swing_high_60d": {"level": H[hi60], "date": iso(D[hi60])},
        "stochastic": {"ds": ds[-1], "dss": dss[-1]},
        "bollinger": {"ubb": ubb[-1], "lbb": lbb[-1],
                      "position": ("above_upper" if C[-1] > ubb[-1]
                                   else "below_lower" if C[-1] < lbb[-1] else "inside")},
        "band_signal": band, "page2_badge": badge,
        "has_benchmark": has_bench,
    }

    if has_bench:
        bench = [r[13] for r in rows]
        rs = [(C[i] / bench[i] * 100 if bench[i] else None) for i in range(n)]
        rs200 = _sma([x if x is not None else 0.0 for x in rs], 200)
        out["relative_strength"] = {
            "benchmark": str(hdr[13]).split(" Index")[0].split(" - ")[0],
            "rs_last": round(rs[-1], 4) if rs[-1] else None,
            "rs200_last": round(rs200[-1], 4) if rs200[-1] else None,
            "rs200_slope_20_40_60": [round(rs200[-1] - rs200[-1 - k], 4) for k in (20, 40, 60)],
            "rs_above_rs200": (rs[-1] or 0) > (rs200[-1] or 0),
        }

    out["verdict_hint"] = _verdict_hint(out)
    return out


def _verdict_hint(a):
    """The §7 grid, mechanically. Advisory only; oscillators never override trend."""
    rising = (a["ma200_slope_5_20_40"][1] or 0) > 0
    falling = (a["ma200_slope_5_20_40"][1] or 0) < 0
    above200 = a["price_above_ma200"]
    upper = a["band_signal"]["last_band_broken"] == "upper"
    if rising and above200 and upper:
        return "BULLISH"            # HH/HL intact; a pullback to the 200-day is a correction within an uptrend
    if falling and not above200 and a["band_signal"]["last_band_broken"] == "lower":
        return "BEARISH"            # lower low + declining 200-day
    if upper and above200:
        return "BULLISH"
    return "NEUTRAL"                # range / price around the 200-day -> state both triggers
