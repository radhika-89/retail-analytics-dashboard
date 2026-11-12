"""Streamlit dashboard: retail sales analysis and customer retention (synthetic data)."""
import streamlit as st
import analytics as a

st.set_page_config(page_title="Retail Analytics", layout="wide")


@st.cache_resource
def get_db():
    return a.load_db()


con = get_db()
st.title("Retail Analytics Dashboard")
st.caption("Synthetic retail dataset (800 customers, 6,000 orders, 2024–2025). Built for practice, not real company data.")

tab_sales, tab_retention = st.tabs(["Sales analysis", "Customer retention"])

with tab_sales:
    kpis = a.sales_kpis(con).iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Orders", f"{int(kpis.orders):,}")
    c2.metric("Active customers", f"{int(kpis.active_customers):,}")
    c3.metric("Revenue", f"{kpis.revenue:,.0f}")
    c4.metric("Avg order value", f"{kpis.avg_order_value:,.0f}")

    monthly = a.monthly_revenue(con)
    st.subheader("Monthly revenue")
    st.line_chart(monthly.set_index("month")["revenue"])

    left, right = st.columns(2)
    with left:
        st.subheader("Revenue by category")
        by_cat = a.revenue_by_category(con)
        st.bar_chart(by_cat.set_index("category")["revenue"])
        st.dataframe(by_cat, hide_index=True)
    with right:
        st.subheader("Top category by region")
        ranks = a.region_category_rank(con)
        st.dataframe(ranks[ranks.rank_in_region == 1], hide_index=True)
        st.metric("Repeat-customer rate", f"{a.repeat_rate(con).iloc[0, 0]}%")

with tab_retention:
    st.subheader("Cohort retention (% of cohort still ordering)")
    st.caption("Rows: month of first order. Columns: months since first order. M0 is always 100%.")
    cohort = a.cohort_retention(con)
    st.dataframe(cohort.style.format("{:.1f}", na_rep="").background_gradient(cmap="Blues", axis=None),
                 use_container_width=True)

    rfm = a.rfm_table(con)
    summary = a.segment_summary(rfm)
    st.subheader("RFM segments")
    st.caption("Recency, frequency and monetary value scored 1–5 each; the total maps to a segment.")
    st.bar_chart(summary.set_index("segment")["customers"])
    st.dataframe(summary, hide_index=True)

    with st.expander("Customer-level RFM scores"):
        st.dataframe(rfm, hide_index=True)
