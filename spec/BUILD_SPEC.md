# TECHNICAL TAKES — Build specification (v1.8, 1 November 2026)

<!-- v1.8 (1 Nov 2026): §7 relative-strength sentence now opens with a bold lead-in
     (`<b>Relative momentum</b> …`). Applies to all future reports with an RS panel. -->


Syz Research, single-instrument technical analysis document.
Deliverable: **one three-page A4 PDF** (page 1 analysis, page 2 signals + description + signature, page 3 disclaimer). No HTML, no other format.

Everything below is normative. `technical_takes.py` implements it exactly; this
document exists so the layout can be rebuilt from scratch if the script is lost.

---

## 1. Document geometry

| Item | Value |
|---|---|
| Page size | A4 portrait (210 × 297 mm) |
| Margins | 12 mm top, 12 mm left/right, 10 mm bottom |
| Page box | 186 × 273 mm, fixed height, `overflow: visible` |
| Pages | Exactly 3 (2 with `page2: False`) |
| Page-1 limit | Bottom of the chart block ≤ **279 mm** from the page top (12 mm margin + 273 mm page − 6 mm footer band). The build prints the measured value and warns above it. |
| Page-2 limit | Bottom of the description box ≤ **263 mm** (the signature sits below it). Also measured and warned. |
| Overflow rule | Shorten the **text**, never the chart — unless the text was supplied verbatim by Florian, in which case keep his wording and recover space with `body_pt` then `chart1_height_mm`, in that order. |
| Font | **Nunito Sans** (Google) — *not* the rounded Nunito. Variable font instanced to static weights 400 / 600 / 700 / 800 at `wdth 100, opsz 12, YTLC 500`, named "Nunito Sans", embedded via `@font-face` from local `.ttf` files. The same family is set in matplotlib `rcParams` and in the motif SVG's `font-family`. |
| Dashes | **En dashes only (U+2013).** Em dashes are never used. The builder normalises `&mdash;` and U+2014 in the CONFIG text *and* in the finished HTML, so the mechanically generated page-2 comment is covered too. |

## 2. Colour palette (Syz corporate)

| Name | Hex | Used for |
|---|---|---|
| Tiger Orange | `#FF6C0E` | title-block gradient start, box eyebrow labels, INTERNAL badge (off by default) |
| Mango Amber | `#FFA400` | title-block gradient middle |
| Gold Yellow | `#FFC545` | title-block gradient end, level labels inside the navy box |
| Space Blue | `#202945` | navy boxes, body text, last-price tag |
| Blueberry Blue | `#4B5F80` | NEUTRAL verdict, author byline |
| Mint Green | `#3BAF90` | BULLISH verdict, **resistance** band line + tag |
| Mulberry Pink | `#AC5D85` | BEARISH verdict, **support** band line + tag |
| Chart navy | `#141a2e` | page-1 OHLC bars (darker than Space Blue, never black) |
| Chart blue / red | `#1f4fd8` / `#d81f2a` | 50-day MA / 200-day MA; page-2 bar colours |
| Overlay blue | `#4b9fe8` | manual overlay lines and their tags |
| Band grey | `#aeb8c7` | Bollinger dotted lines |
| Light grey box | `#f4f6fa` | business / instrument description box |
| Hairlines | `#e8ebf1`, `#b9c2d0` | dividers, chart frames |

---

## 3. PAGE 1

### 3.1 Hero (height 55 mm)

* **Motif** — candlestick tape drawn from scratch as SVG, `viewBox 1440 × 300`,
  placed `top: −2 mm`, width 186 mm, behind everything. Deterministic: `random.seed(11)`.
  * 62 OHLC candles, `X0 = 34`, `DX = 22.4`, body width 11.6.
  * Hollow up-candles `#fff`, filled down-candles `#aab7cd`, edges `#8e9db6`, wicks `#9aa8bf`.
  * Elliott 5-wave smoothstep path, pivot y-values `262 → 172 → 208 → 92 → 130 → 36`,
    Gaussian noise σ 9.5 plus a sine ripple.
  * 6-period rolling-mean MA, Catmull-Rom smoothed, stroked with the
    `#FF6C0E → #FFA400 → #FFC545` gradient, width 3.1.
  * Numbered pivots 1–5 in circles (labels above the tops, below pivot 4).
  * White fade-out gradient over the lower half. **No glow ellipse.**
  * The **last candle ends 0.5 cm from the right edge**, in the top-right corner,
    running behind the Syz mark, with the "5" marker directly above it.
  * Rasterised at 4800 px wide (≈650 dpi at print size).
* **Logo** — official Syz gradient mark, top-right, width 31 mm, embedded as a
  **vector SVG data URI** (base64 in the script). Never rasterised.
* **Eyebrow** — top-left, 7.6 pt bold, letter-spacing .30em, two lines:
  `TECHNICAL ANALYSIS` then the date. No "ADVISORY", no issue number.
* **Title block** — bottom-anchored inline-block, text `TECHNICAL TAKES`,
  17 pt, letter-spacing .14em, white, padding 2 / 5.5 / 2.4 mm.
  The gradient **must be pinned**: `background-color:#FFC545` +
  `background-image:linear-gradient(90deg,#FF6C0E 0%,#FFA400 55%,#FFC545 100%)` +
  `background-repeat:no-repeat` + `background-size:100% 100%`. Without this,
  WeasyPrint tiles the gradient and leaves a dark-orange seam on the right edge.
* **Subtitle row** — left: `Reading markets through trend, momentum and indicators`
  (10.5 pt bold). The right of this row is **empty**: Technical Takes / Advisory
  documents carry **no INTERNAL DOCUMENT badge**. The badge remains implemented
  (1.5 px Tiger Orange outline, radius 2.2 mm, 7 pt bold letter-spaced .24em) but
  renders only when `CONFIG["internal_badge"] = True` is set explicitly.
* **Instrument strip** — 7.6 pt bold, letter-spacing .20em, `#9aa4b5`:
  `NAME · TICKER · CURRENCY · SECTOR · COUNTRY`, or asset-class descriptors for a
  commodity, FX pair or yield.

### 3.2 Verdict box (navy `#202945`, radius 5 mm, padding 5 / 6.5 / 3.5 mm)

In order:

1. **Header row** — conclusion headline on the left (`.vbox p.vhl`, 12.5 pt bold
   white, **must fit on one line** — shorten the headline if it wraps), verdict
   badge right-aligned on the same line: `▲ BULLISH` mint / `◆ NEUTRAL` blueberry /
   `▼ BEARISH` mulberry, 8 pt bold, pill radius 9 mm.
   *No "Technical View" label, no horizon, no conviction line.*
   The CSS rule must be written `.vbox p.vhl`; a bare `.vhl` is overridden by the
   `.vbox p` body rule and silently renders at body size.
2. **Two paragraphs** of commentary at `body_pt` (default 9 pt, `#e9edf5`).
   **Every price level is bold** and white. **Each paragraph is at most 4 lines** as
   rendered; the build prints the line count of each paragraph and warns above 4
   (`max_para_lines`). Shorten the text, never shrink the font to get there.
3. **Levels band** — thin divider, then four or five columns:
   `LAST · SUPPORT · RESISTANCE · [IMPLIED TARGET] · INVALIDATION` (LAST first; INVALIDATION
   gets 1.5× width). Labels 6.6 pt bold gold letter-spaced .16em; values 8.4 pt bold
   white, never wrapped (`white-space:nowrap`, columns sized to content).
   **IMPLIED TARGET appears only when the document reports a breakout** (see §7, breakout
   target). Setting `CONFIG["invalidation"] = ""` drops that column (used on the US
   10-year / 30-year yield versions).

### 3.3 Chart 1

* **191 mm wide × `chart1_height_mm` tall** (default 128 mm), rendered at exactly
  that size — never stretched. The extra 5 mm extends into the right margin so the
  price tags align with the logo's right edge; all text blocks stay 186 mm.
* **No frame or outline** around the image.
* Source line centred underneath: exactly `Source: Syz Research / Bloomberg` —
  **nothing after it**.

### 3.4 Footer

`Syz Research · Technical Takes · <date>` left, `page n/3` right, 7.6 pt `#9aa4b5`,
absolutely positioned at the page bottom. **No horizontal rule.**

---

## 3b. PAGE 3 — disclaimer (from 5 Oct 2026)

The document has **three pages**. Page 2 carries no legal text any more; the **DISCLAIMER**
(Florian's text of 5 Oct 2026, verbatim, `DISCLAIMER_PARAS` in the script) sits at the
**bottom of page 3**, alone, in the same style as before: heading row with the title
`DISCLAIMER` (7.6 pt bold, letter-spaced) alone on the left, then the
paragraphs at 6.8 pt, line-height 1.55, grey `#9aa4b5`, justified, 1.6 mm between
paragraphs. Footers read `page n/3`.
The **signature** (`CONFIG["author"]`) closes **page 2**: right-aligned, 7.6 pt blueberry, just
above the footer (bottom 9 mm of the page box) – it no longer sits on the disclaimer heading. With `page2: False` the disclaimer page becomes page 2/2.

## 4. PAGE 2 — two variants

### Variant A (default): signal chart on the same instrument

Order: signal box → chart 2 → gap → description box → signature (bottom right) → footer.

**4.1 Breakout & Momentum Signals box** — same navy box style as page 1, title
inside the box at 12.5 pt. Badge on the title row: `▲ POSITIVE` / `◆ MIXED` /
`▼ NEGATIVE`.

The comment is **mechanical**, generated from the chart-2 signal file, in this order:

1. **Band paragraph** —
   upper: *"The last band broken was the upper band – a new 100-day high at CCY x
   on `<date>`. This is a positive trend signal: price is printing a succession of
   higher highs and higher lows; the lower band (CCY y) has not been broken since
   `<date>`."*
   lower: the same shape with *new 100-day low*, *negative trend signal*, *lower
   highs and lower lows*, *the upper band … has not been broken since*.
2. **Momentum paragraph** —
   blue last bar: *"Long-term momentum is positive. The latest bar is blue, so the
   long-term momentum regime remains constructive and supports the trend signal above."*
   red last bar: the negative variant.

Wording rules: always **"broken"**, never "touched". The comment **must not mention
the 200-day moving average** — the bar colour stands for it.

Badge logic: POSITIVE when both signals are up, NEGATIVE when both are down, MIXED
otherwise. It may disagree with the discretionary page-1 verdict by design.

**4.2 Chart 2** — same width and placement as chart 1 (191 mm), height
`chart2_height_mm` (default 128 mm). Same source line.

**4.3 Description box** — light grey `#f4f6fa`, radius 5 mm, **11 mm gap above it**.
Eyebrow label in orange: `THE BUSINESS` (single stock), `THE INDEX`, `THE SECTOR`,
`THE INSTRUMENT` (yields), `THE CONTRACT` (futures), `THE PAIR` (FX). Keep to ≤ 4 lines.
Set `CONFIG["page2_description"] = False` to omit it.

**4.4 Signature** — `Florian Marini, CFA, CMT – Head of Research · Syz Private Banking`,
right-aligned, 7.6 pt blueberry, 9 mm above the page bottom. Page 2 carries **no legal
text**; the disclaimer is on page 3 (§3b).

Footer as page 1, `page 2/3`, no rule.

### Variant B (`dual: True`): a second instrument

Page 2 becomes a full second analysis instead of the signal chart: instrument strip →
navy verdict box (same structure as page 1) → a **page-1-style chart of the second
instrument** (price + stochastic, its own overlays, `chart2_height_mm` ≈ 124 to leave
room) → disclaimer. Set `page2_description: False`; there is no space for the grey box,
so any instrument caveat goes in the second box's closing sentence.
Config keys: `xlsx2, strip2, headline2, verdict2, last2, analysis2, supports2,
resistances2, invalidation2, overlays2, relative_strength2, chart2_height_mm`.

---

## 5. CHART SPECIFICATIONS

Common: matplotlib, Nunito Sans, 300 dpi, white background, thin `#b9c2d0` frames,
axis labels on the **right**, no grid, log price scale, and a **trading-day x-axis** —
one unit per bar, with month/year labels mapped onto bar indices. A calendar-date axis
is forbidden: weekend and holiday gaps put a weekly kink into every line.
X ticks: month abbreviation at each quarter start (Jan/Apr/Jul/Oct), year labels 15 pt
below the axis. Right margin: 22 bars of empty space.

Y ticks are chosen adaptively: round numbers on the log scale, falling back to evenly
spaced nice **linear** steps when the range is too narrow for decade ticks (FX, yields).
The y limits are widened when needed so that every overlay level is visible, which lets
a long-term resistance above the traded range be shown as a target.

### 5.1 Chart 1 — 191 mm × `chart1_height_mm`

Panels, height ratios **3.5 / 1.0 / 1.3** (or **4.2 / 1.1** when relative strength is
omitted):

1. **Price** — OHLC bars in `#141a2e`, lw 0.42, tick width 0.42 bars.
   50-day MA blue `#1f4fd8` lw 0.8; 200-day MA red `#d81f2a` lw 0.9;
   Bollinger dotted `#aeb8c7` lw 0.4.
   **Support / resistance as segments only**: the resistance line starts at the bar
   that made the 100-day high, the support line at the bar that made the 100-day low,
   each running to the right edge; dashed (4.5 on / 3 off), lw 0.85, resistance **mint**,
   support **mulberry**.
   *Named pivots instead of the band:* `res_level = (level, "YYYY-MM-DD")` / `sup_level`
   redraw the mint / mulberry segment from that date at that level (the tag keeps the
   decimals, e.g. `2999.0`). House preference: the **latest lower high** as resistance in a
   downtrend, the **latest higher low** as support in an uptrend.
   `hide_lines = ("res",)` and/or `("sup",)` remove the band segment **and** its tag –
   used when the band line is today's bar (a breakout to a record) or sits on top of a
   drawn level.
   Y limits `min(low) × 0.90` to `max(high) × 1.12`, widened for overlays.
   `Log` printed vertically at the right edge.
2. **Stochastic** — `%DS` blue, `%DSS` orange `#e08033`, lw 0.6; horizontal lines at
   80 (red) and 20 (green); y range −4…104; label bottom-left
   `Stochastic %DS(25) / %DSS(15)`.
3. **Relative strength** — close ÷ benchmark × 100, navy line lw 0.6, plus its 200-day
   MA in red lw 0.8, **log scale**; label top-left
   `Relative strength vs <BENCH> and its 200-day MA`.
   **Omitted entirely** for commodities, FX and rates, or whenever the workbook has no
   benchmark column (`relative_strength: False`).

**Manual overlays** (`CONFIG["overlays"]`), drawn in dashed blue `#4b9fe8`, lw 0.85,
above the price bars:
* `hlines` — horizontal levels, dash (5 on / 3 off), each optionally anchored on a date
  via `hline_from` and extended to the right edge.
* `hlines_dotted` — the same but fine dots (1.2 on / 1.6 off), reserved for long-term
  or projected resistance the market has never traded at (e.g. the 2007 highs).
* `trendlines` — pairs of dates; the line is fitted through those bars' **lows**, or
  **highs** with `"highs": True`, and extended to the right edge. The fit is
  **geometric** — a straight line on the log price axis, which is what Bloomberg draws;
  a linear fit overshoots badly on a multi-year log chart.
* `tag: True` adds right-edge tags for the levels, in the same blue.

**Right-edge tags** (white bold text on a filled square, auto-nudged apart so they never
overlap): resistance (mint), 200-day MA (red), last (navy), support (mulberry), plus the
last `%DSS` value and the last RS / RS-MA values. Any of them can be suppressed with
`CONFIG["hide_tags"]` (`"res" | "sup" | "ma200" | "last"`) when a label duplicates a
neighbour. Tags whose labels round to the same string are de-duplicated automatically.

Price-panel y padding: `CONFIG["ypad"]` = (bottom, top) multipliers on the window low/high,
default `(0.90, 1.12)` for equities, `(0.985, 1.02)` for FX and yields (applies to both charts).

### 5.2 Chart 2 — 191 mm × `chart2_height_mm`, single panel

* Same OHLC bars, but **coloured by the slope of the 200-day MA measured over 5 bars**:
  rising → blue `#1f4fd8`, falling → red `#d81f2a`.
* **The moving average itself is not drawn.**
* `Maximum(100)` as a fine **dotted mint** line (1.2 on / 1.6 off, lw 0.8) and
  `Minimum(100)` as a fine dotted mulberry line, across the whole chart. **No shaded area.**
* Right-edge tags: max100 (mint), last (navy), min100 (mulberry).
* Legend bottom-left inside the panel:
  `Bars: blue = rising 200-day MA slope, red = falling · dotted lines = 100-day high (mint) / low (mulberry)`.
* **Band-break detection** — the upper band is broken on a bar whose *high* ≥ that bar's
  `Maximum(100)`; the lower band on a bar whose *low* ≤ its `Minimum(100)`. The more
  recent break wins. Consequence to remember: a swing low only counts once it actually
  sets the 100-day minimum.
* `chart2_red_bars = ("YYYY-MM-DD", …)` forces those bars red – an editorial highlight
  (e.g. the bar that broke key support). Display only: the signals are unchanged.
* Writes `<chart>.json` with `last_bar_up`, `touch` (`upper`/`lower`), the date and level
  of that break, the date and level of the opposite band's last break, and last / max100 / min100.

---

## 6. DATA RULES (non-negotiable)

1. **The workbook is the sole source.** No external data, no substituted indicator
   definitions.
2. **Indicators are used as exported.** The stochastic is always plotted exactly as it
   comes from the sheet.
3. **The one exception — the known export defect.** Bloomberg sometimes writes Sheet 1
   with *zero decimals* (price, MA50, MA200, UBB, LBB rounded to whole units), which
   makes those lines step like a staircase. The script detects this automatically (all
   MA200 values integral) and then **rebuilds MA50, MA200 and the Bollinger bands from
   the workbook's own unrounded closes**. Verified: the rebuilt SMA200 matches Bloomberg's
   decimal column to 0.0001, and `UBB(2)`/`LBB(2)` are **Bollinger (100, 2)** — not (20, 2).
   *The proper fix is to export with 2 decimals; then nothing is rebuilt.*
4. **Relative strength is the only genuinely computed series** (close ÷ benchmark × 100
   and its 200-day mean). When the benchmark lags by a session — the index has not
   printed yet — the last value is carried forward so the ratio has no artificial gap.
5. **Levels** come from the latest row: `Maximum(100)` = resistance, `Minimum(100)` =
   support. When the workbook has no such columns they are rolled from the exported
   highs and lows over 100 bars including the current bar (Bloomberg convention).
6. Rows with empty OHLC (holidays) are dropped.
6b. **Live last row.** When the export is pulled during the session, the last row is a live
   print, not a close. Keep it (the document is dated that day), but state in the delivery
   message that `last` is intraday, and that a breakout counted on that bar is only
   confirmed by the close; if the close fails, rebuild on the closing data. If the live row
   makes text values disagree with the chart (indicators not yet updated), drop the row.
7. **Plotted window** — the Sheet 2 period when the workbook has one, otherwise the last
   `CONFIG["years"]` years (default 4). Override when a trendline anchor sits further
   back (7 for a trendline off a 2020 low), or when a large price range crushes the
   recent action (2 for a stock that ran from 6 to 207).

### Supported workbook layouts

Columns are matched **by header name**, never by position, so all layouts seen so far
work unchanged:

| Layout | Example | Notes |
|---|---|---|
| Sheet 1 + Sheet 2 | `ENR_GY.xlsx`, `Epiroc.xlsx` | Sheet 2 holds decimal OHLC, MA200, Max/Min(100) |
| Sheet 1 only, no Max/Min | `DE_US.xlsx` | bands rolled from highs/lows |
| Sheet 1 only, with Max/Min | `S_1.xlsx`, `PLTR_US.xlsx` | fully decimal, nothing rebuilt |

Expected Sheet 1 headers: `Date, Open, High, Low, Close,
Moving Average(Simple,200,0), UBB(2), LBB(2), Moving Average(Simple,50,0),
[Maximum(100), Minimum(100),] %DS(25), %DSS(15), <BENCH> Index - Last Price`.
The benchmark name shown on the chart is taken from that last header
(`SPX Index - Last Price` → `SPX`).

### Decimal convention

Set by `CONFIG["decimals"]` and applied to **both** the chart labels and the written
commentary:

* **2 decimals** — forex and yields (nominal, real/TIPS, breakevens): `4.94`, `5.02`,
  `0.59`, `2.60`.
* **1 decimal** — equities, commodities and crypto: `258.3`, `1295.5`.
* Integers print plain only from 100 upwards (`USD 701`, not `701.00`); below 100 they keep
  the decimals (`3.0`). Named pivots (`res_level` / `sup_level`) always keep their decimals.
* Indices carry no currency prefix in `last` (`6769.3`); stocks, commodities and FX do
  (`JPY 3159.0`, `USD 1497.9`).
* The unit in `CONFIG["last"]` may be a prefix (`"SEK 258.30"`) or a suffix (`"4.9444%"`);
  the page-2 comment follows whichever form is used.

---

## 7. EDITORIAL RULES (CMT house style)

* **En dashes only (U+2013); em dashes are never used.**
* The verdict is formed in this order and nothing else: **200-day MA slope → trendline →
  structure of highs and lows.** Oscillators never override the trend; they qualify risk
  and opportunity within it.
* **Verdict grid (Florian's corrections, Sep–Oct 2026):**
  | 200-day slope | Structure | Verdict |
  |---|---|---|
  | rising, price above | HH/HL intact on the 100-day band structure (page-2 chart: last band broken = upper) | **BULLISH** – a lost minor swing low or a pullback to the 200-day is "a correction within an uptrend" (Unicaja, Alphabet, SMFG) |
  | rising or flattening | range, price around the 200-day, last band broken = lower | **NEUTRAL with a positive tilt**, with both triggers written (Mitsui) |
  | turned down | key support still holds | **NEUTRAL with a negative tilt** |
  | falling | named support broken / lower low | **BEARISH** (Hermès, Platinum, ENR) |
  Higher highs and lower lows are read on the **100-day high/low structure** (page-2 chart),
  not on every minor swing. A golden cross plus a resistance break upgrades straight to
  Bullish.
* **Stated triggers are rules.** When the text (or Florian) sets "turn Bearish below X /
  Bullish above Y", the verdict changes when the level is reached – no extra confirmation.
* **Standing positions are priors, not vetoes.** If the three inputs turn against a
  standing editorial view, raise it before publishing.
* A channel or trendline break is a *loss of trend strength*, never a "reversal".
* **Golden / death cross must be flagged when present.** A *golden cross* is the 50-day
  crossing above the 200-day **with the 200-day slope recently positive** — highlight it
  in the bullish comment. A *death cross* is the 50-day crossing below the 200-day **with
  the 200-day slope recently negative** — highlight it in the bearish comment. The slope
  condition is part of the definition: a crossover without the matching recent slope is
  not called a golden or death cross. Name the crossover and its date. **Mention it only
  when it is recent (the last few weeks)** — a crossover that is months old is no longer
  news and is left out of the comment.
* The medium-term trend turns structurally bearish only in two stages: first a confirmed
  break of the named horizontal support that interrupts the higher-highs/higher-lows
  sequence, then the 200-day MA rolling into a declining slope. Never conflate the two.
* Every level cited is a specific price, always **bold** in the prose.
* **Relative strength is described, never quantified, and kept simple** (28 Oct 2026): one
  sentence, "Relative momentum remains positive, with a rising 200-day average." /
  "…negative, with a declining 200-day average." (add "against the SMI" etc. when the
  benchmark is not the default). Never print the ratio or its 200-day value, never narrate
  the ratio's path versus its highs.
  **The lead-in of this sentence is bold** (Florian, 1 Nov 2026): wrap the opening phrase
  `Relative momentum` in `<b>…</b>`, e.g. `<b>Relative momentum</b> against the SMI remains
  positive, with a rising 200-day average.` Applies to every report built from now on that
  carries a relative-strength panel; it does not apply to commodities, FX or rates (no RS
  sentence). Previously delivered reports are not rebuilt.
* **No external research provider** is ever named anywhere in the document; the only
  source line is `Source: Syz Research / Bloomberg`.
* **Breakout target (Bollinger(100,2) width, adopted 4 Oct 2026).** Whenever the comment
  reports a breakout (or breakdown) through a named level:
  1. the breakout bar is the **first close** beyond the level — intraday pokes do not count;
  2. on that bar, bandwidth = (UBB − LBB) / ((UBB + LBB) / 2), i.e. the 4-sigma
     "normal volatility" envelope as a % of the 100-day mean, **frozen** there;
  3. target = level × (1 + bandwidth) for a breakout, level × (1 − bandwidth) for a
     breakdown;
  4. the text mentions it ("Projecting the 100-day volatility range on the breakout level
     gives an implied target of USD 8254.1.") and the IMPLIED TARGET column carries it.
  Set `CONFIG["target"] = {"breakout": <level>, "direction": "up" | "down"}`; the script
  finds the bar, computes the target, prints the working, and replaces `__TARGET__`
  (and optionally `__BAR__`, the breakout date, and `__BW__`, the bandwidth) in
  `analysis_html`. A plain string in `target` is shown as is. The width is usually
  compressed at a breakout (bands contract in a consolidation), so the target is
  conservative by construction.
* **Invalidation** is mandatory and falsifiable, and always references the band line or
  the 200-day average — never an arbitrary pivot or a recently broken shelf.
  **Uptrend:** a move below the lower support band line (the mulberry Minimum(100) line)
  or below the 200-day MA. **Downtrend:** a move above the upper resistance band line
  (the mint Maximum(100) line) or above the 200-day MA.
* The written comment and the verdict badge must always agree.
* Headline states the conclusion, not the topic.
* **Page-1 commentary: two paragraphs, each ≤ 4 rendered lines**, following this model —
  * **paragraph 1 template** (Florian's Platinum rewrite, 27 Oct 2026):
    (a) bold verdict sentence ("The primary trend remains positive." / "has turned negative.");
    (b) one sentence on the 200-day slope with its value and where price sits versus the
    200-day and 50-day; (c) **one structural sentence** naming the broken level and what it
    confirms – "The breakout above the August record at **6741.2** confirms the uptrend with
    a higher high." / "The breakdown of the support at **1535.6** confirms the downtrend with
    a lower low." – never a dated narrative of the swing history; (d) on a breakout, the bold
    implied-target sentence; on a Neutral, the two triggers ("A close above X would turn it
    Bullish, a close below Y Bearish.");
  * **paragraph 2 template:** bold momentum sentence → stochastic value and what it permits
    (+ Bollinger band if price is outside it) → relative momentum sentence (if RS panel) →
    closing operative bias tied to a level ("The bullish bias holds above the 200-day moving
    average.");
  * each paragraph opens with a short verdict sentence in bold ("The primary trend has
    turned negative." / "Relative strength reinforces the bearish setup.");
  * signals are named *and* their significance stated ("…forming a death cross with the
    200-day already declining, which gives the signal greater significance");
  * evidence is sequenced — MA slope → crossover → price vs averages → confirming
    low/high — each clause carrying one fact and its level;
  * momentum is framed as what it *permits*, not as a signal ("Momentum remains weak but
    not yet oversold: stochastic at 40 leaves room for further downside");
  * it closes on the operative bias tied to a level, or on the level that would confirm
    the move ("The key resistance to confirm the bull move is USD 207.5");
  * plain institutional phrasing, no rhetorical flourishes, no asides stacking several
    ideas into one sentence.

---

## 8. Build

```bash
pip install weasyprint cairosvg matplotlib openpyxl fonttools
python3 technical_takes.py
```

Fonts are downloaded from the Google Fonts GitHub repository on first run and cached in
`~/fonts` (override with `TT_FONTDIR`). Intermediate artefacts — `motif_hq.svg`,
`chart1.png`, `chart2.png`, `chart2.json` — are written to `./_tt_build` (override with
`TT_WORKDIR`). The PDF goes to `CONFIG["outdir"]`.

Output filename: `<slug>.pdf`.

`TT_OUTDIR` overrides `CONFIG["outdir"]`. The build prints, and you must check:
the target working (`first close above … bandwidth … -> target`), the paragraph line
counts (each ≤ 4), page-1 content bottom (≤ 279 mm) and page-2 description bottom
(≤ 263 mm). Then render the pages (`pdftoppm -r 80 -png`) and look at them.

As shipped, CONFIG reproduces **Technical_Takes_SPIEX_2026-10-29.pdf** pixel for pixel
(verified 1 Nov 2026); put `SPIEX.xlsx` (the SPI Extra export, benchmark column
`SMIC Index - Last Price`) next to the script and run it.

### Per-document workflow (how every document of Oct 2026 was produced)

1. Copy the export next to the script; read the last ~40 rows and the monthly highs/lows
   of the last 2 years; note 200-day slope over 5/20/40 bars, 50/200 crosses and their
   dates, first closes beyond key pivots, the RS ratio vs its 200-day slope.
2. Form the verdict with the grid in §7; pick the drawn levels (named pivots with dates).
3. Edit CONFIG only (or keep a small `build.py` that execs the script without its
   `main()` call and runs `main(cfg)` with `cfg = dict(CONFIG); cfg.pop("target", None);
   cfg.update(...)` – always pop `target` and always pass `overlays`, otherwise the
   shipped example's line and target leak into the new document).
4. Build, check the printed metrics, render, look, deliver; iterate on Florian's edits.

---

## 9. CONFIG reference (all keys)

| Key | Type / example | Default in code | Meaning |
|---|---|---|---|
| `xlsx` | `"SPIEX.xlsx"` | – | Bloomberg export |
| `outdir` | path | `$TT_OUTDIR` or `/mnt/user-data/outputs` | output folder |
| `slug` | `"Technical_Takes_SPIEX_2026-10-29"` | – | PDF file name without `.pdf` |
| `relative_strength` | bool | `True` | third panel on chart 1 |
| `page2` | bool | `True` | signal page |
| `dual` + `*2` keys | bool | `False` | page 2 = second instrument (§4 Variant B) |
| `decimals` | 1 / 2 | 2 | chart labels and text |
| `body_pt` | 8.6 | 9 | verdict-box body size |
| `chart1_height_mm` / `chart2_height_mm` | 128 | 128 | chart heights |
| `years` | 2 | 4 | plotted window – **house standard is 2** |
| `ypad` | `(0.90, 1.12)` | same | price-panel padding |
| `overlays` | dict: `hlines`, `hline_from`, `hlines_dotted`, `trendlines`, `tag` | – | blue manual lines (§5.1) |
| `res_level` / `sup_level` | `(level, "YYYY-MM-DD")` | `None` | named pivot segments |
| `hide_lines` | `("res",)`, `("sup",)` | `()` | drop band segment + tag |
| `hide_tags` | `("ma200",)` … | `()` | drop single tags |
| `chart2_red_bars` | `("2026-10-15",)` | `()` | page-2 highlight |
| `doc_label`, `date`, `strip`, `headline`, `verdict`, `last` | strings | – | page-1 header and box |
| `analysis_html` | two `<p>` blocks; placeholders `__TARGET__`, `__BAR__`, `__BW__` | – | commentary |
| `supports`, `resistances`, `invalidation` | strings, nearest first, `/`-separated | – | levels band; `invalidation=""` drops the column |
| `target` | `{"breakout": lvl, "direction": "up"/"down"}` or a string | absent | IMPLIED TARGET (breakouts only) |
| `max_para_lines` | 4 | 4 | warning threshold |
| `chart2_title`, `business_title`, `business_html`, `page2_description` | strings / bool | – | page 2 |
| `author`, `footer`, `chart_source`, `chart2_source`, `internal_badge` | strings / bool | – | signature, footers, sources |
