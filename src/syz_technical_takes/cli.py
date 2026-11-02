"""``syz-tt`` - deterministic pipeline behind the technical-takes skill.

Subcommands (each prints ONE JSON object on stdout; see the SKILL.md for who
calls what, and src/syz_technical_takes/CLAUDE.md for the map):

  stage-inputs   chat attachments -> .input/ (shared intake; only if a Bloomberg
                 .xlsx was attached - the usual input is a ticker typed in chat)
  fetch          ticker (or an attached .xlsx) -> a Bloomberg-equivalent workbook
                 + a minted run dir  (pulls OHLC, synthesizes every indicator)
  analyze        workbook -> the verdict-driving analytics JSON (§7 inputs)
  build          a spec JSON (the CONFIG the model authors) -> the 3-page PDF
                 + the render checks (paragraph lines, page bounds, target working)
  schema         print the spec template + which keys are required

The division of labour mirrors every sibling skill: deterministic Python does the
data, the indicators (including the decoded %DS/%DSS stochastic), the analytics
and the drawing; the model authors only the verdict spec (headline, verdict,
commentary, drawn levels) - the one judgement step, like `visual`.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

try:                                   # optional: only for the `stage-inputs` command
    from syz_intake import staging     # (chat-attachment intake; present in the SYZ monorepo)
except ImportError:                    # standalone install -> ticker-based use only
    staging = None

from . import benchmarks, data
from .analytics import analyze as analyze_workbook
from .indicators import synthesize_workbook


def _emit(obj):
    print(json.dumps(obj, default=str, ensure_ascii=False))


def _run_dir(tag: str, base: Path) -> Path:
    stamp = dt.datetime.now().strftime("%d-%m-%y-%H-%M")
    safe = re.sub(r"[^A-Za-z0-9]+", "", tag)[:6].upper() or "TT"
    d = base / f"technical_takes_{stamp}_{safe}"
    (d / ".audit").mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- fetch
def cmd_fetch(a):
    base = Path(a.output_root or ".output")
    tag = a.tag or (a.ticker or Path(a.xlsx or "TT").stem)
    run = Path(a.run_dir) if a.run_dir else _run_dir(tag, base)
    (run / ".audit").mkdir(parents=True, exist_ok=True)
    wb_path = run / ".audit" / f"{re.sub(r'[^A-Za-z0-9]+', '_', tag)}.xlsx"
    prov = {"source": None, "notes": []}

    if a.xlsx:                                   # a real Bloomberg export was supplied
        import shutil
        shutil.copy(a.xlsx, wb_path)
        prov["source"] = "bloomberg_export_supplied"
        _emit({"run_dir": str(run), "workbook": str(wb_path), "provenance": prov,
               "benchmark": None, "note": "using the supplied export as-is"})
        return

    # pull OHLC from the feed and synthesize the workbook
    price_sym = a.yahoo or benchmarks.bloomberg_to_yahoo(a.ticker)
    px = data.fetch_ohlc(price_sym, years=a.years)
    prov["source"] = "yahoo_v8_chart (dev licence)"
    prov["price_symbol"] = price_sym

    bench_bars = bench_name = None
    if not a.no_benchmark:
        bench_name = a.benchmark or benchmarks.default_bench(a.country or "")
        bsym = a.benchmark_yahoo or benchmarks.bench_yahoo(bench_name)
        try:
            b = data.fetch_ohlc(bsym, years=a.years)
            bench_bars = b["bars"]
            prov["benchmark_symbol"] = bsym
            if bench_name.upper() in ("SPI", "SMIC") and bsym == "^SSMI":
                prov["notes"].append(f"{bench_name} not on the feed; used SMI (^SSMI) as proxy")
        except Exception as e:
            prov["notes"].append(f"benchmark {bench_name} ({bsym}) failed: {e}; relative strength dropped")
            bench_name = None

    summ = synthesize_workbook(px["bars"], wb_path, bench_bars=bench_bars, bench_name=bench_name)
    _emit({"run_dir": str(run), "workbook": str(wb_path),
           "currency": px.get("currency"), "benchmark": bench_name,
           "relative_strength": bench_bars is not None,
           "provenance": prov, "summary": summ})


# ---------------------------------------------------------------- analyze
def cmd_analyze(a):
    _emit(analyze_workbook(a.workbook))


# ---------------------------------------------------------------- build
def cmd_build(a):
    spec = json.loads(Path(a.spec).read_text())
    # JSON object keys are always strings, but the renderer looks up overlay
    # anchors by the float level (ov["hline_from"].get(lvl)) -> coerce them back.
    ov = spec.get("overlays") or {}
    if isinstance(ov.get("hline_from"), dict):
        ov["hline_from"] = {float(k): v for k, v in ov["hline_from"].items()}
    if a.workbook:
        spec["xlsx"] = a.workbook
    if "xlsx" not in spec:
        _emit({"error": "spec has no 'xlsx' and --workbook not given"}); sys.exit(2)
    run = Path(a.run_dir) if a.run_dir else Path(spec["xlsx"]).resolve().parent.parent
    outdir = Path(a.out_dir) if a.out_dir else run
    workdir = Path(a.work_dir) if a.work_dir else (run / ".audit" / "_build")

    from . import render
    render.configure(outdir=str(outdir), workdir=str(workdir), fontdir=a.font_dir)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        pdf = render.main(dict(spec))
    log = buf.getvalue()

    def _grab(pat, cast=str):
        m = re.search(pat, log)
        return cast(m.group(1)) if m else None

    checks = {
        "paragraph_lines": _grab(r"paragraph lines: (\[[0-9, ]*\])", json.loads),
        "page1_bottom_mm": _grab(r"page-1 content bottom: ([0-9.]+)", float),
        "page2_bottom_mm": _grab(r"page-2 description bottom: ([0-9.]+)", float),
        "target_working": _grab(r"(target: .+?-> target [0-9.]+)"),
        "warnings": re.findall(r"WARNING:[^\n]+", log),
    }
    _emit({"pdf": str(pdf), "slug": spec.get("slug"), "checks": checks, "log": log.strip()})


# ---------------------------------------------------------------- schema
SPEC_TEMPLATE = {
    "slug": "Technical_Takes_<TICKER>_<YYYY-MM-DD>",
    "relative_strength": True, "page2": True, "decimals": 1, "years": 2,
    "body_pt": 8.6, "ypad": [0.90, 1.12],
    "doc_label": "TECHNICAL ANALYSIS", "date": "<e.g. 30 October 2026>",
    "strip": "NAME &middot; TICKER &middot; CCY &middot; SECTOR &middot; COUNTRY",
    "headline": "<conclusion, one line ~55 chars>",
    "verdict": "BULLISH | NEUTRAL | BEARISH",
    "last": "<CCY 123.4 for stocks/commodities/FX; 1234.5 bare for indices>",
    "analysis_html": "<two <p> blocks; every price <b>bold</b>; §7 rules; "
                     "RS sentence opens with <b>Relative momentum</b> (house rule v1.8)>",
    "supports": "<nearest first, /-separated>", "resistances": "<...>",
    "invalidation": "Close below/above <level> (200d MA / band line)",
    "overlays": {"hlines": [], "hline_from": {}, "hlines_dotted": [], "trendlines": [], "tag": True},
    "res_level": None, "sup_level": None, "hide_lines": [], "hide_tags": [],
    "target": "OPTIONAL {\"breakout\": <level>, \"direction\": \"up|down\"} on a breakout only",
    "business_title": "THE BUSINESS | THE INDEX | THE SECTOR | THE COMMODITY | THE PAIR | THE INSTRUMENT",
    "business_html": "<=4 lines; prices <b>bold</b>",
    "author": "Florian Marini, CFA, CMT &ndash; Head of Research &middot; Syz Private Banking",
    "footer": "Syz Research &middot; Technical Takes &middot; <date>",
    "chart_source": "Source: Syz Research / Bloomberg",
    "chart2_source": "Source: Syz Research / Bloomberg",
    "chart2_title": "Breakout &amp; Momentum Signals",
}


def cmd_schema(a):
    _emit({"required": ["slug", "strip", "headline", "verdict", "last",
                        "analysis_html", "supports", "resistances", "invalidation",
                        "business_title", "business_html"],
           "note": "'xlsx' is injected by build --workbook; set relative_strength=False "
                   "for commodities/FX/rates (no RS sentence, no benchmark).",
           "template": SPEC_TEMPLATE})


def main(argv=None):
    p = argparse.ArgumentParser(prog="syz-tt", description="Technical Takes pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    if staging is not None:                      # stage-inputs (only in the SYZ monorepo)
        staging.add_subparser(sub)

    f = sub.add_parser("fetch", help="ticker/xlsx -> workbook + run dir")
    f.add_argument("--ticker", help="Bloomberg-style 'MSFT US' / 'NOVN SW' or a Yahoo symbol")
    f.add_argument("--yahoo", help="override the Yahoo price symbol")
    f.add_argument("--xlsx", help="use a supplied Bloomberg export instead of fetching")
    f.add_argument("--benchmark", help="benchmark NAME (SXXP/SMI/SPX/TPX/MXWO); default by --country")
    f.add_argument("--benchmark-yahoo", help="override the benchmark Yahoo symbol")
    f.add_argument("--country", help="used to default the benchmark when --benchmark omitted")
    f.add_argument("--no-benchmark", action="store_true", help="commodities/FX/rates: no RS panel")
    f.add_argument("--years", type=int, default=5, help="history to pull (>=3 for clean MA200 warm-up)")
    f.add_argument("--tag", help="run-dir tag (default: the ticker)")
    f.add_argument("--run-dir", help="use this run dir instead of minting one")
    f.add_argument("--output-root", help="base for minted run dirs (default .output)")
    f.set_defaults(fn=cmd_fetch)

    an = sub.add_parser("analyze", help="workbook -> verdict analytics JSON")
    an.add_argument("--workbook", required=True)
    an.set_defaults(fn=cmd_analyze)

    b = sub.add_parser("build", help="spec JSON -> PDF + checks")
    b.add_argument("--spec", required=True, help="the CONFIG the model authored, as JSON")
    b.add_argument("--workbook", help="inject as spec['xlsx']")
    b.add_argument("--run-dir"); b.add_argument("--out-dir"); b.add_argument("--work-dir")
    b.add_argument("--font-dir")
    b.set_defaults(fn=cmd_build)

    s = sub.add_parser("schema", help="print the spec template")
    s.set_defaults(fn=cmd_schema)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    main()
