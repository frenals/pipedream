"""Churn scoring — a data-science pipeline in five steps.

    customers ──► features ──► score ──► evaluate ──► report

Run it::

    python -m pipedream run examples/02_churn_scoring.py
"""

import math

from pipedream import Pipeline, step
from pipedream.data import generate_customers
from pipedream.render import markdown_table

# A tiny hand-rolled logistic model. The point of the example is the pipeline
# shape, not the model — swap in scikit-learn when you outgrow the tour.
WEIGHTS = {
    "bias": -4.5,
    "support_tickets_90d": 0.40,
    "inactive_days": 0.050,
    "plan_free": 0.42,
    "plan_enterprise": -0.36,
    "monthly_spend": -0.0020,
}


# Decision threshold: churn is rare (~12% base rate), so acting at p >= 0.5
# would flag almost nobody. Retention teams usually intervene much earlier.
THRESHOLD = 0.30


def _sigmoid(z):
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def _roc_auc(y, p):
    """Rank-based AUC (Mann-Whitney U statistic) — no numpy needed."""
    positives = [pi for yi, pi in zip(y, p) if yi == 1]
    negatives = [pi for yi, pi in zip(y, p) if yi == 0]
    if not positives or not negatives:
        return 0.5
    wins = ties = 0
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                wins += 1
            elif pos == neg:
                ties += 1
    return (wins + 0.5 * ties) / (len(positives) * len(negatives))


@step
def customers(ctx):
    """Extract: a seeded customer base with churn labels."""
    return generate_customers(800, seed=42)


@step(depends_on=["customers"])
def features(ctx, customers):
    """Transform: turn raw records into a feature matrix (list of dicts)."""
    return [
        {
            "customer_id": c["customer_id"],
            "tickets": c["support_tickets_90d"],
            "inactive": c["inactive_days"],
            "plan_free": 1 if c["plan"] == "free" else 0,
            "plan_enterprise": 1 if c["plan"] == "enterprise" else 0,
            "spend": c["monthly_spend"],
            "y": 1 if c["churned"] else 0,
        }
        for c in customers
    ]


@step(depends_on=["features"])
def score(ctx, features):
    """Model: probability of churn per customer."""
    scored = []
    for row in features:
        z = (
            WEIGHTS["bias"]
            + WEIGHTS["support_tickets_90d"] * row["tickets"]
            + WEIGHTS["inactive_days"] * row["inactive"]
            + WEIGHTS["plan_free"] * row["plan_free"]
            + WEIGHTS["plan_enterprise"] * row["plan_enterprise"]
            + WEIGHTS["monthly_spend"] * row["spend"]
        )
        scored.append({
            "customer_id": row["customer_id"],
            "p_churn": _sigmoid(z),
            "y": row["y"],
        })
    return scored


@step(depends_on=["score"])
def evaluate(ctx, score):
    """Evaluate: accuracy / precision / recall / F1 / ROC AUC, pure Python."""
    y = [row["y"] for row in score]
    p = [row["p_churn"] for row in score]
    predicted = [1 if value >= THRESHOLD else 0 for value in p]
    tp = sum(1 for a, b in zip(y, predicted) if a == 1 and b == 1)
    fp = sum(1 for a, b in zip(y, predicted) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y, predicted) if a == 1 and b == 0)
    tn = sum(1 for a, b in zip(y, predicted) if a == 0 and b == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "customers": len(y),
        "churn_rate": round(sum(y) / len(y), 4),
        "accuracy": round((tp + tn) / len(y), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision + recall else 0.0,
        "roc_auc": round(_roc_auc(y, p), 4),
        "threshold": THRESHOLD,
    }


@step(depends_on=["evaluate"])
def report(ctx, evaluate):
    """Report: print the metrics card."""
    metrics = evaluate
    text = "\n".join([
        "",
        "## Churn model — evaluation",
        "",
        markdown_table(["metric", "value"], [
            ["customers", metrics["customers"]],
            ["churn rate", f"{metrics['churn_rate']:.1%}"],
            ["accuracy", f"{metrics['accuracy']:.1%}"],
            ["precision", f"{metrics['precision']:.1%}"],
            ["recall", f"{metrics['recall']:.1%}"],
            ["f1", f"{metrics['f1']:.1%}"],
            ["roc auc", f"{metrics['roc_auc']:.3f}"],
            ["threshold", f"{metrics['threshold']:.2f}"],
        ]),
        "",
        "Hand-rolled logistic model, evaluated by PipeDream —",
        "no third-party packages involved.",
    ])
    print(text)
    return text


pipeline = Pipeline(
    "churn-scoring",
    [customers, features, score, evaluate, report],
    description="feature engineering, scoring and evaluation on synthetic churn data",
)
