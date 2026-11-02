#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SYZ RESEARCH - TECHNICAL TAKES  (v1.7, self-contained build script)
==================================================================
Produces the three-page A4 PDF (analysis page, signal page, disclaimer page)
from one Bloomberg Excel export of a single instrument.

    pip install weasyprint cairosvg matplotlib openpyxl fonttools
    python3 technical_takes.py            # uses CONFIG below

As shipped, CONFIG reproduces the SPI Extra document of 29 October 2026
(Technical_Takes_SPIEX_2026-10-29.pdf - a breakout, so it also shows the
automatic IMPLIED TARGET). Put SPIEX.xlsx next to this script and run it.
For any other instrument edit CONFIG only - nothing below section 1 changes.

Network is needed once, to fetch the Nunito Sans variable font from the
Google Fonts repository on GitHub; the instanced static weights are then
cached in FONT_DIR (default ~/fonts, override with TT_FONTDIR).
Intermediate artefacts go to TT_WORKDIR (default ./_tt_build).

Everything else - the Syz logo, the hero motif, the CSS, the disclaimer -
is embedded in this file. See BUILD_SPEC.md for the full specification
and INPUTS.md for what to supply per document.
"""
import base64, io, json, math, os, pathlib, random, subprocess, sys, datetime as dt

# =============================================================================
# 1. CONFIG — the only section to edit per document
# =============================================================================
CONFIG = dict(
    # --- data and output --------------------------------------------------------
    xlsx            = "SPIEX.xlsx",                    # Bloomberg export, next to the script
    outdir          = os.environ.get("TT_OUTDIR", "/mnt/user-data/outputs"),
    slug            = "Technical_Takes_SPIEX_2026-10-29",   # output = <outdir>/<slug>.pdf
    relative_strength = True,      # False for commodities, FX, rates or no benchmark column
    page2           = True,        # False = page 1 + disclaimer page only
    decimals        = 1,           # 1 equities/indices/commodities/crypto, 2 FX and yields
    body_pt         = 8.6,         # verdict-box body size (pt)
    chart1_height_mm = 128,
    years           = 2,           # plotted window in years (house default for Technical Takes: 2)
    ypad            = (0.90, 1.12),   # price-panel padding; (0.985, 1.02) for FX / yields

    # --- lines drawn on chart 1 -------------------------------------------------
    overlays        = {
        "hlines": [6741.2],                          # 7 Aug 2026 record, broken on 29 Oct
        "hline_from": {6741.2: "2026-08-07"},        # each level starts at its anchor date
        "hlines_dotted": [],                         # fine dots: broken pivots / never-traded levels
        "trendlines": [],                            # e.g. [("2026-03-02", "2026-09-09", "highs")]
        "tag": True,                                 # right-edge tags for the levels above
    },
    res_level       = None,                    # (level, "YYYY-MM-DD"): mint segment at a named pivot
    sup_level       = (6297.2, "2026-09-15"),  # mulberry segment at the 15 Sep 2026 low
    hide_lines      = ("res",),                # drop the 100-day band segment + tag: "res" / "sup"
    hide_tags       = (),                      # drop single right-edge tags: "res" "sup" "ma200" "last"
    chart2_red_bars = (),                      # page-2 bars forced red (display only)

    # --- text ------------------------------------------------------------------------
    doc_label       = "TECHNICAL ANALYSIS",
    date            = "29 October 2026",
    strip           = ("SPI EXTRA &nbsp;&middot;&nbsp; SPIEX &nbsp;&middot;&nbsp; CHF "
                       "&nbsp;&middot;&nbsp; SMALL &amp; MID CAPS &nbsp;&middot;&nbsp; SWITZERLAND"),
    headline        = "SPI Extra: breakout to a new record confirms the uptrend",
    verdict         = "BULLISH",                       # BULLISH / NEUTRAL / BEARISH
    last            = "6769.3",                        # unit prefix optional, e.g. "USD 1497.9"
    analysis_html   = (
        "<p><b>The primary trend remains positive.</b> The 200-day moving average (<b>6366.5</b>) is rising and "
        "price trades above it and the 50-day (<b>6546.5</b>). The breakout above the August record at "
        "<b>6741.2</b> confirms the uptrend with a higher high. <b>Projecting the 100-day volatility range on the "
        "breakout level gives an implied target of __TARGET__.</b></p>"
        "<p><b>Momentum leaves room for further upside.</b> Stochastic at <b>63</b> is not overbought, although "
        "price trades above the upper Bollinger band (<b>6724.2</b>). Relative momentum against the SMI remains "
        "negative, with a declining 200-day average. The bullish bias holds above the 200-day moving average.</p>"
    ),
    supports        = "6741.2 / 6297.2",
    resistances     = "Record high",
    target          = {"breakout": 6741.2, "direction": "up"},   # breakouts only; else delete the key
    invalidation    = "Close below 6366.5 (200d MA)",
    max_para_lines  = 4,                               # verdict-box paragraph cap (lines)
    chart2_title    = "Breakout &amp; Momentum Signals",
    business_title  = "THE INDEX",     # THE BUSINESS / THE INDEX / THE SECTOR / THE INSTRUMENT / THE CONTRACT / THE PAIR
    business_html   = (
        "The <b>SPI Extra</b> covers the Swiss <b>small- and mid-cap</b> segment: all constituents of the Swiss "
        "Performance Index excluding the 20 SMI blue chips. It is weighted by free-float market capitalisation and "
        "calculated as a <b>total-return index</b>. Compared with the SMI, it carries a larger weight in "
        "<b>industrials, technology and domestic financials</b> and a much smaller one in healthcare and staples."
    ),
    author          = "Florian Marini, CFA, CMT &ndash; Head of Research &middot; Syz Private Banking",
    footer          = "Syz Research &middot; Technical Takes &middot; 29 October 2026",
    chart_source    = "Source: Syz Research / Bloomberg",
    chart2_source   = "Source: Syz Research / Bloomberg",
)

# Path globals are resolved lazily by configure() so importing this module has no
# filesystem side effects (it is a package module, not a script). main() calls
# configure() itself if nothing set the paths yet.
WORKDIR = FONT_DIR = ROOT = OUT = None


def configure(outdir=None, workdir=None, fontdir=None):
    """Set the output / scratch / font directories. Call before main()."""
    global WORKDIR, FONT_DIR, ROOT, OUT
    WORKDIR = pathlib.Path(workdir or os.environ.get("TT_WORKDIR", "./_tt_build")).resolve()
    FONT_DIR = pathlib.Path(fontdir or os.environ.get(
        "TT_FONTDIR", pathlib.Path.home() / "fonts")).resolve()
    ROOT = WORKDIR
    OUT = pathlib.Path(outdir or os.environ.get("TT_OUTDIR", "/mnt/user-data/outputs"))
    WORKDIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    return WORKDIR, OUT, FONT_DIR

SYZ_LOGO_SVG_B64 = "PHN2ZyBjbGFzcz0ic3l6bG9nbyIgdmlld0JveD0iMCAwIDEwMTMuOTcgNzA4LjY2IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiBpZD0iTG9nb3MiIG92ZXJmbG93PSJoaWRkZW4iPjxkZWZzPjxsaW5lYXJHcmFkaWVudCB4MT0iMCIgeTE9IjM1NC4zMyIgeDI9Ijc4NC4xOSIgeTI9IjM1NC4zMyIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiIGlkPSJOZXdfR3JhZGllbnRfU3dhdGNoXzIiPjxzdG9wIG9mZnNldD0iMCIgc3RvcC1jb2xvcj0iI0ZGNkMwRSIvPjxzdG9wIG9mZnNldD0iMC41IiBzdG9wLWNvbG9yPSIjRkZBNDAwIi8+PHN0b3Agb2Zmc2V0PSIxIiBzdG9wLWNvbG9yPSIjRkZDNTQ1Ii8+PC9saW5lYXJHcmFkaWVudD48L2RlZnM+PHBhdGggZD0iTTc1My42IDIzMy44QzcyMi44NyAyMzMuOCA2NjEuNTEgMjY0LjQ4IDYxMC43MyAyODcuMTcgNjM2LjQ1IDI1Ny41OCA2NjAuMjYgMjI4LjI0IDY3OC4xNSAyMDMuNDYgNzAwLjAzIDE3My4xNCA3MDMuNDMgMTU4LjkzIDY4OS41MSAxMzQuODUgNjgyLjQ4IDEyMi43IDY3MC43OSAxMTUuMDIgNjU2LjI3IDExNS4wMiA1OTIuNjcgMTE1LjAyIDUyMC43OCAxNjUuMDQgNDc0Ljg0IDIxOC45MiA0NzMuMDUgMTk4LjMxIDQ2OC40IDE3MS4xNSA0NDUuMjEgMTcxLjE1IDQyMi4wMiAxNzEuMTUgNDE5LjIgMTkxLjM4IDQxMy4wMSAyMjMuNiA0MDAuMzggMjg5LjI1IDM4Mi45MiAzMjUuMjkgMzcxLjI0IDMyNS4yOSAzNjYuMjkgMzI1LjI5IDM2NC41NyAzMTkuNDIgMzY0LjU3IDMwNi44MyAzNjQuNTcgMjcwLjkzIDM3OS4wMSAyMjAuMDcgMzg0LjA1IDE4OS45NCAzODYuNzMgMTc2Ljk5IDM4Ny45OSAxNTguMjkgMzc2LjIzIDE1MC4xNSAzNjIuOTkgMTQwLjk4IDM1Mi4wMSAxNDMuMDYgMzIwLjM1IDE2NC41IDMwNS41MSAxNzQuNTUgMjQ1LjYyIDIxMS43NCAxODQuMDYgMjUzLjg4IDEyOS4wNCAyMTQuMjQgNTEuMTYgMTY3LjU5IDUxLjE2IDEwMC40OCA1MS4xNiA2OC4xNSA3Ni4yNiA0Ni4zNSAxMDguMjUgNDYuMzUgMTU0Ljc0IDQ2LjM1IDE2OS45OCA3NS41NCAxNzIuOTcgMTEwLjczIDE3NC45MyAxMzMuOCAxODguMjcgMTQwLjc4IDIwNC4wOCAxMzkuMTUgMjE5Ljk2IDEzNy41MSAyMjguMzMgMTI0LjE1IDIyNy4yMSAxMDEuMzQgMjI1LjM3IDYzLjk4IDE5My43OSAwIDExMi4wNCAwIDM5LjYxIDAgMCA0NS4yNSAwIDEwMC41NiAwIDE4OC41NyA4NC45MyAyNDguODYgMTM5LjU3IDI4NS4xMSA4MC40OSAzMjcuODIgMzAuMDUgMzcwLjEyIDMwLjA1IDM5MC42MiAzMC4wNSA0MDguOTUgNDQuMzMgNDE3LjUxIDc1Ljg4IDQxMy4wMyAxMTUuMTggNDA3LjQ0IDIzNy4zMiAzNzUuODUgMjM3LjMyIDMxNC43NCAyMzcuMzIgMzA0LjIxIDIzMC42NSAyOTMuNzIgMjE5Ljg1IDI4Mi45MSAyNTguNzYgMjU3LjYxIDI5Ny4wNCAyMzUuMzQgMzI2LjM5IDIyMS4yNyAzMTIuMTcgMjkyLjA3IDMwMi4wOCAzNzMuODkgMzU4LjYgMzczLjg5IDM3Mi42NiAzNzMuODkgMzg2LjQ5IDM2NC41MiAzOTkuMjIgMzQ5Ljk4IDM2NS45OCA0MjkuNjkgMzQ4LjUzIDUxMi44NSAzNDguNTMgNTcyLjE5IDM0OC41MyA2NzAuNTMgMzc1LjE2IDcwOC42NiA0MjQuMjMgNzA4LjY2IDQ4My44NyA3MDguNjYgNDkyLjQ2IDYxNS40MiA0OTIuNDYgNTE3LjIgNDkyLjQ2IDQ0My45NCA0ODYuNjUgMzQ5Ljg2IDQ4MC43IDI4NC44OSA1MjcuMDggMjE4LjEgNTg1LjgyIDE3MC4yMyA2NDcuOTkgMTU5LjY0IDYyMy43NCAyMDAuNTcgNTg1LjEzIDI0Mi44OCA1NjEuMDUgMjcyLjUyIDU1MC45IDI4NS4wMSA1NDUuODQgMjk1Ljc0IDU0NS44NCAzMDUuOTUgNTQ1Ljg0IDMyMS4wNyA1NTguNTIgMzM4LjkxIDU4Mi43MiAzMzguOTEgNjA2LjkyIDMzOC45MSA2NjkuNjUgMzEwLjA5IDcyNS43NSAyOTAuNTYgNzQzLjMxIDI4NC40NSA3NTguNDUgMjg4LjQ5IDc3MC4wOSAyODMuMjUgNzgwLjIgMjc4LjY5IDc4NC4xNyAyNzAgNzg0LjE5IDI2MC41OSA3ODQuMjIgMjQ3LjU4IDc3NS4xNyAyMzMuODEgNzUzLjU5IDIzMy44MVpNMTI2Ljc0IDM1NS45NEMxMTguODcgMzU3LjcyIDEyMC4xOSAzNTQuMDcgMTI1LjEgMzUwLjIyIDE0MS40MSAzMzcuNDIgMTU5LjIxIDMyNC4zIDE3Ny41NyAzMTEuNDMgMTgyLjA0IDMxNS4yNCAxODQuNiAzMTguMzggMTg0LjYgMzIwLjg0IDE4NC42IDMzNS41MyAxNTQuMjIgMzQ5LjczIDEyNi43NCAzNTUuOTRaTTQyMy44IDY1OS40OEM0MDcuNjEgNjU5LjQ4IDM5OS4zNSA2MjkuODUgMzk5LjM1IDU4Ni4zIDM5OS4zNSA1MTkuOSA0MTMuNTUgNDMzLjU0IDQ0MC42NiAzNjIuNTUgNDQ2LjE4IDUwNi40NSA0NTAuOTQgNjU5LjQ4IDQyMy44MSA2NTkuNDhaIiBzdHJva2Utd2lkdGg9IjAiIGZpbGw9InVybCgjTmV3X0dyYWRpZW50X1N3YXRjaF8yKSIvPjxwYXRoIGQ9Ik01ODEuNjcgNDU0Ljg0IDYwNC42MyA0NTQuODRDNjE2LjU1IDQ1NC44NCA2MjQuMDcgNDYxLjggNjI0LjA3IDQ3My4zMiA2MjQuMDcgNDg0Ljg0IDYxNi43MSA0OTEuNzIgNjA0LjQ3IDQ5MS43Mkw1OTMuNTEgNDkxLjcyIDU5My41MSA1MTAuODQgNTgxLjY3IDUxMC44NCA1ODEuNjcgNDU0Ljg0Wk02MDQuMyA0ODAuODRDNjA5LjAyIDQ4MC44NCA2MTIuMjIgNDc3Ljk2IDYxMi4yMiA0NzMuMjQgNjEyLjIyIDQ2OC4xMiA2MDkuNSA0NjUuNjQgNjA0LjM4IDQ2NS42NEw1OTMuNSA0NjUuNjQgNTkzLjUgNDgwLjg0IDYwNC4zIDQ4MC44NFoiIHN0cm9rZS13aWR0aD0iMCIgZmlsbD0iI0ZGQTQwMCIvPjxwYXRoIGQ9Ik02OTAgNTEwLjg0IDY3Ny4yOCA1MTAuODQgNjY2LjcyIDQ5MS4xNiA2NTkuNTIgNDkxLjE2IDY1OS41MiA1MTAuODQgNjQ3LjY4IDUxMC44NCA2NDcuNjggNDU0Ljg0IDY3MC40OCA0NTQuODRDNjgyLjMyIDQ1NC44NCA2ODkuNiA0NjEuNzIgNjg5LjYgNDcyLjkyIDY4OS42IDQ4MS4wOCA2ODUuNTIgNDg3LjE2IDY3OC42NCA0ODkuOEw2NzguNjQgNDg5Ljg4IDY5MCA1MTAuODRaTTY2OS4wNCA0ODAuMzZDNjc0LjcyIDQ4MC4zNiA2NzcuNzYgNDc3LjcyIDY3Ny43NiA0NzIuODQgNjc3Ljc2IDQ2Ny45NiA2NzQuOCA0NjUuNjQgNjY5LjA0IDQ2NS42NEw2NTkuNTIgNDY1LjY0IDY1OS41MiA0ODAuMzYgNjY5LjA0IDQ4MC4zNloiIHN0cm9rZS13aWR0aD0iMCIgZmlsbD0iI0ZGQTQwMCIvPjxwYXRoIGQ9Ik03MTUuMjcgNDU0Ljg0IDcyNy4xMSA0NTQuODQgNzI3LjExIDUxMC44NCA3MTUuMjcgNTEwLjg0IDcxNS4yNyA0NTQuODRaIiBzdHJva2Utd2lkdGg9IjAiIGZpbGw9IiNGRkE0MDAiLz48cGF0aCBkPSJNNzQ5LjkgNDU0Ljg0IDc2Mi4zOCA0NTQuODQgNzc1Ljk4IDQ5NC4yOCA3NzYuMTQgNDk0LjI4IDc4OS42NiA0NTQuODQgODAyLjIyIDQ1NC44NCA3ODEuOTggNTEwLjg0IDc3MC4wNiA1MTAuODQgNzQ5LjkgNDU0Ljg0WiIgc3Ryb2tlLXdpZHRoPSIwIiBmaWxsPSIjRkZBNDAwIi8+PHBhdGggZD0iTTg1MC44MSA1MDIuMTIgODI5LjM3IDUwMi4xMiA4MjYuNDEgNTEwLjg0IDgxNC42NSA1MTAuODQgODM0LjY1IDQ1NC44NCA4NDUuNTMgNDU0Ljg0IDg2NS41MyA1MTAuODQgODUzLjc3IDUxMC44NCA4NTAuODEgNTAyLjEyWk04NDcuMjEgNDkxLjcyIDg0MC4xNyA0NzEuMDggODQwLjAxIDQ3MS4wOCA4MzIuOTcgNDkxLjcyIDg0Ny4yMSA0OTEuNzJaIiBzdHJva2Utd2lkdGg9IjAiIGZpbGw9IiNGRkE0MDAiLz48cGF0aCBkPSJNODk0Ljc3IDQ2NS43MiA4NzguNTMgNDY1LjcyIDg3OC41MyA0NTQuODQgOTIyLjc3IDQ1NC44NCA5MjIuNzcgNDY1LjcyIDkwNi42MSA0NjUuNzIgOTA2LjYxIDUxMC44NCA4OTQuNzcgNTEwLjg0IDg5NC43NyA0NjUuNzJaIiBzdHJva2Utd2lkdGg9IjAiIGZpbGw9IiNGRkE0MDAiLz48cGF0aCBkPSJNOTQ2LjczIDQ1NC44NCA5ODIuODEgNDU0Ljg0IDk4Mi44MSA0NjUuNzIgOTU4LjU3IDQ2NS43MiA5NTguNTcgNDc3LjA4IDk4MC42NSA0NzcuMDggOTgwLjY1IDQ4Ny40OCA5NTguNTcgNDg3LjQ4IDk1OC41NyA0OTkuOTYgOTgyLjg5IDQ5OS45NiA5ODIuODkgNTEwLjg0IDk0Ni43MyA1MTAuODQgOTQ2LjczIDQ1NC44NFoiIHN0cm9rZS13aWR0aD0iMCIgZmlsbD0iI0ZGQTQwMCIvPjxwYXRoIGQ9Ik01ODEuNjcgNTY0Ljg0IDYwNS45OSA1NjQuODRDNjE1LjY3IDU2NC44NCA2MjIuNjMgNTcxLjE2IDYyMi42MyA1NzkuODggNjIyLjYzIDU4NC41MiA2MjAuNDcgNTg4LjI4IDYxNi45NSA1OTAuMzZMNjE2Ljk1IDU5MC41MkM2MjEuNzUgNTkyLjc2IDYyNC43MSA1OTcuNDggNjI0LjcxIDYwMy40IDYyNC43MSA2MTUuMDggNjE3Ljc1IDYyMC44NCA2MDMuNDMgNjIwLjg0TDU4MS42NyA2MjAuODQgNTgxLjY3IDU2NC44NFpNNjA0LjMgNTg3LjE2QzYwOC41NCA1ODcuMTYgNjEwLjg2IDU4NS4wOCA2MTAuODYgNTgxLjI0IDYxMC44NiA1NzcuNCA2MDguNTQgNTc1LjQgNjA0LjMgNTc1LjRMNTkzLjUgNTc1LjQgNTkzLjUgNTg3LjE2IDYwNC4zIDU4Ny4xNlpNNjA1LjU4IDYxMC4yOEM2MTAuNjIgNjEwLjI4IDYxMi45NCA2MDguMDQgNjEyLjk0IDYwMy4zMiA2MTIuOTQgNTk4LjkyIDYxMC4zOCA1OTYuNTIgNjA1LjY2IDU5Ni41Mkw1OTMuNSA1OTYuNTIgNTkzLjUgNjEwLjI4IDYwNS41OCA2MTAuMjhaIiBzdHJva2Utd2lkdGg9IjAiIGZpbGw9IiNGRkE0MDAiLz48cGF0aCBkPSJNNjgwLjAxIDYxMi4xMiA2NTguNTcgNjEyLjEyIDY1NS42MSA2MjAuODQgNjQzLjg1IDYyMC44NCA2NjMuODUgNTY0Ljg0IDY3NC43MyA1NjQuODQgNjk0LjczIDYyMC44NCA2ODIuOTcgNjIwLjg0IDY4MC4wMSA2MTIuMTJaTTY3Ni40MSA2MDEuNzIgNjY5LjM3IDU4MS4wOCA2NjkuMjEgNTgxLjA4IDY2Mi4xNyA2MDEuNzIgNjc2LjQxIDYwMS43MloiIHN0cm9rZS13aWR0aD0iMCIgZmlsbD0iI0ZGQTQwMCIvPjxwYXRoIGQ9Ik03MTcuNTcgNTY0Ljg0IDcyOS43MyA1NjQuODQgNzQ4LjY5IDYwMC40NCA3NDguODUgNjAwLjQ0IDc0OC44NSA1NjQuODQgNzYwLjY5IDU2NC44NCA3NjAuNjkgNjIwLjg0IDc0OC41MyA2MjAuODQgNzI5LjU3IDU4NS4yNCA3MjkuNDEgNTg1LjI0IDcyOS40MSA2MjAuODQgNzE3LjU3IDYyMC44NCA3MTcuNTcgNTY0Ljg0WiIgc3Ryb2tlLXdpZHRoPSIwIiBmaWxsPSIjRkZBNDAwIi8+PHBhdGggZD0iTTc4OS4xOSA1NjQuODQgODAxLjAzIDU2NC44NCA4MDEuMDMgNTg3LjcyIDgwMS4xOSA1ODcuNzIgODE5Ljk5IDU2NC44NCA4MzMuODMgNTY0Ljg0IDgxMy4yNyA1ODkuNjQgODM1LjQzIDYyMC44NCA4MjEuMzUgNjIwLjg0IDgwNS45OSA1OTguNDQgODA1LjgzIDU5OC40NCA4MDEuMDMgNjA0LjI4IDgwMS4wMyA2MjAuODQgNzg5LjE5IDYyMC44NCA3ODkuMTkgNTY0Ljg0WiIgc3Ryb2tlLXdpZHRoPSIwIiBmaWxsPSIjRkZBNDAwIi8+PHBhdGggZD0iTTg1OC4yMyA1NjQuODQgODcwLjA3IDU2NC44NCA4NzAuMDcgNjIwLjg0IDg1OC4yMyA2MjAuODQgODU4LjIzIDU2NC44NFoiIHN0cm9rZS13aWR0aD0iMCIgZmlsbD0iI0ZGQTQwMCIvPjxwYXRoIGQ9Ik04OTguNDUgNTY0Ljg0IDkxMC42MSA1NjQuODQgOTI5LjU3IDYwMC40NCA5MjkuNzMgNjAwLjQ0IDkyOS43MyA1NjQuODQgOTQxLjU3IDU2NC44NCA5NDEuNTcgNjIwLjg0IDkyOS40MSA2MjAuODQgOTEwLjQ1IDU4NS4yNCA5MTAuMjkgNTg1LjI0IDkxMC4yOSA2MjAuODQgODk4LjQ1IDYyMC44NCA4OTguNDUgNTY0Ljg0WiIgc3Ryb2tlLXdpZHRoPSIwIiBmaWxsPSIjRkZBNDAwIi8+PHBhdGggZD0iTTk2Ny4xOCA1OTIuODRDOTY3LjE4IDU3NS4xNiA5NzYuOTQgNTYzLjY0IDk5MS45IDU2My42NCAxMDAzLjY2IDU2My42NCAxMDEyLjU0IDU3MS40OCAxMDEzLjk4IDU4Mi44NEwxMDAyLjQ2IDU4NC42OEMxMDAxLjI2IDU3OC4yOCA5OTcuNDIgNTc0LjQ0IDk5MS45IDU3NC40NCA5ODMuODIgNTc0LjQ0IDk3OS4wMiA1ODEuMzIgOTc5LjAyIDU5Mi44NCA5NzkuMDIgNjA0LjM2IDk4My44MiA2MTEuMjQgOTkxLjk4IDYxMS4yNCA5OTguNTQgNjExLjI0IDEwMDIuNDYgNjA3LjQgMTAwMi41NCA2MDAuNzZMOTkyLjU0IDYwMC43NiA5OTIuNTQgNTkxLjI0IDEwMTMuNzQgNTkxLjI0IDEwMTMuNzQgNTk4Ljg0QzEwMTMuNzQgNjEyLjg0IDEwMDUuMSA2MjIuMDQgOTkxLjkgNjIyLjA0IDk3Ni44NiA2MjIuMDQgOTY3LjE4IDYxMC42IDk2Ny4xOCA1OTIuODRaIiBzdHJva2Utd2lkdGg9IjAiIGZpbGw9IiNGRkE0MDAiLz48L3N2Zz4="

# =============================================================================
# 2. FONTS — Nunito static instances (downloaded + instanced once)
# =============================================================================
NUNITO_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/nunitosans/"
              "NunitoSans%5BYTLC,opsz,wdth,wght%5D.ttf")   # Nunito Sans, not the rounded Nunito
NUNITO_WEIGHTS = [("Regular", 400), ("SemiBold", 600), ("Bold", 700), ("ExtraBold", 800)]

def ensure_fonts():
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    if all((FONT_DIR / f"NunitoSans-{n}.ttf").exists() for n, _ in NUNITO_WEIGHTS):
        return
    var = FONT_DIR / "NunitoSans.ttf"
    if not var.exists():
        subprocess.run(["curl", "-sL", "-o", str(var), NUNITO_URL], check=True)
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    for name, wght in NUNITO_WEIGHTS:
        f = TTFont(str(var))
        inst = instancer.instantiateVariableFont(
            f, {"wght": wght, "wdth": 100, "opsz": 12, "YTLC": 500})
        inst["name"].setName("Nunito Sans", 1, 3, 1, 0x409)
        inst["name"].setName(name, 2, 3, 1, 0x409)
        inst["name"].setName(f"Nunito Sans {name}", 4, 3, 1, 0x409)
        inst["name"].setName(f"NunitoSans-{name}", 6, 3, 1, 0x409)
        inst.save(str(FONT_DIR / f"NunitoSans-{name}.ttf"))
    home_fonts = pathlib.Path.home() / ".fonts"
    home_fonts.mkdir(exist_ok=True)
    for n, _ in NUNITO_WEIGHTS:
        tgt = home_fonts / f"NunitoSans-{n}.ttf"
        if not tgt.exists():
            tgt.write_bytes((FONT_DIR / f"NunitoSans-{n}.ttf").read_bytes())
    subprocess.run(["fc-cache", "-f"], capture_output=True)

# =============================================================================
# 3. HERO MOTIF (SVG, drawn from scratch — deterministic, seed 11)
# =============================================================================

def build_motif():
    """Returns the hero candlestick motif as SVG text."""
    random.seed(11)
    W, H = 1440, 300
    N = 62                      # candles
    X0, DX = 34, 22.4

    # ---- 5-wave skeleton (y in svg units, lower value = higher price) ----
    pivots = [(0, 214), (0.17, 140), (0.30, 178), (0.62, 84), (0.74, 118), (1.00, 36)]


    def path_y(t):
        for (t0, y0), (t1, y1) in zip(pivots, pivots[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / (t1 - t0)
                u = u * u * (3 - 2 * u)                      # smoothstep
                return y0 + (y1 - y0) * u
        return pivots[-1][1]


    closes = []
    for i in range(N):
        t = i / (N - 1)
        noise = random.gauss(0, 9.5) + 6.0 * math.sin(i / 2.7)
        closes.append(path_y(t) + noise)

    opens = [closes[0] + 3] + closes[:-1]

    parts = []
    parts.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">')
    parts.append(
        '<defs>'
        '<linearGradient id="og" x1="0" x2="1">'
        '<stop offset="0" stop-color="#FF6C0E"/><stop offset=".55" stop-color="#FFA400"/>'
        '<stop offset="1" stop-color="#FFC545"/></linearGradient>'
        '<linearGradient id="fade" x1="0" x2="0" y1="0" y2="1">'
        '<stop offset=".52" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>'
        '<radialGradient id="lg" cx="0.5" cy="0.5" r="0.5">'
        '<stop offset=".3" stop-color="#fff" stop-opacity=".45"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
        '</defs>'
    )

    BW = 11.6                      # body width
    UP_FILL, UP_EDGE = "#ffffff", "#8e9db6"
    DN_FILL, DN_EDGE = "#aab7cd", "#8e9db6"
    WICK = "#9aa8bf"

    for i in range(N):
        x = X0 + i * DX
        o, c = opens[i], closes[i]
        up = c <= o                                        # lower y = higher price
        rng = abs(o - c) + random.uniform(12, 28)
        mid = (o + c) / 2
        hi, lo = mid - rng / 2, mid + rng / 2
        top, bot = min(o, c), max(o, c)
        if bot - top < 2.2:                                # doji floor
            top, bot = mid - 1.1, mid + 1.1
        parts.append(
            f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{hi:.1f}" y2="{lo:.1f}" '
            f'stroke="{WICK}" stroke-width="1.15"/>'
        )
        parts.append(
            f'<rect x="{x - BW/2:.1f}" y="{top:.1f}" width="{BW:.1f}" height="{bot - top:.1f}" '
            f'rx="1.2" fill="{UP_FILL if up else DN_FILL}" stroke="{UP_EDGE if up else DN_EDGE}" '
            f'stroke-width="1.15"/>'
        )

    # ---- moving average (rolling mean, Catmull-Rom smoothed) ----
    K = 6
    ma = []
    for i in range(N):
        lo_i = max(0, i - K + 1)
        win = closes[lo_i:i + 1]
        ma.append((X0 + i * DX, sum(win) / len(win)))
    ma = ma[K - 1:]

    d = f"M {ma[0][0]:.1f},{ma[0][1]:.1f}"
    for i in range(len(ma) - 1):
        p0 = ma[max(i - 1, 0)]
        p1, p2 = ma[i], ma[i + 1]
        p3 = ma[min(i + 2, len(ma) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C {c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    parts.append(
        f'<path d="{d}" fill="none" stroke="url(#og)" stroke-width="3.1" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # ---- wave pivots ----
    for n, (t, y) in enumerate(pivots[1:], start=1):
        x = X0 + t * (N - 1) * DX
        yy = y - 26 if n != 4 else y + 24
        parts.append(
            f'<circle cx="{x:.0f}" cy="{yy:.0f}" r="9.5" fill="#fff" stroke="#c2cbdb" stroke-width="1.2"/>'
            f'<text x="{x:.0f}" y="{yy + 3.6:.0f}" text-anchor="middle" font-family="Nunito Sans,sans-serif" '
            f'font-weight="800" font-size="11" fill="#8b96ab">{n}</text>'
        )


    parts.append(f'<rect width="{W}" height="{H}" fill="url(#fade)"/>')
    parts.append('</svg>')

    return "".join(parts)


# =============================================================================
# 4. WORKBOOK LOADER — see BUILD_SPEC.md §Data rules
# =============================================================================

def _find(headers, *needles, last=False):
    hits = [i for i, h in enumerate(headers)
            if h and all(n.lower() in str(h).lower() for n in needles)]
    if not hits:
        return None
    return hits[-1] if last else hits[0]


def sma(v, n):
    return [None if i < n - 1 or None in v[i - n + 1:i + 1]
            else sum(v[i - n + 1:i + 1]) / n for i in range(len(v))]


def stdev(v, n):
    out = []
    for i in range(len(v)):
        if i < n - 1:
            out.append(None); continue
        w = v[i - n + 1:i + 1]; m = sum(w) / n
        out.append((sum((z - m) ** 2 for z in w) / n) ** 0.5)
    return out


def load(path, years=4):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Sheet1"]
    rows = list(ws.iter_rows(min_row=1, values_only=True))
    hdr = rows[0]
    c = dict(
        date=_find(hdr, "date"), o=_find(hdr, "open"), h=_find(hdr, "high"),
        l=_find(hdr, "low"), c=_find(hdr, "close"),
        ma200=_find(hdr, "moving average", "200"), ma50=_find(hdr, "moving average", "50"),
        ubb=_find(hdr, "ubb"), lbb=_find(hdr, "lbb"),
        mx=_find(hdr, "maximum"), mn=_find(hdr, "minimum"),
        ds=_find(hdr, "%ds("), dss=_find(hdr, "%dss"),
        bm=_find(hdr, "last price", last=True),
    )
    get = lambda r, k: r[c[k]] if c[k] is not None and c[k] < len(r) else None

    s1 = [r for r in rows[1:] if r[c["date"]] and all(get(r, k) is not None for k in "ohlc")]
    s1.sort(key=lambda r: r[c["date"]])

    # ---- Sheet 2, when the workbook carries one with data -------------------
    S2 = {}
    if "Sheet2" in wb.sheetnames:
        r2 = [r for r in wb["Sheet2"].iter_rows(min_row=2, values_only=True)
              if r and r[0] and all(x is not None for x in r[1:5])]
        r2.sort(key=lambda r: r[0])
        S2 = {r[0]: r for r in r2}

    dt_all = [r[c["date"]] for r in s1]
    close = [S2[d][4] if d in S2 else get(r, "c") for d, r in zip(dt_all, s1)]

    rounded = lambda vals: vals and all(abs(v - round(v)) < 1e-9 for v in vals if v is not None)
    ma200_col = [get(r, "ma200") for r in s1]
    needs_rebuild = rounded([v for v in ma200_col if v is not None])

    if needs_rebuild:
        ma200 = sma(close, 200)
        ma50 = sma(close, 50)
        m100, s100 = sma(close, 100), stdev(close, 100)
        ubb = [m + 2 * s if m and s else None for m, s in zip(m100, s100)]
        lbb = [m - 2 * s if m and s else None for m, s in zip(m100, s100)]
    else:
        ma200 = ma200_col
        ma50 = [get(r, "ma50") for r in s1]
        ubb = [get(r, "ubb") for r in s1]
        lbb = [get(r, "lbb") for r in s1]

    if c["mx"] is not None:
        mx = [get(r, "mx") for r in s1]
        mn = [get(r, "mn") for r in s1]
    elif S2:
        mx = [S2[d][6] if d in S2 else None for d in dt_all]
        mn = [S2[d][7] if d in S2 else None for d in dt_all]
    else:                                    # roll them from the exported highs/lows
        H = [get(r, "h") for r in s1]; L = [get(r, "l") for r in s1]
        mx = [max(H[i - 99:i + 1]) if i >= 99 else None for i in range(len(s1))]
        mn = [min(L[i - 99:i + 1]) if i >= 99 else None for i in range(len(s1))]

    bench = [get(r, "bm") for r in s1] if c["bm"] is not None else None
    rs = rs200 = None
    if bench and any(x for x in bench if x):
        # the benchmark can lag by a session (index not yet published): carry the
        # last value forward for the ratio so the series has no artificial gap
        ff, last_b = [], None
        for b in bench:
            last_b = b if b else last_b
            ff.append(last_b)
        rs = [c / b * 100 if (c and b) else None for c, b in zip(close, ff)]
        rs200 = sma([v if v is not None else 0.0 for v in rs], 200)

    d = dict(
        dt=dt_all,
        o=[S2[x][1] if x in S2 else get(r, "o") for x, r in zip(dt_all, s1)],
        h=[S2[x][2] if x in S2 else get(r, "h") for x, r in zip(dt_all, s1)],
        l=[S2[x][3] if x in S2 else get(r, "l") for x, r in zip(dt_all, s1)],
        c=close, ma200=ma200, ma50=ma50, ubb=ubb, lbb=lbb, mx=mx, mn=mn,
        ds=[get(r, "ds") for r in s1], dss=[get(r, "dss") for r in s1],
        rs=rs, rs200=rs200, rebuilt=needs_rebuild,
        bench_name=(str(hdr[c["bm"]]).split(" Index")[0].split(" - ")[0]
                    if c["bm"] is not None else None),
    )

    # ---- plotted window -----------------------------------------------------
    cut = (min(S2) if S2 else dt_all[-1] - dt.timedelta(days=365 * years))
    keep = [i for i, x in enumerate(dt_all) if x >= cut]
    win = {k: ([v[i] for i in keep] if isinstance(v, list) else v) for k, v in d.items()}
    win["full"] = d
    return win


YPAD = (0.90, 1.12)   # price-panel y padding (bottom, top multipliers); CONFIG["ypad"].
                      # FX and yields: (0.985, 1.02) - the equity default squashes a narrow
                      # range into a band in the middle of the panel
DECIMALS = 2      # set from CONFIG["decimals"] in main(): 2 for FX and yields,
                  # 1 for equities, commodities and crypto


def pf(v):
    """Price label: integers plain, otherwise CONFIG["decimals"] places."""
    if abs(v - round(v)) < 1e-9 and abs(v) >= 100:   # 7300 stays plain; 3.00 keeps its decimals
        return f"{v:.0f}"
    # round half up on the decimal representation (39384.85 -> 39384.9), so chart
    # tags agree with the levels written in the commentary
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(1).scaleb(-DECIMALS)
    return str(Decimal(repr(v)).quantize(q, rounding=ROUND_HALF_UP))


def bb_target(xlsx, level, direction="up"):
    """Breakout target from the 100-day Bollinger band width (house rule, 4 Oct 2026).

    Breakout bar = the most recent first CLOSE beyond `level` (above for "up",
    below for "down"); intraday pokes do not count. On that bar:
        bandwidth = (UBB - LBB) / ((UBB + LBB) / 2)      # 4 sigma as % of the 100d mean
        target    = level * (1 + bandwidth)   for "up"
                    level * (1 - bandwidth)   for "down"
    The width is frozen on the breakout bar and never recomputed afterwards.
    """
    f = load(xlsx, years=50)["full"]
    c, u, l, dts = f["c"], f["ubb"], f["lbb"], f["dt"]
    beyond = (lambda x: x > level) if direction == "up" else (lambda x: x < level)
    i = None
    for k in range(len(c) - 1, 0, -1):
        if beyond(c[k]) and not beyond(c[k - 1]):
            i = k
            break
    if i is None or u[i] is None or l[i] is None:
        raise ValueError(f"no close {'above' if direction == 'up' else 'below'} {level} found")
    mid = (u[i] + l[i]) / 2
    bw = (u[i] - l[i]) / mid
    tgt = level * (1 + bw) if direction == "up" else level * (1 - bw)
    return dict(target=tgt, bar=dts[i], bandwidth=bw, ubb=u[i], lbb=l[i], mid=mid, level=level)


# =============================================================================
# 5. CHARTS
# =============================================================================

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter, FixedLocator
from matplotlib import font_manager
import openpyxl


def build_chart1(SRC, OUTPNG, NO_RS=False, OVERLAYS=None, HEIGHT_MM=128, HIDE_TAGS=(), YEARS=4,
                 RES_LEVEL=None, SUP_LEVEL=None, HIDE_LINES=()):
    """Page-1 chart: price + stochastic (+ relative strength unless NO_RS)."""
    for f in FONT_DIR.glob("NunitoSans-*.ttf"):
        font_manager.fontManager.addfont(str(f))
    plt.rcParams["font.family"] = "Nunito Sans"

    d = load(SRC, years=YEARS)
    dts, op, hi, lo, cl = d["dt"], d["o"], d["h"], d["l"], d["c"]
    ma200, ma50, ubb, lbb = d["ma200"], d["ma50"], d["ubb"], d["lbb"]
    mx, mn, sk, sd_ = d["mx"], d["mn"], d["ds"], d["dss"]
    RS = None if (NO_RS or not d["rs"]) else (d["rs"], d["rs200"], d["bench_name"])

    LAST, RES, SUP = cl[-1], mx[-1], mn[-1]
    MA200_LAST, MA50_LAST = ma200[-1], ma50[-1]
    x = list(range(len(dts)))


    def nice_log_ticks(lo_, hi_, target=12):
        base = [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8]
        cands = sorted({b * 10 ** e for e in range(-3, 8) for b in base if lo_ <= b * 10 ** e <= hi_})
        if len(cands) < 5:                       # narrow range (FX): linear steps
            span = hi_ - lo_
            raw = span / max(target // 2, 4)
            mag = 10 ** math.floor(math.log10(raw))
            step = min((m * mag for m in (1, 2, 2.5, 5, 10)), key=lambda z: abs(z - raw))
            out, v = [], math.ceil(lo_ / step) * step
            while v <= hi_:
                out.append(round(v, 10)); v += step
            return out
        if len(cands) <= target:
            return cands
        return cands[::math.ceil(len(cands) / target)]


    MM = 1 / 25.4
    fig = plt.figure(figsize=(191 * MM, HEIGHT_MM * MM), dpi=300)
    if RS:
        gs = fig.add_gridspec(3, 1, height_ratios=[3.5, 1.0, 1.3], hspace=0.10,
                              left=0.006, right=0.928, top=0.986, bottom=0.078)
        ax1, ax2, ax3 = (fig.add_subplot(g) for g in gs)
        axes = (ax1, ax2, ax3)
    else:
        gs = fig.add_gridspec(2, 1, height_ratios=[4.2, 1.1], hspace=0.09,
                              left=0.006, right=0.928, top=0.986, bottom=0.078)
        ax1, ax2 = (fig.add_subplot(g) for g in gs)
        ax3 = None
        axes = (ax1, ax2)

    FRAME, MUTED = "#b9c2d0", "#8b95a8"
    for ax in axes:
        for s in ax.spines.values():
            s.set_color(FRAME); s.set_linewidth(0.6)
        ax.tick_params(which="both", left=False, labelleft=False, right=True, labelright=True,
                       length=2, width=0.5, labelsize=5.6, colors="#5b6579")
        ax.grid(False)

    # ---- panel 1: price ------------------------------------------------------
    BAR, w = "#141a2e", 0.42
    for i in x:
        ax1.vlines(i, lo[i], hi[i], color=BAR, linewidth=0.42)
        ax1.hlines(op[i], i - w, i, color=BAR, linewidth=0.42)
        ax1.hlines(cl[i], i, i + w, color=BAR, linewidth=0.42)

    ax1.plot(x, ubb, color="#aeb8c7", lw=0.4, ls=(0, (2.5, 2.5)))
    ax1.plot(x, lbb, color="#aeb8c7", lw=0.4, ls=(0, (2.5, 2.5)))
    ax1.plot(x, ma50, color="#1f4fd8", lw=0.8)
    ax1.plot(x, ma200, color="#d81f2a", lw=0.9)

    win = x[-100:]
    RES_I = max(win, key=lambda i: hi[i])
    SUP_I = min(win, key=lambda i: lo[i])
    # optional override of the mint resistance / mulberry support segment with a named pivot,
    # e.g. CONFIG["res_level"] = (1238.0, "2026-08-06") - the latest lower high in a downtrend
    def _pivot(spec):
        lvl, when = spec
        want = dt.date.fromisoformat(when)
        return lvl, min(range(len(dts)), key=lambda i: abs((dts[i].date() - want).days))
    if RES_LEVEL:
        RES, RES_I = _pivot(RES_LEVEL)
    if SUP_LEVEL:
        SUP, SUP_I = _pivot(SUP_LEVEL)
    x_end = x[-1] + 22
    # HIDE_LINES: "res" and/or "sup" drop the band segment AND its tag (CONFIG["hide_lines"]),
    # e.g. when a drawn key level sits right next to the 100-day low and would only add clutter
    if "res" not in HIDE_LINES:
        ax1.hlines(RES, RES_I, x_end, color="#3BAF90", lw=0.85, ls=(0, (4.5, 3)))
    if "sup" not in HIDE_LINES:
        ax1.hlines(SUP, SUP_I, x_end, color="#AC5D85", lw=0.85, ls=(0, (4.5, 3)))
    HIDE_TAGS = tuple(HIDE_TAGS) + tuple(HIDE_LINES)

    # ---- optional manual overlays (CONFIG["overlays"]) ----------------------
    # {"hlines": [level, ...],                      horizontal levels
    #  "hline_from": {level: "YYYY-MM-DD"},         optional left anchor per level
    #  "trendlines": [("YYYY-MM-DD", "YYYY-MM-DD")] anchored on those bars' lows
    #                                               (or highs with "highs": True);
    #                 a third element "highs"/"lows" sets it per line
    #  "tag": True}                                 right-edge tags for the levels
    OV_BLUE = "#4b9fe8"
    ov = OVERLAYS or {}
    bar_of = {}
    for i, dd in enumerate(dts):
        bar_of[dd.date().isoformat()] = i
    def _bar(datestr):
        want = dt.date.fromisoformat(datestr)
        best = min(range(len(dts)), key=lambda i: abs((dts[i].date() - want).days))
        return best
    ov_tags = []
    for lvl in ov.get("hlines", []):
        anchor = ov.get("hline_from", {}).get(lvl)
        i0 = _bar(anchor) if anchor else 0
        ax1.hlines(lvl, i0, x_end, color=OV_BLUE, lw=0.85, ls=(0, (5, 3)), zorder=4)
        if ov.get("tag", True):
            ov_tags.append((lvl, pf(lvl), OV_BLUE))
    # long-term / projected levels: fine DOTTED blue across the whole chart
    for lvl in ov.get("hlines_dotted", []):
        anchor = ov.get("hline_from", {}).get(lvl)
        i0 = _bar(anchor) if anchor else 0
        ax1.hlines(lvl, i0, x_end, color=OV_BLUE, lw=0.8, ls=(0, (1.2, 1.6)), zorder=4)
        if ov.get("tag", True):
            ov_tags.append((lvl, pf(lvl), OV_BLUE))
    for tl in ov.get("trendlines", []):
        (d1, d2) = tl[0], tl[1]
        i1, i2 = _bar(d1), _bar(d2)
        # per-line choice: ("d1", "d2", "highs") or ("d1", "d2", "lows");
        # a bare pair follows the global "highs" flag
        side = tl[2] if len(tl) > 2 else ("highs" if ov.get("highs") else "lows")
        src = hi if side == "highs" else lo
        y1, y2 = src[i1], src[i2]
        # geometric fit: a straight line on the log price axis
        g = (y2 / y1) ** (1.0 / (i2 - i1))
        ax1.plot([i1, x_end], [y1, y1 * g ** (x_end - i1)],
                 color=OV_BLUE, lw=0.85, ls=(0, (5, 3)), zorder=4)

    ax1.set_yscale("log")
    _ov_lv = list((OVERLAYS or {}).get("hlines", [])) + list((OVERLAYS or {}).get("hlines_dotted", []))
    _top = max([max(hi) * YPAD[1]] + [v * (1 + (YPAD[1] - 1) / 4) for v in _ov_lv])
    _bot = min([min(v for v in lo if v) * YPAD[0]] + [v * (1 - (1 - YPAD[0]) / 3) for v in _ov_lv])
    ax1.set_ylim(_bot, _top)
    ax1.yaxis.set_major_locator(FixedLocator(nice_log_ticks(*ax1.get_ylim(), target=14)))
    ax1.yaxis.set_minor_formatter(NullFormatter())
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g}"))
    ax1.text(1.075, 0.5, "Log", transform=ax1.transAxes, rotation=90, va="center", ha="left",
             color=MUTED, fontsize=5)


    def draw_tags(ax, items, logscale=False, min_gap=0.045):
        lo_, hi_ = ax.get_ylim()
        f = (lambda v: (math.log10(v) - math.log10(lo_)) / (math.log10(hi_) - math.log10(lo_))) \
            if logscale else (lambda v: (v - lo_) / (hi_ - lo_))
        seen = set(); uniq = []
        for v, t, c in items:
            if t in seen:
                continue
            seen.add(t); uniq.append((v, t, c))
        placed = sorted([(f(v), t, c) for v, t, c in uniq]); ys = [p[0] for p in placed]
        for i in range(1, len(ys)):
            if ys[i] - ys[i - 1] < min_gap:
                ys[i] = ys[i - 1] + min_gap
        for (f0, t, c), y in zip(placed, ys):
            ax.annotate(t, xy=(1.0, y), xycoords="axes fraction", xytext=(3, 0),
                        textcoords="offset points", va="center", ha="left", fontsize=5.2,
                        fontweight="bold", color="#fff",
                        bbox=dict(boxstyle="square,pad=0.24", fc=c, ec="none"))


    # HIDE_TAGS: any of "res", "sup", "ma200", "last" to drop that right-edge label
    _fx = lambda v, ovr: f"{v:.{DECIMALS}f}" if ovr else pf(v)   # named pivots keep their decimals (1238.0)
    _tags = {"res": (RES, _fx(RES, RES_LEVEL), "#3BAF90"), "ma200": (MA200_LAST, pf(MA200_LAST), "#d81f2a"),
             "last": (LAST, pf(LAST), "#202945"), "sup": (SUP, _fx(SUP, SUP_LEVEL), "#AC5D85")}
    draw_tags(ax1, [v for k, v in _tags.items() if k not in HIDE_TAGS] + ov_tags,
              logscale=True, min_gap=0.045)

    # ---- panel 2: stochastic -------------------------------------------------
    ax2.plot(x, sk, color="#1f4fd8", lw=0.6)
    ax2.plot(x, sd_, color="#e08033", lw=0.6)
    ax2.axhline(80, color="#d81f2a", lw=0.45)
    ax2.axhline(20, color="#2e9e5b", lw=0.45)
    ax2.set_ylim(-4, 104); ax2.set_yticks([0, 20, 50, 80, 100])
    draw_tags(ax2, [(sd_[-1], f"{sd_[-1]:.1f}", "#202945")], min_gap=0.06)
    ax2.text(0.004, 0.02, "Stochastic %DS(25) / %DSS(15)", transform=ax2.transAxes,
             fontsize=5.2, color=MUTED, va="bottom")

    # ---- panel 3: relative strength -----------------------------------------
    if RS:
        rs, rs200, bname = RS
        ax3.set_yscale("log")
        ax3.plot(x, rs, color="#202945", lw=0.6)
        ax3.plot(x, rs200, color="#d81f2a", lw=0.8)
        vals = [v for v in rs if v]
        ax3.set_ylim(min(vals) * 0.88, max(vals) * 1.12)
        ax3.yaxis.set_major_locator(FixedLocator(nice_log_ticks(*ax3.get_ylim(), target=5)))
        ax3.yaxis.set_minor_formatter(NullFormatter())
        ax3.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g}"))
        rs_last = next(v for v in reversed(rs) if v)
        rs200_last = next(v for v in reversed(rs200) if v)
        rfmt = lambda v: f"{v:.1f}" if v >= 10 else f"{v:.2f}" if v >= 1 else f"{v:.3f}"
        draw_tags(ax3, [(rs_last, rfmt(rs_last), "#202945"),
                        (rs200_last, rfmt(rs200_last), "#d81f2a")], logscale=True, min_gap=0.14)
        ax3.text(0.004, 0.93, f"Relative strength vs {bname} and its 200-day MA",
                 transform=ax3.transAxes, fontsize=5.2, color=MUTED, va="top")

    # ---- shared x ------------------------------------------------------------
    qt, ql = [], []
    for i, dd in enumerate(dts):
        if i > 0 and dd.month != dts[i - 1].month and dd.month in (1, 4, 7, 10):
            qt.append(i); ql.append(dd.strftime("%b"))
    last_ax = axes[-1]
    for ax in axes:
        ax.set_xlim(-4, x[-1] + 22)
        ax.set_xticks(qt); ax.set_xticklabels(ql)
        ax.tick_params(labelbottom=(ax is last_ax))
    last_ax.tick_params(axis="x", labelsize=5.2, pad=1.5)
    for y in sorted({dd.year for dd in dts}):
        ids = [i for i, dd in enumerate(dts) if dd.year == y]
        last_ax.annotate(str(y), xy=(ids[len(ids) // 2], 0), xycoords=("data", "axes fraction"),
                         xytext=(0, -15), textcoords="offset points", ha="center",
                         fontsize=5.4, color="#7b8598")

    fig.savefig(OUTPNG, dpi=300, facecolor="white")
    print(f"chart1 {OUTPNG} | last {pf(LAST)} res {pf(RES)} sup {pf(SUP)} "
          f"ma200 {MA200_LAST:.2f} ma50 {MA50_LAST:.2f} stoch {sk[-1]:.1f}/{sd_[-1]:.1f} "
          f"| rebuilt={d['rebuilt']} rs={'no' if not RS else RS[2]}")



def build_chart2(SRC, OUTPNG, YEARS=4, RED_BARS=()):
    """Page-2 chart + the mechanical signal dict (also written as JSON)."""
    for f in FONT_DIR.glob("NunitoSans-*.ttf"):
        font_manager.fontManager.addfont(str(f))
    plt.rcParams["font.family"] = "Nunito Sans"

    d = load(SRC, years=YEARS)
    dts, op, hi, lo, cl = d["dt"], d["o"], d["h"], d["l"], d["c"]
    ma, mx, mn = d["ma200"], d["mx"], d["mn"]
    LAST, RES, SUP = cl[-1], mx[-1], mn[-1]
    x = list(range(len(dts)))

    SLOPE_N = 5
    up = [True if i < SLOPE_N or ma[i] is None or ma[i - SLOPE_N] is None
          else ma[i] > ma[i - SLOPE_N] for i in range(len(dts))]


    def nice_log_ticks(lo_, hi_, target=14):
        base = [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8]
        c = sorted({b * 10 ** e for e in range(-3, 8) for b in base if lo_ <= b * 10 ** e <= hi_})
        if len(c) < 5:                           # narrow range (FX): linear steps
            span = hi_ - lo_
            raw = span / max(target // 2, 4)
            mag = 10 ** math.floor(math.log10(raw))
            step = min((m * mag for m in (1, 2, 2.5, 5, 10)), key=lambda z: abs(z - raw))
            out, v = [], math.ceil(lo_ / step) * step
            while v <= hi_:
                out.append(round(v, 10)); v += step
            return out
        return c if len(c) <= target else c[::math.ceil(len(c) / target)]


    MM = 1 / 25.4
    fig = plt.figure(figsize=(191 * MM, 128 * MM), dpi=300)
    ax = fig.add_axes([0.006, 0.072, 0.922, 0.918])
    for s in ax.spines.values():
        s.set_color("#b9c2d0"); s.set_linewidth(0.6)
    ax.tick_params(which="both", left=False, labelleft=False, right=True, labelright=True,
                   length=2, width=0.5, labelsize=5.6, colors="#5b6579")

    xs = [i for i in x if mx[i] is not None and mn[i] is not None]
    ax.plot(xs, [mx[i] for i in xs], color="#3BAF90", lw=0.8, ls=(0, (1.2, 1.6)), zorder=2)
    ax.plot(xs, [mn[i] for i in xs], color="#AC5D85", lw=0.8, ls=(0, (1.2, 1.6)), zorder=2)

    BLUE, RED, w = "#1f4fd8", "#d81f2a", 0.42
    for i in x:
        # RED_BARS: dates drawn red as an editorial highlight (e.g. the bar that broke key support);
        # display only - the slope rule and the mechanical signals below are unchanged
        c = RED if (dts[i].date().isoformat() in RED_BARS) else (BLUE if up[i] else RED)
        ax.vlines(i, lo[i], hi[i], color=c, linewidth=0.5, zorder=3)
        ax.hlines(op[i], i - w, i, color=c, linewidth=0.5, zorder=3)
        ax.hlines(cl[i], i, i + w, color=c, linewidth=0.5, zorder=3)

    ax.set_yscale("log")
    ax.set_ylim(min(v for v in lo if v) * YPAD[0], max(hi) * YPAD[1])
    ax.yaxis.set_major_locator(FixedLocator(nice_log_ticks(*ax.get_ylim())))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:g}"))
    ax.text(1.052, 0.5, "Log", transform=ax.transAxes, rotation=90, va="center", ha="left",
            color="#8b95a8", fontsize=5)


    def draw_tags(ax, items, min_gap=0.045):
        lo_, hi_ = ax.get_ylim()
        f = lambda v: (math.log10(v) - math.log10(lo_)) / (math.log10(hi_) - math.log10(lo_))
        seen = set(); uniq = []
        for v, t, c in items:
            if t in seen:
                continue
            seen.add(t); uniq.append((v, t, c))
        placed = sorted([(f(v), t, c) for v, t, c in uniq]); ys = [p[0] for p in placed]
        for i in range(1, len(ys)):
            if ys[i] - ys[i - 1] < min_gap: ys[i] = ys[i - 1] + min_gap
        for (f0, t, c), y in zip(placed, ys):
            ax.annotate(t, xy=(1.0, y), xycoords="axes fraction", xytext=(3, 0),
                        textcoords="offset points", va="center", ha="left", fontsize=5.2,
                        fontweight="bold", color="#fff",
                        bbox=dict(boxstyle="square,pad=0.24", fc=c, ec="none"))


    draw_tags(ax, [(RES, pf(RES), "#3BAF90"), (LAST, pf(LAST), "#202945"), (SUP, pf(SUP), "#AC5D85")])

    qt, ql = [], []
    for i, dd in enumerate(dts):
        if i > 0 and dd.month != dts[i - 1].month and dd.month in (1, 4, 7, 10):
            qt.append(i); ql.append(dd.strftime("%b"))
    ax.set_xlim(-4, x[-1] + 22)
    ax.set_xticks(qt); ax.set_xticklabels(ql)
    ax.tick_params(axis="x", labelsize=5.2, pad=1.5)
    for y in sorted({dd.year for dd in dts}):
        ids = [i for i, dd in enumerate(dts) if dd.year == y]
        ax.annotate(str(y), xy=(ids[len(ids) // 2], 0), xycoords=("data", "axes fraction"),
                    xytext=(0, -15), textcoords="offset points", ha="center", fontsize=5.4,
                    color="#7b8598")

    ax.text(0.006, 0.02, "Bars: blue = rising 200-day MA slope, red = falling  ·  "
                         "dotted lines = 100-day high (mint) / low (mulberry)",
            transform=ax.transAxes, fontsize=5.2, color="#8b95a8", va="bottom")

    fig.savefig(OUTPNG, dpi=300, facecolor="white")

    # ---- mechanical signals for the page-2 comment --------------------------
    up_break = max((i for i in xs if hi[i] >= mx[i] - 1e-9), default=None)
    dn_break = max((i for i in xs if lo[i] <= mn[i] + 1e-9), default=None)
    if up_break is None and dn_break is None:
        touch = None
    elif dn_break is None or (up_break is not None and up_break > dn_break):
        touch = "upper"
    else:
        touch = "lower"
    ti = up_break if touch == "upper" else dn_break
    oi = dn_break if touch == "upper" else up_break
    sig = dict(last_bar_up=bool(up[-1]), touch=touch,
               touch_date=dts[ti].strftime("%d %B %Y").lstrip("0") if ti is not None else None,
               touch_level=(mx[ti] if touch == "upper" else mn[ti]) if ti is not None else None,
               other_date=dts[oi].strftime("%d %B %Y").lstrip("0") if oi is not None else None,
               other_level=(mn[oi] if touch == "upper" else mx[oi]) if oi is not None else None,
               last=LAST, max100=RES, min100=SUP)
    json.dump(sig, open(OUTPNG.replace(".png", ".json"), "w"), indent=1)
    print("chart2", OUTPNG, "| signals:", sig, "| red bars:", sum(1 for u in up if not u), "of", len(up))


# =============================================================================
# 6. DOCUMENT (CSS + HTML + PDF)
# =============================================================================
import cairosvg


DISCLAIMER_TITLE = "DISCLAIMER"
# Legal text supplied by Florian, 5 Oct 2026 - verbatim, one string per paragraph.
# It sits at the bottom of its own last page (page 3); page 2 carries no disclaimer.
DISCLAIMER_PARAS = [
    "This communication has been issued and made available to recipients for the purpose of advertising investment "
    "services and/or financial instruments. It has been sent for information purposes and cannot be considered as an "
    "offer or a personalised recommendation to buy or sell a financial instrument or any other investment or currency. "
    "This communication does not constitute investment research within the meaning of regulatory rules applicable in "
    "the European Economic Area, or research under the rules of the U.S. Self-Regulatory Organizations.",
    "This information is made solely for professional and institutional clients as defined by the Swiss Financial "
    "Services Act, as well as qualified investors according to the Swiss Collective Investment Schemes Act. It is not "
    "intended for retail clients or non-qualified investors and consequently cannot be transmitted to any third party.",
    "This communication is not directed to any person in any jurisdiction where, by reason of that person&rsquo;s "
    "nationality, residence or otherwise, its dissemination or use is prohibited. It cannot be quoted, reproduced, "
    "disclosed, distributed or otherwise referred to, in whole or in part, to any third party without the Bank&rsquo;s "
    "prior written consent.",
    "This communication may contain information on past performances of a financial product, all kinds of economic "
    "and financial valuations and analyses, as well as opinions of the Bank or of third parties. Any market "
    "valuations, terms and calculation methods, yields and opinions expressed are subject to change without notice. "
    "The information and opinions contained herein have been compiled and provided in good faith, based on "
    "information obtained from sources believed to be trustworthy. However, such information has not been "
    "independently verified. No guarantee, representation, or warranty of any kind, whether express or implied, is "
    "provided by the Bank or by relevant data vendors and other sources with respect to the accuracy, reliability, "
    "currentness or exhaustiveness of the information communicated, the methodology employed or the prices contained "
    "herein.",
    "Past performance is not a reliable indicator of current or future results. Any reference to the past "
    "performance of an investment does not guarantee its future performance. Fluctuations in exchange rates may "
    "adversely affect the value, price or income of any investment.",
    "Nothing in the present communication constitutes investment, legal, accounting or tax advice. This information "
    "is purely objective since it does not take into consideration the personal situation (including financial "
    "knowledge and experience), the investment objectives and risk profile of any recipient. Moreover, certain "
    "financial instruments mentioned (in particular, but not exclusively, derivatives, options and futures) involve a "
    "high risk of loss and may not be suitable. Accordingly, recipients should consult their own advisors on such "
    "matters, including but not limited to the possible tax consequences of investing in any financial product "
    "mentioned herein, and make their own assessment of the suitability of such investment product.",
    "Should a recipient make an investment on the basis of the present communication, the recipient alone shall bear "
    "the consequences thereof. In no event shall the Bank, its directors, employees, affiliates or agents be held "
    "responsible for damages of any kind arising out of the use of all or part of the information provided herein.",
]
DISCLAIMER_HTML = "".join(f"<p>{t}</p>" for t in DISCLAIMER_PARAS)

VERDICT_COLOR = {"BULLISH": "#3BAF90", "NEUTRAL": "#4B5F80", "BEARISH": "#AC5D85"}
VERDICT_GLYPH = {"BULLISH": "&#9650;", "NEUTRAL": "&#9670;", "BEARISH": "&#9660;"}

# ----------------------------------------------------------------------------
# ASSETS -> data URIs
# ----------------------------------------------------------------------------
def svg_to_png_uri(path, width):
    png = cairosvg.svg2png(url=str(path), output_width=width)
    return "data:image/png;base64," + base64.b64encode(png).decode()

def img_uri(path):
    ext = pathlib.Path(path).suffix.lower()
    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()

MOTIF_URI = None  # set in main()
LOGO = "data:image/svg+xml;base64," + SYZ_LOGO_SVG_B64


# ----------------------------------------------------------------------------
# CSS
# ----------------------------------------------------------------------------
FONTDIR = FONT_DIR
FONTFACE = "".join(
    f"@font-face{{font-family:NunitoL;src:url('file://{FONTDIR}/NunitoSans-{n}.ttf');font-weight:{w};font-style:normal}}"
    for n, w in [("Regular", 400), ("SemiBold", 600), ("Bold", 700), ("ExtraBold", 800)]
)

CSS = FONTFACE + """
:root{--orange:#FF6C0E;--amber:#FFA400;--gold:#FFC545;--space:#202945;--blue:#4B5F80;
      --mint:#3BAF90;--mulb:#AC5D85;--line:#e8ebf1;--vc:__VC__;}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:NunitoL,'Nunito Sans','Segoe UI',Helvetica,Arial,sans-serif;color:var(--space);
     background:#eef1f6;font-size:9.4pt;line-height:1.48;-webkit-font-smoothing:antialiased}

@page{size:A4;margin:12mm 12mm 10mm 12mm}
.page{position:relative;width:186mm;height:273mm;background:#fff;margin:0 auto;overflow:visible}
.page+.page{margin-top:10mm}

/* ---------- HERO ---------- */
.hero{position:relative;height:55mm}
.motif{position:absolute;top:-2mm;left:0;width:186mm;height:auto;z-index:0}
.logo{position:absolute;top:1mm;right:0;width:31mm;z-index:2}
.eyebrow{position:relative;z-index:2;font-weight:800;font-size:7.6pt;letter-spacing:.30em;
         color:var(--space);line-height:1.9;padding-top:2mm}
.titleblock{position:absolute;left:0;bottom:0;z-index:2;width:100%}
.tb{display:inline-block;background-color:var(--gold);background-image:linear-gradient(90deg,var(--orange) 0%,var(--amber) 55%,var(--gold) 100%);background-repeat:no-repeat;background-size:100% 100%;
    color:#fff;font-weight:400;font-size:17pt;letter-spacing:.14em;padding:2mm 5.5mm 2.4mm}
.tagrow{display:flex;align-items:center;justify-content:space-between;margin:3mm 0 1.2mm}
.tagline{font-weight:700;font-size:10.5pt;margin:0;color:var(--space)}
.internal{display:inline-block;line-height:1.1;font-weight:800;font-size:7pt;letter-spacing:.24em;color:var(--orange);border:1.5px solid var(--orange);border-radius:2.2mm;padding:1.2mm 3.2mm 1.1mm;white-space:nowrap}
.strip{font-weight:700;font-size:7.6pt;letter-spacing:.20em;color:#9aa4b5;margin:0 0 1mm}

/* ---------- VERDICT BOX ---------- */
.vbox{background:var(--space);border-radius:5mm;padding:5mm 6.5mm 3.5mm;color:#fff;margin-top:3.5mm}
.vhead{display:flex;align-items:center;gap:5mm;margin-bottom:3.5mm}
.pill{font-weight:800;font-size:8pt;letter-spacing:.06em;color:#fff;background:var(--vc);
      border-radius:9mm;padding:1mm 4mm}
.vmeta{font-size:8pt;color:#c3ccdd}
.pill{margin-left:auto}
.vmeta b{color:#fff;font-weight:700}
.vbox p.vhl{font-weight:800;font-size:12.5pt;line-height:1.25;margin:0;flex:1 1 auto;color:#fff}
.vbox p{margin:0 0 2.3mm;color:#e9edf5;font-size:__BODYPT__pt}
.vbox p b{color:#fff;font-weight:700}
.levels{display:flex;gap:5mm;border-top:1px solid rgba(255,255,255,.14);padding-top:2.4mm;margin-top:.5mm}
.lv{flex:1 1 auto}
.lv.wide{flex:1.5 1 auto}
.lv .v{white-space:nowrap}
.lv .k{font-weight:800;font-size:6.6pt;letter-spacing:.16em;color:var(--gold);display:block;margin-bottom:.4mm}
.lv .v{font-weight:700;font-size:8.4pt;color:#fff}

/* ---------- CHART ---------- */
.chartblock{margin-top:3.5mm}
.vbox.p2{margin-top:0}
.p2strip{margin:0 0 2.5mm}
.pill2{background:var(--vc2)}
.bbox.below{margin-top:11mm}
.chartttl{font-weight:800;font-size:10pt;color:var(--space);margin:0 0 2mm;text-align:left}
.chartttl span{color:var(--orange)}
.chartblock{text-align:center}
.chartwrap{display:block;padding:0;background:#fff;width:191mm}   /* extends 5mm into the right margin */
.chartwrap img{display:block;width:191mm;border-radius:1mm}
.csource{font-size:7.2pt;color:#9aa4b5;text-align:center;margin:1.6mm 0 0;width:186mm}

/* ---------- BUSINESS BOX ---------- */
.bbox{margin-top:0;background:#f4f6fa;border-radius:5mm;padding:4.5mm 6mm}
.bbox .k{font-weight:800;font-size:7.4pt;letter-spacing:.20em;color:var(--orange);display:block;margin-bottom:2mm}
.bbox p{margin:0;font-size:8.8pt;color:#3a445f}
.bbox b{color:var(--space);font-weight:700}

/* ---------- FOOTER ---------- */
.foot{position:absolute;left:0;right:0;bottom:0;display:flex;justify-content:space-between;align-items:flex-end;
      font-size:7.6pt;color:#9aa4b5}

/* ---------- DISCLAIMER (last page, page 3) ---------- */
.disc{position:absolute;left:0;right:0;bottom:9mm}
.disc .k{font-weight:800;font-size:7.6pt;letter-spacing:.20em;color:var(--space);display:block;margin-bottom:2.5mm}
.disc p{margin:0 0 1.6mm;font-size:6.8pt;line-height:1.55;color:#9aa4b5;text-align:justify}
.disc p:last-child{margin-bottom:0}
.dhead{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2mm}
.dhead .k{margin-bottom:0}
.author{font-size:7.6pt;color:var(--blue);margin:0}
/* signature: end of page 2, right-aligned above the footer (Florian, 5 Oct 2026) */
.sig{position:absolute;right:0;bottom:9mm;margin:0;font-size:7.6pt;color:var(--blue);text-align:right}

@media screen{
  body{padding:16mm 0}
  .page{box-shadow:0 6px 26px rgba(32,41,69,.14);padding:12mm;width:210mm;height:297mm}
  .foot{left:12mm;right:12mm;bottom:10mm}
  .disc{left:12mm;right:12mm;bottom:21mm}
  .sig{right:12mm;bottom:21mm}
}
@media print{
  body{background:#fff;padding:0}
  .page{box-shadow:none;margin:0}
  .page+.page{margin-top:0;break-before:page}
}
"""

# ----------------------------------------------------------------------------
# Page-2 mechanical comment (from the chart-2 signal file)
# ----------------------------------------------------------------------------

def page2_comment(d):
    """Returns (verdict_key, html) for the Breakout & Momentum box."""
    jpath = d["chart2_path"].replace(".png", ".json")
    sg = json.load(open(jpath))
    tok = d["last"].split()
    if len(tok) >= 2:                      # "SEK 258.30" -> prefix unit
        ccy = tok[0]
        fmt = lambda v: f"{ccy} {pf(v)}"
    else:                                  # "4.9444%" -> suffix unit
        suf = "".join(ch for ch in d["last"] if not (ch.isdigit() or ch == "."))
        fmt = lambda v: f"{pf(v)}{suf}"
    # the opposite band may never have been broken inside the plotted window
    since = (lambda: f"since {sg['other_date']}" if sg.get("other_date") else "over the period shown")
    if sg["last_bar_up"]:
        p1 = ("<p><b>Long-term momentum is positive.</b> The latest bar is blue, so the long-term momentum regime "
              "remains constructive and supports the trend signal above.</p>")
    else:
        p1 = ("<p><b>Long-term momentum is negative.</b> The latest bar is red, so the long-term momentum regime "
              "is unfavourable and does not support a recovery.</p>")
    if sg["touch"] == "upper":
        p2 = (f"<p><b>The last band broken was the upper band</b> &mdash; a new 100-day high at <b>{fmt(sg['touch_level'])}</b> "
              f"on {sg['touch_date']}. This is a positive trend signal: price is printing a succession of higher highs and "
              f"higher lows; the lower band (<b>{fmt(sg['min100'])}</b>) has not been broken {since()}.</p>")
    else:
        p2 = (f"<p><b>The last band broken was the lower band</b> &mdash; a new 100-day low at <b>{fmt(sg['touch_level'])}</b> "
              f"on {sg['touch_date']}. This is a negative trend signal: price is printing a succession of lower highs and "
              f"lower lows; the upper band (<b>{fmt(sg['max100'])}</b>) has not been broken {since()}.</p>")
    pos = sg["last_bar_up"] + (sg["touch"] == "upper")
    key = "BULLISH" if pos == 2 else "BEARISH" if pos == 0 else "NEUTRAL"
    label = {"BULLISH": "POSITIVE", "BEARISH": "NEGATIVE", "NEUTRAL": "MIXED"}[key]
    return key, label, p2 + p1


# ----------------------------------------------------------------------------
# HTML
# ----------------------------------------------------------------------------
def _endash(x):
    """House rule: en dashes only – never em dashes."""
    if isinstance(x, str):
        return x.replace("&mdash;", "&ndash;").replace("\u2014", "\u2013")
    return x


def build_html(d, MOTIF, CHART, CHART2):
    d = {k: _endash(v) for k, v in d.items()}
    if d.get("dual") and CHART2:
        vc2 = VERDICT_COLOR[d["verdict2"]]
        p2box = (f'<p class="strip p2strip">{d["strip2"]}</p>'
                 f'<div class="vbox p2" style="--vc2:{vc2}"><div class="vhead">'
                 f'<p class="vhl">{d["headline2"]}</p>'
                 f'<span class="pill pill2">{VERDICT_GLYPH[d["verdict2"]]} {d["verdict2"]}</span></div>'
                 f'{d["analysis2"]}'
                 f'<div class="levels">'
                 f'<div class="lv"><span class="k">LAST</span><span class="v">{d["last2"]}</span></div>'
                 f'<div class="lv"><span class="k">SUPPORT</span><span class="v">{d["supports2"]}</span></div>'
                 f'<div class="lv"><span class="k">RESISTANCE</span><span class="v">{d["resistances2"]}</span></div>'
                 f'<div class="lv wide"><span class="k">INVALIDATION</span><span class="v">{d["invalidation2"]}</span></div>'
                 f'</div></div>')
        p2chart = (f'<div class="chartblock"><div class="chartwrap"><img src="{CHART2}" alt="chart">'
                   f'<p class="csource">{d["chart2_source"]}</p></div></div>')
    elif CHART2:
        k2, label2, c2 = page2_comment(d)
        p2box = (f'<div class="vbox p2" style="--vc2:{VERDICT_COLOR[k2]}"><div class="vhead">'
                 f'<p class="vhl">{d["chart2_title"]}</p>'
                 f'<span class="pill pill2">{VERDICT_GLYPH[k2]} {label2}</span></div>{c2}</div>')
        p2chart = (f'<div class="chartblock"><div class="chartwrap"><img src="{CHART2}" alt="chart">'
                   f'<p class="csource">{d["chart2_source"]}</p></div></div>')
    else:
        p2box = p2chart = ""
    # No INTERNAL DOCUMENT badge on Technical Takes / Advisory documents
    # (Florian, 25 Sep 2026). Set internal_badge=True to bring it back.
    internal_html = ('<span class="internal">INTERNAL DOCUMENT</span>'
                     if d.get("internal_badge") is True else "")
    inval_html = ("" if not d.get("invalidation") else
                  f'<div class="lv wide"><span class="k">INVALIDATION</span>'
                  f'<span class="v">{d["invalidation"]}</span></div>')
    target_html = ("" if not d.get("target_str") else
                   f'<div class="lv"><span class="k">IMPLIED TARGET</span>'
                   f'<span class="v">{d["target_str"]}</span></div>')
    bbox_html = ("" if d.get("page2_description") is False else
                 f'<div class="bbox below"><span class="k">{d["business_title"]}</span>'
                 f'<p>{d["business_html"]}</p></div>')
    has_p2 = bool(p2box or p2chart or bbox_html.strip())
    npages = 3 if has_p2 else 2
    page2_html = ("" if not has_p2 else
                  f'<div class="page">\n  {p2box}\n  {p2chart}\n  {bbox_html}\n'
                  f'  <p class="sig">{d["author"]}</p>\n'
                  f'  <div class="foot"><span>{d["footer"]}</span><span>page 2/{npages}</span></div>\n</div>\n')
    vc = VERDICT_COLOR[d["verdict"]]
    css = CSS.replace("__VC__", vc).replace("__BODYPT__", str(d.get("body_pt", 9)))
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Technical Takes &mdash; {d['headline']}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>{css}</style></head>
<body>

<!-- ============================ PAGE 1 ============================ -->
<div class="page">
  <div class="hero">
    <img class="motif" src="{MOTIF}" alt="">
    <img class="logo" src="{LOGO}" alt="Syz">
    <div class="eyebrow">{d['doc_label']}<br>{d['date']}</div>
    <div class="titleblock">
      <span class="tb">TECHNICAL TAKES</span>
      <div class="tagrow"><p class="tagline">Reading markets through trend, momentum and indicators</p>
        {internal_html}</div>
      <p class="strip">{d['strip']}</p>
    </div>
  </div>

  <div class="vbox">
    <div class="vhead">
      <p class="vhl">{d['headline']}</p>
      <span class="pill">{VERDICT_GLYPH[d['verdict']]} {d['verdict']}</span>
    </div>
    {d['analysis_html']}
    <div class="levels">
      <div class="lv"><span class="k">LAST</span><span class="v">{d['last']}</span></div>
      <div class="lv"><span class="k">SUPPORT</span><span class="v">{d['supports']}</span></div>
      <div class="lv"><span class="k">RESISTANCE</span><span class="v">{d['resistances']}</span></div>
      {target_html}
      {inval_html}
    </div>
  </div>

  <div class="chartblock">
    <div class="chartwrap"><img src="{CHART}" alt="chart">
      <p class="csource">{d['chart_source']}</p></div>
  </div>

  <div class="foot"><span>{d['footer']}</span><span>page 1/{npages}</span></div>
</div>

<!-- ============================ PAGE 2 ============================ -->
{page2_html}
<!-- ======================= LAST PAGE: DISCLAIMER ====================== -->
<div class="page">
  <div class="disc">
    <div class="dhead"><span class="k">{DISCLAIMER_TITLE}</span></div>
    {DISCLAIMER_HTML}
  </div>
  <div class="foot"><span>{d['footer']}</span><span>page {npages}/{npages}</span></div>
</div>

</body></html>"""


def block_bottom_mm(html, page, cls):
    """Bottom edge (mm from page top) of the first block with this class."""
    from weasyprint import HTML
    MM = 96 / 25.4
    doc = HTML(string=html, base_url=".").render()
    worst = 0.0
    def walk(b, inside=False):
        nonlocal worst
        el = getattr(b, "element", None)
        c = el.get("class") if el is not None and hasattr(el, "get") else None
        here = inside or (c or "") == cls
        if here:
            try:
                worst = max(worst, (b.position_y + b.height) / MM)
            except Exception:
                pass
        for ch in getattr(b, "children", []):
            walk(ch, here)
    walk(doc.pages[page]._page_box)
    return worst


def content_bottom_mm(html):
    """Bottom edge (mm from page top) of the chart frame on page 1."""
    from weasyprint import HTML
    MM = 96 / 25.4
    doc = HTML(string=html, base_url=".").render()
    worst = 0.0
    def walk(b, inside=False):
        nonlocal worst
        el = getattr(b, "element", None)
        cls = el.get("class") if el is not None and hasattr(el, "get") else None
        here = inside or (cls or "").startswith("chartwrap")
        if here:
            try:
                worst = max(worst, (b.position_y + b.height) / MM)
            except Exception:
                pass
        for c in getattr(b, "children", []):
            walk(c, here)
    walk(doc.pages[0]._page_box)
    return worst





def paragraph_lines(html, page=0, cls="vbox"):
    """Line count of each body paragraph inside the first block with this class."""
    from weasyprint import HTML
    from weasyprint.formatting_structure.boxes import LineBox
    doc = HTML(string=html, base_url=".").render()
    out = []
    def walk(b, inside=False):
        el = getattr(b, "element", None)
        c = (el.get("class") or "") if el is not None and hasattr(el, "get") else ""
        tag = getattr(el, "tag", "") if el is not None else ""
        here = inside or c == cls
        if here and tag == "p" and c != "vhl" and getattr(b, "element_tag", "p") == "p":
            n = sum(1 for ch in getattr(b, "children", []) if isinstance(ch, LineBox))
            if n:
                out.append(n)
                return
        for ch in getattr(b, "children", []):
            walk(ch, here)
    walk(doc.pages[page]._page_box)
    return out


# =============================================================================
# 7. MAIN
# =============================================================================
def main(cfg=CONFIG):
    global DECIMALS, YPAD
    if WORKDIR is None or OUT is None:          # not configured yet -> env/defaults
        configure(cfg.get("outdir"))
    DECIMALS = cfg.get("decimals", 2)
    YPAD = tuple(cfg.get("ypad", (0.90, 1.12)))
    import cairosvg
    from weasyprint import HTML
    ensure_fonts()

    motif_svg = build_motif()
    (WORKDIR / "motif_hq.svg").write_text(motif_svg, encoding="utf-8")
    motif_png = cairosvg.svg2png(bytestring=motif_svg.encode(), output_width=4800)
    MOTIF = "data:image/png;base64," + base64.b64encode(motif_png).decode()

    p1 = str(WORKDIR / "chart1.png")
    build_chart1(cfg["xlsx"], p1, NO_RS=not cfg["relative_strength"], OVERLAYS=cfg.get("overlays"),
                 HEIGHT_MM=cfg.get("chart1_height_mm", 128), HIDE_TAGS=tuple(cfg.get("hide_tags", ())), YEARS=cfg.get("years", 4),
                 RES_LEVEL=cfg.get("res_level"), SUP_LEVEL=cfg.get("sup_level"),
                 HIDE_LINES=tuple(cfg.get("hide_lines", ())))
    CHART = img_uri(p1)

    if cfg.get("dual"):
        p2 = str(WORKDIR / "chart2.png")
        build_chart1(cfg["xlsx2"], p2, NO_RS=not cfg.get("relative_strength2", False),
                     OVERLAYS=cfg.get("overlays2"), HEIGHT_MM=cfg.get("chart2_height_mm", 128))
        cfg = dict(cfg, chart2_path=p2)
        CHART2 = img_uri(p2)
    elif cfg.get("page2", True):
        p2 = str(WORKDIR / "chart2.png")
        build_chart2(cfg["xlsx"], p2, YEARS=cfg.get("years", 4),
                     RED_BARS=tuple(cfg.get("chart2_red_bars", ())))
        cfg = dict(cfg, chart2_path=p2)
        CHART2 = img_uri(p2)
    else:
        CHART2 = None

    tg = cfg.get("target")
    if isinstance(tg, dict):                         # breakout -> Bollinger(100,2) width target
        bt = bb_target(cfg["xlsx"], tg["breakout"], tg.get("direction", "up"))
        tstr = pf(round(bt["target"], DECIMALS))
        print(f"target: first close {'above' if tg.get('direction','up')=='up' else 'below'} "
              f"{pf(bt['level'])} on {bt['bar']:%d %b %Y}; UBB {bt['ubb']:.2f} LBB {bt['lbb']:.2f} "
              f"mid {bt['mid']:.2f}; bandwidth {bt['bandwidth']*100:.2f}% -> target {tstr}")
        cfg = dict(cfg, target_str=tstr,
                   analysis_html=cfg["analysis_html"].replace("__TARGET__", tstr)
                   .replace("__BW__", f"{bt['bandwidth']*100:.1f}%")
                   .replace("__BAR__", f"{bt['bar'].day} {bt['bar']:%B}"))
    elif isinstance(tg, str) and tg:
        cfg = dict(cfg, target_str=tg)

    html = _endash(build_html(cfg, MOTIF, CHART, CHART2))
    lines = paragraph_lines(html)
    print(f"verdict-box paragraph lines: {lines}")
    if any(n > cfg.get("max_para_lines", 4) for n in lines):
        print(f"WARNING: a verdict-box paragraph exceeds {cfg.get('max_para_lines', 4)} lines {lines} — "
              f"shorten the text (house rule: max 4 lines per paragraph).")
    bottom = content_bottom_mm(html)
    limit = 12 + 273 - 6
    if bottom > limit:
        print(f"WARNING: page-1 content overflows ({bottom:.1f}mm vs {limit}mm) — shorten the commentary, "
              f"never the chart.")
    if cfg.get("page2", True):
        p2b = block_bottom_mm(html, 1, "bbox below" if cfg.get("page2_description") is not False else "chartblock")
        if p2b > 263:      # page 2 no longer carries the disclaimer (moved to page 3)
            print(f"WARNING: page-2 content overflows into the footer "
                  f"({p2b:.1f}mm vs 263mm) — shorten the page-2 text or the chart.")
        else:
            print(f"page-2 description bottom: {p2b:.1f}mm")
    pdf = OUT / f"{cfg['slug']}.pdf"
    HTML(string=html, base_url=str(ROOT)).write_pdf(str(pdf))
    print(f"page-1 content bottom: {bottom:.1f}mm")
    print("written:", pdf)
    return pdf


if __name__ == "__main__":
    main()
