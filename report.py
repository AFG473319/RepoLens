import datetime
import json
from html import escape
from string import Template

import github


# Canonical list of supported report formats. Kept here so report generation,
# the settings/validation layer, the interactive prompt, and the main-loop
# dispatch all read it from this single source of truth.
SUPPORTED_REPORT_FORMATS = ("text", "json", "html")


def generate_text_report(analysis: dict, scores: dict) -> str:
    """Generate a plain text report from analysis and scores.

    Args:
        analysis: Dictionary containing analyzed metrics.
        scores: Dictionary containing calculated scores.

    Returns:
        Formatted text report as a string.
    """
    repo = analysis.get("repo", {})
    commits = analysis.get("commits", {})
    contributors = analysis.get("contributors", {})
    languages = analysis.get("languages", {})
    issues = analysis.get("issues", {})
    if analysis.get("approximate", False):
        limit = github.MAX_PAGES * github.PER_PAGE
        approximate = (
            "\nNote: This report is approximated because one or more GitHub"
            f" endpoints returned more than {limit} results, so counts are"
            " lower bounds.\n"
        )
        truncated_endpoints = ", ".join(analysis.get("truncated_endpoints", []))
        if truncated_endpoints:
            approximate += f"Truncated endpoints: {truncated_endpoints}\n"
    else:
        approximate = ""

    return (
        "RepoLens Analysis Report\n"
        + "=" * 40 + "\n\n"
        + "Repository Info\n"
        + f"  Name: {repo.get('name', 'Unknown')}\n"
        + f"  Description: {repo.get('description', 'No description')}\n"
        + f"  Stars: {repo.get('stars', 0)}\n"
        + f"  Forks: {repo.get('forks', 0)}\n"
        + f"  Language: {repo.get('language', 'Unknown')}\n\n"
        + "Commits\n"
        + f"  Total commits: {commits.get('total_commits', 0)}\n"
        + f"  Unique contributors: {commits.get('unique_contributors', 0)}\n"
        + f"  Latest commit date: {commits.get('latest_commit_date', 'N/A')}\n\n"
        + "Contributors\n"
        + f"  Total contributors: {contributors.get('total_contributors', 0)}\n"
        + f"  Top contributor: {contributors.get('top_contributor', 'N/A')}\n"
        + f"  Most contributions: {contributors.get('most_contributions', 0)}\n\n"
        + "Languages\n"
        + f"  Primary language: {languages.get('primary_language', 'Unknown')}\n"
        + f"  Language count: {languages.get('language_count', 0)}\n\n"
        + "Issues\n"
        + f"  Total issues: {issues.get('total_issues', 0)}\n"
        + f"  Open issues: {issues.get('open_issues', 0)}\n"
        + f"  Closed issues: {issues.get('closed_issues', 0)}\n\n"
        + "Scores\n"
        + f"  Health score: {scores.get('health_score', 0)}\n"
        + f"  Activity score: {scores.get('activity_score', 0)}\n"
        + f"  Community score: {scores.get('community_score', 0)}\n"
        + f"  Maintainability score: {scores.get('maintainability_score', 0)}\n"
        + f"  Grade: {scores.get('grade', 'N/A')}\n"
        + f"{approximate}"
    )


def generate_json_report(analysis: dict, scores: dict) -> str:
    """
    Generate a JSON formatted report.

    Args:
        analysis: Dictionary containing analyzed metrics.
        scores: Dictionary containing calculated scores.

    Returns:
        JSON string of the report.
    """
    data = {
        "analysis": analysis,
        "scores": scores,
        # Always present so consumers of the JSON schema can rely on
        # these keys regardless of which pipeline version produced
        # the analysis payload.
        "approximate": bool(analysis.get("approximate", False)),
        "truncated_endpoints": list(analysis.get("truncated_endpoints", [])),
    }
    return json.dumps(data, indent=4)


def save_report(report_content: str, filename: str) -> None:
    """
    Save a report to a file.

    Args:
        report_content: Report content as a string.
        filename: Output file path.
    """
    with open(filename, "w", encoding="utf-8") as file_handle:
        file_handle.write(report_content)


def print_summary(scores: dict, analysis: dict | None = None) -> None:
    """Print a brief summary of scores to the console.

    Args:
        scores: Dictionary containing calculated scores.
        analysis: Optional analyzed metrics dictionary. When pagination
            was capped ("approximate" is truthy), a warning listing the
            truncated endpoints is printed after the scores so counts
            are not mistaken for exact totals.
    """
    print("Summary")
    print(f"  Health score: {scores.get('health_score')}")
    print(f"  Grade: {scores.get('grade')}")

    if analysis and analysis.get("approximate", False):
        limit = github.MAX_PAGES * github.PER_PAGE
        truncated_endpoints = ", ".join(analysis.get("truncated_endpoints", []))
        message = (
            "\nWarning: counts are approximate because one or more GitHub"
            f" endpoints returned more than {limit} results."
        )
        if truncated_endpoints:
            message += f"\nTruncated endpoints: {truncated_endpoints}"
        print(message)


_GRADE_BANDS = (
    ("F", 0, 60),
    ("D", 60, 70),
    ("C", 70, 80),
    ("B", 80, 90),
    ("A", 90, 101),
)


def _grade_of(score: float) -> str:
    """Map a numeric score to its letter band for rulers and chips."""
    for grade, low, high in _GRADE_BANDS:
        if low <= score < high:
            return grade
    return "F"


def _grade_range(grade: str) -> str:
    """Human-readable score range for a grade, e.g. ``90-100``."""
    for g, low, high in _GRADE_BANDS:
        if g == grade:
            return f"{low}-{high if g != 'A' else 100}"
    return "?"


def _score_chip(score: float) -> str:
    """Build the grade chip span for a health or dimension score."""
    grade = _grade_of(score)
    return (
        f'<span class="chip g-{grade}" '
        f'title="Grade {grade}: {_grade_range(grade)}">{grade}</span>'
    )


def _clamp_percent(value) -> str:
    """Coerce a score to a safe 0-100 CSS percentage string.

    Non-numeric or missing scores become 0 so bars never render
    ``width:None%`` or negative widths.
    """
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(100.0, score))
    return f"{score:g}%"


def _display(value, fallback: str) -> str:
    """Render a possibly-None analysis value for display.

    ``dict.get(key, default)`` only fires when the key is absent, but
    ``analyzer`` emits explicit ``None`` for null GitHub fields — an ``or``
    fallback covers both cases.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return fallback
    return str(value)


def _format_int(value, fallback: str = "0") -> str:
    """Render an integer count with thousands separators."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return fallback


def _score_ruler(label: str, score: float) -> str:
    """Build the expandable grade-ruler detail for one score row."""
    grade = _grade_of(score)
    bands_html = []
    for g, low, high in _GRADE_BANDS:
        hi = " hi" if g == grade else ""
        top = 100 if g == "A" else high
        bands_html.append(
            f'<div class="band{hi}" title="{g}: {low}-{top}">{g}</div>'
        )
    if grade == "A":
        note = f"{score:g} → grade A (90-100) · {100 - score:g} pts of headroom"
    else:
        idx = [b[0] for b in _GRADE_BANDS].index(grade)
        next_grade, next_low = _GRADE_BANDS[idx + 1][0], _GRADE_BANDS[idx + 1][1]
        note = f"{score:g} → grade {grade} ({_grade_range(grade)}) · {next_low - score:g} pts to grade {next_grade}"
    detail_id = f"detail-{label.lower().replace(' ', '-')}"
    escaped_label = escape(label)
    return (
        f'<div class="row-detail" id="{detail_id}" hidden>'
        f'<div class="ruler" role="img" aria-label="{escaped_label} {score:g} of 100, grade {grade}">'
        + "".join(bands_html)
        + f'<div class="marker" data-score="{score:g}" style="left: {score:g}%"></div>'
        "</div>"
        f'<p class="ruler-note">{escape(note)}</p>'
        "</div>"
    )


_HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<style>
  :root {
    --bg: #0a0e1f; --text: #e9ebf8; --muted: #8f96b8;
    --blue: #4f7ce8; --blue-dim: rgba(79,124,232,.14);
    --amber: #FFBF00; --track: #1b2140; --rule: #232a4d;
    --row-hover: rgba(79,124,232,.07);
    --tip-bg: #1c2344; --tip-edge: #35406e; --flash: rgba(255,191,0,.14);
  }
  :root[data-theme="light"] {
    --bg: #f7f8fc; --text: #1a2040; --muted: #5d6480;
    --blue: #2c50b8; --blue-dim: rgba(44,80,184,.10);
    --amber: #b57e00; --track: #e3e7f2; --rule: #d8dded;
    --row-hover: rgba(44,80,184,.06);
    --tip-bg: #fff; --tip-edge: #c4cce4; --flash: rgba(181,126,0,.12);
  }
  .g-A { --fg: #4ed07e; --fill: #2fbf63; }
  .g-B { --fg: #3fb6dd; --fill: #2196c4; }
  .g-C { --fg: #e8b23a; --fill: #e0a010; }
  .g-D { --fg: #f0813c; --fill: #e0722a; }
  .g-F { --fg: #ef6a6a; --fill: #e04848; }
  .g-Neutral { --fg: #8f96b8; --fill: #8f96b8; }
  :root[data-theme="light"] .g-A { --fg: #1a7f37; }
  :root[data-theme="light"] .g-B { --fg: #0a6478; }
  :root[data-theme="light"] .g-C { --fg: #8a5300; }
  :root[data-theme="light"] .g-D { --fg: #ad3d00; }
  :root[data-theme="light"] .g-F { --fg: #c2272c; }
  :root { color-scheme: dark; scroll-behavior: smooth; }
  :root[data-theme="light"] { color-scheme: light; }
  *, *::before, *::after { box-sizing: border-box; }
  body { margin: 0 auto; max-width: 780px; padding: 0 1.25rem 3rem;
    background: var(--bg); color: var(--text);
    font-family: system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
    line-height: 1.6; }
  h1, h2, h3, p, ul { margin: 0; }
  .topline { position: sticky; top: 0; z-index: 10; margin: 0 -1.25rem; padding: .7rem 1.25rem;
    display: flex; align-items: center; gap: .9rem; font-size: .8rem; color: var(--muted);
    letter-spacing: .03em; background: color-mix(in srgb, var(--bg) 82%, transparent);
    backdrop-filter: blur(8px); border-bottom: 1px solid var(--rule); }
  .topline .dot { width: .55rem; height: .55rem; border-radius: 50%; background: var(--amber);
    flex: none; animation: pulse 2.4s ease-in-out infinite; }
  @keyframes pulse { 0%,100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--amber) 45%, transparent); }
    50% { box-shadow: 0 0 0 5px transparent; } }
  .topline .path { color: var(--blue); }
  .topline .nav { margin-left: auto; display: flex; gap: .9rem; }
  .topline .nav a { color: var(--muted); text-decoration: none; padding: .1rem 0;
    border-bottom: 1px solid transparent; }
  .topline .nav a:hover { color: var(--blue); }
  .topline .nav a.active { color: var(--amber); border-bottom-color: var(--amber); }
  .progress { position: absolute; left: 0; bottom: -1px; height: 2px; width: 0;
    background: linear-gradient(90deg, var(--blue), var(--amber)); transition: width .08s linear; }
  .btn { all: unset; cursor: pointer; padding: .15rem .55rem; border: 1px solid var(--rule);
    border-radius: 6px; color: var(--muted); font-size: .78rem; }
  .btn:hover { color: var(--amber); border-color: var(--amber); }
  .btn:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }
  .btn.done { color: #4ed07e; border-color: #2fbf63; }
  .hero { padding: 2.2rem 0 1.6rem; border-bottom: 1px solid var(--rule); scroll-margin-top: 3.4rem; }
  .hero h1 { font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;
    font-size: clamp(1.5rem,3.4vw,2rem); letter-spacing: -.01em; }
  .hero h1 .owner { color: var(--muted); font-weight: 600; }
  .hero h1 .sep { color: var(--blue); font-weight: 700; }
  .hero-desc { margin-top: .4rem; color: var(--muted); max-width: 62ch; }
  .hero-meta { margin-top: .6rem; font-size: .78rem; color: var(--muted); }
  .health { margin-top: 1.5rem; }
  .health-caption { font-size: .7rem; font-weight: 700; color: var(--muted);
    text-transform: uppercase; letter-spacing: .12em; }
  .health-row { display: flex; align-items: baseline; gap: .9rem; margin: .35rem 0 .6rem; }
  .health-num { color: var(--amber); font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;
    font-size: clamp(2.6rem,6vw,3.4rem); font-weight: 700; line-height: 1;
    font-variant-numeric: tabular-nums; }
  .health-num .of { color: var(--muted); font-size: 38%; font-weight: 500; }
  .chip { display: inline-flex; align-items: center; justify-content: center; min-width: 2rem;
    height: 2rem; padding: 0 .55rem; color: var(--fg); border: 1px solid var(--fill);
    border-radius: 6px; background: color-mix(in srgb, var(--fill) 14%, transparent);
    font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace; font-weight: 700; font-size: .95rem; }
  .bar { height: .5rem; background: var(--track); border-radius: 3px; overflow: hidden; }
  .bar > span { display: block; height: 100%; width: 0; background: var(--fill, var(--blue));
    transition: width .9s cubic-bezier(.25,.8,.3,1); transition-delay: var(--d, 0s); }
  .bar.hero-bar { max-width: 430px; height: .7rem; }
  section { scroll-margin-top: 3.4rem; }
  section + section { border-top: 1px solid var(--rule); }
  details { padding: 1.15rem 0 1.4rem; }
  summary { list-style: none; cursor: pointer; user-select: none; display: flex;
    align-items: center; gap: .55rem; font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;
    font-size: .8rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
    color: var(--amber); }
  summary::-webkit-details-marker { display: none; }
  summary:focus-visible { outline: 2px solid var(--blue); outline-offset: 4px; border-radius: 2px; }
  summary .tick { color: var(--blue); }
  summary::after { content: "+"; margin-left: auto; color: var(--muted); font-weight: 400;
    font-size: 1rem; transition: transform .2s ease; }
  details[open] summary::after { content: "\\2212"; }
  .score-list { margin-top: 1.1rem; display: grid; gap: .15rem; }
  .score-item + .score-item { border-top: 1px solid var(--rule); }
  .score-row { all: unset; cursor: pointer; user-select: none; display: grid;
    grid-template-columns: 10rem 1fr 4.6rem 2.2rem; align-items: center; gap: 1rem;
    padding: .55rem .5rem; border-radius: 6px; width: 100%; }
  .score-row:hover { background: var(--row-hover); }
  .score-row:focus-visible { outline: 2px solid var(--blue); outline-offset: -2px; }
  .score-row .label { font-size: .92rem; font-weight: 600; }
  .score-row .num { color: var(--fg); font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;
    font-size: .95rem; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums;
    white-space: nowrap; }
  .score-row .num .of { color: var(--muted); font-weight: 500; font-size: .8rem; }
  .score-row .chip { min-width: 1.7rem; height: 1.7rem; font-size: .8rem; }
  .row-detail { padding: .4rem .5rem .9rem; }
  .row-detail[hidden] { display: none; }
  .ruler { position: relative; display: flex; height: 1.5rem; border-radius: 4px;
    overflow: hidden; max-width: 430px; border: 1px solid var(--rule); }
  .ruler .band { display: flex; align-items: center; justify-content: center;
    font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace; font-size: .62rem;
    font-weight: 700; letter-spacing: .06em; color: var(--muted); background: var(--track); }
  .ruler .band + .band { border-left: 1px solid var(--rule); }
  .ruler .band.hi { color: var(--text); background: var(--blue-dim); }
  .ruler .band.f { width: 60%; }
  .ruler .band.d, .ruler .band.c, .ruler .band.b, .ruler .band.a { width: 10%; }
  .ruler .marker { position: absolute; top: -3px; bottom: -3px; width: 2px;
    background: var(--amber); border-radius: 2px; left: 0;
    transition: left .7s cubic-bezier(.25,.8,.3,1); }
  .ruler-note { margin-top: .4rem; font-size: .78rem; color: var(--muted);
    font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace; }
  .metrics { margin-top: 1.1rem; }
  .search-wrap { margin-bottom: .7rem; display: flex; align-items: center; gap: .5rem; }
  .search { all: unset; flex: 1; max-width: 320px; padding: .32rem .65rem;
    border: 1px solid var(--rule); border-radius: 6px; font-size: .82rem; color: var(--text);
    background: color-mix(in srgb, var(--track) 55%, transparent); }
  .search:focus-visible { outline: none; border-color: var(--blue);
    box-shadow: 0 0 0 2px var(--blue-dim); }
  .search::placeholder { color: var(--muted); }
  .search-kbd { font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;
    font-size: .68rem; color: var(--muted); border: 1px solid var(--rule);
    border-radius: 4px; padding: .05rem .35rem; }
  .metrics .row { display: grid; grid-template-columns: 13rem 1fr auto; gap: 1rem;
    padding: .5rem .5rem; border-radius: 6px; cursor: pointer; }
  .metrics .row:hover { background: var(--row-hover); }
  .metrics .row.copied { background: var(--flash); }
  .metrics .row + .row { border-top: 1px solid var(--rule); }
  .metrics .row.filtered + .row { border-top: none; }
  .metrics .k { color: var(--muted); font-size: .9rem; }
  .metrics .v { font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
  .metrics .copy-tag { font-size: .68rem; color: var(--muted); opacity: 0;
    font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace; align-self: center; }
  .metrics .row:hover .copy-tag { opacity: .7; }
  .metrics .row.copied .copy-tag { opacity: 1; color: #4ed07e; }
  .no-match { padding: .7rem .5rem; color: var(--muted); font-size: .85rem; font-style: italic; }
  .limits-body { margin-top: 1rem; padding-left: 1rem; border-left: 3px solid var(--amber); }
  .limits-body .limit-title { font-weight: 700; }
  .limits-body p + p { margin-top: .35rem; color: var(--muted); }
  .overlay { position: fixed; inset: 0; z-index: 50; display: flex; align-items: center;
    justify-content: center; background: rgba(4,6,18,.62); backdrop-filter: blur(3px); }
  .overlay[hidden] { display: none; }
  .kbd-panel { width: min(420px, calc(100vw - 2.5rem)); background: var(--tip-bg);
    border: 1px solid var(--tip-edge); border-radius: 10px; padding: 1.2rem 1.4rem 1rem;
    box-shadow: 0 12px 40px rgba(0,0,0,.5); }
  .kbd-panel h3 { font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace;
    font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; color: var(--amber);
    margin-bottom: .8rem; }
  .kbd-panel table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  .kbd-panel td { padding: .28rem 0; }
  .kbd-panel td:last-child { text-align: right; color: var(--muted); }
  kbd { font-family: ui-monospace,"Cascadia Mono",Consolas,Menlo,monospace; font-size: .72rem;
    border: 1px solid var(--tip-edge); border-bottom-width: 2px; border-radius: 4px;
    padding: .08rem .4rem; background: color-mix(in srgb, var(--track) 60%, transparent); }
  .kbd-hint { text-align: center; font-size: .75rem; color: var(--muted); margin-top: .9rem; }
  .page-foot { margin-top: 2.2rem; padding-top: 1rem; border-top: 1px solid var(--rule);
    text-align: center; font-size: .78rem; color: var(--muted); }
  @media (max-width: 560px) {
    .score-row { grid-template-columns: 6.4rem 1fr 4.2rem 1.9rem; gap: .6rem; }
    .metrics .row { grid-template-columns: 9rem 1fr auto; }
    .topline .nav { display: none; } }
  @media print {
    :root { --bg: #fff; --text: #111; --muted: #555; --blue: #2c50b8; --amber: #7a5b00;
      --track: #e5e5e5; --rule: #ccc; --row-hover: transparent; --flash: transparent; }
    body { max-width: none; }
    .topline { position: static; backdrop-filter: none; background: none;
      border-bottom: 1px solid #ccc; }
    .topline .nav, .btn, .progress, .search-wrap, .copy-tag { display: none !important; }
    .bar > span { transition: none; width: var(--w) !important; }
    .ruler .marker { transition: none; }
    .health-num, .score-row .num { color: #000; } }
</style>
</head>
<body>
<div class="topline">
  <span class="dot"></span><span>repolens</span><span class="path">$crumb</span>
  <nav class="nav">
    <a href="#scores" data-spy="scores">scores</a>
    <a href="#metrics" data-spy="metrics">metrics</a>
    <a href="#limits" data-spy="limits">limits</a>
  </nav>
  <button class="btn" id="copy-summary" type="button">copy summary</button>
  <button class="btn" id="theme-toggle" type="button" aria-label="Toggle color theme">☾ light</button>
  <div class="progress" id="progress"></div>
</div>
<header class="hero">
<h1><span class="owner">$owner</span><span class="sep">&gt;</span> <span class="repo-name">$repo</span></h1>
<p class="hero-desc">$description</p>
<p class="hero-meta mono">$generated</p>
<div class="health">
<p class="health-caption">Overall health score</p>
<div class="health-row">
<p class="health-num"><span class="value" data-count="$health">$health</span><span class="of">/100</span></p>
$health_chip
</div>
<div class="bar hero-bar"><span class="$health_cls" style="--w: $health_pct"></span></div>
</div>
</header>
<main>
<section id="scores" aria-labelledby="h-scores">
<details open id="sec-scores">
<summary id="h-scores"><span class="tick">//</span> scores</summary>
<div class="score-list">
$score_rows
</div>
</details>
</section>
<section id="metrics" aria-labelledby="h-metrics">
<details open id="sec-metrics">
<summary id="h-metrics"><span class="tick">//</span> metrics</summary>
<div class="metrics">
<div class="search-wrap">
<input class="search" id="metric-search" type="search" placeholder="filter metrics…" aria-label="Filter metrics">
<span class="search-kbd">/</span>
</div>
<div class="metrics-list" id="metrics-list">
$metric_rows
</div>
<div class="no-match" id="no-match" hidden>no metrics match this filter</div>
</div>
</details>
</section>
<section id="limits" aria-labelledby="h-limits">
<details open id="sec-limits">
<summary id="h-limits"><span class="tick">//</span> data &amp; limitations</summary>
<div class="limits-body">
$limits_body
</div>
</details>
</section>
</main>
<footer class="page-foot">Generated by RepoLens · press <kbd>?</kbd> for shortcuts</footer>
<div class="overlay" id="kbd-overlay" hidden>
<div class="kbd-panel" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts">
<h3>// keyboard shortcuts</h3>
<table><tbody>
<tr><td><kbd>s</kbd></td><td>jump to scores</td></tr>
<tr><td><kbd>m</kbd></td><td>jump to metrics</td></tr>
<tr><td><kbd>l</kbd></td><td>jump to limitations</td></tr>
<tr><td><kbd>j</kbd> / <kbd>k</kbd></td><td>next / previous section</td></tr>
<tr><td><kbd>/</kbd></td><td>focus metric filter</td></tr>
<tr><td><kbd>c</kbd></td><td>copy summary</td></tr>
<tr><td><kbd>t</kbd></td><td>toggle theme</td></tr>
<tr><td><kbd>esc</kbd></td><td>close / clear filter</td></tr>
</tbody></table>
<p class="kbd-hint">press <kbd>esc</kbd> or click outside to close</p>
</div>
</div>
<script>
(function () {
  "use strict";
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var root = document.documentElement;
  var store = {
    get: function (k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { window.localStorage.setItem(k, v); } catch (e) {} }
  };
  var themeBtn = document.getElementById("theme-toggle");
  function applyTheme(t) { root.setAttribute("data-theme", t);
    themeBtn.textContent = t === "light" ? "\\u2600 dark" : "\\u263e light"; }
  var saved = store.get("repolens-theme");
  if (saved === "light" || saved === "dark") applyTheme(saved);
  else if (window.matchMedia("(prefers-color-scheme: light)").matches) applyTheme("light");
  function toggleTheme() { var n = root.getAttribute("data-theme") === "light" ? "dark" : "light";
    applyTheme(n); store.set("repolens-theme", n); }
  themeBtn.addEventListener("click", toggleTheme);
  ["sec-scores", "sec-metrics", "sec-limits"].forEach(function (id) {
    var el = document.getElementById(id); if (!el) return;
    if (store.get("repolens-" + id) === "closed") el.removeAttribute("open");
    el.addEventListener("toggle", function () {
      store.set("repolens-" + id, el.hasAttribute("open") ? "open" : "closed"); });
  });
  var progress = document.getElementById("progress");
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".nav a[data-spy]"));
  var sections = ["scores", "metrics", "limits"].map(function (id) { return document.getElementById(id); });
  function nearBottom() { var d = document.documentElement;
    return window.innerHeight + window.scrollY >= d.scrollHeight - 4; }
  function onScroll() { var d = document.documentElement;
    var max = d.scrollHeight - window.innerHeight;
    progress.style.width = (max > 0 ? (window.scrollY / max) * 100 : 0) + "%";
    var current = null;
    for (var i = 0; i < sections.length; i++) {
      if (sections[i] && sections[i].getBoundingClientRect().top <= window.innerHeight * 0.4) current = sections[i].id; }
    if (nearBottom() && sections.length) current = sections[sections.length - 1].id;
    navLinks.forEach(function (a) { a.classList.toggle("active", a.getAttribute("data-spy") === current); }); }
  window.addEventListener("scroll", onScroll, { passive: true }); onScroll();
  function countUp(el) { var t = parseFloat(el.getAttribute("data-count"));
    var dec = parseInt(el.getAttribute("data-decimals") || "0", 10);
    if (isNaN(t)) return;
    if (reducedMotion) { el.textContent = t.toFixed(dec); return; }
    var start = null, dur = 900;
    function step(ts) { if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1); var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = (t * eased).toFixed(dec);
      if (p < 1) requestAnimationFrame(step); }
    requestAnimationFrame(step); }
  function growBar(bar) { bar.style.width = bar.style.getPropertyValue("--w"); }
  var revealables = [];
  document.querySelectorAll(".bar > span").forEach(function (b) { revealables.push({ el: b, kind: "bar" }); });
  document.querySelectorAll("[data-count]").forEach(function (e) { revealables.push({ el: e, kind: "count" }); });
  if ("IntersectionObserver" in window && !reducedMotion) {
    var seen = new WeakSet();
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting || seen.has(entry.target)) return;
        seen.add(entry.target);
        var item = revealables.filter(function (r) { return r.el === entry.target; })[0];
        if (!item) return;
        if (item.kind === "bar") growBar(entry.target); else countUp(entry.target);
        io.unobserve(entry.target); });
    }, { threshold: 0.4 });
    revealables.forEach(function (r) { io.observe(r.el); });
  } else { revealables.forEach(function (r) { r.kind === "bar" ? growBar(r.el) : countUp(r.el); }); }
  document.querySelectorAll(".score-row").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var detail = document.getElementById(btn.getAttribute("aria-controls"));
      var open = detail.hasAttribute("hidden");
      detail.toggleAttribute("hidden", !open);
      btn.setAttribute("aria-expanded", String(open));
      if (open && !reducedMotion) { var m = detail.querySelector(".marker");
        if (m) { m.style.left = "0%";
          requestAnimationFrame(function () { requestAnimationFrame(function () {
            m.style.left = m.getAttribute("data-score") + "%"; }); }); } } });
  });
  var search = document.getElementById("metric-search");
  var rows = Array.prototype.slice.call(document.querySelectorAll("#metrics-list .row"));
  var noMatch = document.getElementById("no-match");
  function applyFilter() { var q = search.value.trim().toLowerCase(); var visible = 0;
    rows.forEach(function (row) { var show = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
      row.hidden = !show; if (show) visible++; });
    noMatch.hidden = visible > 0; }
  search.addEventListener("input", applyFilter);
  search.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { search.value = ""; applyFilter(); search.blur(); } });
  function copyText(text, done) {
    function fallback() { var ta = document.createElement("textarea"); ta.value = text;
      ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta);
      ta.select(); try { document.execCommand("copy"); done(); } catch (e) {}
      document.body.removeChild(ta); }
    if (navigator.clipboard && navigator.clipboard.writeText)
      navigator.clipboard.writeText(text).then(done, fallback);
    else fallback(); }
  rows.forEach(function (row) {
    row.addEventListener("click", function () {
      copyText(row.getAttribute("data-value") || row.querySelector(".v").textContent, function () {
        row.classList.add("copied");
        var tag = row.querySelector(".copy-tag"); if (tag) tag.textContent = "copied \\u2713";
        setTimeout(function () { row.classList.remove("copied");
          if (tag) tag.textContent = "click to copy"; }, 1100); }); });
  });
  var copyBtn = document.getElementById("copy-summary");
  function summaryText() { var h1 = document.querySelector(".hero h1");
    var health = document.querySelector(".health-num .value").textContent;
    var grade = document.querySelector(".health-row .chip").textContent;
    var dims = Array.prototype.slice.call(document.querySelectorAll(".score-row")).map(function (r) {
      return r.querySelector(".label").textContent + " " +
        r.querySelector(".num").textContent.replace("/100", "").trim(); }).join(" \\u00b7 ");
    var stars = rows[0] ? rows[0].querySelector(".v").textContent : "";
    var issues = rows[rows.length - 1] ? rows[rows.length - 1].querySelector(".v").textContent : "";
    return ["RepoLens \\u2014 " + h1.querySelector(".owner").textContent + "/" + h1.querySelector(".repo-name").textContent,
      "Health " + health + "/100 (" + grade + ")", dims,
      "Stars " + stars + " · Issues " + issues,
      document.querySelector(".hero-meta").textContent].join("\\n"); }
  copyBtn.addEventListener("click", function () {
    copyText(summaryText(), function () { copyBtn.textContent = "\\u2713 copied";
      copyBtn.classList.add("done");
      setTimeout(function () { copyBtn.textContent = "copy summary";
        copyBtn.classList.remove("done"); }, 1300); }); });
  var overlay = document.getElementById("kbd-overlay");
  var ORDER = ["scores", "metrics", "limits"];
  function jumpTo(id) { var el = document.getElementById(id); if (!el) return;
    var det = el.querySelector("details") || (el.matches("details") ? el : null);
    if (det) det.setAttribute("open", "");
    el.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" }); }
  function currentIdx() { if (nearBottom()) return ORDER.length - 1; var idx = 0;
    ORDER.forEach(function (id, i) { var el = document.getElementById(id);
      if (el && el.getBoundingClientRect().top <= window.innerHeight * 0.4) idx = i; });
    return idx; }
  document.addEventListener("keydown", function (e) {
    var typing = e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA");
    if (e.key === "Escape") { if (!overlay.hidden) { overlay.hidden = true; return; }
      if (typing) { e.target.value = ""; applyFilter(); e.target.blur(); } return; }
    if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
    switch (e.key) {
      case "s": jumpTo("scores"); break;
      case "m": jumpTo("metrics"); break;
      case "l": jumpTo("limits"); break;
      case "j": jumpTo(ORDER[Math.min(currentIdx() + 1, ORDER.length - 1)]); break;
      case "k": jumpTo(ORDER[Math.max(currentIdx() - 1, 0)]); break;
      case "/": e.preventDefault(); search.focus(); break;
      case "t": toggleTheme(); break;
      case "c": copyBtn.click(); break;
      case "?": overlay.hidden = false; break; } });
  overlay.addEventListener("click", function (e) { if (e.target === overlay) overlay.hidden = true; });
})();
</script>
</body>
</html>
""")


def generate_html_report(owner: str, repo_name: str, analysis: dict, scores: dict) -> str:
    """Generate a self-contained interactive HTML report.

    The output is a single file with inline CSS/JS and no external
    requests, so it renders identically offline. Every repo-sourced
    string is HTML-escaped before interpolation.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo_name: Repository name.
        analysis: Dictionary containing analyzed metrics.
        scores: Dictionary containing calculated scores.

    Returns:
        Formatted HTML report as a string.
    """
    repo = analysis.get("repo") or {}
    commits = analysis.get("commits") or {}
    contributors = analysis.get("contributors") or {}
    languages = analysis.get("languages") or {}
    issues = analysis.get("issues") or {}

    description = _display(repo.get("description"), "No description")

    def _label(value, fallback: str) -> str:
        """Render the owner/repo label, stripping whitespace.

        Blank or non-string values fall back to the placeholder so the
        hero never renders an empty label or a value the user did not
        supply.
        """
        if isinstance(value, str) and value.strip():
            return value.strip()
        return fallback

    owner = _label(owner, "Unknown")
    repo_label = _label(repo_name, "Unknown")

    def score_value(key) -> float:
        try:
            return max(0.0, min(100.0, float(scores.get(key))))
        except (TypeError, ValueError):
            return 0.0

    health = score_value("health_score")
    dimensions = [
        ("Activity", score_value("activity_score")),
        ("Community", score_value("community_score")),
        ("Maintainability", score_value("maintainability_score")),
    ]

    score_rows = []
    for i, (label, value) in enumerate(dimensions):
        grade = _grade_of(value)
        score_rows.append(
            '<div class="score-item">'
            f'<button class="score-row" type="button" aria-expanded="false" '
            f'aria-controls="detail-{label.lower().replace(" ", "-")}">'
            f'<span class="label">{escape(label)}</span>'
            f'<span class="bar"><span class="g-{grade}" '
            f'style="--w: {value:g}%; --d: {0.1 * (i + 1):.1f}s"></span></span>'
            f'<span class="num g-{grade}"><span data-count="{value:g}" '
            f'data-decimals="1">{value:.1f}</span><span class="of">/100</span></span>'
            + _score_chip(value)
            + "</button>"
            + _score_ruler(label, value)
            + "</div>"
        )

    top_contributor = _display(contributors.get("top_contributor"), "N/A")
    metric_values = [
        ("Stars", _format_int(repo.get("stars"))),
        ("Forks", _format_int(repo.get("forks"))),
        ("Primary language", _display(repo.get("language"), "Unknown")),
        ("Languages used", _format_int(languages.get("language_count"))),
        ("Total commits", _format_int(commits.get("total_commits"))),
        ("Unique commit authors", _format_int(commits.get("unique_contributors"))),
        ("Latest commit", _display(commits.get("latest_commit_date"), "N/A")),
        ("Total contributors", _format_int(contributors.get("total_contributors"))),
        ("Top contributor", f"{top_contributor} "
         f"({_format_int(contributors.get('most_contributions'))} contributions)"),
        ("Issues", f"{_format_int(issues.get('total_issues'))} total · "
                   f"{_format_int(issues.get('open_issues'))} open · "
                   f"{_format_int(issues.get('closed_issues'))} closed"),
    ]
    metric_rows = []
    for label, value in metric_values:
        metric_rows.append(
            f'<div class="row" data-value="{escape(value, quote=True)}">'
            f'<span class="k">{escape(label)}</span>'
            f'<span class="v">{escape(value)}</span>'
            f'<span class="copy-tag">click to copy</span></div>'
        )

    if analysis.get("approximate", False):
        limit = github.MAX_PAGES * github.PER_PAGE
        truncated = ", ".join(
            escape(str(endpoint)) for endpoint in analysis.get("truncated_endpoints", [])
        )
        limits_body = (
            '<p class="limit-title">Some counts are approximate lower bounds</p>'
            f"<p>One or more GitHub endpoints returned more than {limit:,} results; "
            "deeper history was not fetched."
            + (f" Truncated endpoints: {truncated}." if truncated else "")
            + "</p>"
        )
    else:
        limits_body = '<p>No pagination truncation detected — all counts are exact.</p>'

    raw_grade = scores.get("grade")
    if not (isinstance(raw_grade, str) and raw_grade.strip().upper() in {"A", "B", "C", "D", "F"}):
        raw_grade = None
    health_grade = raw_grade.upper() if raw_grade else _grade_of(health)
    health_cls = f"g-{health_grade}" if health_grade else "g-Neutral"

    generated = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    return _HTML_TEMPLATE.substitute(
        title=escape(f"RepoLens Report — {owner}/{repo_label}"),
        crumb=escape(f"~/report/{owner}/{repo_label}"),
        owner=escape(owner),
        repo=escape(repo_label),
        description=escape(description),
        generated=f"generated {generated}",
        health=f"{health:.1f}",
        health_chip=_score_chip(health),
        health_cls=health_cls,
        health_pct=_clamp_percent(scores.get("health_score")),
        score_rows="\n".join(score_rows),
        metric_rows="\n".join(metric_rows),
        limits_body=limits_body,
    )


# Data-driven dispatch: each supported format maps to a generator callable
# and the file extension used when saving the report. The adapters keep the
# registry's common call signature without hiding the behavior in lambdas.
def _generate_text_report(owner: str, repo: str, analysis: dict, scores: dict) -> str:
    return generate_text_report(analysis, scores)


def _generate_json_report(owner: str, repo: str, analysis: dict, scores: dict) -> str:
    return generate_json_report(analysis, scores)


REPORT_FORMAT_GENERATORS = {
    "text": (_generate_text_report, ".txt"),
    "json": (_generate_json_report, ".json"),
    "html": (generate_html_report, ".html"),
}
