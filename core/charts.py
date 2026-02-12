import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

def line_trend(d: pd.DataFrame, c: pd.DataFrame):
    d_m = d.groupby("month")["amount"].sum().reset_index().rename(columns={"amount": "raised"})
    c_m = c.groupby("month")["cost_amount"].sum().reset_index().rename(columns={"cost_amount": "costs"})
    m = pd.merge(d_m, c_m, on="month", how="outer").fillna(0).sort_values("month")
    m["net"] = m["raised"] - m["costs"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m["month"], y=m["raised"], mode="lines+markers", name="Raised"))
    fig.add_trace(go.Scatter(x=m["month"], y=m["costs"], mode="lines+markers", name="Costs"))
    fig.add_trace(go.Scatter(x=m["month"], y=m["net"], mode="lines+markers", name="Net"))
    fig.update_layout(title="Monthly Trend: Raised vs Costs vs Net", xaxis_title="Month", yaxis_title="USD")
    return fig

def bar_compare(rollup: pd.DataFrame, group_col: str):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=rollup[group_col], y=rollup["raised"], name="Raised"))
    fig.add_trace(go.Bar(x=rollup[group_col], y=rollup["costs"], name="Costs"))
    fig.update_layout(
        barmode="group",
        title=f"Raised vs Costs by {group_col}",
        xaxis_title=group_col,
        yaxis_title="USD"
    )
    return fig

def waterfall_net(kpis: dict):
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative", "relative", "total"],
        x=["Raised", "Costs", "Net"],
        y=[kpis["total_raised"], -kpis["total_costs"], kpis["net_raised"]],
        connector={"line": {"dash": "dot"}}
    ))
    fig.update_layout(title="Waterfall: Raised → Costs → Net", yaxis_title="USD")
    return fig

def donor_mix_pie(d: pd.DataFrame):
    s = d.groupby("donor_segment")["amount"].sum().reset_index()
    fig = px.pie(s, values="amount", names="donor_segment", title="Donations by Donor Segment")
    return fig
