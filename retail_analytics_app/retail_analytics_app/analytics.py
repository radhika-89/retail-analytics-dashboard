"""Data logic for the retail analytics dashboard. No UI code here, so it can be tested on its own."""
import sqlite3
import pandas as pd


def load_db(customers_csv="data/customers.csv", orders_csv="data/orders.csv"):
    """Load both CSVs into an in-memory SQLite database and return the connection."""
    con = sqlite3.connect(":memory:")
    pd.read_csv(customers_csv, parse_dates=["signup_date"]).to_sql("customers", con, index=False)
    pd.read_csv(orders_csv, parse_dates=["order_date"]).to_sql("orders", con, index=False)
    return con


def q(con, sql):
    return pd.read_sql_query(sql, con)


def sales_kpis(con):
    return q(con, """
        SELECT COUNT(DISTINCT order_id) AS orders,
               COUNT(DISTINCT customer_id) AS active_customers,
               ROUND(SUM(quantity * unit_price), 2) AS revenue,
               ROUND(SUM(quantity * unit_price) / COUNT(DISTINCT order_id), 2) AS avg_order_value
        FROM orders""")


def monthly_revenue(con):
    return q(con, """
        SELECT strftime('%Y-%m', order_date) AS month,
               ROUND(SUM(quantity * unit_price), 2) AS revenue,
               COUNT(*) AS orders
        FROM orders GROUP BY month ORDER BY month""")


def revenue_by_category(con):
    return q(con, """
        SELECT category,
               ROUND(SUM(quantity * unit_price), 2) AS revenue,
               ROUND(100.0 * SUM(quantity * unit_price) /
                     (SELECT SUM(quantity * unit_price) FROM orders), 1) AS share_pct
        FROM orders GROUP BY category ORDER BY revenue DESC""")


def region_category_rank(con):
    return q(con, """
        WITH cat_region AS (
          SELECT c.region, o.category, ROUND(SUM(o.quantity * o.unit_price), 2) AS revenue
          FROM orders o JOIN customers c USING (customer_id)
          GROUP BY c.region, o.category)
        SELECT region, category, revenue,
               RANK() OVER (PARTITION BY region ORDER BY revenue DESC) AS rank_in_region
        FROM cat_region ORDER BY region, rank_in_region""")


def repeat_rate(con):
    return q(con, """
        WITH per_cust AS (SELECT customer_id, COUNT(*) AS n FROM orders GROUP BY customer_id)
        SELECT ROUND(100.0 * SUM(CASE WHEN n > 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS repeat_customer_pct
        FROM per_cust""")


def cohort_retention(con, max_offset=6):
    """Share of each first-order-month cohort still ordering N months later (M0 = 100%)."""
    cohort = q(con, """
        WITH first_order AS (
          SELECT customer_id, MIN(strftime('%Y-%m', order_date)) AS cohort_month
          FROM orders GROUP BY customer_id),
        activity AS (
          SELECT o.customer_id, f.cohort_month,
                 (CAST(substr(strftime('%Y-%m', o.order_date),1,4) AS INT)*12
                  + CAST(substr(strftime('%Y-%m', o.order_date),6,2) AS INT))
               - (CAST(substr(f.cohort_month,1,4) AS INT)*12
                  + CAST(substr(f.cohort_month,6,2) AS INT)) AS month_offset
          FROM orders o JOIN first_order f USING (customer_id))
        SELECT cohort_month, month_offset, COUNT(DISTINCT customer_id) AS active
        FROM activity GROUP BY cohort_month, month_offset""")
    size = cohort[cohort.month_offset == 0][["cohort_month", "active"]].rename(columns={"active": "cohort_size"})
    merged = cohort.merge(size, on="cohort_month")
    merged["retention_pct"] = (100 * merged.active / merged.cohort_size).round(1)
    table = merged.pivot(index="cohort_month", columns="month_offset", values="retention_pct")
    return table.loc[:, [c for c in range(max_offset + 1) if c in table.columns]]


def rfm_table(con):
    """Customer-level recency, frequency and monetary scores (1-5) and a segment label."""
    rfm = q(con, """
        SELECT customer_id,
               CAST(julianday((SELECT MAX(order_date) FROM orders)) - julianday(MAX(order_date)) AS INT) AS recency_days,
               COUNT(*) AS frequency,
               ROUND(SUM(quantity * unit_price), 2) AS monetary
        FROM orders GROUP BY customer_id""")
    rfm["R"] = pd.qcut(rfm.recency_days.rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F"] = pd.qcut(rfm.frequency.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M"] = pd.qcut(rfm.monetary.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["score"] = rfm.R + rfm.F + rfm.M
    rfm["segment"] = rfm.score.apply(segment_label)
    return rfm


def segment_label(score):
    if score >= 12:
        return "Champions"
    if score >= 9:
        return "Loyal"
    if score >= 6:
        return "At risk"
    return "Lapsed"


def segment_summary(rfm):
    return (rfm.groupby("segment")
               .agg(customers=("customer_id", "count"),
                    avg_spend=("monetary", "mean"),
                    avg_orders=("frequency", "mean"))
               .round(1).sort_values("avg_spend", ascending=False).reset_index())
