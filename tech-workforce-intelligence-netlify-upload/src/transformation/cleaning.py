"""
Phase 4/5 - Data cleaning, validation and transformation.

Reads the untouched raw extraction (data/raw/layoffs_raw.csv) and produces:
  - data/processed/layoffs_clean.csv   (cleaned, analysis-ready dataset)
  - docs/data_quality.md               (data quality report, real numbers only)

Every removal/modification is counted and documented in the quality report.
Raw data is never modified in place.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "data" / "raw" / "layoffs_raw.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
DOCS_DIR = ROOT / "docs"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

report = {}


def main():
    df = pd.read_csv(RAW_PATH)
    report["records_extracted"] = len(df)

    # ---- 1. Duplicate records (exact full-row duplicates only) ----
    dup_mask = df.duplicated(keep="first")
    report["duplicate_records"] = int(dup_mask.sum())
    df = df.loc[~dup_mask].copy()

    # ---- 2. Whitespace / capitalization normalization on text fields ----
    text_cols = ["Company", "Industry", "Stage", "Country", "AI Mentioned"]
    for c in text_cols:
        df[c] = df[c].astype("string").str.strip()
        df[c] = df[c].replace({"": pd.NA, "nan": pd.NA})

    # ---- 3. Location HQ: split multi-select cell into City + Non-U.S. flag ----
    def split_location(val):
        if pd.isna(val):
            return pd.Series([pd.NA, pd.NA])
        parts = [p.strip() for p in str(val).split("\n") if p.strip()]
        city = parts[0] if parts else pd.NA
        is_non_us = "Non-U.S." in parts[1:]
        return pd.Series([city, is_non_us])

    df[["City", "Is_Non_US_HQ"]] = df["Location HQ"].apply(split_location)

    # ---- 4. Numeric fields stored as strings ----
    report["missing_employee_counts_raw"] = int(df["Employees Laid Off"].isna().sum())
    df["Employees Laid Off"] = pd.to_numeric(df["Employees Laid Off"], errors="coerce")

    report["missing_percentage_raw"] = int(df["Percentage Laid Off"].isna().sum())
    df["Percentage Laid Off"] = (
        df["Percentage Laid Off"].astype("string").str.rstrip("%").astype(float)
    )
    # invalid percentages: outside 0-100
    invalid_pct = df["Percentage Laid Off"].notna() & (
        (df["Percentage Laid Off"] < 0) | (df["Percentage Laid Off"] > 100)
    )
    report["invalid_percentages_flagged"] = int(invalid_pct.sum())
    df.loc[invalid_pct, "Percentage Laid Off"] = np.nan

    df["Funds Raised (mm USD)"] = (
        df["Funds Raised (mm USD)"]
        .astype("string")
        .str.replace(r"[\$,]", "", regex=True)
        .astype(float)
    )

    # ---- 5. Dates (source format is day-first, e.g. 3/9/2026 = 3 Sep 2026) ----
    report["missing_dates_raw"] = int(df["Date"].isna().sum())
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df["Date Added"] = pd.to_datetime(df["Date Added"], dayfirst=True, errors="coerce")
    invalid_dates = df["Date"].isna()
    report["invalid_or_missing_dates"] = int(invalid_dates.sum())

    # ---- 6. Missing company / core-field validation (documented, not silently dropped) ----
    missing_company = df["Company"].isna()
    report["missing_company"] = int(missing_company.sum())

    # A record is "valid" for analysis if it has Company + a parseable Date.
    valid_mask = df["Company"].notna() & df["Date"].notna()
    report["invalid_records_removed"] = int((~valid_mask).sum())
    invalid_df = df.loc[~valid_mask].copy()
    df = df.loc[valid_mask].copy()

    # ---- 7. Derived date fields ----
    df["Year"] = df["Date"].dt.year
    df["Quarter"] = df["Date"].dt.quarter
    df["Month"] = df["Date"].dt.month
    df["Month_Name"] = df["Date"].dt.strftime("%B")
    df["Year_Month"] = df["Date"].dt.strftime("%Y-%m")
    df["Week"] = df["Date"].dt.isocalendar().week

    # ---- 8. Layoff size classification (thresholds from actual distribution) ----
    emp = df["Employees Laid Off"].dropna()
    q1, med, q3, p90 = emp.quantile([0.25, 0.5, 0.75, 0.90])
    report["layoff_size_thresholds"] = {
        "q25": float(q1), "median": float(med), "q75": float(q3), "p90": float(p90)
    }

    def size_cat(n):
        if pd.isna(n):
            return "Unknown"
        if n <= q1:
            return "Small"
        if n <= q3:
            return "Medium"
        if n <= p90:
            return "Large"
        return "Very Large"

    df["Layoff_Size_Category"] = df["Employees Laid Off"].apply(size_cat)

    # ---- 9. AI signal classification ----
    # Primary signal: source-provided "AI Mentioned" field (Yes/No), which is
    # only populated for a subset of records. Missing values are labeled
    # "Unknown" rather than assumed "No" (Rule 10/16 - do not hide missing data,
    # do not fabricate). A supplementary weak keyword scan of the Source URL
    # slug is also captured, clearly separated, since it is a much weaker
    # signal than the source's own explicit field.
    ai_keywords = ["ai", "artificial-intelligence", "genai", "generative-ai",
                   "machine-learning", "automation", "llm"]

    def url_keyword_hit(url):
        if pd.isna(url):
            return False
        low = str(url).lower()
        return any(k in low for k in ai_keywords)

    df["AI_URL_Keyword_Signal"] = df["Source URL"].apply(url_keyword_hit)

    def ai_category(row):
        mentioned = row["AI Mentioned"]
        if pd.notna(mentioned):
            return "Explicit AI-related (source-labeled)" if str(mentioned).strip().lower() == "yes" else "No AI signal (source-labeled)"
        if row["AI_URL_Keyword_Signal"]:
            return "AI-mentioned (weak keyword signal only)"
        return "Unknown"

    df["AI_Signal_Category"] = df.apply(ai_category, axis=1)

    # ---- Save cleaned dataset ----
    out_cols = [
        "Company", "City", "Is_Non_US_HQ", "Country", "Employees Laid Off",
        "Percentage Laid Off", "Date", "Year", "Quarter", "Month", "Month_Name",
        "Year_Month", "Week", "Industry", "Stage", "Funds Raised (mm USD)",
        "Layoff_Size_Category", "AI Mentioned", "AI_URL_Keyword_Signal",
        "AI_Signal_Category", "Source URL", "Date Added",
        "extraction_timestamp", "source", "source_url",
    ]
    df[out_cols].to_csv(PROCESSED_DIR / "layoffs_clean.csv", index=False)
    if len(invalid_df):
        invalid_df.to_csv(PROCESSED_DIR / "layoffs_invalid_removed.csv", index=False)

    # ---- Data quality report numbers ----
    report["valid_records"] = len(df)
    report["date_range"] = [str(df["Date"].min().date()), str(df["Date"].max().date())]
    report["num_companies"] = int(df["Company"].nunique())
    report["num_industries"] = int(df["Industry"].nunique())
    report["num_countries"] = int(df["Country"].nunique())
    report["total_employees_affected"] = float(df["Employees Laid Off"].sum())
    report["missing_employee_counts_in_clean"] = int(df["Employees Laid Off"].isna().sum())
    report["missing_percentage_in_clean"] = int(df["Percentage Laid Off"].isna().sum())
    report["ai_signal_breakdown"] = df["AI_Signal_Category"].value_counts().to_dict()

    write_markdown_report(report)
    with open(DOCS_DIR / "data_quality.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(json.dumps(report, indent=2, default=str))


def write_markdown_report(r):
    md = f"""# DATA QUALITY REPORT

Generated from `data/raw/layoffs_raw.csv` -> `data/processed/layoffs_clean.csv`

## Summary

| Metric | Value |
|---|---|
| Records extracted | {r['records_extracted']} |
| Duplicate records removed | {r['duplicate_records']} |
| Records with missing/invalid company or date (removed) | {r['invalid_records_removed']} |
| Valid records (final) | {r['valid_records']} |
| Missing employee counts (raw) | {r['missing_employee_counts_raw']} |
| Missing employee counts (in clean dataset) | {r['missing_employee_counts_in_clean']} |
| Missing percentage laid off (raw) | {r['missing_percentage_raw']} |
| Invalid percentages flagged (out of 0-100 range) | {r['invalid_percentages_flagged']} |
| Missing dates (raw) | {r['missing_dates_raw']} |
| Missing company | {r['missing_company']} |

## Coverage

- Date range: {r['date_range'][0]} -> {r['date_range'][1]}
- Number of companies: {r['num_companies']}
- Number of industries: {r['num_industries']}
- Number of countries: {r['num_countries']}
- Total employees affected (sum, valid records): {int(r['total_employees_affected']):,}

## Layoff Size Classification Thresholds (derived from actual distribution)

- Small: <= {r['layoff_size_thresholds']['q25']:.0f} employees (25th percentile)
- Medium: <= {r['layoff_size_thresholds']['q75']:.0f} employees (75th percentile)
- Large: <= {r['layoff_size_thresholds']['p90']:.0f} employees (90th percentile)
- Very Large: > {r['layoff_size_thresholds']['p90']:.0f} employees

## AI Signal Breakdown

{json.dumps(r['ai_signal_breakdown'], indent=2)}

**Methodology note:** The source (Layoffs.fyi) only populates the explicit
"AI Mentioned" field for a subset of records (recent events). Records without
this field are labeled "Unknown" rather than assumed "No AI signal" -
missing data is never hidden or silently imputed. A supplementary weak
keyword scan of the article URL slug is tracked separately
(`AI_URL_Keyword_Signal`) but is NOT used to override the source's own
explicit label, and does not by itself establish that AI caused a layoff.

## Records Removed (documented, not silently deleted)

Rows missing both a usable Company name and a parseable Date were excluded
from the analysis-ready dataset and preserved unmodified in
`data/processed/layoffs_invalid_removed.csv` for audit purposes.
"""
    with open(DOCS_DIR / "data_quality.md", "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    main()
