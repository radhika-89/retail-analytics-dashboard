# Retail Analytics Dashboard (SQL + Python + Streamlit)

An interactive dashboard for a synthetic retail dataset. It covers:
- **Sales analysis:** headline KPIs, monthly revenue trend, revenue and share by category, top category per region (SQL `RANK()` window function), repeat-customer rate
- **Customer retention:** monthly cohort retention table and RFM (recency, frequency, monetary) segmentation

The data is generated randomly for practice, so the findings describe the sample, not a real business.

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```

## Project structure
- `analytics.py`: SQL queries and pandas logic (no UI code)
- `app.py`: Streamlit dashboard
- `data/`: `customers.csv` and `orders.csv`

## Deploy on Streamlit Community Cloud
1. Push this folder to a public GitHub repo.
2. Go to share.streamlit.io, sign in with GitHub, pick the repo, and set the main file to `app.py`.
3. Click Deploy.
