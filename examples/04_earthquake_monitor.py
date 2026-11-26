"""Earthquake monitor — a real pipeline on live data, end to end.

    ┌────────────► by_band ────────┐
    │             by_hour          │
fetch ────────► largest ────────► report ──► reports/earthquakes.md
    └────────────► top_felt ───────┘

Fetches every M >= 2.5 earthquake on Earth in the last ``hours`` hours
from the USGS real-time Feed API, fans the events out to four parallel
aggregations, and renders a markdown report.

The data is real and updates by the minute; USGS needs no API key, which
keeps the zero-dependency promise intact (plain ``urllib`` from the
standard library).

Run it from the repo root::

    python -m pipedream run examples/04_earthquake_monitor.py

Override the window or threshold::

    python -m pipedream run examples/04_earthquake_monitor.py \\
        --param hours=24 --param min_magnitude=4.0
"""

import json
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipedream import Pipeline, step
from pipedream.render import markdown_table

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USER_AGENT = "pipedream-earthquake-monitor/0.1 (github.com/frenals/PipeDream)"

# Magnitude bands: label, lower bound (inclusive), upper bound (exclusive).
# Anything below 2.5 is excluded by the query itself.
BANDS = [
    ("M 6.0+   (strong)", 6.0, float("inf")),
    ("M 5.0-5.9 (moderate)", 5.0, 6.0),
    ("M 4.0-4.9 (light)", 4.0, 5.0),
    ("M 2.5-3.9 (minor)", 2.5, 4.0),
]


def _fetch_window_hours(ctx):
    """CLI params arrive as strings; coerce with a sane fallback."""
    try:
        return float(ctx.params.get("hours", 24))
    except (TypeError, ValueError):
        return 24.0


@step(retries=3, retry_delay=1.0, backoff=2.0, cache=False)
def fetch(ctx):
    """Extract: live M >= 2.5 quakes from the USGS Feed API.

    Retries three times with exponential backoff — a monitoring pipeline
    that dies on the first network hiccup is not a pipeline. Caching is
    off: the outside world changes even when this function's code doesn't.
    """
    hours = _fetch_window_hours(ctx)
    try:
        min_mag = float(ctx.params.get("min_magnitude", 2.5))
    except (TypeError, ValueError):
        min_mag = 2.5
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = (
        f"{USGS_URL}?format=geojson"
        f"&starttime={start.strftime('%Y-%m-%dT%H:%M:%S')}"
        f"&minmagnitude={min_mag}"
    )
    request = urllib.request.Request(query, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    events = []
    for feature in payload["features"]:
        props = feature["properties"]
        lon, lat, depth_km = feature["geometry"]["coordinates"]
        events.append({
            "id": feature["id"],
            "mag": props["mag"] if props["mag"] is not None else 0.0,
            "place": props.get("place") or "unknown region",
            "time_ms": props["time"],
            "felt": props.get("felt") or 0,
            "tsunami": bool(props.get("tsunami")),
            "depth_km": round(depth_km, 1),
            "lat": round(lat, 2),
            "lon": round(lon, 2),
            "url": props.get("url") or "https://earthquake.usgs.gov/",
        })
    events.sort(key=lambda e: e["time_ms"], reverse=True)  # newest first
    return events


@step(depends_on=["fetch"])
def by_band(ctx, fetch):
    """Aggregate: event count and strongest quake per magnitude band."""
    rows = []
    for label, lo, hi in BANDS:
        in_band = [e for e in fetch if lo <= e["mag"] < hi]
        strongest = max(in_band, key=lambda e: e["mag"]) if in_band else None
        rows.append({
            "band": label.strip(),
            "count": len(in_band),
            "strongest": (strongest["mag"], strongest["place"]) if strongest
            else None,
        })
    return rows


@step(depends_on=["fetch"])
def by_hour(ctx, fetch):
    """Aggregate: quakes per UTC hour — a histogram of the window."""
    counts = Counter(
        datetime.fromtimestamp(e["time_ms"] / 1000, tz=timezone.utc)
        .strftime("%m-%d %H:00")
        for e in fetch
    )
    return sorted(counts.items())  # [(hour_label, count)] oldest first


@step(depends_on=["fetch"])
def largest(ctx, fetch):
    """Aggregate: the strongest quake in the window, with details."""
    if not fetch:
        return None
    return max(fetch, key=lambda e: e["mag"])


@step(depends_on=["fetch"])
def top_felt(ctx, fetch):
    """Aggregate: the quake most reported as felt by people nearby."""
    felt = [e for e in fetch if e["felt"]]
    if not felt:
        return None
    return max(felt, key=lambda e: e["felt"])


@step(depends_on=["by_band", "by_hour", "largest", "top_felt"], cache=False)
def report(ctx, by_band, by_hour, largest, top_felt):
    """Report: render markdown, print it, and persist it to disk.

    Caching is off: the report carries a generation timestamp and must
    be rewritten on every run.
    """
    now = datetime.now(timezone.utc)
    hours = _fetch_window_hours(ctx)
    total = sum(row["count"] for row in by_band)
    peak = max((count for _, count in by_hour), default=0)
    lines = [
        "# Earthquake monitor",
        "",
        f"Every earthquake on Earth of magnitude 2.5 or greater in the "
        f"last {hours:g} hours, straight from the USGS real-time Feed API.",
        "",
        markdown_table(["generated (UTC)", "events", "busiest hour"], [[
            now.strftime("%Y-%m-%d %H:%M"),
            total,
            f"{peak} quakes" if peak else "-",
        ]]),
        "",
        "## By magnitude band",
        "",
        markdown_table(["band", "events", "strongest"], [
            [row["band"], row["count"],
             f"M {row['strongest'][0]:.1f} — {row['strongest'][1]}"
             if row["strongest"] else "-"]
            for row in by_band
        ]),
        "",
        "## Events per UTC hour",
        "",
        markdown_table(["hour (UTC)", "events", "histogram"], [
            [hour, count, "\u2588" * count] for hour, count in by_hour
        ]),
        "",
        "## Strongest quake in the window",
        "",
    ]
    if largest:
        lines += [
            markdown_table(["field", "value"], [
                ["magnitude", f"M {largest['mag']:.1f}"],
                ["where", largest["place"]],
                ["when (UTC)", datetime.fromtimestamp(
                    largest["time_ms"] / 1000, tz=timezone.utc,
                ).strftime("%Y-%m-%d %H:%M:%S")],
                ["depth", f"{largest['depth_km']} km"],
                ["coordinates", f"{largest['lat']}, {largest['lon']}"],
                ["tsunami flag", "yes" if largest["tsunami"] else "no"],
            ]),
            "",
            f"[USGS event page]({largest['url']})",
        ]
    else:
        lines.append("_No events in the window._")

    lines += ["", "## Most reported as felt", ""]
    if top_felt:
        lines += [
            markdown_table(["field", "value"], [
                ["magnitude", f"M {top_felt['mag']:.1f}"],
                ["where", top_felt["place"]],
                ["felt by", f"{top_felt['felt']} people"],
                ["when (UTC)", datetime.fromtimestamp(
                    top_felt["time_ms"] / 1000, tz=timezone.utc,
                ).strftime("%Y-%m-%d %H:%M:%S")],
            ]),
            "",
            f"[USGS event page]({top_felt['url']})",
        ]
    else:
        lines.append("_No felt reports in the window._")

    lines += [
        "",
        "---",
        "Gathered by [PipeDream](https://github.com/frenals/PipeDream) "
        "from the [USGS Feed API](https://earthquake.usgs.gov/fdsnws/event/1/). "
        "Refreshed every 12 hours by GitHub Actions.",
        "",
    ]
    text = "\n".join(lines)

    print(text)
    out = Path(ctx.params.get("report_path", "reports/earthquakes.md"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"\nreport written to {out}")
    return text


pipeline = Pipeline(
    "earthquake-monitor",
    [fetch, by_band, by_hour, largest, top_felt, report],
    description="live global earthquake activity from the USGS Feed API",
    params={"hours": 24, "min_magnitude": 2.5},
)
