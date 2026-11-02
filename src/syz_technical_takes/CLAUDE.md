# technical_takes — a ticker → the three-page Technical Takes PDF (dev map)

The deterministic half of the **technical-takes** skill. Same shape as every
sibling: **deterministic Python does every number and draws every pixel; the model
(or an analyst subagent) authors only the typed verdict spec.** No price is
hand-written; no indicator is estimated.

The asymmetry that defines the package:

    Every NUMBER printed comes from the synthesized workbook (OHLC feed → indicators).
    Every WORD of the verdict is the model's, bound by §7 and gated by the render checks.

```
ticker ─data.fetch_ohlc──▶ OHLC bars ─indicators.synthesize_workbook─▶ Sheet1.xlsx
 (or an attached              (Yahoo v8,            (MA50/200, Bollinger(100,2),
  Bloomberg .xlsx,             dev licence)          Max/Min(100), %DS/%DSS, benchmark)
  used as-is)                                                 │
                                                     analytics.analyze ─▶ §7 inputs JSON
                                                                │   (slopes, 50/200 cross,
                                                                │    band-break signal,
                                                                │    breakout levels, RS slope,
                                                                │    verdict_hint, page2_badge)
                                   model authors the spec ◀─────┘
                                   (headline, verdict, 2×<p>, levels)
                                                │
                                   render.main(spec) ─▶ Technical_Takes_<TICKER>_<date>.pdf
                                                        (+ paragraph-line / page-bound checks)
```

## Files

- **`data.py`** — the ONLY networked module. Keyless Yahoo v8 chart endpoint with
  host/attempt retry, nulls/holidays dropped, bars ascending. Swap this (and the
  symbol maps in `benchmarks.py`) for a licensed feed; nothing else touches a
  provider. Dev-licence provenance, same caveat as the newsletter's yfinance use.
- **`benchmarks.py`** — Bloomberg ticker → Yahoo symbol (`NOVN SW`→`NOVN.SW`),
  benchmark NAME → index symbol, country → default benchmark (INPUTS §D convention:
  SXXP Europe, SPI/SMI Swiss, TPX Japan, SPX US, MXWO world). SPI isn't on the feed →
  SMI proxy, flagged in `provenance.notes`.
- **`indicators.py`** — rebuilds the Bloomberg workbook from bare OHLC. Every
  definition matches BUILD_SPEC §Data rules. **The crown jewel is `stochastic()`:**
  the Bloomberg `%DS(25)`/`%DSS(15)` decoded as `SMA(SMA(rawK(99),25),25)` and
  `SMA(%DS,15)` — fitted to a real SPIEX export (reproduces it to ~1e-4). The 99/25/25
  constants and the 146-bar warm-up are measured, not guessed; do not "simplify" them.
- **`analytics.py`** — reads the workbook, returns the §7 verdict inputs. The
  `band_signal` reproduces `render.build_chart2`'s band-break logic exactly, so the
  analytics and the page-2 chart never disagree. `verdict_hint` is the §7 grid run
  mechanically — advisory; oscillators never override the trend.
- **`render.py`** — the vendored Syz renderer (Florian's `technical_takes.py`,
  v1.7), verbatim except: the path globals are resolved by `configure(outdir,
  workdir, fontdir)` instead of at import (no import-time filesystem side effects),
  and `main()` calls `configure()` itself if nothing did. `main(cfg)` takes the spec
  dict, draws both charts, computes the Bollinger-width target, writes the PDF, and
  prints the checks `cli.build` folds into its JSON. **Do not edit the layout here** —
  it reproduces the shipped SPIEX document pixel-for-pixel; BUILD_SPEC.md is its spec.
- **`cli.py`** — `syz-tt`: `stage-inputs` (shared intake, for an attached export),
  `fetch`, `analyze`, `build`, `schema`. Each prints one JSON object.

## Where the rest of the skill lives

- The user command + step-by-step: `skill/SKILL.md`.
- The normative spec + per-document inputs: `spec/{BUILD_SPEC,INPUTS}.md`
  (BUILD_SPEC is at **v1.8**: §7's relative-strength sentence opens with a bold
  `<b>Relative momentum</b>` lead-in — Florian, 1 Nov 2026).

(This is the standalone repo. In the SYZ monorepo the same package sits under
`src/`, the skill under `.claude/skills/technical-takes/`, and the spec under
`assets/technical_takes/`.)

## House rules worth re-reading before editing

- The verdict order is **200-day slope → trendline → 100-day high/low structure**;
  oscillators qualify risk only. The grid is in BUILD_SPEC §7.
- Invalidation always references the band line or the 200-day MA.
- Provenance is stated, never faked: the template's "Source: Syz Research / Bloomberg"
  stays, and the delivery note tells the user the data is from the dev feed.

## Natural next step (not built yet)

The verdict authoring is the main model's job today (SKILL.md drives it). The
on-convention upgrade is a fresh-context **verdict-author subagent** that reads the
`analyze` JSON + the rendered chart and emits the spec JSON, plus a golden test that
asserts the SPIEX workbook still renders byte-stable. `analyze` already emits a clean
typed payload for exactly that agent.
