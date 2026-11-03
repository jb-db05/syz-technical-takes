"""Usage log: one row per Technical Takes document, kept on the repo's ``usage-log`` branch.

Every successful ``syz-tt build`` appends a row to ``usage/log.csv`` on that branch.
The branch never touches the working tree: the row is committed with git plumbing
(hash-object / mktree / commit-tree) and pushed directly, retrying when another
session pushed first. If the push fails (offline, no credentials) the row waits in
``.output/usage_pending.csv`` and goes out with the next build or ``syz-tt usage-log``.

The repository is public, so the log holds no personal data: no user name, no email,
only the document itself (date, underlying, verdict, data source).

``TT_USAGE_LOG=0`` turns logging off (tests, dry runs).
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import io
import json
import os
import re
import subprocess
import time
from collections import Counter, OrderedDict
from pathlib import Path

BRANCH = "usage-log"
LOG_PATH = "usage/log.csv"
FIELDS = ["logged_at_utc", "doc_date", "ticker", "name", "verdict", "data_source", "slug"]

README = """# usage-log

Written by `syz-tt build`: one row per Technical Takes document built
(`usage/log.csv`). Do not edit by hand and never merge this branch into `main`.
The monthly report (`syz-tt usage-report`) reads it.

Columns: logged_at_utc, doc_date, ticker, name, verdict, data_source, slug.
No personal data is recorded (the repository is public).
"""

_SLUG = re.compile(r"^Technical_Takes_(.+)_(\d{4}-\d{2}-\d{2})$")


# ----------------------------------------------------------------- building a row
def row_from_spec(spec: dict, provenance: dict | None = None, logged_at: str | None = None) -> dict:
    """The log row for a built document, from the spec the model authored."""
    slug = spec.get("slug", "")
    m = _SLUG.match(slug)
    ticker, doc_date = (m.group(1), m.group(2)) if m else (slug, "")
    strip = html.unescape(spec.get("strip", ""))
    name = spec.get("name") or (_nice(re.split(r"\s*·\s*", strip)[0]) if strip else ticker)
    return {
        "logged_at_utc": logged_at or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "doc_date": doc_date,
        "ticker": ticker,
        "name": name,
        "verdict": str(spec.get("verdict", "")).upper(),
        "data_source": data_source_label(provenance),
        "slug": slug,
    }


def _nice(s: str) -> str:
    """'US GENERIC GOVT 10 YR' -> 'US Generic Govt 10 YR': title case, short codes kept."""
    s = s.strip()
    if s != s.upper():
        return s
    return " ".join(w if len(w) <= 2 or not w.isalpha() else w.capitalize() for w in s.split())


def data_source_label(prov: dict | None) -> str:
    src = (prov or {}).get("source") or ""
    if src.startswith("bloomberg"):
        return "Bloomberg export"
    if src:
        sym = (prov or {}).get("price_symbol")
        return f"Free feed ({sym})" if sym else "Free feed"
    return "Unknown"


def _csv_lines(rows) -> list[str]:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    for r in rows:
        w.writerow({k: r.get(k, "") for k in FIELDS})
    return buf.getvalue().splitlines()


def _header() -> str:
    return ",".join(FIELDS)


# ----------------------------------------------------------------- git plumbing
def _git(repo, *args, data: str | None = None, timeout=60) -> str:
    env = dict(os.environ)
    env.setdefault("GIT_AUTHOR_NAME", "syz-tt"); env.setdefault("GIT_AUTHOR_EMAIL", "syz-tt@users.noreply.github.com")
    env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"]); env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])
    p = subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True,
                       text=True, timeout=timeout, env=env)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])}: {p.stderr.strip()[:300]}")
    return p.stdout


def repo_root(start: Path | None = None) -> Path | None:
    try:
        return Path(_git(start or Path.cwd(), "rev-parse", "--show-toplevel").strip())
    except Exception:
        return None


def _remote_log(repo) -> tuple[str | None, str]:
    """(commit sha of origin/usage-log or None, log.csv text)."""
    heads = _git(repo, "ls-remote", "--heads", "origin", BRANCH).strip()
    if not heads:
        return None, _header() + "\n"
    _git(repo, "fetch", "-q", "origin", f"+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}", timeout=120)
    sha = _git(repo, "rev-parse", f"refs/remotes/origin/{BRANCH}").strip()
    try:
        text = _git(repo, "show", f"{sha}:{LOG_PATH}")
    except RuntimeError:
        text = _header() + "\n"
    return sha, text


def _commit(repo, parent: str | None, text: str, n_new: int) -> str:
    blob = _git(repo, "hash-object", "-w", "--stdin", data=text).strip()
    readme = _git(repo, "hash-object", "-w", "--stdin", data=README).strip()
    inner = _git(repo, "mktree", data=f"100644 blob {blob}\tlog.csv\n").strip()
    root = _git(repo, "mktree", data=f"100644 blob {readme}\tREADME.md\n040000 tree {inner}\tusage\n").strip()
    args = ["commit-tree", root, "-m", f"usage: +{n_new} document build(s)"]
    if parent:
        args[2:2] = ["-p", parent]
    return _git(repo, *args).strip()


def _pending_file(repo) -> Path:
    return Path(repo) / ".output" / "usage_pending.csv"


def flush(repo) -> dict:
    """Push every pending row to origin/usage-log. Returns a status dict."""
    pf = _pending_file(repo)
    pending = [l for l in pf.read_text().splitlines() if l.strip()] if pf.exists() else []
    if not pending:
        return {"status": "nothing_pending"}
    last_err = None
    for attempt in range(4):
        try:
            parent, text = _remote_log(repo)
            have = set(text.splitlines())
            new = [l for l in pending if l not in have]
            if not new:
                pf.unlink(missing_ok=True)
                return {"status": "already_logged", "rows": len(pending)}
            body = text if text.endswith("\n") else text + "\n"
            commit = _commit(repo, parent, body + "\n".join(new) + "\n", len(new))
            _git(repo, "push", "-q", "origin", f"{commit}:refs/heads/{BRANCH}", timeout=120)
            pf.unlink(missing_ok=True)
            return {"status": "logged", "rows": len(new), "branch": BRANCH, "commit": commit[:10]}
        except Exception as e:                    # race with another push, or network
            last_err = str(e)
            time.sleep(2 ** (attempt + 1))
    return {"status": "pending", "rows": len(pending), "error": last_err,
            "note": f"kept in {pf}; retried on the next build or `syz-tt usage-log`"}


def record(row: dict, repo: Path | None = None) -> dict:
    """Queue one row and try to push it. Never raises: logging must not break a build."""
    if os.environ.get("TT_USAGE_LOG", "1") == "0":
        return {"status": "disabled"}
    try:
        repo = repo or repo_root(Path(__file__).resolve().parent) or repo_root()
        if repo is None:
            return {"status": "skipped", "note": "not inside a git checkout"}
        pf = _pending_file(repo)
        pf.parent.mkdir(parents=True, exist_ok=True)
        with pf.open("a") as fh:
            fh.write("\n".join(_csv_lines([row])) + "\n")
        return flush(repo)
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ----------------------------------------------------------------- reading + reporting
def read_log(repo: Path | None = None, path: str | None = None) -> list[dict]:
    if path:
        text = Path(path).read_text()
    else:
        repo = repo or repo_root(Path(__file__).resolve().parent) or repo_root()
        _, text = _remote_log(repo)
    return list(csv.DictReader(io.StringIO(text)))


def documents(rows: list[dict]) -> list[dict]:
    """One row per document: builds of the same underlying for the same document date
    count once (rebuilds and data-source swaps). The last build wins; `builds` counts them."""
    docs: "OrderedDict[tuple, dict]" = OrderedDict()
    for r in sorted(rows, key=lambda r: r["logged_at_utc"]):
        k = (r["ticker"].upper(), r["doc_date"])
        prev = docs.pop(k, None)
        d = dict(r, builds=(prev["builds"] + 1) if prev else 1,
                 first_logged_utc=prev["first_logged_utc"] if prev else r["logged_at_utc"])
        docs[k] = d
    out = []
    for d in docs.values():
        d["month"] = d["first_logged_utc"][:7]
        out.append(d)
    return out


def previous_month(today: dt.date | None = None) -> str:
    t = today or dt.date.today()
    first = t.replace(day=1)
    return (first - dt.timedelta(days=1)).strftime("%Y-%m")


def report(rows: list[dict], month: str) -> dict:
    docs = documents(rows)
    m_docs = [d for d in docs if d["month"] == month]
    m_builds = [r for r in rows if r["logged_at_utc"][:7] == month]
    by_u: "OrderedDict[str, dict]" = OrderedDict()
    for d in sorted(m_docs, key=lambda d: d["first_logged_utc"]):
        u = by_u.setdefault(d["ticker"], {"ticker": d["ticker"], "name": d["name"], "documents": 0,
                                          "last_verdict": "", "last_doc_date": ""})
        u["documents"] += 1
        u["last_verdict"], u["last_doc_date"] = d["verdict"], d["doc_date"]
    history = Counter(d["month"] for d in docs)
    return {
        "month": month,
        "documents": len(m_docs),
        "builds": len(m_builds),
        "underlyings": len(by_u),
        "by_underlying": sorted(by_u.values(), key=lambda u: (-u["documents"], u["ticker"])),
        "verdicts": dict(Counter(d["verdict"] for d in m_docs)),
        "data_sources": dict(Counter("Bloomberg export" if d["data_source"].startswith("Bloomberg")
                                     else "Free feed" if d["data_source"].startswith("Free") else "Unknown"
                                     for d in m_docs)),
        "history": [{"month": k, "documents": history[k]} for k in sorted(history)],
    }


def documents_csv(rows: list[dict]) -> str:
    """The document-level table the dashboard reads."""
    cols = ["month", "first_logged_utc", "doc_date", "ticker", "name", "verdict", "data_source", "builds"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for d in documents(rows):
        w.writerow(d)
    return buf.getvalue()


def email_html(rep: dict, dashboard_url: str | None = None) -> str:
    """A short Syz-styled summary for the monthly email."""
    month_name = dt.datetime.strptime(rep["month"], "%Y-%m").strftime("%B %Y")
    e = html.escape
    rows = "".join(
        f"<tr><td style='padding:4px 10px 4px 0'><b>{e(u['ticker'])}</b></td>"
        f"<td style='padding:4px 10px'>{e(u['name'])}</td>"
        f"<td style='padding:4px 10px;text-align:right'>{u['documents']}</td>"
        f"<td style='padding:4px 0 4px 10px'>{e(u['last_verdict'].title())}</td></tr>"
        for u in rep["by_underlying"]) or "<tr><td colspan='4'>No documents this month.</td></tr>"
    mix = lambda d: " &middot; ".join(f"{e(k.title() if k.isupper() else k)} {v}" for k, v in d.items()) or "&ndash;"
    link = (f"<p style='margin:18px 0 0'><a href='{e(dashboard_url)}' style='color:#FF6C0E;font-weight:700'>"
            f"Open the usage dashboard</a></p>") if dashboard_url else ""
    return f"""<div style="font-family:Nunito,Arial,sans-serif;color:#202945;max-width:620px">
<div style="background:linear-gradient(90deg,#FF6C0E,#FFA400 55%,#FFC545);color:#fff;padding:10px 16px;
border-radius:6px;font-weight:700;letter-spacing:.12em">TECHNICAL TAKES &middot; USAGE {e(month_name.upper())}</div>
<p style="font-size:15px;margin:16px 0 6px"><b>{rep['documents']}</b> documents on <b>{rep['underlyings']}</b>
underlyings ({rep['builds']} builds).</p>
<p style="margin:0 0 4px;color:#4B5F80">Verdicts: {mix(rep['verdicts'])}</p>
<p style="margin:0 0 14px;color:#4B5F80">Data: {mix(rep['data_sources'])}</p>
<table style="border-collapse:collapse;font-size:13px">
<tr style="color:#4B5F80;text-align:left"><th style="padding:4px 10px 4px 0">Ticker</th><th style="padding:4px 10px">Underlying</th>
<th style="padding:4px 10px;text-align:right">Docs</th><th style="padding:4px 0 4px 10px">Last verdict</th></tr>{rows}</table>
{link}
<p style="margin:18px 0 0;font-size:11px;color:#9aa4b5">Documents count once per underlying and document date;
rebuilds are counted as builds. Source: syz-technical-takes usage log.</p></div>"""


def write_provenance(run_dir: Path, prov: dict) -> None:
    (Path(run_dir) / ".audit").mkdir(parents=True, exist_ok=True)
    (Path(run_dir) / ".audit" / "provenance.json").write_text(json.dumps(prov, default=str))


def read_provenance(workbook: str | Path) -> dict | None:
    p = Path(workbook).resolve().parent / "provenance.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return None
