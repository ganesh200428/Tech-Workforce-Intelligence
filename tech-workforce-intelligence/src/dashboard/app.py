"""
Tech Workforce Intelligence - Interactive Dashboard
Run: streamlit run src/dashboard/app.py

Power BI Desktop is not available in this environment, so this Streamlit
dashboard delivers the same page structure / KPIs / business questions
defined in the project brief, sourced from the cleaned Layoffs.fyi dataset
(data/processed/layoffs_clean.csv). It can be swapped for a .pbix later
using the same data model without any changes to the ETL layer.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "layoffs_clean.csv"

st.set_page_config(
    page_title="Tech Workforce Intelligence",
    page_icon=":material/query_stats:",
    layout="wide",
    initial_sidebar_state="expanded",
)

px.defaults.template = "plotly_white"
CHART_COLORWAY = [
    "#1D4E89", "#2A9D8F", "#E76F51", "#E9C46A", "#457B9D",
    "#6C5B7B", "#4D908E", "#F4A261", "#577590", "#264653",
]
px.defaults.color_discrete_sequence = CHART_COLORWAY

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
body, .stApp { background: #fbfaf7; color: #243b53; }
.dashboard-icon {
    display: inline-block;
    width: 1.35rem;
    height: 1.35rem;
    line-height: 1;
    vertical-align: middle;
    fill: none;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 1.8;
}

/* Hide default Streamlit chrome for a cleaner, bigger canvas */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
button[data-testid="stDeployButton"] { display: none; }

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

/* Hero banner */
.hero-banner {
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-left: 6px solid #1d4e89;
    border-radius: 10px;
    padding: 2.2rem 2.6rem;
    margin-bottom: 1.8rem;
    box-shadow: 0 8px 24px rgba(36, 59, 83, 0.1);
}
.hero-eyebrow {
    color: #1d4e89;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.4rem;
}
.hero-title {
    color: #102a43;
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1.15;
    margin: 0;
}
.hero-subtitle {
    color: #52606d;
    font-size: 1.02rem;
    font-weight: 400;
    margin-top: 0.6rem;
    max-width: 900px;
}

/* KPI cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 14px;
    margin-bottom: 1.6rem;
}
.kpi-card {
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-top: 3px solid var(--accent, #1d4e89);
    border-radius: 8px;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 4px 14px rgba(36, 59, 83, 0.08);
    transition: transform 0.15s ease;
}
.kpi-card:hover { transform: translateY(-3px); }
.kpi-icon { color: var(--accent, #1d4e89); margin-bottom: 0.35rem; }
.kpi-label {
    color: #52606d;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.kpi-value {
    color: #102a43;
    font-size: 1.65rem;
    font-weight: 800;
    margin-top: 0.15rem;
}

/* Section headers */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1.6rem 0 0.6rem 0;
    font-size: 1.15rem;
    font-weight: 700;
    color: #243b53;
    border-left: 4px solid #2a9d8f;
    padding-left: 0.6rem;
}

/* Chart card wrapper */
div[data-testid="stPlotlyChart"] {
    background: #ffffff;
    border-radius: 8px;
    padding: 0.35rem 0.55rem 0.1rem 0.55rem;
    border: 1px solid #d9e2ec;
    box-shadow: 0 4px 14px rgba(36, 59, 83, 0.08);
    overflow: hidden;
}
div[data-testid="stPlotlyChart"] .js-plotly-plot {
    min-height: 320px;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #d9e2ec;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 0.95rem;
    color: #243b53;
}
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] [data-testid="stMultiSelect"] label,
section[data-testid="stSidebar"] [data-testid="stTextInput"] label {
    color: #102a43;
}
section[data-testid="stSidebar"] [data-testid="stTextInput"] label {
    font-weight: 700;
}
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #ffffff;
    border-color: #bcccdc;
    color: #243b53;
}
section[data-testid="stSidebar"] [data-baseweb="select"] input {
    color: #243b53;
}
section[data-testid="stSidebar"] [data-baseweb="tag"] {
    background: #1d4e89;
    color: #ffffff;
}
section[data-testid="stSidebar"] [data-testid="stTextInput"] input {
    background: #fffdf5;
    border: 2px solid #2a9d8f;
    border-radius: 8px;
    color: #102a43;
    box-shadow: 0 0 0 3px rgba(42, 157, 143, 0.12);
}
section[data-testid="stSidebar"] [data-testid="stTextInput"] input:focus {
    border-color: #1d4e89;
    box-shadow: 0 0 0 4px rgba(29, 78, 137, 0.18);
}

/* Dataframe */
div[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid #d9e2ec;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def hero(eyebrow, title, subtitle):
    st.markdown(
        f"""
        <div class="hero-banner">
            <div class="hero-eyebrow">{eyebrow}</div>
            <div class="hero-title">{title}</div>
            <div class="hero-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


ICON_PATHS = {
    "groups": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    "trending_up": '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    "business": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 21V7h5v14M12 11h5v10M7 11h5M7 15h5M15 15h2M15 18h2"/>',
    "analytics": '<path d="M3 3v18h18"/><path d="m7 16 4-5 3 3 5-7"/>',
    "local_fire_department": '<path d="M12 22a7 7 0 0 0 7-7c0-4.5-3.5-7.5-5-11-2 1.5-3 3.5-3 6 0 1.5-.5 2.5-1.5 3.5C8 12 7 10.5 7 8.5 5 11 5 13 5 15a7 7 0 0 0 7 7Z"/><path d="M12 22c-2 0-3.5-1.5-3.5-3.5 0-1.5 1-2.5 2-3.5 1 1 1.5 2 1.5 3.5 0-1.5.5-2.5 1.5-3.5 1 1 2 2 2 3.5A3.5 3.5 0 0 1 12 22Z"/>',
    "smart_toy": '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4M8 13h.01M16 13h.01M8 17h8"/><circle cx="12" cy="3" r="1"/>',
    "public": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "calendar_month": '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M16 2v4M8 2v4M3 10h18M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>',
    "assignment": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5"/>',
    "query_stats": '<path d="M3 3v18h18"/><path d="m7 16 3-4 3 2 5-7"/><circle cx="18" cy="7" r="2"/>',
    "grid_on": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7"/>',
    "travel_explore": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5M10.5 7v7M7 10.5h7"/>',
    "build": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.1 2.1-2.8-.7-.7-2.8Z"/>',
    "verified": '<path d="M12 3 4 6v5c0 5 3.4 8.8 8 10 4.6-1.2 8-5 8-10V6l-8-3Z"/><path d="m8 12 2.5 2.5L16 9"/>',
    "warning": '<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v4M12 17h.01"/>',
    "science": '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6A2 2 0 0 0 19 18l-5-9V3M8 16h8"/>',
    "bar_chart": '<path d="M3 3v18h18"/><path d="M7 16v-5M12 16V7M17 16v-9"/>'
}


def svg_icon(name, size="1.35rem"):
    path = ICON_PATHS.get(name, ICON_PATHS["bar_chart"])
    return f'<svg class="dashboard-icon" style="width:{size};height:{size};" viewBox="0 0 24 24" aria-hidden="true">{path}</svg>'


def section(title, icon="bar_chart"):
    st.markdown(
        f'<div class="section-header">{svg_icon(icon)}<span>{title}</span></div>',
        unsafe_allow_html=True,
    )


CHART_HEIGHT = 430
MAP_COLORS = [
    "#1D4E89", "#2A9D8F", "#E76F51", "#E9C46A", "#457B9D",
    "#6C5B7B", "#4D908E", "#F4A261", "#577590", "#264653",
    "#C44536", "#3A86FF", "#8338EC", "#FF006E", "#06A77D",
    "#D1495B", "#0077B6", "#588157", "#BC6C25", "#7B2CBF",
    "#118AB2", "#EF476F", "#073B4C", "#8AB17D", "#B56576",
    "#6A994E", "#9B5DE5", "#F15BB5", "#00B4D8", "#F3722C",
]


def country_color_map(countries):
    return {
        country: MAP_COLORS[index % len(MAP_COLORS)]
        for index, country in enumerate(sorted(countries))
    }


def style_fig(fig, height=CHART_HEIGHT):
    left_margin = 150 if any(
        getattr(trace, "orientation", None) == "h" for trace in fig.data
    ) else 58
    fig.update_layout(
        height=height,
        margin=dict(l=left_margin, r=24, t=72, b=52),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#243b53", size=12),
        title=dict(
            x=0.02,
            xanchor="left",
            y=0.97,
            yanchor="top",
            font=dict(size=17, color="#102a43"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color="#52606d"),
            bgcolor="rgba(255,255,255,0.85)",
        ),
        hoverlabel=dict(
            bgcolor="#102a43",
            bordercolor="#102a43",
            font=dict(color="#ffffff", size=12),
        ),
    )
    fig.update_xaxes(
        showline=True,
        linecolor="#bcccdc",
        linewidth=1,
        gridcolor="#eef2f6",
        zeroline=False,
        tickfont=dict(color="#52606d", size=11),
        title_font=dict(color="#52606d", size=12),
    )
    fig.update_yaxes(
        showline=True,
        linecolor="#bcccdc",
        linewidth=1,
        gridcolor="#eef2f6",
        zeroline=False,
        tickfont=dict(color="#52606d", size=11),
        title_font=dict(color="#52606d", size=12),
    )
    for trace in fig.data:
        if hasattr(trace, "marker") and trace.marker is not None:
            try:
                trace.marker.line = dict(color="#ffffff", width=0.8)
            except (ValueError, AttributeError):
                pass
            try:
                trace.marker.opacity = 0.92
            except (ValueError, AttributeError):
                pass
    return fig


FORECAST_DISCLAIMER = (
    "The 2027 outlook is a statistical projection based on historical "
    "Layoffs.fyi data. It should not be interpreted as a guaranteed "
    "prediction of future layoffs."
)
AI_METHOD_NOTE = (
    "AI-related classification identifies signals in available source "
    "information and does not establish that AI directly caused a layoff."
)


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["Date", "Date Added"])
    return df


df = load_data()
CURRENT_MAX_DATE = df["Date"].max()
LATEST_FULL_YEAR = CURRENT_MAX_DATE.year - 1  # current year is partial

# ---------------------------------------------------------------- Sidebar --
st.sidebar.markdown(
    f"""
    <div style="text-align:center; padding: 0.5rem 0 1.2rem 0;">
        {svg_icon("query_stats", "2.1rem")}
        <div style="font-size:1.15rem; font-weight:800; color:#102a43; line-height:1.2;">
            Tech Workforce<br/>Intelligence
        </div>
        <div style="font-size:0.75rem; color:#52606d; margin-top:0.3rem;">
            Layoffs.fyi &middot; Analytics Suite
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
page = st.sidebar.radio(
    "Page",
    [
        "1. Executive Overview",
        "2. Workforce Trends",
        "3. Company Intelligence",
        "4. Industry & Geography",
        "5. AI Workforce Impact",
        "6. 2027 Workforce Outlook",
        "7. Data & Methodology",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown("### Filters")
years = sorted(df["Year"].dropna().unique().astype(int))
sel_years = st.sidebar.multiselect("Year", years, default=years)
industries = sorted(df["Industry"].dropna().unique())
sel_industries = st.sidebar.multiselect("Industry", industries, default=[])
countries = sorted(df["Country"].dropna().unique())
sel_countries = st.sidebar.multiselect("Country", countries, default=[])
ai_cats = sorted(df["AI_Signal_Category"].dropna().unique())
sel_ai = st.sidebar.multiselect("AI Signal", ai_cats, default=[])
company_search = st.sidebar.text_input("Company contains", placeholder="Search by company name")
matching_companies = []
if company_search:
    matching_companies = sorted(
        df.loc[
            df["Company"].str.contains(company_search, case=False, na=False, regex=False),
            "Company",
        ].unique()
    )
    selected_company = st.sidebar.selectbox(
        "Matching companies",
        ["No company selected"] + matching_companies,
        label_visibility="collapsed",
    )
else:
    selected_company = "No company selected"

fdf = df[df["Year"].isin(sel_years)].copy()
if sel_industries:
    fdf = fdf[fdf["Industry"].isin(sel_industries)]
if sel_countries:
    fdf = fdf[fdf["Country"].isin(sel_countries)]
if sel_ai:
    fdf = fdf[fdf["AI_Signal_Category"].isin(sel_ai)]
if selected_company != "No company selected":
    fdf = fdf[fdf["Company"] == selected_company]
    st.sidebar.caption(
        f"Selected company: {selected_company} ({len(fdf):,} records)"
    )

if fdf.empty:
    st.warning("No records match the current filters. Adjust the filters to continue.")
    st.stop()

reported_fdf = fdf.dropna(subset=["Employees Laid Off"])


def reported_sum(series):
    value = series.sum(min_count=1)
    return 0 if pd.isna(value) else value

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Data through {CURRENT_MAX_DATE.date()}. {years[-1]} is a partial year."
)


KPI_ICONS = ["groups", "trending_up", "business", "analytics", "local_fire_department", "smart_toy", "public", "calendar_month"]
KPI_ACCENTS = ["#1D4E89", "#2A9D8F", "#E76F51", "#E9C46A", "#457B9D", "#6C5B7B", "#4D908E", "#F4A261"]


def kpi_row(cols_data):
    cards = "".join(
        f'<div class="kpi-card" style="--accent:{KPI_ACCENTS[i % len(KPI_ACCENTS)]}">'
        f'<div class="kpi-icon">{svg_icon(KPI_ICONS[i % len(KPI_ICONS)])}</div>'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        "</div>"
        for i, (label, value) in enumerate(cols_data)
    )
    st.markdown(f'<div class="kpi-grid">{cards}</div>', unsafe_allow_html=True)


def chart(fig, height=CHART_HEIGHT):
    st.plotly_chart(style_fig(fig, height), width="stretch")


# ============================================================ PAGE 1 =======
if page.startswith("1"):
    hero(
        "Executive Overview",
        "Global Tech Workforce Intelligence",
        "How has the global technology workforce changed over time, which "
        "companies and industries have been most affected, and what does "
        "the data suggest about AI-related workforce signals?",
    )

    total_emp = reported_sum(fdf["Employees Laid Off"])
    total_events = len(fdf)
    companies_affected = fdf["Company"].nunique()
    avg_size = reported_fdf["Employees Laid Off"].mean() if not reported_fdf.empty else 0
    largest = reported_fdf["Employees Laid Off"].max() if not reported_fdf.empty else 0
    ai_related = reported_sum(
        fdf[fdf["AI_Signal_Category"] == "Explicit AI-related (source-labeled)"]["Employees Laid Off"]
    )

    kpi_row([
        ("Total Employees Laid Off", f"{total_emp:,.0f}"),
        ("Total Layoff Events", f"{total_events:,}"),
        ("Companies Affected", f"{companies_affected:,}"),
        ("Avg Layoff Size", f"{avg_size:,.0f}"),
        ("Largest Single Event", f"{largest:,.0f}"),
        ("AI-Related Layoffs (explicit)", f"{ai_related:,.0f}"),
    ])

    c1, c2 = st.columns(2)
    with c1:
        annual = reported_fdf.groupby("Year", as_index=False)["Employees Laid Off"].sum()
        fig = px.bar(annual, x="Year", y="Employees Laid Off", title="Annual Layoff Trend")
        chart(fig)
    with c2:
        monthly = reported_fdf.groupby("Year_Month", as_index=False)["Employees Laid Off"].sum()
        fig = px.line(monthly, x="Year_Month", y="Employees Laid Off", title="Monthly Layoff Trend")
        fig.update_xaxes(tickangle=45)
        chart(fig)

    c3, c4 = st.columns(2)
    with c3:
        top_co = (reported_fdf.groupby("Company", as_index=False)["Employees Laid Off"].sum()
                  .sort_values("Employees Laid Off", ascending=False).head(10))
        fig = px.bar(top_co, x="Employees Laid Off", y="Company", orientation="h", title="Top 10 Companies")
        fig.update_yaxes(categoryorder="total ascending")
        chart(fig)
    with c4:
        top_ind = (reported_fdf.groupby("Industry", as_index=False)["Employees Laid Off"].sum()
                   .sort_values("Employees Laid Off", ascending=False).head(10))
        fig = px.bar(top_ind, x="Employees Laid Off", y="Industry", orientation="h", title="Top Industries")
        fig.update_yaxes(categoryorder="total ascending")
        chart(fig)

    geo = reported_fdf.groupby("Country", as_index=False)["Employees Laid Off"].sum()
    fig = px.choropleth(
        geo,
        locations="Country",
        locationmode="country names",
        color="Country",
        hover_data={"Employees Laid Off": ":,.0f", "Country": False},
        title="Geographic Distribution by Country",
        color_discrete_map=country_color_map(geo["Country"]),
    )
    fig.update_geos(
        showframe=False,
        showcountries=True,
        countrycolor="#ffffff",
        showcoastlines=True,
        coastlinecolor="#bcccdc",
    )
    chart(fig, height=620)

# ============================================================ PAGE 2 =======
elif page.startswith("2"):
    hero(
        "Trend Analysis",
        "Workforce Trends",
        "Is global technology workforce volatility increasing or decreasing?",
    )

    annual = reported_fdf.groupby("Year", as_index=False).agg(
        Employees=("Employees Laid Off", "sum"),
        Events=("Company", "count"),
        Companies=("Company", "nunique"),
        Avg_Size=("Employees Laid Off", "mean"),
    )
    annual["YoY_Employees_Change"] = annual["Employees"].diff()
    annual["YoY_Employees_Pct"] = annual["Employees"].pct_change() * 100

    c1, c2 = st.columns(2)
    with c1:
        chart(px.bar(annual, x="Year", y="Employees", title="Annual Layoffs"))
    with c2:
        chart(px.bar(annual, x="Year", y="YoY_Employees_Pct", title="YoY % Change"))

    c3, c4 = st.columns(2)
    with c3:
        chart(px.line(annual, x="Year", y="Events", title="Layoff Events per Year"))
    with c4:
        chart(px.line(annual, x="Year", y="Avg_Size", title="Average Layoff Size per Event"))

    monthly = reported_fdf.groupby("Year_Month", as_index=False)["Employees Laid Off"].sum().sort_values("Year_Month")
    monthly["Rolling_3M"] = monthly["Employees Laid Off"].rolling(3).mean()
    monthly["Rolling_12M"] = monthly["Employees Laid Off"].rolling(12).mean()
    fig = px.line(monthly, x="Year_Month", y=["Employees Laid Off", "Rolling_3M", "Rolling_12M"],
                  title="Monthly Layoffs with 3M / 12M Rolling Average")
    fig.update_xaxes(tickangle=45)
    chart(fig)

    st.dataframe(annual, width="stretch")

# ============================================================ PAGE 3 =======
elif page.startswith("3"):
    hero("Company Intelligence", "Company Intelligence", "Who is cutting the deepest, and who keeps coming back? Track repeat offenders and cumulative impact.")

    by_company = reported_fdf.groupby("Company", as_index=False).agg(
        Total_Laid_Off=("Employees Laid Off", "sum"),
        Events=("Company", "count"),
    ).sort_values("Total_Laid_Off", ascending=False)

    c1, c2 = st.columns(2)
    with c1:
        top = by_company.head(15)
        fig = px.bar(top, x="Total_Laid_Off", y="Company", orientation="h", title="Top Companies by Total Layoffs")
        fig.update_yaxes(categoryorder="total ascending")
        chart(fig)
    with c2:
        repeated = by_company[by_company["Events"] > 1].sort_values("Events", ascending=False).head(15)
        fig = px.bar(repeated, x="Events", y="Company", orientation="h", title="Companies with Repeated Layoff Events")
        fig.update_yaxes(categoryorder="total ascending")
        chart(fig)

    section("Largest Individual Layoff Events", "local_fire_department")
    largest_events = reported_fdf.sort_values("Employees Laid Off", ascending=False).head(20)[
        ["Company", "Date", "Employees Laid Off", "Percentage Laid Off", "Industry", "Country"]
    ]
    st.dataframe(largest_events, width="stretch")

    section("Cumulative Layoffs Over Time (Top 10 Companies)", "trending_up")
    top10_names = by_company.head(10)["Company"]
    cum = reported_fdf[reported_fdf["Company"].isin(top10_names)].sort_values("Date").copy()
    cum["Cumulative"] = cum.groupby("Company")["Employees Laid Off"].cumsum()
    fig = px.line(cum, x="Date", y="Cumulative", color="Company", title="Cumulative Layoffs: Top 10 Companies")
    chart(fig)

    section("Company Detail (search / filter above)", "assignment")
    st.dataframe(by_company, width="stretch")

# ============================================================ PAGE 4 =======
elif page.startswith("4"):
    hero("Industry & Geography", "Industry & Geography", "Which sectors and regions have absorbed the heaviest workforce reductions?")

    c1, c2 = st.columns(2)
    with c1:
        ind = reported_fdf.groupby("Industry", as_index=False)["Employees Laid Off"].sum().sort_values("Employees Laid Off", ascending=False)
        fig = px.bar(ind, x="Employees Laid Off", y="Industry", orientation="h", title="Industry Ranking")
        fig.update_yaxes(categoryorder="total ascending")
        chart(fig)
    with c2:
        ctry = reported_fdf.groupby("Country", as_index=False)["Employees Laid Off"].sum().sort_values("Employees Laid Off", ascending=False).head(20)
        fig = px.bar(ctry, x="Employees Laid Off", y="Country", orientation="h", title="Country Ranking (Top 20)")
        fig.update_yaxes(categoryorder="total ascending")
        chart(fig)

    section("Industry Trend Over Time", "query_stats")
    ind_year = reported_fdf.groupby(["Year", "Industry"], as_index=False)["Employees Laid Off"].sum()
    fig = px.line(ind_year, x="Year", y="Employees Laid Off", color="Industry", title="Industry x Year Trend")
    chart(fig)

    section("Industry x Year Matrix", "grid_on")
    matrix = reported_fdf.pivot_table(index="Industry", columns="Year", values="Employees Laid Off", aggfunc="sum", fill_value=0)
    st.dataframe(matrix, width="stretch")

    geo = reported_fdf.groupby("Country", as_index=False)["Employees Laid Off"].sum()
    fig = px.choropleth(
        geo,
        locations="Country",
        locationmode="country names",
        color="Country",
        hover_data={"Employees Laid Off": ":,.0f", "Country": False},
        title="Geographic Map by Country",
        color_discrete_map=country_color_map(geo["Country"]),
    )
    fig.update_geos(
        showframe=False,
        showcountries=True,
        countrycolor="#ffffff",
        showcoastlines=True,
        coastlinecolor="#bcccdc",
    )
    chart(fig, height=620)

# ============================================================ PAGE 5 =======
elif page.startswith("5"):
    hero("AI Workforce Impact", "AI & Automation Workforce Signals", "Where is AI-related workforce disruption showing up explicitly in the data?")
    st.info(AI_METHOD_NOTE)

    ai_counts = fdf["AI_Signal_Category"].value_counts().reset_index()
    ai_counts.columns = ["AI_Signal_Category", "Events"]

    explicit_ai = fdf[fdf["AI_Signal_Category"] == "Explicit AI-related (source-labeled)"]
    ai_emp = reported_sum(explicit_ai["Employees Laid Off"])
    total_emp = reported_sum(fdf["Employees Laid Off"])
    ai_pct = (ai_emp / total_emp * 100) if total_emp else 0

    kpi_row([
        ("Explicit AI-Related Events", f"{len(explicit_ai):,}"),
        ("Explicit AI-Related Employees Affected", f"{ai_emp:,.0f}"),
        ("AI-Related % of Total Employees (explicit only)", f"{ai_pct:.1f}%"),
    ])

    c1, c2 = st.columns(2)
    with c1:
        fig = px.pie(ai_counts, names="AI_Signal_Category", values="Events", title="AI Signal Breakdown (all records)")
        chart(fig)
    with c2:
        ai_year = explicit_ai.dropna(subset=["Employees Laid Off"]).groupby("Year", as_index=False)["Employees Laid Off"].sum()
        fig = px.bar(ai_year, x="Year", y="Employees Laid Off", title="Explicit AI-Related Layoffs by Year")
        chart(fig)

    ai_ind = explicit_ai.dropna(subset=["Employees Laid Off"]).groupby("Industry", as_index=False)["Employees Laid Off"].sum().sort_values("Employees Laid Off", ascending=False).head(10)
    fig = px.bar(ai_ind, x="Employees Laid Off", y="Industry", orientation="h", title="Industries with Strongest Explicit AI Signal")
    fig.update_yaxes(categoryorder="total ascending")
    chart(fig)

    section("Companies with AI-Related Signals", "smart_toy")
    ai_companies = explicit_ai.groupby("Company", as_index=False).agg(
        Events=("Company", "count"), Employees=("Employees Laid Off", reported_sum)
    ).sort_values("Employees", ascending=False)
    st.dataframe(ai_companies, width="stretch")

    st.caption(
        "Note: `AI_Signal_Category` is 'Unknown' for the majority of records "
        "because Layoffs.fyi only began populating an explicit AI field for "
        "recent events; older records are not assumed to have no AI signal."
    )

# ============================================================ PAGE 6 =======
elif page.startswith("6"):
    hero("Forecast", "2027 Statistical Workforce Outlook", "A trend-based statistical projection, not a guarantee of future layoffs.")
    st.warning(FORECAST_DISCLAIMER)

    # Use FULL calendar years only for forecasting (exclude partial current year).
    annual_full = df[df["Year"] < CURRENT_MAX_DATE.year].groupby("Year", as_index=False)["Employees Laid Off"].sum()
    annual_full = annual_full.sort_values("Year")

    def evaluate_models(series_years, series_vals):
        results = {}
        if len(series_vals) >= 3:
            ma_pred = np.mean(series_vals[-3:-1])
            ma_actual = series_vals[-1]
            results["Moving Average (2yr)"] = abs(ma_pred - ma_actual)
        if len(series_vals) >= 3:
            x = np.array(series_years[:-1])
            y = np.array(series_vals[:-1])
            coef = np.polyfit(x, y, 1)
            lr_pred = np.polyval(coef, series_years[-1])
            results["Linear Regression"] = abs(lr_pred - series_vals[-1])
        return results

    yrs = annual_full["Year"].values
    vals = annual_full["Employees Laid Off"].values
    if len(yrs) < 2:
        st.error("At least two complete years with reported employee counts are required for forecasting.")
        st.stop()
    backtest = evaluate_models(yrs, vals)

    section("Model Backtest (Mean Absolute Error on last full year)", "science")
    if backtest:
        bt_df = pd.DataFrame(list(backtest.items()), columns=["Model", "MAE"])
        st.dataframe(bt_df, width="stretch")
        best_model = bt_df.sort_values("MAE").iloc[0]["Model"]
    else:
        bt_df = pd.DataFrame(columns=["Model", "MAE"])
        best_model = "Linear Regression"
    st.caption(f"Selected model for 2027 forecast: **{best_model}** (lowest backtest error)")

    future_years = np.array([CURRENT_MAX_DATE.year, CURRENT_MAX_DATE.year + 1])
    if best_model == "Moving Average (2yr)":
        forecast_vals = np.repeat(np.mean(vals[-2:]), len(future_years))
        fitted_vals = np.repeat(np.mean(vals[-2:]), len(vals))
    else:
        coef = np.polyfit(yrs, vals, 1)
        forecast_vals = np.polyval(coef, future_years)
        fitted_vals = np.polyval(coef, yrs)

    resid = vals - fitted_vals
    resid_std = resid.std() if len(resid) > 1 else 0

    hist_df = pd.DataFrame({"Year": yrs, "Employees Laid Off": vals, "Type": "Actual"})
    fc_df = pd.DataFrame({
        "Year": future_years,
        "Employees Laid Off": forecast_vals,
        "Type": "Forecast",
    })
    combined = pd.concat([hist_df, fc_df], ignore_index=True)

    fig = px.bar(combined, x="Year", y="Employees Laid Off", color="Type",
                 title=f"Historical Actuals + Forecast ({best_model})")
    chart(fig)

    kpi_row([
        (f"{CURRENT_MAX_DATE.year} Forecast (full-year est.)", f"{forecast_vals[0]:,.0f}"),
        ("2027 Forecast", f"{forecast_vals[1]:,.0f}"),
        ("Backtest MAE (best model)", f"{bt_df['MAE'].min():,.0f}" if len(bt_df) else "n/a"),
    ])
    st.caption(f"Approx. 2027 confidence band: {max(forecast_vals[1]-resid_std,0):,.0f} – {forecast_vals[1]+resid_std:,.0f} (±1 residual std dev)")

    model_description = (
        "2-year moving average of annual employee totals"
        if best_model == "Moving Average (2yr)"
        else "linear regression on annual employee totals"
    )
    st.markdown(
        f"""
**Model used:** {model_description} (full calendar years only,
2020–{LATEST_FULL_YEAR}), compared against the alternative model via
1-step-ahead backtesting.

**Limitations:**
- Only {len(yrs)} full historical years are available; this is a very small sample
  for time-series forecasting; confidence intervals are wide.
- The historical series includes an anomalous low year (2021) and very
  high years (2022–2023), driven by macro/COVID-recovery cycles the model
  cannot causally explain.
- Layoffs.fyi is self-reported/crowdsourced and likely undercounts
  unreported or non-public layoffs.
- The forecast is a trend extrapolation, not a causal or economic model.
"""
    )

# ============================================================ PAGE 7 =======
else:
    hero("Reference", "Data & Methodology", "How this dataset was sourced, cleaned, and prepared for analysis.")

    section("Data Source", "database")
    st.write("Layoffs.fyi (https://layoffs.fyi/), the primary and only data source.")

    section("Extraction", "travel_explore")
    st.write(
        "Python + Playwright (headless Chromium) rendering the public, "
        "no-login Airtable embed used by the site itself; virtualized grid "
        "rows harvested via stable DOM row/column indices. No internal "
        "Airtable API calls, no authentication bypass."
    )

    section("Pipeline", "build")
    st.code(
        "Layoffs.fyi -> Playwright extraction -> data/raw/layoffs_raw.csv "
        "-> cleaning/validation -> data/processed/layoffs_clean.csv -> "
        "this dashboard",
        language="text",
    )

    section("Data Quality", "verified")
    dq_path = ROOT / "docs" / "data_quality.md"
    if dq_path.exists():
        st.markdown(dq_path.read_text(encoding="utf-8"))

    section("Limitations", "warning")
    st.markdown(
        """
- Source coverage: crowdsourced/self-reported; likely undercounts
  unreported layoffs, especially outside the US and outside high-profile
  tech companies.
- `Employees Laid Off` and `Percentage Laid Off` are missing for a large
    share of records where the exact figure was never disclosed publicly,
  these are left blank (not assumed zero).
- AI signal is limited to what the source explicitly labels; most records
  predate that field and are marked "Unknown", not "No".
- Forecast uncertainty: only a handful of full historical years exist;
  2027 projection should be treated as directional, not exact.
"""
    )

    st.caption(
        "Layoffs.fyi is the original source and data owner. This project is "
        "an independent analysis and is not affiliated with or endorsed by "
        "Layoffs.fyi."
    )
