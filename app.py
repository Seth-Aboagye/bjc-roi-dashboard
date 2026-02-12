import pandas as pd
import streamlit as st
from datetime import datetime

from core.utils import normalize_columns, ensure_datetime, segment_donors_basic, month_floor
from core.metrics import compute_kpis, compute_rollups
from core.charts import line_trend, bar_compare, waterfall_net, donor_mix_pie
from core.reports_excel import build_excel_report
from core.reports_word import build_word_report

st.set_page_config(page_title="BJC Fundraising ROI Dashboard", layout="wide")
st.title("BJC Fundraising ROI Dashboard (CSV Upload)")
st.caption("Upload donation exports + a simple fundraising cost file to compute ROI and generate reports (Excel/Word).")

# -----------------------------
# Sidebar uploads
# -----------------------------
st.sidebar.header("1) Upload Data (CSV)")

donations_file = st.sidebar.file_uploader("Donations CSV (EveryAction export)", type=["csv"])
costs_file = st.sidebar.file_uploader("Costs CSV (your template)", type=["csv"])

with st.expander("Required columns + common aliases"):
    st.markdown("""
**Donations CSV required fields:**
- `date` (GiftDate, ContributionDate, Date)
- `amount` (Amount, ContributionAmount, GiftAmount)
- `donor_id` (VANID, PersonID, DonorID)
- `campaign_code` (AppealCode, Campaign, SourceCode, FundraisingCode)
- `channel` (Channel, Source, Medium)

**Costs CSV required fields:**
- `date` (ExpenseDate, PaidDate)
- `cost_amount` (Amount, Expense, Cost)
- `campaign_code` (optional but recommended; can be blank -> UNMAPPED)
- `channel` (recommended; can be blank -> UNMAPPED)
- `cost_type` (Direct, Labor, Overhead) (optional; default Direct)
""")

if not donations_file or not costs_file:
    st.info("Upload both **Donations CSV** and **Costs CSV** to begin.")
    st.stop()

donations_raw = pd.read_csv(donations_file)
costs_raw = pd.read_csv(costs_file)

donations_df = normalize_columns(donations_raw, kind="donations")
costs_df = normalize_columns(costs_raw, kind="costs")

donations_df = ensure_datetime(donations_df, "date")
costs_df = ensure_datetime(costs_df, "date")

# Add donor segment + month bucket
donations_df = segment_donors_basic(donations_df)
donations_df["month"] = donations_df["date"].apply(month_floor)
costs_df["month"] = costs_df["date"].apply(month_floor)

# -----------------------------
# Filters
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.header("2) Filters")

min_date = min(donations_df["date"].min(), costs_df["date"].min())
max_date = max(donations_df["date"].max(), costs_df["date"].max())

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date()
)
start_dt = pd.to_datetime(date_range[0])
end_dt = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

channels = sorted(set(donations_df["channel"].dropna().unique()).union(set(costs_df["channel"].dropna().unique())))
campaigns = sorted(set(donations_df["campaign_code"].dropna().unique()).union(set(costs_df["campaign_code"].dropna().unique())))
segments = sorted(donations_df["donor_segment"].dropna().unique())

sel_channels = st.sidebar.multiselect("Channel", options=channels, default=channels)
sel_campaigns = st.sidebar.multiselect("Campaign code", options=campaigns, default=campaigns)
sel_segments = st.sidebar.multiselect("Donor segment", options=segments, default=segments)

# Filtered data
d = donations_df[
    (donations_df["date"] >= start_dt) & (donations_df["date"] <= end_dt) &
    (donations_df["channel"].isin(sel_channels)) &
    (donations_df["campaign_code"].isin(sel_campaigns)) &
    (donations_df["donor_segment"].isin(sel_segments))
].copy()

c = costs_df[
    (costs_df["date"] >= start_dt) & (costs_df["date"] <= end_dt) &
    (costs_df["channel"].isin(sel_channels)) &
    (costs_df["campaign_code"].isin(sel_campaigns))
].copy()

# -----------------------------
# KPIs
# -----------------------------
kpis = compute_kpis(d, c)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Raised", f"${kpis['total_raised']:,.0f}")
k2.metric("Total Costs", f"${kpis['total_costs']:,.0f}")
k3.metric("Net Raised", f"${kpis['net_raised']:,.0f}")
k4.metric("ROI", f"{kpis['roi']*100:,.1f}%")
k5.metric("Cost to Raise $1", f"${kpis['cost_to_raise_1']:,.2f}")

st.markdown("---")
st.subheader("Interactive Charts")

tab1, tab2, tab3, tab4 = st.tabs(["Trend", "Compare Campaigns", "Compare Channels", "Donor Mix"])

with tab1:
    st.plotly_chart(line_trend(d, c), use_container_width=True)
    st.plotly_chart(waterfall_net(kpis), use_container_width=True)

with tab2:
    roll = compute_rollups(d, c, by="campaign_code")
    top_n = st.slider("Top N (by Raised)", 5, 50, 15)
    roll_top = roll.sort_values("raised", ascending=False).head(top_n)
    st.dataframe(roll_top, use_container_width=True)
    st.plotly_chart(bar_compare(roll_top, group_col="campaign_code"), use_container_width=True)

with tab3:
    roll = compute_rollups(d, c, by="channel").sort_values("raised", ascending=False)
    st.dataframe(roll, use_container_width=True)
    st.plotly_chart(bar_compare(roll, group_col="channel"), use_container_width=True)

with tab4:
    st.plotly_chart(donor_mix_pie(d), use_container_width=True)

# -----------------------------
# Report generation (Excel + Word only)
# -----------------------------
st.markdown("---")
st.subheader("Generate Reports (Excel + Word)")

report_title = st.text_input("Report title", value="BJC Fundraising ROI Report")
notes = st.text_area("Interpretation / Notes (optional)", value="")

payload = {
    "title": report_title,
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "filters": {
        "start": str(start_dt.date()),
        "end": str(end_dt.date()),
        "channels": sel_channels,
        "campaigns": sel_campaigns,
        "segments": sel_segments
    },
    "kpis": kpis,
}

colx, colw = st.columns(2)

with colx:
    xlsx_bytes = build_excel_report(d, c, payload)
    st.download_button(
        "Download Excel report",
        data=xlsx_bytes,
        file_name="bjc_roi_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with colw:
    docx_bytes = build_word_report(d, c, payload, notes=notes)
    st.download_button(
        "Download Word report",
        data=docx_bytes,
        file_name="bjc_roi_report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

st.markdown("---")
with st.expander("Preview (first 200 rows)"):
    st.write("Donations (filtered)")
    st.dataframe(d.head(200), use_container_width=True)
    st.write("Costs (filtered)")
    st.dataframe(c.head(200), use_container_width=True)
