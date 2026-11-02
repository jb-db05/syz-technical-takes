# What I need from you for each Technical Takes

## A. Required every time

| # | Input | Example | Notes |
|---|---|---|---|
| 1 | **Bloomberg Excel export** | `SPIEX.xlsx`, `8316_JT_Sumitomo_Mitsui_Financial.xlsx` | The only data source. Column list in §D. ~2 years of history needed for the 2-year chart plus 200 bars of MA warm-up (exports from late 2020 work). |
| 2 | **Instrument identity** | `SPI Extra · SPIEX · CHF · Small & Mid Caps · Switzerland` – usually just the ticker in the file name; I derive the rest | Goes into the grey strip under the subtitle. For a future: name, contract code, quotation unit, asset class. For FX or a yield: the pair or tenor, code, unit. |
| 3 | **Document date** | `28 September 2026` | Appears in the eyebrow and both footers. Defaults to the last date in the workbook if you say nothing. If the last row is today during market hours it is a live print: I keep it and flag it. |
| 4 | **Description text** | 3–4 lines | The page-2 grey box. Tell me which label: `THE BUSINESS` (single stock), `THE INDEX`, `THE SECTOR`, `THE INSTRUMENT` (yields), `THE CONTRACT` (futures), `THE PAIR` (FX). I draft it, you approve. |

## B. Optional — only if you want to override my reading

Left unspecified, I derive these from the chart and the data, and you review them:

| # | Input | Notes |
|---|---|---|
| 5 | Verdict | `BULLISH` / `NEUTRAL` / `BEARISH` |
| 6 | Headline | must fit one line at 12.5 pt — roughly 55 characters |
| 7 | The two commentary paragraphs | I draft them in house style; if you supply text verbatim I keep your wording and take the space from `body_pt`, then the chart |
| 8 | Support / resistance / invalidation | defaults: `Minimum(100)` and `Maximum(100)` from the workbook, plus the moving averages; invalidation follows the band-line / 200-day rule |
| 8b | Breakout target | automatic whenever the comment reports a breakout: Bollinger(100,2) width on the first close beyond the level, projected from that level; shown in the text and in an IMPLIED TARGET column |
| 9 | **Lines to draw** | levels and trendlines you want on the chart — give me the level and the date it starts from, or the two dates a trendline runs through (see §C) |

## C. Flags and per-document settings

| Setting | When | Effect |
|---|---|---|
| `relative_strength = False` | commodities, FX, rates, or any workbook without a benchmark column | drops the third panel on chart 1; the price panel expands |
| `decimals` | `2` for FX and yields, `1` for equities, commodities, crypto | applies to the chart labels **and** the written commentary |
| `years` | house standard 2 (code default 4) | shortens or lengthens the plotted window: `2` when a large price range crushes the recent action (Palantir 6 → 207), `7` when a trendline anchor sits further back (uranium off the 2020 low) |
| `overlays` | named levels and trendlines | `hlines` = dashed blue levels (anchor each with `hline_from`); `hlines_dotted` = fine dots for long-term or never-traded resistance (the 2007 highs); `trendlines` = pairs of dates fitted through the lows, or the highs with `"highs": True`; add `"highs"` / `"lows"` as a third element to set it per line (one chart can carry both) |
| `hide_tags` | when two right-edge labels collide | `"res" \| "sup" \| "ma200" \| "last"` |
| `invalidation = ""` | the US yield versions | drops the column; the others share the width |
| `target` | breakouts only | `{"breakout": 7273.4, "direction": "up"}` computes the target and adds the IMPLIED TARGET column; `__TARGET__` in the text is replaced by the value |
| `ypad` | FX and yields | `(0.985, 1.02)` tightens the price-panel padding; the equity default `(0.90, 1.12)` squashes a narrow range into a band |
| `res_level` / `sup_level` | named pivot instead of the 100-day high/low | `(1238.0, "2026-08-06")` redraws the mint resistance (or mulberry support) segment from that date at that level, tagged with its decimals – e.g. the latest lower high in a downtrend |
| `hide_lines` | when a drawn key level sits next to the 100-day high/low | `("sup",)` and/or `("res",)` removes that band segment **and** its tag from chart 1 |
| `chart2_red_bars` | editorial highlight on page 2 | dates drawn red on chart 2 (e.g. `("2026-10-15",)`, the bar that broke key support); display only – the slope rule and the mechanical signals are unchanged |
| `max_para_lines` | default 4 | verdict-box paragraphs are capped at 4 rendered lines each; the build warns above |
| `page2 = False` | one-page version | page 1 only |
| `dual = True` | two instruments in one document | page 2 becomes a second full analysis instead of the signal chart |
| `internal_badge` | off by default | Technical Takes / Advisory documents carry **no** INTERNAL DOCUMENT badge |

## D. The Excel export

**One worksheet is enough.** Sheet 1 must contain these columns — order does not
matter, they are matched by header name:

```
Date | Open | High | Low | Close
Moving Average(Simple,200,0)
UBB(2) | LBB(2)
Moving Average(Simple,50,0)
Maximum(100) | Minimum(100)          <- optional, rolled from highs/lows if absent
%DS(25) | %DSS(15)
<BENCHMARK> Index - Last Price       <- omit for commodities, FX and rates
```

Benchmark convention: **SXXP** for European names, **SPI** for Swiss (**SMIC** for the SPI Extra), **TPX** for Japan, **SPX** for US,
**MXWO** when you want the world index. The name printed on the relative-strength panel
is read from that header, so the workbook decides it — if you want a benchmark other
than the one in the file, re-export with that column.

**One request:** export with **2 decimals**. Some files come through rounded to whole
units, which makes the moving averages and Bollinger bands step visibly; the script then
has to rebuild them from the closes. Decimals in the export avoid that entirely.

## E. What you get back

1. The three-page PDF (analysis · signals + description + signature · disclaimer), named `Technical_Takes_<TICKER>_<YYYY-MM-DD>.pdf`.
2. A short delivery note: verdict and why, the levels drawn, the implied target working
   if any, anything to decide (e.g. page-2 mechanical badge vs page-1 verdict), and a
   live-print warning when relevant.
3. On request, the full CMT analysis in the chat — verdict with conviction and horizon, setup, key
   levels, risk/reward, invalidation, what would change the view, then the evidence by
   pillar (trend, relative strength, momentum, risks).

## F. A worked request

> Technical Takes on Palantir. File attached. PLTR US, USD, software, United States.
> Date 28 September 2026. Equity, so `THE BUSINESS`, benchmark SPX.
> Draw the November 2025 record at 207.5. Draft the verdict and commentary yourself.

That is enough to produce the document and the analysis in one pass.

## G. Minimum message that works

Attach the export and send nothing else (or "make the doc"). I read the ticker from the
file name, take the last date as the document date, draft verdict, headline, commentary,
levels, lines and description, deliver, and you correct. Corrections you ask me to
"learn" become house rules (BUILD_SPEC §7).
