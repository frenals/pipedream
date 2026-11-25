"""Sales report — the classic ETL shape.

    customers ──► orders ──► revenue_by_region ──┐
        │            └──────► plan_mix ──────────┴──► report

Run it::

    python -m pipedream run examples/01_sales_report.py
"""

from pipedream import Pipeline, step
from pipedream.data import generate_customers, generate_sales
from pipedream.render import markdown_table


@step
def customers(ctx):
    """Extract: synthesize a customer base (seeded, reproducible)."""
    return generate_customers(400, seed=7)


@step(depends_on=["customers"])
def orders(ctx, customers):
    """Extract: synthesize the orders those customers placed."""
    return generate_sales(customers, seed=11)


@step(depends_on=["orders"])
def revenue_by_region(ctx, orders):
    """Transform: aggregate order value by region."""
    totals = {}
    for order in orders:
        bucket = totals.setdefault(order["region"], {"orders": 0, "revenue": 0.0})
        bucket["orders"] += 1
        bucket["revenue"] += order["amount_usd"]
    return {
        region: {
            "orders": stats["orders"],
            "revenue": round(stats["revenue"], 2),
            "avg_order": round(stats["revenue"] / stats["orders"], 2),
        }
        for region, stats in sorted(totals.items())
    }


@step(depends_on=["customers", "orders"])
def plan_mix(ctx, customers, orders):
    """Transform: revenue and ARPU per plan (runs alongside revenue_by_region)."""
    plan_of = {c["customer_id"]: c["plan"] for c in customers}
    totals = {}
    for order in orders:
        plan = plan_of[order["customer_id"]]
        bucket = totals.setdefault(plan, {"customers": set(), "revenue": 0.0})
        bucket["customers"].add(order["customer_id"])
        bucket["revenue"] += order["amount_usd"]
    for customer in customers:  # customers with zero orders still count
        bucket = totals.setdefault(customer["plan"], {"customers": set(), "revenue": 0.0})
        bucket["customers"].add(customer["customer_id"])
    return {
        plan: {
            "customers": len(stats["customers"]),
            "revenue": round(stats["revenue"], 2),
            "arpu": round(stats["revenue"] / len(stats["customers"]), 2),
        }
        for plan, stats in sorted(totals.items())
    }


@step(depends_on=["revenue_by_region", "plan_mix"])
def report(ctx, revenue_by_region, plan_mix):
    """Load: render the report."""
    text = "\n".join([
        "",
        "## Regional revenue",
        "",
        markdown_table(
            ["region", "orders", "revenue $", "avg order $"],
            [[region, s["orders"], f"{s['revenue']:,.2f}", f"{s['avg_order']:,.2f}"]
             for region, s in revenue_by_region.items()],
        ),
        "",
        "## Plan performance",
        "",
        markdown_table(
            ["plan", "customers", "revenue $", "ARPU $"],
            [[plan, s["customers"], f"{s['revenue']:,.2f}", f"{s['arpu']:,.2f}"]
             for plan, s in plan_mix.items()],
        ),
    ])
    print(text)
    return text


pipeline = Pipeline(
    "sales-report",
    [customers, orders, revenue_by_region, plan_mix, report],
    description="synthetic sales data to a regional revenue + plan ARPU report",
)
