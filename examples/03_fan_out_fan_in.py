"""Fan-out / fan-in — watch independent steps run in parallel.

    fetch ──┬──► aggregate_Nairobi ───────┐
            ├──► aggregate_Lagos ─────────┤
            ├──► aggregate_Cairo ─────────┼──► combine
            └──► aggregate_Johannesburg ──┘

Run it, then try ``--serial`` and compare the wall time::

    python -m pipedream run examples/03_fan_out_fan_in.py
    python -m pipedream run examples/03_fan_out_fan_in.py --serial
"""

import time

from pipedream import Pipeline, step
from pipedream.data import generate_customers, generate_sales
from pipedream.render import markdown_table

REGIONS = ("Nairobi", "Lagos", "Cairo", "Johannesburg")
API_LATENCY = 0.3  # simulated per-region API round trip, seconds


@step(cache=False)
def fetch(ctx):
    """Extract: pull the raw order feed (simulated slow I/O)."""
    time.sleep(0.25)
    customers = generate_customers(300, seed=3)
    return generate_sales(customers, seed=5)


def _region_aggregate(region):
    @step(name=f"aggregate_{region}", depends_on=["fetch"], cache=False,
          tags=(region,))
    def _aggregate(ctx, fetch):
        # `fetch` here is the *result* of the fetch step (the order list).
        time.sleep(API_LATENCY)  # pretend we called a regional API
        rows = [order for order in fetch if order["region"] == region]
        revenue = sum(order["amount_usd"] for order in rows)
        return {
            "region": region,
            "orders": len(rows),
            "revenue": round(revenue, 2),
            "avg_order": round(revenue / len(rows), 2) if rows else 0.0,
        }

    return _aggregate


@step(name="combine", depends_on=[f"aggregate_{r}" for r in REGIONS],
      cache=False)
def combine(ctx, fetch):
    """Fan-in: merge the regional summaries and print the leaderboard."""
    rows = [ctx[f"aggregate_{region}"] for region in REGIONS]
    rows.sort(key=lambda row: row["revenue"], reverse=True)
    text = "\n".join([
        "",
        "## Regional revenue (fan-out / fan-in)",
        "",
        markdown_table(
            ["region", "orders", "revenue $", "avg order $"],
            [[row["region"], row["orders"], f"{row['revenue']:,.2f}",
              f"{row['avg_order']:,.2f}"] for row in rows],
        ),
        "",
        f"Four regional aggregations ran concurrently — that is the "
        f"point of the exercise.",
    ])
    print(text)
    return rows


pipeline = Pipeline(
    "fan-out-fan-in",
    [fetch] + [_region_aggregate(region) for region in REGIONS] + [combine],
    description="four regional aggregations fanning out from one fetch, then merging",
)
