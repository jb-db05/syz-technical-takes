# syz-technical-takes

Generate the Syz Research **Technical Takes** document — a three-page A4 PDF
(verdict box with implied-target levels, a price / stochastic / relative-strength
chart, a page-2 breakout & momentum signal page, and a page-3 disclaimer) — for
**one instrument, from just its ticker**. No Bloomberg export required.

The run pulls daily OHLC itself, rebuilds every indicator column the renderer
expects — including the **decoded Bloomberg `%DS(25)/%DSS(15)` stochastic** — computes
the verdict inputs deterministically, and draws the document. A human (or an LLM
following the skill) authors only the verdict, headline, commentary and the drawn
levels; every printed level comes from the data.

## How it works

```
ticker ──fetch──▶ OHLC + synthesized workbook ──analyze──▶ verdict inputs (JSON)
                          │                                        │
                          │              author the spec ◀─────────┘
                          │              (headline, verdict, 2 paragraphs, levels)
                          └──────────────────build──────────────▶ Technical_Takes_<TICKER>_<date>.pdf
```

Deterministic Python does the data, the indicators, the analytics and every pixel.
The one judgement step — the verdict and its prose — is authored against the rules
in [`spec/BUILD_SPEC.md`](spec/BUILD_SPEC.md) §7 and gated by the render's
paragraph-line / page-bound checks.

## Install

```bash
# with uv (recommended)
uv venv && uv pip install -e .
# or plain pip
python -m venv .venv && . .venv/bin/activate && pip install -e .
```

System libraries for WeasyPrint (Pango/Cairo/HarfBuzz) and `pdftoppm` (poppler,
to look at the pages) must be present on the host. Nunito Sans is fetched once and
cached in `TT_FONTDIR` (default `~/fonts`).

## Usage

The CLI is `syz-tt`; every command prints one JSON object.

```bash
# 1. Equity / index with a benchmark (auto-defaults by country):
syz-tt fetch --ticker "NOVN SW" --country Switzerland        # → run_dir + workbook
#    US→SPX, Swiss→SMI, European→SXXP, Japan→TPX, world→MXWO; override with --benchmark.

#    Commodity / FX / yield — drop the relative-strength panel:
syz-tt fetch --ticker "GC=F" --tag XAU --no-benchmark

# 2. Read the verdict-driving analytics:
syz-tt analyze --workbook <run_dir>/.audit/<TAG>.xlsx

# 3. Author the spec (see `syz-tt schema` for the template) and build:
syz-tt build --spec spec.json --workbook <run_dir>/.audit/<TAG>.xlsx
#    → the PDF at the top of run_dir, plus the render checks (paragraph lines ≤ 4,
#      page-1 ≤ 279 mm, page-2 ≤ 263 mm, the implied-target working, warnings).

syz-tt schema      # the spec template + which keys are required
```

A real Bloomberg export can be used instead of the feed: `syz-tt fetch --xlsx
export.xlsx` copies it in unchanged.

## The decoded stochastic

The renderer uses the Bloomberg indicators as exported; the only one it cannot
recompute is the `%DS(25)/%DSS(15)` stochastic. It was reverse-engineered from a real
export (it reproduces both columns to ~1e-4):

```
rawK(99) = 100 · (Close − min(Low, 99)) / (max(High, 99) − min(Low, 99))
%DS(25)  = SMA( SMA(rawK(99), 25), 25 )
%DSS(15) = SMA( %DS(25), 15 )
```

The 99 / 25 / 25 constants and the 146-bar warm-up are fitted, not guessed — see
`src/syz_technical_takes/indicators.py`.

## Data provenance

The bundled feed (`data.py`) is a **keyless, dev-licence** source, not Bloomberg. The
template's source line still reads "Source: Syz Research / Bloomberg", so when you
publish a document, **state in the delivery note that the data came from the free
feed** — a licensed feed is needed for client use. Swapping `data.py` (and the symbol
maps in `benchmarks.py`) is the only change required; nothing else touches a provider.
Commodities use the front-month future as the spot proxy, and SPI (not on the free
feed) falls back to SMI — both are reported in `fetch`'s `provenance`.

## Layout

```
src/syz_technical_takes/
  data.py         the OHLC feed (the only networked module)
  benchmarks.py   ticker→symbol + benchmark conventions (SXXP/SPI→SMI/TPX/SPX/MXWO)
  indicators.py   synthesize the Bloomberg workbook (+ the decoded %DS/%DSS stochastic)
  analytics.py    the §7 verdict inputs (slopes, 50/200 cross, band-break signal, …)
  render.py       the Syz renderer: spec → the 3-page PDF
  cli.py          syz-tt: fetch · analyze · build · schema
  CLAUDE.md       dev map
spec/BUILD_SPEC.md  the normative document specification (v1.8)
spec/INPUTS.md      what each document needs
skill/SKILL.md      the step-by-step workflow for an LLM operator
```
