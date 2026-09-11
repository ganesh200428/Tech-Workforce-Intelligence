"""
Static site generator for Netlify deployment.

Streamlit needs a persistent server, which Netlify (a static host) cannot
run. This script pre-renders the same dataset into a single self-contained
static HTML page (interactive Plotly.js charts, no server required) that
can be uploaded/dragged straight into Netlify.

Run: python src/dashboard/build_static_site.py
Output: netlify_site/index.html
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "layoffs_clean.csv"
DQ_PATH = ROOT / "docs" / "data_quality.md"
OUT_DIR = ROOT / "netlify_site"
OUT_PATH = OUT_DIR / "index.html"

px.defaults.template = "plotly_white"
CHART_COLORWAY = [
    "#1D4E89", "#2A9D8F", "#E76F51", "#E9C46A", "#457B9D",
    "#6C5B7B", "#4D908E", "#F4A261", "#577590", "#264653",
]
px.defaults.color_discrete_sequence = CHART_COLORWAY
MAP_COLORS = CHART_COLORWAY + [
    "#C44536", "#3A86FF", "#8338EC", "#FF006E", "#06A77D",
    "#D1495B", "#0077B6", "#588157", "#BC6C25", "#7B2CBF",
    "#118AB2", "#EF476F", "#073B4C", "#8AB17D", "#B56576",
    "#6A994E", "#9B5DE5", "#F15BB5", "#00B4D8", "#F3722C",
]

FORECAST_DISCLAIMER = (
    "The 2027 outlook is a statistical projection based on historical "
    "Layoffs.fyi data. It should not be interpreted as a guaranteed "
    "prediction of future layoffs."
)
AI_METHOD_NOTE = (
    "AI-related classification identifies signals in available source "
    "information and does not establish that AI directly caused a layoff."
)


def reported_sum(series):
    value = series.sum(min_count=1)
    return 0 if pd.isna(value) else value


def country_color_map(countries):
    return {c: MAP_COLORS[i % len(MAP_COLORS)] for i, c in enumerate(sorted(countries))}


def style_fig(fig, height=430):
    fig.update_layout(
        height=height,
        margin=dict(l=58, r=24, t=72, b=52),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#243b53", size=12),
        title=dict(x=0.02, xanchor="left", y=0.97, yanchor="top", font=dict(size=17, color="#102a43")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11, color="#52606d"), bgcolor="rgba(255,255,255,0.85)"),
        hoverlabel=dict(bgcolor="#102a43", bordercolor="#102a43", font=dict(color="#ffffff", size=12)),
    )
    fig.update_xaxes(showline=True, linecolor="#bcccdc", linewidth=1, gridcolor="#eef2f6",
                      zeroline=False, tickfont=dict(color="#52606d", size=11), title_font=dict(color="#52606d", size=12))
    fig.update_yaxes(showline=True, linecolor="#bcccdc", linewidth=1, gridcolor="#eef2f6",
                      zeroline=False, tickfont=dict(color="#52606d", size=11), title_font=dict(color="#52606d", size=12))
    for trace in fig.data:
        if hasattr(trace, "marker") and trace.marker is not None:
            trace.marker.line = dict(color="#ffffff", width=0.8)
            if "opacity" in type(trace.marker)._valid_props:
                trace.marker.opacity = 0.92
    return fig


def fig_html(fig, height=430):
    style_fig(fig, height)
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})


def kpi_card(label, value, accent="#1D4E89"):
    return (
        f'<div class="kpi-card" style="--accent:{accent}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div></div>'
    )


def section(title):
    return f'<div class="section-header">{title}</div>'


def table_html(df, max_rows=25):
    return df.head(max_rows).to_html(index=False, classes="data-table", border=0, na_rep="")


def build_forecast(df, current_max_date):
    annual_full = df[df["Year"] < current_max_date.year].groupby("Year", as_index=False)["Employees Laid Off"].sum()
    annual_full = annual_full.sort_values("Year")
    yrs = annual_full["Year"].values
    vals = annual_full["Employees Laid Off"].values
    if len(yrs) < 2:
        return None

    def evaluate_models(series_years, series_vals):
        results = {}
        if len(series_vals) >= 3:
            results["Moving Average (2yr)"] = abs(np.mean(series_vals[-3:-1]) - series_vals[-1])
            coef = np.polyfit(series_years[:-1], series_vals[:-1], 1)
            results["Linear Regression"] = abs(np.polyval(coef, series_years[-1]) - series_vals[-1])
        return results

    backtest = evaluate_models(yrs, vals)
    bt_df = pd.DataFrame(list(backtest.items()), columns=["Model", "MAE"])
    best_model = bt_df.sort_values("MAE").iloc[0]["Model"] if len(bt_df) else "Linear Regression"

    future_years = np.array([current_max_date.year, current_max_date.year + 1])
    if best_model == "Moving Average (2yr)":
        forecast_vals = np.repeat(np.mean(vals[-2:]), len(future_years))
    else:
        coef = np.polyfit(yrs, vals, 1)
        forecast_vals = np.polyval(coef, future_years)

    hist_df = pd.DataFrame({"Year": yrs, "Employees Laid Off": vals, "Type": "Actual"})
    fc_df = pd.DataFrame({"Year": future_years, "Employees Laid Off": forecast_vals, "Type": "Forecast"})
    combined = pd.concat([hist_df, fc_df], ignore_index=True)
    fig = px.bar(combined, x="Year", y="Employees Laid Off", color="Type",
                 title=f"Historical Actuals + Forecast ({best_model})")
    return {
        "chart": fig_html(fig),
        "bt_table": table_html(bt_df),
        "best_model": best_model,
        "forecast_current": forecast_vals[0],
        "forecast_2027": forecast_vals[1],
    }


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["Date", "Date Added"])
    current_max_date = df["Date"].max()
    reported = df.dropna(subset=["Employees Laid Off"])

    total_emp = reported_sum(df["Employees Laid Off"])
    total_events = len(df)
    companies_affected = df["Company"].nunique()
    avg_size = reported["Employees Laid Off"].mean() if not reported.empty else 0
    largest = reported["Employees Laid Off"].max() if not reported.empty else 0
    ai_related = reported_sum(df[df["AI_Signal_Category"] == "Explicit AI-related (source-labeled)"]["Employees Laid Off"])

    kpis = "".join([
        kpi_card("Total Employees Laid Off", f"{total_emp:,.0f}", "#1D4E89"),
        kpi_card("Total Layoff Events", f"{total_events:,}", "#2A9D8F"),
        kpi_card("Companies Affected", f"{companies_affected:,}", "#E76F51"),
        kpi_card("Avg Layoff Size", f"{avg_size:,.0f}", "#E9C46A"),
        kpi_card("Largest Single Event", f"{largest:,.0f}", "#457B9D"),
        kpi_card("AI-Related Layoffs (explicit)", f"{ai_related:,.0f}", "#6C5B7B"),
    ])

    # --- Executive overview charts ---
    annual = reported.groupby("Year", as_index=False)["Employees Laid Off"].sum()
    fig_annual = fig_html(px.bar(annual, x="Year", y="Employees Laid Off", title="Annual Layoff Trend"))

    monthly = reported.groupby("Year_Month", as_index=False)["Employees Laid Off"].sum()
    fig_monthly_fig = px.line(monthly, x="Year_Month", y="Employees Laid Off", title="Monthly Layoff Trend")
    fig_monthly_fig.update_xaxes(tickangle=45)
    fig_monthly = fig_html(fig_monthly_fig)

    top_co = (reported.groupby("Company", as_index=False)["Employees Laid Off"].sum()
              .sort_values("Employees Laid Off", ascending=False).head(10))
    fig_topco_fig = px.bar(top_co, x="Employees Laid Off", y="Company", orientation="h", title="Top 10 Companies")
    fig_topco_fig.update_yaxes(categoryorder="total ascending")
    fig_topco = fig_html(fig_topco_fig)

    top_ind = (reported.groupby("Industry", as_index=False)["Employees Laid Off"].sum()
               .sort_values("Employees Laid Off", ascending=False).head(10))
    fig_topind_fig = px.bar(top_ind, x="Employees Laid Off", y="Industry", orientation="h", title="Top Industries")
    fig_topind_fig.update_yaxes(categoryorder="total ascending")
    fig_topind = fig_html(fig_topind_fig)

    geo = reported.groupby("Country", as_index=False)["Employees Laid Off"].sum()
    fig_geo_fig = px.choropleth(
        geo, locations="Country", locationmode="country names", color="Country",
        hover_data={"Employees Laid Off": ":,.0f", "Country": False},
        title="Geographic Distribution by Country", color_discrete_map=country_color_map(geo["Country"]),
    )
    fig_geo_fig.update_geos(showframe=False, showcountries=True, countrycolor="#ffffff",
                             showcoastlines=True, coastlinecolor="#bcccdc")
    fig_geo = fig_html(fig_geo_fig, height=620)

    # --- Trend analysis ---
    trend_annual = reported.groupby("Year", as_index=False).agg(
        Employees=("Employees Laid Off", "sum"), Events=("Company", "count"),
        Avg_Size=("Employees Laid Off", "mean"),
    )
    trend_annual["YoY_Employees_Pct"] = trend_annual["Employees"].pct_change() * 100
    fig_yoy = fig_html(px.bar(trend_annual, x="Year", y="YoY_Employees_Pct", title="YoY % Change"))
    fig_events = fig_html(px.line(trend_annual, x="Year", y="Events", title="Layoff Events per Year"))
    fig_avgsize = fig_html(px.line(trend_annual, x="Year", y="Avg_Size", title="Average Layoff Size per Event"))

    monthly_roll = monthly.sort_values("Year_Month").copy()
    monthly_roll["Rolling_3M"] = monthly_roll["Employees Laid Off"].rolling(3).mean()
    monthly_roll["Rolling_12M"] = monthly_roll["Employees Laid Off"].rolling(12).mean()
    fig_roll_fig = px.line(monthly_roll, x="Year_Month", y=["Employees Laid Off", "Rolling_3M", "Rolling_12M"],
                            title="Monthly Layoffs with 3M / 12M Rolling Average")
    fig_roll_fig.update_xaxes(tickangle=45)
    fig_roll = fig_html(fig_roll_fig)

    # --- Company intelligence ---
    by_company = reported.groupby("Company", as_index=False).agg(
        Total_Laid_Off=("Employees Laid Off", "sum"), Events=("Company", "count"),
    ).sort_values("Total_Laid_Off", ascending=False)
    fig_top15_fig = px.bar(by_company.head(15), x="Total_Laid_Off", y="Company", orientation="h",
                            title="Top Companies by Total Layoffs")
    fig_top15_fig.update_yaxes(categoryorder="total ascending")
    fig_top15 = fig_html(fig_top15_fig)

    repeated = by_company[by_company["Events"] > 1].sort_values("Events", ascending=False).head(15)
    fig_repeat_fig = px.bar(repeated, x="Events", y="Company", orientation="h",
                             title="Companies with Repeated Layoff Events")
    fig_repeat_fig.update_yaxes(categoryorder="total ascending")
    fig_repeat = fig_html(fig_repeat_fig)

    largest_events = reported.sort_values("Employees Laid Off", ascending=False).head(20)[
        ["Company", "Date", "Employees Laid Off", "Percentage Laid Off", "Industry", "Country"]
    ]
    largest_events_table = table_html(largest_events, max_rows=20)

    top10_names = by_company.head(10)["Company"]
    cum = reported[reported["Company"].isin(top10_names)].sort_values("Date").copy()
    cum["Cumulative"] = cum.groupby("Company")["Employees Laid Off"].cumsum()
    fig_cum = fig_html(px.line(cum, x="Date", y="Cumulative", color="Company",
                                title="Cumulative Layoffs: Top 10 Companies"))

    # --- Industry & geography ---
    ind = reported.groupby("Industry", as_index=False)["Employees Laid Off"].sum().sort_values("Employees Laid Off", ascending=False)
    fig_ind_fig = px.bar(ind, x="Employees Laid Off", y="Industry", orientation="h", title="Industry Ranking")
    fig_ind_fig.update_yaxes(categoryorder="total ascending")
    fig_ind = fig_html(fig_ind_fig)

    ctry = reported.groupby("Country", as_index=False)["Employees Laid Off"].sum().sort_values("Employees Laid Off", ascending=False).head(20)
    fig_ctry_fig = px.bar(ctry, x="Employees Laid Off", y="Country", orientation="h", title="Country Ranking (Top 20)")
    fig_ctry_fig.update_yaxes(categoryorder="total ascending")
    fig_ctry = fig_html(fig_ctry_fig)

    ind_year = reported.groupby(["Year", "Industry"], as_index=False)["Employees Laid Off"].sum()
    fig_indyear = fig_html(px.line(ind_year, x="Year", y="Employees Laid Off", color="Industry", title="Industry x Year Trend"))

    # --- AI workforce impact ---
    ai_counts = df["AI_Signal_Category"].value_counts().reset_index()
    ai_counts.columns = ["AI_Signal_Category", "Events"]
    explicit_ai = df[df["AI_Signal_Category"] == "Explicit AI-related (source-labeled)"]
    ai_emp = reported_sum(explicit_ai["Employees Laid Off"])
    ai_pct = (ai_emp / total_emp * 100) if total_emp else 0

    ai_kpis = "".join([
        kpi_card("Explicit AI-Related Events", f"{len(explicit_ai):,}", "#1D4E89"),
        kpi_card("Explicit AI-Related Employees Affected", f"{ai_emp:,.0f}", "#2A9D8F"),
        kpi_card("AI-Related % of Total Employees (explicit only)", f"{ai_pct:.1f}%", "#E76F51"),
    ])
    fig_ai_pie = fig_html(px.pie(ai_counts, names="AI_Signal_Category", values="Events", title="AI Signal Breakdown (all records)"))
    ai_year = explicit_ai.dropna(subset=["Employees Laid Off"]).groupby("Year", as_index=False)["Employees Laid Off"].sum()
    fig_ai_year = fig_html(px.bar(ai_year, x="Year", y="Employees Laid Off", title="Explicit AI-Related Layoffs by Year"))

    ai_ind = explicit_ai.dropna(subset=["Employees Laid Off"]).groupby("Industry", as_index=False)["Employees Laid Off"].sum().sort_values("Employees Laid Off", ascending=False).head(10)
    fig_ai_ind_fig = px.bar(ai_ind, x="Employees Laid Off", y="Industry", orientation="h", title="Industries with Strongest Explicit AI Signal")
    fig_ai_ind_fig.update_yaxes(categoryorder="total ascending")
    fig_ai_ind = fig_html(fig_ai_ind_fig)

    # --- Forecast ---
    forecast = build_forecast(df, current_max_date)

    # --- Methodology ---
    dq_text = DQ_PATH.read_text(encoding="utf-8") if DQ_PATH.exists() else ""

    forecast_section = ""
    if forecast:
        forecast_section = f"""
    <section id="forecast">
      {section("6. 2027 Workforce Outlook")}
      <div class="notice">{FORECAST_DISCLAIMER}</div>
      <div class="chart-card">{forecast['chart']}</div>
      <div class="kpi-grid">
        {kpi_card('Forecast (full-year est.)', f"{forecast['forecast_current']:,.0f}", "#1D4E89")}
        {kpi_card('2027 Forecast', f"{forecast['forecast_2027']:,.0f}", "#2A9D8F")}
      </div>
      <p class="caption">Selected model: <strong>{forecast['best_model']}</strong> (lowest backtest error)</p>
      <div class="table-wrap">{forecast['bt_table']}</div>
    </section>
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Tech Workforce Intelligence</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
{CSS}
</style>
</head>
<body>
<header class="topbar">
  <div class="brand">Tech Workforce Intelligence</div>
  <nav>
    <a href="#overview">Overview</a>
    <a href="#trends">Trends</a>
    <a href="#companies">Companies</a>
    <a href="#industry">Industry &amp; Geo</a>
    <a href="#ai">AI Impact</a>
    <a href="#forecast">Forecast</a>
    <a href="#methodology">Methodology</a>
  </nav>
</header>

<main>
  <div class="hero-banner">
    <div class="hero-eyebrow">Executive Overview</div>
    <div class="hero-title">Global Tech Workforce Intelligence</div>
    <div class="hero-subtitle">
      Static export of the interactive Streamlit dashboard, sourced from
      the cleaned Layoffs.fyi dataset. Data through {current_max_date.date()}.
    </div>
  </div>

  <section id="overview">
    {section("1. Executive Overview")}
    <div class="kpi-grid">{kpis}</div>
    <div class="chart-grid-2">
      <div class="chart-card">{fig_annual}</div>
      <div class="chart-card">{fig_monthly}</div>
    </div>
    <div class="chart-grid-2">
      <div class="chart-card">{fig_topco}</div>
      <div class="chart-card">{fig_topind}</div>
    </div>
    <div class="chart-card">{fig_geo}</div>
  </section>

  <section id="trends">
    {section("2. Workforce Trends")}
    <div class="chart-grid-2">
      <div class="chart-card">{fig_annual}</div>
      <div class="chart-card">{fig_yoy}</div>
    </div>
    <div class="chart-grid-2">
      <div class="chart-card">{fig_events}</div>
      <div class="chart-card">{fig_avgsize}</div>
    </div>
    <div class="chart-card">{fig_roll}</div>
  </section>

  <section id="companies">
    {section("3. Company Intelligence")}
    <div class="chart-grid-2">
      <div class="chart-card">{fig_top15}</div>
      <div class="chart-card">{fig_repeat}</div>
    </div>
    <h3>Largest Individual Layoff Events</h3>
    <div class="table-wrap">{largest_events_table}</div>
    <h3>Cumulative Layoffs Over Time (Top 10 Companies)</h3>
    <div class="chart-card">{fig_cum}</div>
  </section>

  <section id="industry">
    {section("4. Industry &amp; Geography")}
    <div class="chart-grid-2">
      <div class="chart-card">{fig_ind}</div>
      <div class="chart-card">{fig_ctry}</div>
    </div>
    <div class="chart-card">{fig_indyear}</div>
  </section>

  <section id="ai">
    {section("5. AI Workforce Impact")}
    <div class="notice">{AI_METHOD_NOTE}</div>
    <div class="kpi-grid">{ai_kpis}</div>
    <div class="chart-grid-2">
      <div class="chart-card">{fig_ai_pie}</div>
      <div class="chart-card">{fig_ai_year}</div>
    </div>
    <div class="chart-card">{fig_ai_ind}</div>
  </section>
{forecast_section}
  <section id="methodology">
    {section("7. Data &amp; Methodology")}
    <div class="markdown">{dq_text}</div>
    <p class="caption">Layoffs.fyi is the original source and data owner. This
    project is an independent analysis and is not affiliated with or
    endorsed by Layoffs.fyi.</p>
  </section>

  <footer class="footer">Built from data/processed/layoffs_clean.csv &middot; Static export for Netlify</footer>
</main>
</body>
</html>
"""

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* { box-sizing: border-box; }
body { margin:0; font-family:'Inter',sans-serif; background:#fbfaf7; color:#243b53; }
.topbar { display:flex; justify-content:space-between; align-items:center; padding:0.9rem 2rem; background:#ffffff; border-bottom:1px solid #d9e2ec; position:sticky; top:0; z-index:10; flex-wrap:wrap; gap:0.6rem; }
.brand { font-weight:800; color:#102a43; font-size:1.1rem; }
.topbar nav a { color:#1d4e89; text-decoration:none; margin-left:1.1rem; font-weight:600; font-size:0.92rem; }
.topbar nav a:hover { text-decoration:underline; }
main { max-width:1400px; margin:0 auto; padding:1.5rem 2rem 3rem; }
.hero-banner { background:#ffffff; border:1px solid #d9e2ec; border-left:6px solid #1d4e89; border-radius:10px; padding:2.2rem 2.6rem; margin-bottom:1.8rem; box-shadow:0 8px 24px rgba(36,59,83,0.1); }
.hero-eyebrow { color:#1d4e89; font-size:0.85rem; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:0.4rem; }
.hero-title { color:#102a43; font-size:2.2rem; font-weight:800; margin:0; }
.hero-subtitle { color:#52606d; font-size:1rem; margin-top:0.6rem; max-width:900px; }
section { margin-bottom:2.4rem; scroll-margin-top:80px; }
.section-header { font-size:1.15rem; font-weight:700; color:#243b53; border-left:4px solid #2a9d8f; padding-left:0.6rem; margin:1.2rem 0 0.9rem; }
.kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin-bottom:1.4rem; }
.kpi-card { background:#ffffff; border:1px solid #d9e2ec; border-top:3px solid var(--accent,#1d4e89); border-radius:8px; padding:1.1rem 1.2rem; box-shadow:0 4px 14px rgba(36,59,83,0.08); }
.kpi-label { color:#52606d; font-size:0.78rem; font-weight:600; text-transform:uppercase; letter-spacing:0.04em; }
.kpi-value { color:#102a43; font-size:1.55rem; font-weight:800; margin-top:0.15rem; }
.chart-grid-2 { display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:16px; margin-bottom:16px; }
.chart-card { background:#ffffff; border-radius:8px; padding:0.4rem 0.6rem; border:1px solid #d9e2ec; box-shadow:0 4px 14px rgba(36,59,83,0.08); overflow:hidden; }
.notice { background:#fff8e6; border:1px solid #e9c46a; color:#7a5c00; padding:0.8rem 1rem; border-radius:8px; margin-bottom:1rem; font-size:0.92rem; }
.table-wrap { overflow-x:auto; background:#ffffff; border:1px solid #d9e2ec; border-radius:8px; padding:0.5rem; }
.data-table { border-collapse:collapse; width:100%; font-size:0.85rem; }
.data-table th, .data-table td { padding:0.45rem 0.7rem; border-bottom:1px solid #eef2f6; text-align:left; white-space:nowrap; }
.data-table th { color:#52606d; text-transform:uppercase; font-size:0.72rem; letter-spacing:0.03em; }
.caption { color:#829ab1; font-size:0.85rem; }
.markdown { background:#ffffff; border:1px solid #d9e2ec; border-radius:8px; padding:1rem 1.4rem; white-space:pre-wrap; font-size:0.92rem; line-height:1.55; }
.footer { text-align:center; color:#829ab1; font-size:0.82rem; padding:2rem 0 0.5rem; }
h3 { color:#243b53; font-size:1rem; margin:0.4rem 0 0.6rem; }
"""

if __name__ == "__main__":
    main()
