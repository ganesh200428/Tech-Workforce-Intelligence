# DATA QUALITY REPORT

Generated from `data/raw/layoffs_raw.csv` -> `data/processed/layoffs_clean.csv`

## Summary

| Metric | Value |
|---|---|
| Records extracted | 4595 |
| Duplicate records removed | 0 |
| Records with missing/invalid company or date (removed) | 0 |
| Valid records (final) | 4595 |
| Missing employee counts (raw) | 1595 |
| Missing employee counts (in clean dataset) | 1595 |
| Missing percentage laid off (raw) | 1713 |
| Invalid percentages flagged (out of 0-100 range) | 0 |
| Missing dates (raw) | 0 |
| Missing company | 0 |

## Coverage

- Date range: 2020-03-11 -> 2026-09-03
- Number of companies: 2976
- Number of industries: 30
- Number of countries: 66
- Total employees affected (sum, valid records): 932,766

## Layoff Size Classification Thresholds (derived from actual distribution)

- Small: <= 40 employees (25th percentile)
- Medium: <= 200 employees (75th percentile)
- Large: <= 500 employees (90th percentile)
- Very Large: > 500 employees

## AI Signal Breakdown

{
  "Unknown": 3363,
  "AI-mentioned (weak keyword signal only)": 534,
  "No AI signal (source-labeled)": 529,
  "Explicit AI-related (source-labeled)": 169
}

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
