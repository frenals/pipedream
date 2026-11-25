"""Tests for the synthetic data generators."""

from pipedream.data import churn_probability, generate_customers, generate_sales


def test_same_seed_same_data():
    assert generate_customers(100, seed=1) == generate_customers(100, seed=1)


def test_different_seed_different_data():
    assert generate_customers(100, seed=1) != generate_customers(100, seed=2)


def test_customer_fields_and_uniqueness():
    customers = generate_customers(200, seed=9)
    assert len(customers) == 200
    ids = [c["customer_id"] for c in customers]
    assert len(set(ids)) == 200
    for customer in customers:
        assert customer["plan"] in ("free", "pro", "enterprise")
        assert customer["region"] in ("Nairobi", "Lagos", "Cairo", "Johannesburg")
        assert 0 <= customer["monthly_spend"]
        probability = churn_probability(
            customer["plan"], customer["support_tickets_90d"],
            customer["inactive_days"], customer["monthly_spend"])
        assert 0.0 <= probability <= 1.0


def test_churn_correlates_with_support_tickets():
    customers = generate_customers(2000, seed=5)
    churned = [c["support_tickets_90d"] for c in customers if c["churned"]]
    staying = [c["support_tickets_90d"] for c in customers if not c["churned"]]
    assert churned and staying
    assert sum(churned) / len(churned) > sum(staying) / len(staying)


def test_sales_reference_real_customers():
    customers = generate_customers(50, seed=2)
    sales = generate_sales(customers, seed=4)
    assert sales
    valid_ids = {c["customer_id"] for c in customers}
    valid_regions = {c["region"] for c in customers}
    for sale in sales:
        assert sale["customer_id"] in valid_ids
        assert sale["region"] in valid_regions
        assert sale["amount_usd"] >= 0


def test_sales_count_override():
    customers = generate_customers(20, seed=3)
    assert len(generate_sales(customers, 7, seed=1)) == 7


def test_sales_empty_customers():
    assert generate_sales([], seed=1) == []
