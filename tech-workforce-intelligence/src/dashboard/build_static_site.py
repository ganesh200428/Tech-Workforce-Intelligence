"""
Static (but fully interactive) site generator for Netlify deployment.

Netlify can't run the Streamlit server, so this script embeds the cleaned
dataset as JSON directly in the page and reproduces the sidebar
filters (Year / Industry / Country / AI signal / company search) and all
charts with vanilla JavaScript + Plotly.js. Everything runs client-side in
the browser - no backend required - so filters and buttons keep working
after deployment to Netlify.

Run: python src/dashboard/build_static_site.py
Output: netlify_site/index.html
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "layoffs_clean.csv"
OUT_DIR = ROOT / "netlify_site"
OUT_PATH = OUT_DIR / "index.html"

AI_METHOD_NOTE = (
    "AI-related classification identifies signals in available source "
    "information and does not establish that AI directly caused a layoff."
)

# Minimal Feather-style stroke icons (single-quoted attrs so they can be
# embedded inside both HTML attributes and double-quoted JS strings).
_SVG_OPEN = "<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>"
ICONS = {
    "brand": _SVG_OPEN + "<line x1='18' y1='20' x2='18' y2='10'/><line x1='12' y1='20' x2='12' y2='4'/><line x1='6' y1='20' x2='6' y2='14'/></svg>",
    "calendar": _SVG_OPEN + "<rect x='3' y='4' width='18' height='18' rx='2' ry='2'/><line x1='16' y1='2' x2='16' y2='6'/><line x1='8' y1='2' x2='8' y2='6'/><line x1='3' y1='10' x2='21' y2='10'/></svg>",
    "briefcase": _SVG_OPEN + "<rect x='2' y='7' width='20' height='14' rx='2' ry='2'/><path d='M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16'/></svg>",
    "globe": _SVG_OPEN + "<circle cx='12' cy='12' r='10'/><line x1='2' y1='12' x2='22' y2='12'/><path d='M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z'/></svg>",
    "cpu": _SVG_OPEN + "<rect x='4' y='4' width='16' height='16' rx='2' ry='2'/><rect x='9' y='9' width='6' height='6'/><line x1='9' y1='1' x2='9' y2='4'/><line x1='15' y1='1' x2='15' y2='4'/><line x1='9' y1='20' x2='9' y2='23'/><line x1='15' y1='20' x2='15' y2='23'/><line x1='20' y1='9' x2='23' y2='9'/><line x1='20' y1='14' x2='23' y2='14'/><line x1='1' y1='9' x2='4' y2='9'/><line x1='1' y1='14' x2='4' y2='14'/></svg>",
    "search": _SVG_OPEN + "<circle cx='11' cy='11' r='8'/><line x1='21' y1='21' x2='16.65' y2='16.65'/></svg>",
    "refresh": _SVG_OPEN + "<polyline points='23 4 23 10 17 10'/><polyline points='1 20 1 14 7 14'/><path d='M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15'/></svg>",
    "home": _SVG_OPEN + "<path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><polyline points='9 22 9 12 15 12 15 22'/></svg>",
    "trending": _SVG_OPEN + "<polyline points='23 6 13.5 15.5 8.5 10.5 1 18'/><polyline points='17 6 23 6 23 12'/></svg>",
    "filetext": _SVG_OPEN + "<path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><polyline points='14 2 14 8 20 8'/><line x1='16' y1='13' x2='8' y2='13'/><line x1='16' y1='17' x2='8' y2='17'/></svg>",
    "users": _SVG_OPEN + "<path d='M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2'/><circle cx='9' cy='7' r='4'/><path d='M23 21v-2a4 4 0 0 0-3-3.87'/><path d='M16 3.13a4 4 0 0 1 0 7.75'/></svg>",
    "clipboard": _SVG_OPEN + "<rect x='8' y='2' width='8' height='4' rx='1' ry='1'/><path d='M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2'/><line x1='9' y1='11' x2='15' y2='11'/><line x1='9' y1='15' x2='15' y2='15'/></svg>",
    "zap": _SVG_OPEN + "<polygon points='13 2 3 14 12 14 11 22 21 10 12 10 13 2'/></svg>",
    "chevron": _SVG_OPEN + "<polyline points='6 9 12 15 18 9'/></svg>",
}


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["Date"])
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")

    cols = [
        "Company", "Country", "Employees Laid Off", "Percentage Laid Off",
        "Date", "Year", "Year_Month", "Industry", "AI_Signal_Category",
    ]
    # Cast to object first: .where(..., None) on float columns silently
    # reverts back to NaN otherwise, which serializes as invalid JS `NaN`.
    sub = df[cols].astype(object)
    records = sub.where(pd.notnull(sub), None).to_dict(orient="records")
    data_json = json.dumps(records, separators=(",", ":"))

    years = sorted(int(y) for y in df["Year"].dropna().unique())
    industries = sorted(str(x) for x in df["Industry"].dropna().unique())
    countries = sorted(str(x) for x in df["Country"].dropna().unique())
    ai_cats = sorted(str(x) for x in df["AI_Signal_Category"].dropna().unique())
    current_max_date = df["Date"].max()

    def option_list(values, id_prefix, checked=True):
        chk = "checked" if checked else ""
        return "".join(
            f'<label class="chk"><input type="checkbox" data-group="{id_prefix}" value="{v}" {chk}> {v}</label>'
            for v in values
        )

    years_html = option_list([str(y) for y in years], "year", checked=True)
    industries_html = option_list(industries, "industry", checked=False)
    countries_html = option_list(countries, "country", checked=False)
    ai_html = option_list(ai_cats, "ai", checked=False)

    html = HTML_TEMPLATE.format(
        data_json=data_json,
        years_html=years_html,
        industries_html=industries_html,
        countries_html=countries_html,
        ai_html=ai_html,
        current_max_date=current_max_date,
        ai_method_note=AI_METHOD_NOTE,
        css=CSS,
        **{f"icon_{name}": svg for name, svg in ICONS.items()},
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
* { box-sizing: border-box; }
::-webkit-scrollbar { width:8px; height:8px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#cbd5e1; border-radius:8px; }
::-webkit-scrollbar-thumb:hover { background:#9fb3c8; }
body { margin:0; font-family:'Inter',sans-serif; background:#f4f6fb; color:#243b53; -webkit-font-smoothing:antialiased; }
.layout { display:flex; min-height:100vh; }

/* Sidebar */
.sidebar { width:280px; flex-shrink:0; background:linear-gradient(180deg,#0f2545 0%,#132f5c 100%); color:#e8eef7; padding:1.4rem 1.1rem; position:sticky; top:0; height:100vh; overflow-y:auto; }
.sidebar h2 { font-size:1.05rem; color:#ffffff; margin:0 0 0.15rem; font-weight:800; display:flex; align-items:center; gap:8px; }
.sidebar h2 svg { width:19px; height:19px; flex-shrink:0; }
.sidebar .tagline { font-size:0.72rem; color:#93aecb; margin-bottom:1.3rem; letter-spacing:0.03em; }
.reset-btn { width:100%; display:flex; align-items:center; justify-content:center; gap:6px; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.18); color:#e8eef7; border-radius:7px; padding:7px 10px; font-size:0.78rem; font-weight:600; cursor:pointer; margin-bottom:1.2rem; transition:background 0.15s ease; }
.reset-btn svg { width:14px; height:14px; flex-shrink:0; }
.reset-btn:hover { background:rgba(255,255,255,0.18); }
.filter-block { margin-bottom:1.1rem; }
.filter-block h4 { font-size:0.74rem; text-transform:uppercase; letter-spacing:0.06em; color:#93aecb; margin:0 0 0.45rem; font-weight:700; display:flex; align-items:center; gap:6px; }
.filter-block h4 svg { width:14px; height:14px; flex-shrink:0; }
.filter-actions { display:flex; gap:0.4rem; margin-bottom:0.4rem; }
.filter-actions button { font-size:0.68rem; font-weight:600; border:1px solid rgba(255,255,255,0.2); background:rgba(255,255,255,0.06); color:#cfe0f5; border-radius:5px; padding:3px 9px; cursor:pointer; transition:background 0.15s ease; }
.filter-actions button:hover { background:rgba(255,255,255,0.16); }
.chk-list { max-height:130px; overflow-y:auto; border:1px solid rgba(255,255,255,0.12); border-radius:7px; padding:0.35rem 0.55rem; background:rgba(255,255,255,0.05); }
.chk { display:block; font-size:0.81rem; padding:3px 0; cursor:pointer; color:#dbe6f5; }
.chk input { margin-right:7px; accent-color:#2ad1c9; }

/* Searchable dropdown (Industry / Country) */
.dropdown-select { position:relative; }
.dropdown-toggle { width:100%; display:flex; align-items:center; justify-content:space-between; gap:8px; background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.2); color:#e8eef7; border-radius:7px; padding:8px 10px; font-size:0.82rem; cursor:pointer; text-align:left; transition:background 0.15s ease; }
.dropdown-toggle:hover { background:rgba(255,255,255,0.14); }
.dropdown-toggle span:first-child { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.dropdown-toggle .chevron svg { width:14px; height:14px; flex-shrink:0; transition:transform 0.15s ease; }
.dropdown-select.open .dropdown-toggle .chevron svg { transform:rotate(180deg); }
.dropdown-panel { position:fixed; z-index:200; display:none; background:#132f5c; border:1px solid rgba(255,255,255,0.18); border-radius:8px; padding:0.55rem; box-shadow:0 16px 32px rgba(5,15,35,0.45); }
.dropdown-select.open .dropdown-panel { display:block; }
.dropdown-search { width:100%; margin-bottom:0.45rem; padding:0.4rem 0.55rem; border-radius:6px; border:1.5px solid rgba(42,209,201,0.5); background:rgba(255,255,255,0.08); color:#fff; font-size:0.8rem; outline:none; }
.dropdown-search::placeholder { color:#8ba3c2; }
.dropdown-search:focus { border-color:#2ad1c9; box-shadow:0 0 0 3px rgba(42,209,201,0.18); }
.dropdown-panel .chk-list { max-height:230px; }
#companySearch { width:100%; padding:0.45rem 0.6rem; border:1.5px solid rgba(42,209,201,0.55); border-radius:7px; font-size:0.85rem; background:rgba(255,255,255,0.07); color:#fff; outline:none; }
#companySearch::placeholder { color:#8ba3c2; }
#companySearch:focus { border-color:#2ad1c9; box-shadow:0 0 0 3px rgba(42,209,201,0.18); }
.company-matches { max-height:160px; overflow-y:auto; margin-top:0.35rem; border-radius:6px; }
.company-match { display:block; width:100%; border:0; border-bottom:1px solid rgba(255,255,255,0.08); background:rgba(255,255,255,0.04); color:#cfe0f5; text-align:left; padding:0.4rem 0.5rem; cursor:pointer; font-size:0.78rem; }
.company-match:hover { background:rgba(42,209,201,0.18); color:#fff; }
.sidebar .caption { color:#7d99bb; }

main { flex:1; padding:1.6rem 2.2rem 3rem; max-width:1500px; }

/* Topbar */
.topbar { display:flex; gap:0.4rem; flex-wrap:wrap; padding:0.4rem; margin-bottom:1.5rem; position:sticky; top:0; background:rgba(244,246,251,0.92); backdrop-filter:blur(6px); z-index:5; border-radius:12px; box-shadow:0 2px 10px rgba(36,59,83,0.06); }
.tab-btn { background:none; border:none; font-weight:600; font-size:0.87rem; color:#52606d; padding:0.55rem 0.95rem; cursor:pointer; border-radius:8px; transition:all 0.15s ease; display:inline-flex; align-items:center; gap:6px; }
.tab-btn svg { width:15px; height:15px; flex-shrink:0; }
.tab-btn:hover { background:#e9eef7; color:#1d4e89; }
.tab-btn.active { color:#fff; background:linear-gradient(135deg,#1d4e89,#2a9d8f); box-shadow:0 4px 12px rgba(29,78,137,0.3); }
.tab-panel { display:none; animation:fadeIn 0.25s ease; }
.tab-panel.active { display:block; }
@keyframes fadeIn { from{opacity:0; transform:translateY(4px);} to{opacity:1; transform:translateY(0);} }

/* Hero */
.hero-banner { background:linear-gradient(120deg,#12315c 0%,#1d4e89 55%,#2a9d8f 130%); border-radius:14px; padding:2rem 2.3rem; margin-bottom:1.7rem; box-shadow:0 12px 28px rgba(18,49,92,0.25); position:relative; overflow:hidden; }
.hero-eyebrow { color:#8fe3d9; font-size:0.78rem; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; margin-bottom:0.35rem; }
.hero-title { color:#ffffff; font-size:2rem; font-weight:800; margin:0; letter-spacing:-0.01em; }
.hero-subtitle { color:#dce9f7; font-size:0.95rem; margin-top:0.5rem; max-width:900px; }

.section-header { font-size:1.15rem; font-weight:800; color:#102a43; padding-left:0.7rem; margin:1.2rem 0 0.9rem; position:relative; }
.section-header::before { content:""; position:absolute; left:0; top:2px; bottom:2px; width:4px; border-radius:3px; background:linear-gradient(180deg,#1d4e89,#2a9d8f); }

/* KPI cards */
.kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:14px; margin-bottom:1.3rem; }
.kpi-card { background:#ffffff; border:1px solid #e4ebf3; border-radius:12px; padding:1.05rem 1.2rem; box-shadow:0 4px 16px rgba(36,59,83,0.07); position:relative; overflow:hidden; transition:transform 0.18s ease, box-shadow 0.18s ease; }
.kpi-card:hover { transform:translateY(-3px); box-shadow:0 10px 24px rgba(36,59,83,0.14); }
.kpi-card::before { content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background:var(--accent,#1d4e89); }
.kpi-icon { color:var(--accent,#1d4e89); margin-bottom:0.5rem; display:inline-flex; }
.kpi-icon svg { width:22px; height:22px; }
.kpi-label { color:#627d98; font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.03em; }
.kpi-value { color:#102a43; font-size:1.55rem; font-weight:800; margin-top:0.2rem; letter-spacing:-0.01em; }
.kpi-sub { color:#9aa8bb; font-size:0.72rem; margin-top:0.2rem; }

.chart-grid-2 { display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:16px; margin-bottom:16px; }
.chart-card { background:#ffffff; border-radius:12px; padding:0.6rem 0.8rem; border:1px solid #e4ebf3; box-shadow:0 4px 16px rgba(36,59,83,0.07); overflow:hidden; transition:box-shadow 0.18s ease; }
.chart-card:hover { box-shadow:0 8px 22px rgba(36,59,83,0.12); }
.chart-card > div { width:100%; }
.notice { background:#fff8e6; border:1px solid #e9c46a; color:#7a5c00; padding:0.75rem 1rem; border-radius:10px; margin-bottom:1rem; font-size:0.9rem; }
.table-wrap { overflow-x:auto; background:#ffffff; border:1px solid #e4ebf3; border-radius:12px; padding:0.5rem; max-height:420px; overflow-y:auto; box-shadow:0 4px 16px rgba(36,59,83,0.07); }
.data-table { border-collapse:collapse; width:100%; font-size:0.83rem; }
.data-table th, .data-table td { padding:0.5rem 0.7rem; border-bottom:1px solid #eef2f6; text-align:left; white-space:nowrap; }
.data-table th { color:#627d98; text-transform:uppercase; font-size:0.68rem; letter-spacing:0.03em; position:sticky; top:0; background:#fff; }
.data-table tbody tr:hover { background:#f4f9ff; }
.data-table tbody tr:nth-child(even) { background:#fbfcfe; }
.caption { color:#829ab1; font-size:0.83rem; }
.site-footer { margin-top:2rem; padding-top:1rem; border-top:1px solid #e4ebf3; color:#829ab1; font-size:0.82rem; text-align:center; }
.site-footer a { color:#1d4e89; font-weight:600; text-decoration:none; }
.site-footer a:hover { text-decoration:underline; }
.empty-state { padding:2rem; text-align:center; color:#829ab1; font-size:0.95rem; }
.empty-state svg { width:20px; height:20px; vertical-align:-4px; margin-right:6px; }
h3 { color:#243b53; font-size:0.95rem; margin:0.4rem 0 0.6rem; font-weight:700; }
@media (max-width:900px) {
  .layout { flex-direction:column; }
  .sidebar { width:100%; height:auto; position:relative; }
  main { padding:1rem; min-width:0; }
  .chart-grid-2 { grid-template-columns:minmax(0,1fr); }
  .chart-card { min-width:0; }
  .topbar { overflow-x:auto; flex-wrap:nowrap; }
}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Tech Workforce Intelligence</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
{css}
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <h2>{icon_brand} Tech Workforce Intelligence</h2>
    <div class="tagline">Layoffs.fyi &middot; Analytics Suite</div>

    <button class="reset-btn" onclick="resetFilters()">{icon_refresh} Reset all filters</button>

    <div class="filter-block">
      <h4>{icon_calendar} Year</h4>
      <div class="filter-actions"><button onclick="setAll('year',true)">All</button><button onclick="setAll('year',false)">None</button></div>
      <div class="chk-list" id="yearList">{years_html}</div>
    </div>

    <div class="filter-block">
      <h4>{icon_briefcase} Industry</h4>
      <div class="dropdown-select" id="industryDropdown">
        <button type="button" class="dropdown-toggle" onclick="toggleDropdown('industry')">
          <span id="industrySummary">All industries</span>
          <span class="chevron">{icon_chevron}</span>
        </button>
        <div class="dropdown-panel">
          <input type="text" class="dropdown-search" placeholder="Search industry" oninput="filterDropdownOptions('industry', this.value)" />
          <div class="filter-actions"><button onclick="setAll('industry',true)">All</button><button onclick="setAll('industry',false)">None</button></div>
          <div class="chk-list" id="industryList">{industries_html}</div>
        </div>
      </div>
    </div>

    <div class="filter-block">
      <h4>{icon_globe} Country</h4>
      <div class="dropdown-select" id="countryDropdown">
        <button type="button" class="dropdown-toggle" onclick="toggleDropdown('country')">
          <span id="countrySummary">All countries</span>
          <span class="chevron">{icon_chevron}</span>
        </button>
        <div class="dropdown-panel">
          <input type="text" class="dropdown-search" placeholder="Search country" oninput="filterDropdownOptions('country', this.value)" />
          <div class="filter-actions"><button onclick="setAll('country',true)">All</button><button onclick="setAll('country',false)">None</button></div>
          <div class="chk-list" id="countryList">{countries_html}</div>
        </div>
      </div>
    </div>

    <div class="filter-block">
      <h4>{icon_cpu} AI Signal</h4>
      <div class="dropdown-select" id="aiDropdown">
        <button type="button" class="dropdown-toggle" onclick="toggleDropdown('ai')">
          <span id="aiSummary">All AI signals</span>
          <span class="chevron">{icon_chevron}</span>
        </button>
        <div class="dropdown-panel">
          <input type="text" class="dropdown-search" placeholder="Search AI signal" oninput="filterDropdownOptions('ai', this.value)" />
          <div class="filter-actions"><button onclick="setAll('ai',true)">All</button><button onclick="setAll('ai',false)">None</button></div>
          <div class="chk-list" id="aiList">{ai_html}</div>
        </div>
      </div>
    </div>

    <div class="filter-block">
      <h4>{icon_search} Company contains</h4>
      <input id="companySearch" type="text" placeholder="Search by company name" />
      <div id="companyMatches" class="company-matches"></div>
      <p id="searchStatus" class="caption"></p>
    </div>

    <p class="caption">Data through {current_max_date}. Filters apply instantly to every tab.</p>
  </aside>

  <main>
    <div class="hero-banner">
      <div class="hero-eyebrow">Executive Overview</div>
      <div class="hero-title">Global Tech Workforce Intelligence</div>
      <div class="hero-subtitle">Interactive dashboard, fully client-side, sourced from the cleaned Layoffs.fyi dataset.</div>
    </div>

    <div class="topbar">
      <button class="tab-btn active" data-tab="overview" onclick="showTab('overview')">{icon_home} Overview</button>
      <button class="tab-btn" data-tab="trends" onclick="showTab('trends')">{icon_trending} Trends</button>
      <button class="tab-btn" data-tab="companies" onclick="showTab('companies')">{icon_briefcase} Companies</button>
      <button class="tab-btn" data-tab="industry" onclick="showTab('industry')">{icon_globe} Industry &amp; Geo</button>
      <button class="tab-btn" data-tab="ai" onclick="showTab('ai')">{icon_cpu} AI Impact</button>
    </div>

    <div id="tab-overview" class="tab-panel active">
      <div class="section-header">Executive Overview</div>
      <div class="kpi-grid" id="overviewKpis"></div>
      <div class="chart-grid-2">
        <div class="chart-card"><div id="chartAnnual"></div></div>
        <div class="chart-card"><div id="chartMonthly"></div></div>
      </div>
      <div class="chart-grid-2">
        <div class="chart-card"><div id="chartTopCo"></div></div>
        <div class="chart-card"><div id="chartTopInd"></div></div>
      </div>
      <div class="chart-card"><div id="chartGeo"></div></div>
    </div>

    <div id="tab-trends" class="tab-panel">
      <div class="section-header">Workforce Trends</div>
      <div class="chart-grid-2">
        <div class="chart-card"><div id="chartYoy"></div></div>
        <div class="chart-card"><div id="chartEvents"></div></div>
      </div>
      <div class="chart-grid-2">
        <div class="chart-card"><div id="chartAvgSize"></div></div>
        <div class="chart-card"><div id="chartRolling"></div></div>
      </div>
    </div>

    <div id="tab-companies" class="tab-panel">
      <div class="section-header">Company Intelligence</div>
      <div class="chart-grid-2">
        <div class="chart-card"><div id="chartTop15"></div></div>
        <div class="chart-card"><div id="chartRepeat"></div></div>
      </div>
      <h3>Largest Individual Layoff Events</h3>
      <div class="table-wrap" id="largestEventsTable"></div>
      <h3 style="margin-top:1rem;">Cumulative Layoffs Over Time (Top 5 Companies)</h3>
      <div class="chart-card"><div id="chartCumulative"></div></div>
    </div>

    <div id="tab-industry" class="tab-panel">
      <div class="section-header">Industry &amp; Geography</div>
      <div class="chart-grid-2">
        <div class="chart-card"><div id="chartIndRank"></div></div>
        <div class="chart-card"><div id="chartCtryRank"></div></div>
      </div>
      <div class="chart-card"><div id="chartIndYear"></div></div>
    </div>

    <div id="tab-ai" class="tab-panel">
      <div class="section-header">AI Workforce Impact</div>
      <div class="notice">{ai_method_note}</div>
      <div class="kpi-grid" id="aiKpis"></div>
      <div class="chart-grid-2">
        <div class="chart-card"><div id="chartAiPie"></div></div>
        <div class="chart-card"><div id="chartAiYear"></div></div>
      </div>
      <div class="chart-card"><div id="chartAiInd"></div></div>
    </div>

    <footer class="site-footer">Data source: <a href="https://layoffs.fyi" target="_blank" rel="noopener">Layoffs.fyi</a>. This project is an independent analysis and is not affiliated with or endorsed by Layoffs.fyi.</footer>
  </main>
</div>

<script>
const RAW_DATA = {data_json};
const COLORWAY = ["#1D4E89","#E76F51","#2A9D8F","#E9C46A","#8E44AD","#F4A261","#C0392B","#935116","#34495E","#D4AC0D"];
const BASE_LAYOUT = {{
  paper_bgcolor:"#ffffff", plot_bgcolor:"#ffffff",
  font:{{family:"Inter, sans-serif", color:"#334e68", size:12}},
  title:{{font:{{family:"Inter, sans-serif", color:"#102a43", size:15}}, x:0.02, xanchor:"left", y:0.97, yanchor:"top", pad:{{b:10}}}},
  margin:{{l:60, r:24, t:64, b:56}},
  colorway: COLORWAY,
  legend:{{orientation:"h", yanchor:"top", y:-0.18, xanchor:"center", x:0.5}},
  hovermode:"closest",
  hoverlabel:{{bgcolor:"#102a43", bordercolor:"#102a43", font:{{color:"#ffffff", size:12}}}},
  xaxis:{{gridcolor:"#eef2f6", zerolinecolor:"#e4ebf3", linecolor:"#d9e2ec"}},
  yaxis:{{gridcolor:"#eef2f6", zerolinecolor:"#e4ebf3", linecolor:"#d9e2ec"}},
}};
const PLOTLY_CONFIG = {{responsive:true, displaylogo:false, displayModeBar:false}};

function showTab(name) {{
  document.querySelectorAll(".tab-panel").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  document.querySelector(`.tab-btn[data-tab="${{name}}"]`).classList.add("active");
  window.dispatchEvent(new Event("resize"));
}}

function setAll(group, checked) {{
  document.querySelectorAll(`input[data-group="${{group}}"]`).forEach(cb => cb.checked = checked);
  render();
}}

function resetFilters() {{
  document.querySelectorAll('input[type="checkbox"][data-group="year"]').forEach(cb => cb.checked = true);
  document.querySelectorAll('input[type="checkbox"]:not([data-group="year"])').forEach(cb => cb.checked = false);
  const input = document.getElementById("companySearch");
  input.value = "";
  delete input.dataset.selectedCompany;
  render();
}}

function toggleDropdown(name) {{
  const wrapper = document.getElementById(name + "Dropdown");
  const panel = wrapper.querySelector(".dropdown-panel");
  const isOpen = wrapper.classList.contains("open");
  document.querySelectorAll(".dropdown-select.open").forEach(w => w.classList.remove("open"));
  if (isOpen) return;
  const btnRect = wrapper.querySelector(".dropdown-toggle").getBoundingClientRect();
  panel.style.top = (btnRect.bottom + 6) + "px";
  panel.style.left = btnRect.left + "px";
  panel.style.width = btnRect.width + "px";
  wrapper.classList.add("open");
  const search = panel.querySelector(".dropdown-search");
  search.value = "";
  filterDropdownOptions(name, "");
  search.focus();
}}

function filterDropdownOptions(name, query) {{
  const q = query.trim().toLowerCase();
  document.querySelectorAll(`#${{name}}List .chk`).forEach(label => {{
    label.style.display = !q || label.textContent.trim().toLowerCase().includes(q) ? "" : "none";
  }});
}}

function updateDropdownSummary(name, label) {{
  const summaryEl = document.getElementById(name + "Summary");
  if (!summaryEl) return;
  const total = document.querySelectorAll(`input[data-group="${{name}}"]`).length;
  const checked = document.querySelectorAll(`input[data-group="${{name}}"]:checked`).length;
  summaryEl.textContent = (checked === 0 || checked === total) ? `All ${{label}}` : `${{checked}} of ${{total}} selected`;
}}

document.addEventListener("click", event => {{
  document.querySelectorAll(".dropdown-select.open").forEach(wrapper => {{
    if (!wrapper.contains(event.target)) wrapper.classList.remove("open");
  }});
}}, true);

function getChecked(group) {{
  return Array.from(document.querySelectorAll(`input[data-group="${{group}}"]:checked`)).map(cb => cb.value);
}}

function sumBy(arr, keyFn) {{
  const map = new Map();
  for (const row of arr) {{
    const k = keyFn(row);
    const v = row["Employees Laid Off"];
    if (v === null || v === undefined) continue;
    map.set(k, (map.get(k) || 0) + v);
  }}
  return map;
}}

function countBy(arr, keyFn) {{
  const map = new Map();
  for (const row of arr) {{
    const k = keyFn(row);
    map.set(k, (map.get(k) || 0) + 1);
  }}
  return map;
}}

function sortedEntries(map, desc=true) {{
  return Array.from(map.entries()).sort((a,b) => desc ? b[1]-a[1] : a[1]-b[1]);
}}

function fmt(n) {{ return Math.round(n).toLocaleString("en-US"); }}

function fmtCompact(n) {{
  const abs = Math.abs(n);
  if (abs >= 1e6) return (n/1e6).toFixed(abs >= 1e7 ? 1 : 2).replace(/\\.0+$/,"") + "M";
  if (abs >= 1e3) return (n/1e3).toFixed(abs >= 1e4 ? 0 : 1).replace(/\\.0+$/,"") + "K";
  return fmt(n);
}}

function kpiCard(icon, label, value, accent, sub) {{
  return `<div class="kpi-card" style="--accent:${{accent}}">`
    + `<div class="kpi-icon">${{icon}}</div>`
    + `<div class="kpi-label">${{label}}</div>`
    + `<div class="kpi-value">${{value}}</div>`
    + (sub ? `<div class="kpi-sub">${{sub}}</div>` : "")
    + `</div>`;
}}

function plot(divId, traces, layoutExtra) {{
  // Plotly mutates layout sub-objects (ranges, types) in place, so each
  // chart needs its own deep-cloned copy of BASE_LAYOUT to stay isolated.
  const base = JSON.parse(JSON.stringify(BASE_LAYOUT));
  const layout = Object.assign({{}}, base, layoutExtra);
  layout.xaxis = Object.assign({{}}, base.xaxis, layoutExtra.xaxis || {{}});
  layout.yaxis = Object.assign({{}}, base.yaxis, layoutExtra.yaxis || {{}});
  layout.legend = Object.assign({{}}, base.legend, layoutExtra.legend || {{}});
  if (typeof layoutExtra.title === "string") {{
    layout.title = Object.assign({{}}, base.title, {{text: layoutExtra.title}});
  }}
  const hasLegend = traces.length > 1 || traces.some(trace => trace.name || trace.type === "pie");
  const tickAngled = layout.xaxis.tickangle ? 24 : 0;
  layout.showlegend = hasLegend;
  layout.margin = Object.assign({{}}, base.margin, layoutExtra.margin || {{}},
    {{b:(layoutExtra.margin && layoutExtra.margin.b) || (base.margin.b + (hasLegend ? 40 : 0) + tickAngled)}});
  if (traces.some(trace => trace.orientation === "h")) {{
    layout.margin.l = 150;
  }}
  Plotly.newPlot(divId, traces, layout, PLOTLY_CONFIG);
}}

function applyFilters() {{
  const years = new Set(getChecked("year"));
  const industries = new Set(getChecked("industry"));
  const countries = new Set(getChecked("country"));
  const aiCats = new Set(getChecked("ai"));
  const selectedCompany = document.getElementById("companySearch").dataset.selectedCompany || "";

  return RAW_DATA.filter(row => {{
    if (!years.has(String(row["Year"]))) return false;
    if (industries.size && !industries.has(String(row["Industry"]))) return false;
    if (countries.size && !countries.has(String(row["Country"]))) return false;
    if (aiCats.size && !aiCats.has(String(row["AI_Signal_Category"]))) return false;
    if (selectedCompany && row["Company"] !== selectedCompany) return false;
    return true;
  }});
}}

function render() {{
  updateDropdownSummary("industry", "industries");
  updateDropdownSummary("country", "countries");
  updateDropdownSummary("ai", "AI signals");
  const fdf = applyFilters();
  const search = document.getElementById("companySearch").value.trim();
  const selectedCompany = document.getElementById("companySearch").dataset.selectedCompany || "";
  const matches = [...new Set(RAW_DATA
    .map(row => row["Company"])
    .filter(company => company && company.toLowerCase().includes(search.toLowerCase())))]
    .sort()
    .slice(0, 20);
  const matchesEl = document.getElementById("companyMatches");
  matchesEl.innerHTML = search && !selectedCompany
    ? matches.map(company => `<button type="button" class="company-match" data-company="${{company.replace(/"/g, '&quot;')}}">${{company}}</button>`).join("")
    : "";
  matchesEl.querySelectorAll(".company-match").forEach(button => button.addEventListener("click", () => {{
    const company = button.dataset.company;
    const input = document.getElementById("companySearch");
    input.value = company;
    input.dataset.selectedCompany = company;
    render();
  }}));
  const matchingCompanies = new Set(fdf.map(row => row["Company"])).size;
  document.getElementById("searchStatus").textContent = selectedCompany
    ? `Selected company: ${{selectedCompany}} (${{fdf.length.toLocaleString("en-US")}} records)`
    : search
      ? `Select a company from the list (${{matches.length.toLocaleString("en-US")}} matches shown)`
      : "";
  if (!fdf.length) {{
    document.querySelectorAll(".chart-card > div, #largestEventsTable").forEach(el => el.innerHTML = "");
    document.getElementById("overviewKpis").innerHTML = "<div class='empty-state'>{icon_search} No records match the current filters.</div>";
    document.getElementById("aiKpis").innerHTML = "";
    return;
  }}
  const reported = fdf.filter(r => r["Employees Laid Off"] !== null && r["Employees Laid Off"] !== undefined);

  renderOverview(fdf, reported);
  renderTrends(reported);
  renderCompanies(reported);
  renderIndustryGeo(reported);
  renderAi(fdf, reported);
}}

function renderOverview(fdf, reported) {{
  const totalEmp = reported.reduce((s,r)=>s+r["Employees Laid Off"],0);
  const totalEvents = fdf.length;
  const companies = new Set(fdf.map(r=>r["Company"])).size;
  const avgSize = reported.length ? totalEmp/reported.length : 0;
  const largest = reported.length ? Math.max(...reported.map(r=>r["Employees Laid Off"])) : 0;
  const aiEmp = reported.filter(r=>r["AI_Signal_Category"]==="Explicit AI-related (source-labeled)").reduce((s,r)=>s+r["Employees Laid Off"],0);

  document.getElementById("overviewKpis").innerHTML = [
    kpiCard("{icon_users}", "Total Employees Laid Off", fmtCompact(totalEmp), "#1D4E89", fmt(totalEmp) + " exact"),
    kpiCard("{icon_clipboard}", "Total Layoff Events", totalEvents.toLocaleString("en-US"), "#2A9D8F", "reported incidents"),
    kpiCard("{icon_briefcase}", "Companies Affected", companies.toLocaleString("en-US"), "#E76F51", "unique employers"),
    kpiCard("{icon_trending}", "Avg Layoff Size", fmt(avgSize), "#E9C46A", "employees per event"),
    kpiCard("{icon_zap}", "Largest Single Event", fmt(largest), "#457B9D", "peak workforce cut"),
    kpiCard("{icon_cpu}", "AI-Related Layoffs (explicit)", fmtCompact(aiEmp), "#6C5B7B", "source-labeled only"),
  ].join("");

  const annual = sortedEntries(sumBy(reported, r=>r["Year"]), false).sort((a,b)=>a[0]-b[0]);
  plot("chartAnnual", [{{x:annual.map(e=>e[0]), y:annual.map(e=>e[1]), type:"bar",
    marker:{{color:"#1D4E89", line:{{color:"#ffffff", width:0.5}}}},
    hovertemplate:"%{{x}}<br>%{{y:,}} employees<extra></extra>"}}],
    {{title:"Annual Layoff Trend"}});

  const monthly = sortedEntries(sumBy(reported, r=>r["Year_Month"]), false).sort((a,b)=>a[0]<b[0]?-1:1);
  plot("chartMonthly", [{{x:monthly.map(e=>e[0]), y:monthly.map(e=>e[1]), type:"scatter", mode:"lines", fill:"tozeroy",
    fillcolor:"rgba(29,78,137,0.08)", line:{{color:"#1D4E89", width:2.5}},
    hovertemplate:"%{{x}}<br>%{{y:,}} employees<extra></extra>"}}],
    {{title:"Monthly Layoff Trend", xaxis:{{tickangle:45}}}});

  const topCo = sortedEntries(sumBy(reported, r=>r["Company"])).slice(0,10).reverse();
  plot("chartTopCo", [{{x:topCo.map(e=>e[1]), y:topCo.map(e=>e[0]), type:"bar", orientation:"h",
    marker:{{color:"#2A9D8F", line:{{color:"#ffffff", width:0.5}}}},
    hovertemplate:"%{{y}}<br>%{{x:,}} employees<extra></extra>"}}],
    {{title:"Top 10 Companies"}});

  const topInd = sortedEntries(sumBy(reported, r=>r["Industry"])).slice(0,10).reverse();
  plot("chartTopInd", [{{x:topInd.map(e=>e[1]), y:topInd.map(e=>e[0]), type:"bar", orientation:"h",
    marker:{{color:"#E76F51", line:{{color:"#ffffff", width:0.5}}}},
    hovertemplate:"%{{y}}<br>%{{x:,}} employees<extra></extra>"}}],
    {{title:"Top Industries"}});

  const geo = sortedEntries(sumBy(reported, r=>r["Country"]));
  plot("chartGeo", [{{
    type:"choropleth", locationmode:"country names",
    locations:geo.map(e=>e[0]), z:geo.map(e=>e[1]),
    colorscale:[[0,"#e3f0ff"],[0.5,"#5b8fc9"],[1,"#12315c"]],
    marker:{{line:{{color:"#ffffff", width:0.8}}}},
    colorbar:{{title:"Employees", thickness:14}},
    hovertemplate:"%{{location}}<br>%{{z:,}} employees<extra></extra>",
  }}], {{title:"Geographic Distribution by Country", height:560, geo:{{showframe:false, showcountries:true, countrycolor:"#ffffff", showcoastlines:true, coastlinecolor:"#bcccdc", bgcolor:"#ffffff"}}}});
}}

function renderTrends(reported) {{
  const byYear = new Map();
  for (const r of reported) {{
    const y = r["Year"];
    if (!byYear.has(y)) byYear.set(y, {{emp:0, events:0}});
    const o = byYear.get(y);
    o.emp += r["Employees Laid Off"];
    o.events += 1;
  }}
  const years = Array.from(byYear.keys()).sort((a,b)=>a-b);
  const emp = years.map(y=>byYear.get(y).emp);
  const events = years.map(y=>byYear.get(y).events);
  const avgSize = years.map(y=>byYear.get(y).emp/byYear.get(y).events);
  const yoyPct = emp.map((v,i)=> i===0 ? null : ((v-emp[i-1])/emp[i-1]*100));

  plot("chartYoy", [{{x:years, y:yoyPct, type:"bar", marker:{{color:"#2A9D8F"}}}}], {{title:"YoY % Change"}});
  plot("chartEvents", [{{x:years, y:events, type:"scatter", mode:"lines+markers", line:{{color:"#E76F51"}}}}], {{title:"Layoff Events per Year"}});
  plot("chartAvgSize", [{{x:years, y:avgSize, type:"scatter", mode:"lines+markers", line:{{color:"#E9C46A"}}}}], {{title:"Average Layoff Size per Event"}});

  const monthlyMap = sortedEntries(sumBy(reported, r=>r["Year_Month"]), false).sort((a,b)=>a[0]<b[0]?-1:1);
  const mLabels = monthlyMap.map(e=>e[0]);
  const mVals = monthlyMap.map(e=>e[1]);
  const roll = (arr, w) => arr.map((_,i)=> i<w-1 ? null : arr.slice(i-w+1,i+1).reduce((a,b)=>a+b,0)/w);
  plot("chartRolling", [
    {{x:mLabels, y:mVals, type:"scatter", mode:"lines", name:"Employees Laid Off", line:{{color:"#bcccdc"}}}},
    {{x:mLabels, y:roll(mVals,3), type:"scatter", mode:"lines", name:"Rolling 3M", line:{{color:"#2A9D8F"}}}},
    {{x:mLabels, y:roll(mVals,12), type:"scatter", mode:"lines", name:"Rolling 12M", line:{{color:"#1D4E89"}}}},
  ], {{title:"Monthly Layoffs with 3M / 12M Rolling Average", xaxis:{{tickangle:45}}}});
}}

function renderCompanies(reported) {{
  const totals = sumBy(reported, r=>r["Company"]);
  const counts = countBy(reported, r=>r["Company"]);
  const ranked = sortedEntries(totals);

  const top15 = ranked.slice(0,15).reverse();
  plot("chartTop15", [{{x:top15.map(e=>e[1]), y:top15.map(e=>e[0]), type:"bar", orientation:"h", marker:{{color:"#1D4E89"}}}}],
    {{title:"Top Companies by Total Layoffs"}});

  const repeated = ranked.filter(([name])=>counts.get(name)>1)
    .map(([name])=>[name, counts.get(name)])
    .sort((a,b)=>b[1]-a[1]).slice(0,15).reverse();
  plot("chartRepeat", [{{x:repeated.map(e=>e[1]), y:repeated.map(e=>e[0]), type:"bar", orientation:"h", marker:{{color:"#E76F51"}}}}],
    {{title:"Companies with Repeated Layoff Events"}});

  const largest = [...reported].sort((a,b)=>b["Employees Laid Off"]-a["Employees Laid Off"]).slice(0,20);
  const headers = ["Company","Date","Employees Laid Off","Percentage Laid Off","Industry","Country"];
  let tbl = "<table class='data-table'><thead><tr>" + headers.map(h=>`<th>${{h}}</th>`).join("") + "</tr></thead><tbody>";
  for (const row of largest) {{
    tbl += "<tr>" + headers.map(h => `<td>${{row[h] ?? ""}}</td>`).join("") + "</tr>";
  }}
  tbl += "</tbody></table>";
  document.getElementById("largestEventsTable").innerHTML = tbl;

  const top5Names = new Set(ranked.slice(0,5).map(e=>e[0]));
  const byCompanySorted = [...reported].filter(r=>top5Names.has(r["Company"])).sort((a,b)=> a["Date"] < b["Date"] ? -1 : 1);
  const running = new Map();
  const traceData = new Map();
  for (const r of byCompanySorted) {{
    const name = r["Company"];
    running.set(name, (running.get(name)||0) + r["Employees Laid Off"]);
    if (!traceData.has(name)) traceData.set(name, {{x:[], y:[]}});
    traceData.get(name).x.push(r["Date"]);
    traceData.get(name).y.push(running.get(name));
  }}
  // Order by final total (highest first) so legend and end labels read top-to-bottom by rank.
  const orderedNames = Array.from(traceData.keys())
    .sort((a,b) => traceData.get(b).y.at(-1) - traceData.get(a).y.at(-1));
  const cumTraces = orderedNames.map((name, i) => {{
    const d = traceData.get(name);
    return {{
      x:d.x, y:d.y, type:"scatter", mode:"lines", name,
      line:{{color: COLORWAY[i % COLORWAY.length], width:2.5}},
      hovertemplate: `<b>${{name}}</b><br>%{{x}}<br>%{{y:,}} cumulative<extra></extra>`,
    }};
  }});
  const endLabels = orderedNames.map((name, i) => {{
    const d = traceData.get(name);
    return {{
      x:d.x.at(-1), y:d.y.at(-1), xref:"x", yref:"y", text:`  ${{name}}`, showarrow:false,
      xanchor:"left", yanchor:"middle", font:{{size:11, color:COLORWAY[i % COLORWAY.length]}},
    }};
  }});
  plot("chartCumulative", cumTraces, {{
    title:"Cumulative Layoffs: Top 5 Companies (ranked by total, labeled at line end)",
    height:480, margin:{{r:130}}, annotations: endLabels,
  }});
}}

function renderIndustryGeo(reported) {{
  const ind = sortedEntries(sumBy(reported, r=>r["Industry"])).reverse();
  plot("chartIndRank", [{{x:ind.map(e=>e[1]), y:ind.map(e=>e[0]), type:"bar", orientation:"h", marker:{{color:"#1D4E89"}}}}],
    {{title:"Industry Ranking"}});

  const ctry = sortedEntries(sumBy(reported, r=>r["Country"])).slice(0,20).reverse();
  plot("chartCtryRank", [{{x:ctry.map(e=>e[1]), y:ctry.map(e=>e[0]), type:"bar", orientation:"h", marker:{{color:"#2A9D8F"}}}}],
    {{title:"Country Ranking (Top 20)"}});

  const indYearMap = new Map();
  const allYears = new Set();
  for (const r of reported) {{
    const ind2 = r["Industry"];
    if (!indYearMap.has(ind2)) indYearMap.set(ind2, new Map());
    indYearMap.get(ind2).set(r["Year"], (indYearMap.get(ind2).get(r["Year"])||0) + r["Employees Laid Off"]);
    allYears.add(r["Year"]);
  }}
  // Heatmap instead of a multi-line chart: 30 industries as overlapping lines
  // is unreadable, a matrix of industry x year makes spikes easy to scan.
  const years = Array.from(allYears).sort((a,b)=>a-b);
  const industriesByTotal = Array.from(indYearMap.entries())
    .map(([name, yMap]) => [name, Array.from(yMap.values()).reduce((a,b)=>a+b,0)])
    .sort((a,b)=>a[1]-b[1])
    .map(([name])=>name);
  const z = industriesByTotal.map(name => years.map(y => indYearMap.get(name).get(y) || 0));
  plot("chartIndYear", [{{
    type:"heatmap", x:years, y:industriesByTotal, z,
    colorscale:[[0,"#eef4fb"],[0.5,"#5b8fc9"],[1,"#12315c"]],
    hovertemplate:"%{{y}}, %{{x}}<br>%{{z:,}} employees<extra></extra>",
    colorbar:{{title:"Employees", thickness:14}},
  }}], {{title:"Industry x Year Heatmap", height:640, margin:{{l:140}},
    xaxis:{{type:"category", dtick:1}}}});
}}

function renderAi(fdf, reported) {{
  const aiCounts = countBy(fdf, r=>r["AI_Signal_Category"]);
  const explicit = reported.filter(r=>r["AI_Signal_Category"]==="Explicit AI-related (source-labeled)");
  const aiEmp = explicit.reduce((s,r)=>s+r["Employees Laid Off"],0);
  const totalEmp = reported.reduce((s,r)=>s+r["Employees Laid Off"],0);
  const aiPct = totalEmp ? (aiEmp/totalEmp*100) : 0;

  document.getElementById("aiKpis").innerHTML = [
    kpiCard("{icon_cpu}", "Explicit AI-Related Events", explicit.length.toLocaleString("en-US"), "#1D4E89", "reported incidents"),
    kpiCard("{icon_users}", "Explicit AI-Related Employees Affected", fmtCompact(aiEmp), "#2A9D8F", fmt(aiEmp) + " exact"),
    kpiCard("{icon_trending}", "AI-Related % of Total Employees (explicit only)", aiPct.toFixed(1)+"%", "#E76F51", "share of filtered total"),
  ].join("");

  const pieEntries = Array.from(aiCounts.entries());
  const pieTotal = pieEntries.reduce((s,e)=>s+e[1],0);
  plot("chartAiPie", [{{labels:pieEntries.map(e=>e[0]), values:pieEntries.map(e=>e[1]), type:"pie", hole:0.58,
    marker:{{colors:COLORWAY, line:{{color:"#ffffff", width:2}}}},
    textinfo:"percent", hovertemplate:"%{{label}}<br>%{{value:,}} records<extra></extra>"}}],
    {{title:"AI Signal Breakdown (all records)",
      annotations:[{{text:`${{pieTotal.toLocaleString("en-US")}}<br>records`, showarrow:false, font:{{size:15, color:"#102a43"}}}}]}});

  const aiYear = sortedEntries(sumBy(explicit, r=>r["Year"]), false).sort((a,b)=>a[0]-b[0]);
  plot("chartAiYear", [{{x:aiYear.map(e=>e[0]), y:aiYear.map(e=>e[1]), type:"bar", marker:{{color:"#1D4E89"}}}}],
    {{title:"Explicit AI-Related Layoffs by Year"}});

  const aiInd = sortedEntries(sumBy(explicit, r=>r["Industry"])).slice(0,10).reverse();
  plot("chartAiInd", [{{x:aiInd.map(e=>e[1]), y:aiInd.map(e=>e[0]), type:"bar", orientation:"h", marker:{{color:"#E76F51"}}}}],
    {{title:"Industries with Strongest Explicit AI Signal"}});
}}

document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.addEventListener("change", render));
document.getElementById("companySearch").addEventListener("input", event => {{
  if (event.target.value !== event.target.dataset.selectedCompany) delete event.target.dataset.selectedCompany;
  render();
}});
render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
