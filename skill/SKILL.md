---
name: technical-takes
description: >
  Build a Syz "Technical Takes" — the three-page A4 technical-analysis PDF (verdict
  box with implied-target levels, price/stochastic/relative-strength chart, a page-2
  breakout & momentum signal page, page-3 disclaimer) — for ONE instrument, from
  just its ticker. No Bloomberg export needed: the run pulls daily OHLC itself,
  synthesizes every indicator column the renderer expects (including the decoded
  Bloomberg %DS/%DSS stochastic), computes the §7 verdict inputs, and draws the
  document deterministically; you author only the verdict, headline, commentary and
  the drawn levels. Use whenever the user asks for a "Technical Takes", a technical
  analysis / chart read / trend verdict on a single name, index, commodity, FX pair
  or yield — "Technical Takes on Microsoft", "do ASML", "XAU", or drops a Bloomberg
  export and asks for the doc. For a whole chart image re-brand use chart-to-svg; for
  a client portfolio deck use portfolio-analysis.
---

# technical-takes — a ticker → the three-page Technical Takes PDF

Deterministic Python does the data, the indicators, the analytics and every pixel;
**you author only the verdict spec** (headline, verdict, two commentary paragraphs,
drawn levels). This is the one judgement step, like `visual`. You never write the
PDF, never compute an indicator, never type a level that isn't in the data.

The whole spec is `assets/technical_takes/BUILD_SPEC.md` (normative) and
`assets/technical_takes/INPUTS.md` (what each document needs). Read §7 of BUILD_SPEC
before writing any commentary — the verdict grid and the editorial rules live there.

**Three invariants:**
- **Every number you print is in the data.** `analyze` hands you every level; a
  price in the prose must be one of them (last, MA50/200, the 100-day high/low, a
  named swing pivot, the implied target). Don't invent or round away from them.
- **The verdict follows §7, in order: 200-day slope → trendline → structure of the
  100-day highs/lows.** Oscillators qualify risk within the trend, they never set it.
  The page-2 badge is mechanical and *may* disagree with your page-1 verdict by
  design — but if `analyze`'s `verdict_hint` and `page2_badge` disagree with the
  verdict you're reaching, re-read the band signal before overriding them.
- **Provenance is stated, never faked.** The data source is a keyless feed (dev
  licence), but the template's source line says "Bloomberg". Keep the template line
  so the document looks right, and **tell the user in the delivery note** that the
  data is from the free feed and a licensed source is needed for client use.

## Input

- **Primary: a ticker typed in chat** — "Microsoft", "MSFT US", "ASML", "NOVN SW",
  "XAU / gold", "EURUSD". This is the normal mode; no attachment needed.
- **Or an attached Bloomberg `.xlsx` export** — then run step 0 and pass `--xlsx`.
- **Optional metadata** (you draft what's missing, the user corrects): display name,
  currency, sector, country, benchmark, the `decimals` (1 equities/indices/
  commodities/crypto, 2 FX/yields), and the eyebrow label.

Run to the end without stopping to ask; surface only genuine blockers (a ticker that
won't resolve, a feed failure). The user corrects the draft after.

## Output (I/O convention)

`fetch` mints the run dir `.output/technical_takes_<dd-mm-yy-HH-MM>_<TAG>/` and prints
`run_dir`. Reuse it verbatim for the whole run. The PDF lands at the top (the
deliverable); the workbook, spec and renders go under `.audit/`. `.input/` and
`.output/` are gitignored — client-adjacent data stays local, never committed.

## Steps

All commands: `syz-tt <cmd>` (prints one JSON object). Run them with the project venv.

**0. Stage inputs — only if a Bloomberg `.xlsx` was attached.**
`syz-tt stage-inputs`. Zero files is the normal case (the input is a ticker); skip to 1.

**1. Fetch the data and build the workbook.**
- Equity/index with a benchmark: `syz-tt fetch --ticker "NOVN SW" --country Switzerland`
  (benchmark auto-defaults by country — US→SPX, Swiss→SMI, European→SXXP, Japan→TPX;
  override with `--benchmark SXXP`, or `--yahoo`/`--benchmark-yahoo` for odd symbols).
- **Commodity / FX / yield: `--no-benchmark`** (e.g. `syz-tt fetch --ticker "GC=F"
  --tag XAU --no-benchmark`) — this drops the relative-strength panel.
- Keep `--years 5` (needs ≥3 for a clean MA200 warm-up; house plot window is 2).
- Capture `run_dir`, `workbook`, `currency`, `benchmark`, and `provenance.notes`
  (e.g. "SPI not on the feed; used SMI"). A supplied export: add `--xlsx <path>`.

**2. Read the analytics.** `syz-tt analyze --workbook <workbook>`. This is your
evidence: `ma200_slope_5_20_40`, `cross_50_200`, `band_signal` (last band broken +
dates — the 100-day structure), `high_100d`/`low_100d`, `stochastic`, `bollinger`,
`relative_strength.rs200_slope_*`, `swing_*`, `page2_badge`, `verdict_hint`.

**3. Form the verdict (§7 grid) and pick the drawn levels.** Classify with the grid
in BUILD_SPEC §7 (rising 200-day + price above + last band broken = upper → BULLISH,
a pullback *to* the 200-day is "a correction within an uptrend"; falling + lower low
→ BEARISH; range around the 200-day with last band broken = lower → NEUTRAL, write
both triggers). Resistance = latest lower high / 100-day high; support = latest
higher low / 100-day low or the 200-day. **Invalidation must reference the band line
or the 200-day MA**, never an arbitrary pivot. On a breakout/breakdown through a
named level, add the implied target (step 4).

**4. Author the spec JSON** (`syz-tt schema` prints the template + required keys).
Write it to `<run_dir>/.audit/spec.json`. Editorial rules (BUILD_SPEC §7):
- Two paragraphs, **each ≤ 4 rendered lines**; every price **`<b>bold</b>`**.
- P1: bold verdict sentence → 200-day slope + price vs MAs → one structural sentence
  naming the level that confirms the move → (breakout) the bold implied-target
  sentence / (neutral) both triggers. Name a golden/death cross only if it's recent
  (last few weeks) and the slope condition holds.
- P2: bold momentum sentence → stochastic value and what it permits → the
  relative-strength sentence → closing bias tied to a level.
- **HOUSE RULE (v1.8, 1 Nov 2026): the relative-strength sentence opens with a bold
  lead-in** — `<b>Relative momentum</b> against the <bench> remains positive, with a
  rising 200-day average.` Keep it to that one sentence; never print the ratio.
  Omit it entirely for commodities/FX/rates (no RS panel) — `relative_strength:false`.
- `decimals`, `last` (currency-prefixed for stocks/commodities/FX: `USD 521.9`; bare
  for indices), `strip`, `business_title` (THE BUSINESS / THE INDEX / THE SECTOR /
  THE COMMODITY / THE PAIR / THE INSTRUMENT), `business_html` (≤4 lines), `slug`
  `Technical_Takes_<TICKER>_<YYYY-MM-DD>`, the date = the last workbook date.
- Breakout only: `target:{"breakout":<level>,"direction":"up"|"down"}` and put
  `__TARGET__` in the prose; on a new-high/new-low that is today's bar, hide that band
  segment (`hide_lines:["res"]` for a record high, `["sup"]` for a new low) and draw
  the broken level as a blue overlay (`overlays.hlines`).

**5. Build and check.** `syz-tt build --spec <run_dir>/.audit/spec.json --workbook
<workbook>`. Read `checks`: `paragraph_lines` each ≤ 4, `page1_bottom_mm` ≤ 279,
`page2_bottom_mm` ≤ 263, `target_working` (verify the number), empty `warnings`.
On overflow, **shorten the text, never the chart** (keep `body_pt` 8.6); re-build.

**6. Look at it.** Render and read the pages:
`pdftoppm -r 110 -png <pdf> <run_dir>/.audit/pg`. Check the headline fits one line,
the verdict badge matches the prose, page-1 and page-2 badges are consistent (or a
deliberate §7 divergence), the drawn levels sit right, and **"Relative momentum" is
bold**. Fix the spec and rebuild if not.

**7. Deliver.** Send the PDF as a file card (its own markdown link / SendUserFile).
Then a short delivery note: the verdict and why (the §7 chain), the drawn levels, the
implied-target working if any, any page-2-badge-vs-page-1 divergence, and the
**provenance caveat** (data from the free feed, not Bloomberg; any benchmark
substitution from `provenance.notes`; a commodity uses the front-month future as the
spot proxy). Session is ephemeral — tell them to download to keep it.

## Build environment

The renderer needs `weasyprint cairosvg matplotlib fonttools` (declared in
`pyproject.toml`). In a fresh cloud session they may be missing from the venv —
`uv pip install --python .venv/bin/python weasyprint cairosvg matplotlib fonttools`.
Fonts (Nunito Sans) are fetched once and cached in `TT_FONTDIR`. `pdftoppm` renders
the pages for the look-at step.
