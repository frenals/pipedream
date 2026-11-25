"""Synthetic data generators for the example pipelines.

Everything here is deterministic given a seed and uses only the standard
library, so the examples run anywhere with zero downloads.  The churn labels
come from a logistic model of the same features the scoring example uses,
which keeps the demo metrics satisfyingly realistic.
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta

_TODAY = date.today()

FIRST_NAMES = (
    "Amina", "Joseph", "Grace", "Peter", "Fatuma", "Daniel", "Zawadi",
    "Collins", "Njeri", "Otieno", "Mariam", "Kofi", "Abena", "Kwame",
    "Chidi", "Amara", "Tariq", "Layla", "Omar", "Sana",
)
LAST_NAMES = (
    "Ochieng", "Wanjiru", "Mwangi", "Adeyemi", "Okonkwo", "Mensah",
    "Boateng", "Abebe", "Tesfaye", "Hassan", "Kimani", "Njoroge", "Diallo",
    "Traore", "Kamau", "Banda", "Chirwa", "Moyo", "Dlamini", "Nkosi",
)
PLANS = ("free", "pro", "enterprise")
CATEGORIES = ("compute", "storage", "bandwidth", "support", "training")

REGIONS = ("Nairobi", "Lagos", "Cairo", "Johannesburg")
COUNTRIES = (
    "Kenya", "Tanzania", "Uganda", "Rwanda",          # -> Nairobi
    "Nigeria", "Ghana", "Senegal",                    # -> Lagos
    "Egypt", "Morocco", "Ethiopia",                   # -> Cairo
    "South Africa", "Zambia",                         # -> Johannesburg
)
_REGION_BY_COUNTRY = {
    "Kenya": "Nairobi", "Tanzania": "Nairobi", "Uganda": "Nairobi",
    "Rwanda": "Nairobi", "Nigeria": "Lagos", "Ghana": "Lagos",
    "Senegal": "Lagos", "Egypt": "Cairo", "Morocco": "Cairo",
    "Ethiopia": "Cairo", "South Africa": "Johannesburg", "Zambia": "Johannesburg",
}

# order volume per plan, used to weight who places an order
_PLAN_ORDER_WEIGHT = {"free": 1, "pro": 3, "enterprise": 9}
_PLAN_SPEND_BASE = {"free": 8.0, "pro": 90.0, "enterprise": 700.0}


def churn_probability(plan, support_tickets, inactive_days, monthly_spend):
    """Ground-truth logistic model behind the synthetic churn labels.

    The churn-scoring example "learns" weights close to these by hand; swap
    in a real model once you outgrow the tour.
    """
    z = (
        -4.6
        + 0.42 * support_tickets
        + 0.052 * inactive_days
        + (0.45 if plan == "free" else -0.38 if plan == "enterprise" else 0.0)
        - 0.0022 * min(monthly_spend, 400.0)
    )
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def generate_customers(n=500, *, seed=None):
    """Synthesize ``n`` customers with churn-driving behavioural signals."""
    rng = random.Random(seed)
    customers = []
    for i in range(1, n + 1):
        plan = rng.choices(PLANS, weights=(60, 30, 10))[0]
        country = rng.choice(COUNTRIES)
        base = _PLAN_SPEND_BASE[plan]
        monthly_spend = round(max(0.0, rng.gauss(base, base * 0.35)), 2)
        support_tickets = rng.choice((0, 0, 1, 1, 2, 3, 4, 6))
        inactive_days = min(int(rng.expovariate(1 / 22.0)), 180)
        churned = rng.random() < churn_probability(
            plan, support_tickets, inactive_days, monthly_spend)
        customers.append({
            "customer_id": f"C{i:05d}",
            "name": f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
            "country": country,
            "region": _REGION_BY_COUNTRY[country],
            "plan": plan,
            "age": rng.randint(18, 69),
            "signup_date": (_TODAY - timedelta(days=rng.randint(30, 1500))).isoformat(),
            "monthly_spend": monthly_spend,
            "support_tickets_90d": support_tickets,
            "inactive_days": inactive_days,
            "churned": churned,
        })
    return customers


def generate_sales(customers, n=None, *, seed=None):
    """Synthesize ``n`` orders (default 4 per customer) placed by ``customers``.

    Enterprise customers order more often and spend more per order, so the
    regional roll-ups in the examples have some texture to them.
    """
    if not customers:
        return []
    rng = random.Random(seed)
    n = n if n is not None else 4 * len(customers)
    weights = [_PLAN_ORDER_WEIGHT[c["plan"]] for c in customers]
    orders = []
    for j in range(1, n + 1):
        customer = rng.choices(customers, weights=weights)[0]
        weight = _PLAN_ORDER_WEIGHT[customer["plan"]]
        amount = min(round(math.exp(rng.gauss(math.log(45.0 + 38.0 * weight), 0.75)), 2), 5000.0)
        orders.append({
            "order_id": f"O{j:06d}",
            "customer_id": customer["customer_id"],
            "region": customer["region"],
            "category": rng.choice(CATEGORIES),
            "amount_usd": amount,
            "days_ago": min(int(rng.expovariate(1 / 45.0)), 365),
        })
    return orders
