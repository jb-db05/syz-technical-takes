"""Ticker / benchmark resolution for the Technical Takes data feed.

This is the ONE place that knows about the (currently keyless, dev-licence) data
source. Swap the symbol maps here when wiring a licensed feed; nothing else in the
package hard-codes a provider.

Benchmark convention (INPUTS.md §D): SXXP for European names, SPI for Swiss
(SMIC for the SPI Extra), TPX for Japan, SPX for US, MXWO for the world index.
"""
from __future__ import annotations

# Bloomberg exchange code (the " XX" suffix in "NOVN SW") -> Yahoo ticker suffix.
EXCH_SUFFIX = {
    "US": "", "UN": "", "UW": "", "UQ": "",         # United States
    "NA": ".AS",      # Amsterdam
    "SW": ".SW", "VX": ".SW",                        # SIX Swiss
    "LN": ".L",       # London
    "GY": ".DE", "GR": ".DE",                        # Xetra
    "FP": ".PA",      # Paris
    "IM": ".MI",      # Milan
    "SM": ".MC",      # Madrid
    "SS": ".ST",      # Stockholm
    "JT": ".T", "JP": ".T",                          # Tokyo
    "HK": ".HK",      # Hong Kong
}

# Benchmark NAME (what the RS panel prints) -> Yahoo symbol for its index.
# SPI is not on the keyless feed; SMI (^SSMI) is the practical Swiss proxy.
BENCH_YAHOO = {
    "SPX": "^GSPC",
    "SXXP": "^STOXX",
    "SMI": "^SSMI",
    "SPI": "^SSMI",     # fallback: no SPI on this feed -> SMI (note it to the user)
    "SMIC": "^SSMI",
    "TPX": "^TPX",
    "MXWO": "^990100-USD-STRD",
}

# Country / region -> default benchmark NAME.
REGION_BENCH = {
    "UNITED STATES": "SPX", "US": "SPX", "USA": "SPX",
    "SWITZERLAND": "SMI", "CH": "SMI",
    "NETHERLANDS": "SXXP", "GERMANY": "SXXP", "FRANCE": "SXXP", "ITALY": "SXXP",
    "SPAIN": "SXXP", "SWEDEN": "SXXP", "EUROPE": "SXXP", "EUROZONE": "SXXP",
    "UNITED KINGDOM": "SXXP", "UK": "SXXP",
    "JAPAN": "TPX",
    "WORLD": "MXWO", "GLOBAL": "MXWO",
}


def bloomberg_to_yahoo(ticker: str) -> str:
    """'NOVN SW' -> 'NOVN.SW', 'MSFT US' -> 'MSFT', 'ASML NA' -> 'ASML.AS'.

    A plain symbol with no space is returned unchanged (already a Yahoo symbol).
    """
    t = ticker.strip()
    if " " in t:
        root, exch = t.rsplit(" ", 1)
        return root.strip() + EXCH_SUFFIX.get(exch.strip().upper(), "")
    return t


def bench_yahoo(name: str) -> str:
    return BENCH_YAHOO.get(name.strip().upper(), name)


def default_bench(country: str) -> str:
    return REGION_BENCH.get((country or "").strip().upper(), "SPX")
