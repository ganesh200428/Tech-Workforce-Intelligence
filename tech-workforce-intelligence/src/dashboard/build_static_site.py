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
DQ_PATH = ROOT / "docs" / "data_quality.md"
OUT_DIR = ROOT / "netlify_site"
OUT_PATH = OUT_DIR / "index.html"

AI_METHOD_NOTE = (
    "AI-related classification identifies signals in available source "
    "information and does not establish that AI directly caused a layoff."
)


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

    dq_text = DQ_PATH.read_text(encoding="utf-8") if DQ_PATH.exists() else ""

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
        dq_text=dq_text,
        css=CSS,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* { box-sizing: border-box; }
body { margin:0; font-family:'Inter',sans-serif; background:#fbfaf7; color:#243b53; }
.layout { display:flex; min-height:100vh; }
.sidebar { width:270px; flex-shrink:0; background:#ffffff; border-right:1px solid #d9e2ec; padding:1.2rem 1rem; position:sticky; top:0; height:100vh; overflow-y:auto; }
.sidebar h2 { font-size:1rem; color:#102a43; margin:0 0 0.2rem; }
.sidebar .tagline { font-size:0.75rem; color:#829ab1; margin-bottom:1rem; }
.filter-block { margin-bottom:1.1rem; }
.filter-block h4 { font-size:0.78rem; text-transform:uppercase; letter-spacing:0.04em; color:#52606d; margin:0 0 0.4rem; }
.filter-actions { display:flex; gap:0.4rem; margin-bottom:0.4rem; }
.filter-actions button { font-size:0.7rem; border:1px solid #bcccdc; background:#f0f4f8; color:#1d4e89; border-radius:5px; padding:2px 7px; cursor:pointer; }
.filter-actions button:hover { background:#e3f0ff; }
.chk-list { max-height:130px; overflow-y:auto; border:1px solid #eef2f6; border-radius:6px; padding:0.3rem 0.5rem; background:#fbfdff; }
.chk { display:block; font-size:0.82rem; padding:2px 0; cursor:pointer; }
.chk input { margin-right:6px; }
#companySearch { width:100%; padding:0.4rem 0.5rem; border:2px solid #2a9d8f; border-radius:6px; font-size:0.85rem; }
main { flex:1; padding:1.5rem 2rem 3rem; max-width:1400px; }
.topbar { display:flex; gap:1rem; flex-wrap:wrap; border-bottom:1px solid #d9e2ec; padding-bottom:0.6rem; margin-bottom:1.4rem; position:sticky; top:0; background:#fbfaf7; z-index:5; }
.tab-btn { background:none; border:none; font-weight:600; font-size:0.92rem; color:#52606d; padding:0.5rem 0.2rem; cursor:pointer; border-bottom:3px solid transparent; }
.tab-btn.active { color:#1d4e89; border-bottom-color:#1d4e89; }
.tab-panel { display:none; }
.tab-panel.active { display:block; }
.hero-banner { background:#ffffff; border:1px solid #d9e2ec; border-left:6px solid #1d4e89; border-radius:10px; padding:1.8rem 2.2rem; margin-bottom:1.6rem; box-shadow:0 8px 24px rgba(36,59,83,0.1); }
.hero-eyebrow { color:#1d4e89; font-size:0.82rem; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:0.3rem; }
.hero-title { color:#102a43; font-size:1.9rem; font-weight:800; margin:0; }
.hero-subtitle { color:#52606d; font-size:0.95rem; margin-top:0.5rem; max-width:900px; }
.section-header { font-size:1.1rem; font-weight:700; color:#243b53; border-left:4px solid #2a9d8f; padding-left:0.6rem; margin:1.1rem 0 0.8rem; }
.kpi-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:1.2rem; }
.kpi-card { background:#ffffff; border:1px solid #d9e2ec; border-top:3px solid var(--accent,#1d4e89); border-radius:8px; padding:1rem 1.1rem; box-shadow:0 4px 14px rgba(36,59,83,0.08); }
.kpi-label { color:#52606d; font-size:0.74rem; font-weight:600; text-transform:uppercase; letter-spacing:0.03em; }
.kpi-value { color:#102a43; font-size:1.45rem; font-weight:800; margin-top:0.15rem; }
.chart-grid-2 { display:grid; grid-template-columns:repeat(auto-fit,minmax(420px,1fr)); gap:16px; margin-bottom:16px; }
.chart-card { background:#ffffff; border-radius:8px; padding:0.4rem 0.6rem; border:1px solid #d9e2ec; box-shadow:0 4px 14px rgba(36,59,83,0.08); overflow:hidden; }
.chart-card > div { width:100%; }
.notice { background:#fff8e6; border:1px solid #e9c46a; color:#7a5c00; padding:0.75rem 1rem; border-radius:8px; margin-bottom:1rem; font-size:0.9rem; }
.table-wrap { overflow-x:auto; background:#ffffff; border:1px solid #d9e2ec; border-radius:8px; padding:0.5rem; max-height:420px; overflow-y:auto; }
.data-table { border-collapse:collapse; width:100%; font-size:0.83rem; }
.data-table th, .data-table td { padding:0.4rem 0.65rem; border-bottom:1px solid #eef2f6; text-align:left; white-space:nowrap; }
.data-table th { color:#52606d; text-transform:uppercase; font-size:0.7rem; letter-spacing:0.03em; position:sticky; top:0; background:#fff; }
.caption { color:#829ab1; font-size:0.83rem; }
.markdown { background:#ffffff; border:1px solid #d9e2ec; border-radius:8px; padding:1rem 1.4rem; white-space:pre-wrap; font-size:0.9rem; line-height:1.5; }
.empty-state { padding:2rem; text-align:center; color:#829ab1; font-size:0.95rem; }
h3 { color:#243b53; font-size:0.95rem; margin:0.4rem 0 0.6rem; }
@media (max-width:900px) {
  .layout { flex-direction:column; }
  .sidebar { width:100%; height:auto; position:relative; }
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
    <h2>Tech Workforce Intelligence</h2>
    <div class="tagline">Layoffs.fyi &middot; Analytics Suite</div>

    <div class="filter-block">
      <h4>Year</h4>
      <div class="filter-actions"><button onclick="setAll('year',true)">All</button><button onclick="setAll('year',false)">None</button></div>
      <div class="chk-list" id="yearList">{years_html}</div>
    </div>

    <div class="filter-block">
      <h4>Industry</h4>
      <div class="filter-actions"><button onclick="setAll('industry',true)">All</button><button onclick="setAll('industry',false)">None</button></div>
      <div class="chk-list" id="industryList">{industries_html}</div>
    </div>

    <div class="filter-block">
      <h4>Country</h4>
      <div class="filter-actions"><button onclick="setAll('country',true)">All</button><button onclick="setAll('country',false)">None</button></div>
      <div class="chk-list" id="countryList">{countries_html}</div>
    </div>

    <div class="filter-block">
      <h4>AI Signal</h4>
      <div class="filter-actions"><button onclick="setAll('ai',true)">All</button><button onclick="setAll('ai',false)">None</button></div>
      <div class="chk-list" id="aiList">{ai_html}</div>
    </div>

    <div class="filter-block">
      <h4>Company contains</h4>
      <input id="companySearch" type="text" placeholder="Search by company name" />
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
      <button class="tab-btn active" data-tab="overview" onclick="showTab('overview')">1. Overview</button>
      <button class="tab-btn" data-tab="trends" onclick="showTab('trends')">2. Trends</button>
      <button class="tab-btn" data-tab="companies" onclick="showTab('companies')">3. Companies</button>
      <button class="tab-btn" data-tab="industry" onclick="showTab('industry')">4. Industry &amp; Geo</button>
      <button class="tab-btn" data-tab="ai" onclick="showTab('ai')">5. AI Impact</button>
      <button class="tab-btn" data-tab="methodology" onclick="showTab('methodology')">6. Methodology</button>
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
      <h3 style="margin-top:1rem;">Cumulative Layoffs Over Time (Top 10 Companies)</h3>
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

    <div id="tab-methodology" class="tab-panel">
      <div class="section-header">Data &amp; Methodology</div>
      <div class="markdown">{dq_text}</div>
      <p class="caption">Layoffs.fyi is the original source and data owner. This project is an independent analysis and is not affiliated with or endorsed by Layoffs.fyi.</p>
    </div>
  </main>
</div>

<script>
const RAW_DATA = {data_json};
const COLORWAY = ["#1D4E89","#2A9D8F","#E76F51","#E9C46A","#457B9D","#6C5B7B","#4D908E","#F4A261","#577590","#264653"];
const BASE_LAYOUT = {{
  paper_bgcolor:"#ffffff", plot_bgcolor:"#ffffff",
  font:{{family:"Inter, sans-serif", color:"#243b53", size:12}},
  margin:{{l:60, r:24, t:56, b:52}},
  colorway: COLORWAY,
  legend:{{orientation:"h", yanchor:"bottom", y:1.02, xanchor:"right", x:1}},
}};
const PLOTLY_CONFIG = {{responsive:true, displaylogo:false}};

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

function kpiCard(label, value, accent) {{
  return `<div class="kpi-card" style="--accent:${{accent}}"><div class="kpi-label">${{label}}</div><div class="kpi-value">${{value}}</div></div>`;
}}

function plot(divId, traces, layoutExtra) {{
  Plotly.newPlot(divId, traces, Object.assign({{}}, BASE_LAYOUT, layoutExtra), PLOTLY_CONFIG);
}}

function applyFilters() {{
  const years = new Set(getChecked("year").map(Number));
  const industries = new Set(getChecked("industry"));
  const countries = new Set(getChecked("country"));
  const aiCats = new Set(getChecked("ai"));
  const search = document.getElementById("companySearch").value.trim().toLowerCase();

  return RAW_DATA.filter(row => {{
    if (!years.has(row["Year"])) return false;
    if (industries.size && !industries.has(row["Industry"])) return false;
    if (countries.size && !countries.has(row["Country"])) return false;
    if (aiCats.size && !aiCats.has(row["AI_Signal_Category"])) return false;
    if (search && !(row["Company"] || "").toLowerCase().includes(search)) return false;
    return true;
  }});
}}

function render() {{
  const fdf = applyFilters();
  if (!fdf.length) {{
    document.querySelectorAll(".chart-card > div, #largestEventsTable").forEach(el => el.innerHTML = "");
    document.getElementById("overviewKpis").innerHTML = '<div class="empty-state">No records match the current filters.</div>';
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
    kpiCard("Total Employees Laid Off", fmt(totalEmp), "#1D4E89"),
    kpiCard("Total Layoff Events", totalEvents.toLocaleString("en-US"), "#2A9D8F"),
    kpiCard("Companies Affected", companies.toLocaleString("en-US"), "#E76F51"),
    kpiCard("Avg Layoff Size", fmt(avgSize), "#E9C46A"),
    kpiCard("Largest Single Event", fmt(largest), "#457B9D"),
    kpiCard("AI-Related Layoffs (explicit)", fmt(aiEmp), "#6C5B7B"),
  ].join("");

  const annual = sortedEntries(sumBy(reported, r=>r["Year"]), false).sort((a,b)=>a[0]-b[0]);
  plot("chartAnnual", [{{x:annual.map(e=>e[0]), y:annual.map(e=>e[1]), type:"bar", marker:{{color:"#1D4E89"}}}}],
    {{title:"Annual Layoff Trend"}});

  const monthly = sortedEntries(sumBy(reported, r=>r["Year_Month"]), false).sort((a,b)=>a[0]<b[0]?-1:1);
  plot("chartMonthly", [{{x:monthly.map(e=>e[0]), y:monthly.map(e=>e[1]), type:"scatter", mode:"lines", line:{{color:"#1D4E89"}}}}],
    {{title:"Monthly Layoff Trend", xaxis:{{tickangle:45}}}});

  const topCo = sortedEntries(sumBy(reported, r=>r["Company"])).slice(0,10).reverse();
  plot("chartTopCo", [{{x:topCo.map(e=>e[1]), y:topCo.map(e=>e[0]), type:"bar", orientation:"h", marker:{{color:"#2A9D8F"}}}}],
    {{title:"Top 10 Companies"}});

  const topInd = sortedEntries(sumBy(reported, r=>r["Industry"])).slice(0,10).reverse();
  plot("chartTopInd", [{{x:topInd.map(e=>e[1]), y:topInd.map(e=>e[0]), type:"bar", orientation:"h", marker:{{color:"#E76F51"}}}}],
    {{title:"Top Industries"}});

  const geo = sortedEntries(sumBy(reported, r=>r["Country"]));
  plot("chartGeo", [{{
    type:"choropleth", locationmode:"country names",
    locations:geo.map(e=>e[0]), z:geo.map(e=>e[1]),
    colorscale:[[0,"#dbe9f6"],[1,"#1D4E89"]],
    marker:{{line:{{color:"#ffffff", width:0.8}}}},
    colorbar:{{title:"Employees"}},
  }}], {{title:"Geographic Distribution by Country", height:560, geo:{{showframe:false, showcountries:true, countrycolor:"#ffffff", showcoastlines:true, coastlinecolor:"#bcccdc"}}}});
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

  const top10Names = new Set(ranked.slice(0,10).map(e=>e[0]));
  const byCompanySorted = [...reported].filter(r=>top10Names.has(r["Company"])).sort((a,b)=> a["Date"] < b["Date"] ? -1 : 1);
  const running = new Map();
  const traceData = new Map();
  for (const r of byCompanySorted) {{
    const name = r["Company"];
    running.set(name, (running.get(name)||0) + r["Employees Laid Off"]);
    if (!traceData.has(name)) traceData.set(name, {{x:[], y:[]}});
    traceData.get(name).x.push(r["Date"]);
    traceData.get(name).y.push(running.get(name));
  }}
  const cumTraces = Array.from(traceData.entries()).map(([name, d], i) => ({{
    x:d.x, y:d.y, type:"scatter", mode:"lines", name, line:{{color: COLORWAY[i % COLORWAY.length]}},
  }}));
  plot("chartCumulative", cumTraces, {{title:"Cumulative Layoffs: Top 10 Companies"}});
}}

function renderIndustryGeo(reported) {{
  const ind = sortedEntries(sumBy(reported, r=>r["Industry"])).reverse();
  plot("chartIndRank", [{{x:ind.map(e=>e[1]), y:ind.map(e=>e[0]), type:"bar", orientation:"h", marker:{{color:"#1D4E89"}}}}],
    {{title:"Industry Ranking"}});

  const ctry = sortedEntries(sumBy(reported, r=>r["Country"])).slice(0,20).reverse();
  plot("chartCtryRank", [{{x:ctry.map(e=>e[1]), y:ctry.map(e=>e[0]), type:"bar", orientation:"h", marker:{{color:"#2A9D8F"}}}}],
    {{title:"Country Ranking (Top 20)"}});

  const indYearMap = new Map();
  for (const r of reported) {{
    const ind2 = r["Industry"];
    if (!indYearMap.has(ind2)) indYearMap.set(ind2, new Map());
    const yMap = indYearMap.get(ind2);
    yMap.set(r["Year"], (yMap.get(r["Year"])||0) + r["Employees Laid Off"]);
  }}
  const traces = Array.from(indYearMap.entries()).map(([name, yMap], i) => {{
    const years = Array.from(yMap.keys()).sort((a,b)=>a-b);
    return {{x:years, y:years.map(y=>yMap.get(y)), type:"scatter", mode:"lines", name, line:{{color: COLORWAY[i % COLORWAY.length]}}}};
  }});
  plot("chartIndYear", traces, {{title:"Industry x Year Trend"}});
}}

function renderAi(fdf, reported) {{
  const aiCounts = countBy(fdf, r=>r["AI_Signal_Category"]);
  const explicit = reported.filter(r=>r["AI_Signal_Category"]==="Explicit AI-related (source-labeled)");
  const aiEmp = explicit.reduce((s,r)=>s+r["Employees Laid Off"],0);
  const totalEmp = reported.reduce((s,r)=>s+r["Employees Laid Off"],0);
  const aiPct = totalEmp ? (aiEmp/totalEmp*100) : 0;

  document.getElementById("aiKpis").innerHTML = [
    kpiCard("Explicit AI-Related Events", explicit.length.toLocaleString("en-US"), "#1D4E89"),
    kpiCard("Explicit AI-Related Employees Affected", fmt(aiEmp), "#2A9D8F"),
    kpiCard("AI-Related % of Total Employees (explicit only)", aiPct.toFixed(1)+"%", "#E76F51"),
  ].join("");

  const pieEntries = Array.from(aiCounts.entries());
  plot("chartAiPie", [{{labels:pieEntries.map(e=>e[0]), values:pieEntries.map(e=>e[1]), type:"pie",
    marker:{{colors:COLORWAY}}}}], {{title:"AI Signal Breakdown (all records)"}});

  const aiYear = sortedEntries(sumBy(explicit, r=>r["Year"]), false).sort((a,b)=>a[0]-b[0]);
  plot("chartAiYear", [{{x:aiYear.map(e=>e[0]), y:aiYear.map(e=>e[1]), type:"bar", marker:{{color:"#1D4E89"}}}}],
    {{title:"Explicit AI-Related Layoffs by Year"}});

  const aiInd = sortedEntries(sumBy(explicit, r=>r["Industry"])).slice(0,10).reverse();
  plot("chartAiInd", [{{x:aiInd.map(e=>e[1]), y:aiInd.map(e=>e[0]), type:"bar", orientation:"h", marker:{{color:"#E76F51"}}}}],
    {{title:"Industries with Strongest Explicit AI Signal"}});
}}

document.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.addEventListener("change", render));
document.getElementById("companySearch").addEventListener("input", render);
render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
