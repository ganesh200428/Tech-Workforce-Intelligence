"""
Phase 2/3 - Full raw data extraction from the public Layoffs.fyi Airtable
embed (https://layoffs.fyi/ -> embedded Airtable grid, view shroKsHx3SdYYOzeh).

Approach (documented, responsible):
  - Renders the SAME public, no-login-required embed page a normal site
    visitor sees, using a real headless browser (Playwright/Chromium).
  - Does not call Airtable's internal/undocumented API directly, does not
    use credentials, does not bypass any access control.
  - The Airtable grid virtualizes rows (only ~25 rows exist in the DOM at
    a time). We scroll the grid's internal scroll container in small,
    rate-limited steps and harvest each newly-rendered row via its stable
    `data-rowindex` attribute until every row (per the on-page
    "N records" counter) has been captured exactly once.
  - A short delay is used between scroll steps to avoid hammering the
    page/render pipeline (responsible-scraping requirement).

Output: data/raw/layoffs_raw.csv  (untouched raw extraction; no cleaning)
Also writes data/raw/extraction_metadata.json with run metadata.
"""
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

EMBED_URL = "https://airtable.com/embed/app1PaujS9zxVGUZ4/shroKsHx3SdYYOzeh?backgroundColor=green&viewControls=on"
SOURCE_PAGE_URL = "https://layoffs.fyi/"

COLUMNS = [
    "Company",        # left pane, primary cell
    "Location HQ",    # col idx 1
    "Employees Laid Off",  # col idx 2  (source header: "# Laid Off")
    "Date",           # col idx 3
    "Percentage Laid Off",  # col idx 4  (source header: "%")
    "Industry",       # col idx 5
    "Source URL",     # col idx 6  (source header: "Source")
    "Stage",          # col idx 7
    "Funds Raised (mm USD)",  # col idx 8  (source header: "$ Raised (mm)")
    "Country",        # col idx 9
    "Date Added",     # col idx 10
    "AI Mentioned",   # col idx 11 (source header: "AI")
]

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

SCROLL_WAIT_MS = 350   # delay between scroll steps (responsible pacing)
STALL_LIMIT = 8        # consecutive no-new-row scrolls before stopping


def get_total_record_count(page) -> int:
    text = page.evaluate("document.body.innerText")
    m = re.search(r"([\d,]+)\s+records", text)
    return int(m.group(1).replace(",", "")) if m else -1


def harvest_visible_rows(page) -> dict:
    """Returns {rowindex(int): {col_name: value}} for currently rendered rows."""
    data = page.evaluate("""
    () => {
        const out = {};
        document.querySelectorAll('.dataRow.leftPane').forEach(row => {
            const cell = row.querySelector('.cell.primary') || row.querySelector('.cell');
            const idx = cell ? cell.getAttribute('data-rowindex') : null;
            if (idx === null) return;
            if (!out[idx]) out[idx] = {};
            out[idx]['0'] = cell.innerText;
        });
        document.querySelectorAll('.dataRow.rightPane .cell').forEach(cell => {
            const idx = cell.getAttribute('data-rowindex');
            const colIdx = cell.getAttribute('data-columnindex');
            if (idx === null || colIdx === null) return;
            if (!out[idx]) out[idx] = {};
            out[idx][colIdx] = cell.innerText;
        });
        return out;
    }
    """)
    return {int(k): v for k, v in data.items()}


def main():
    extraction_ts = datetime.now(timezone.utc).isoformat()
    all_rows: dict[int, dict] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1800, "height": 1000})
        page.goto(EMBED_URL, wait_until="load", timeout=60000)
        page.wait_for_timeout(8000)

        total_records = get_total_record_count(page)
        print(f"Source reports total records: {total_records}")

        box = page.eval_on_selector(".dataRightPane", """
            el => { const r = el.getBoundingClientRect(); return {x: r.x + r.width/2, y: r.y + r.height/2}; }
        """)
        page.mouse.move(box["x"], box["y"])

        # Harvest the initial (pre-scroll) view first - rows 0..N are visible
        # before any wheel event and would otherwise be missed.
        all_rows.update(harvest_visible_rows(page))
        print(f"Initial view harvested: {len(all_rows)} rows")

        def scroll_pass(direction: int, max_iters: int, label: str):
            """direction: +1 scrolls down, -1 scrolls up. Wheels repeatedly,
            harvesting newly rendered rows each step, until stalled or capped."""
            stall = 0
            prev_count = len(all_rows)
            it = 0
            while it < max_iters:
                page.mouse.wheel(0, direction * step)
                page.wait_for_timeout(SCROLL_WAIT_MS)
                harvested = harvest_visible_rows(page)
                all_rows.update(harvested)
                it += 1
                if len(all_rows) == prev_count:
                    stall += 1
                else:
                    stall = 0
                prev_count = len(all_rows)
                if it % 40 == 0:
                    print(f"  [{label}] iter={it} rows_collected={len(all_rows)}")
                if total_records > 0 and len(all_rows) >= total_records:
                    print(f"  [{label}] reached full record count at iter={it}")
                    break
                if stall >= STALL_LIMIT * 4:
                    print(f"  [{label}] stalled at iter={it}, rows={len(all_rows)}")
                    break

        step = 605
        # Pass 1: scroll all the way down collecting rows.
        scroll_pass(+1, 1200, "down-pass-1")
        # Pass 2: scroll back up to top to catch any rows missed on the way down
        # (virtualization can skip rows during fast/large wheel jumps).
        if total_records <= 0 or len(all_rows) < total_records:
            scroll_pass(-1, 1200, "up-pass-1")
        # Pass 3: one more down pass with a smaller step for finer coverage,
        # only if gaps remain.
        if total_records <= 0 or len(all_rows) < total_records:
            step = 250
            scroll_pass(+1, 1200, "down-pass-2-fine")

        missing = sorted(set(range(total_records)) - set(all_rows.keys())) if total_records > 0 else []
        if missing:
            print(f"Rows still missing after all passes: {len(missing)} (e.g. {missing[:10]})")

        print(f"Finished scrolling. Rows collected: {len(all_rows)} / reported {total_records}")
        browser.close()

    # Write raw CSV, preserving source column order + metadata columns.
    out_path = RAW_DIR / "layoffs_raw.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS + ["extraction_timestamp", "source", "source_url"])
        for idx in sorted(all_rows.keys()):
            row = all_rows[idx]
            values = [row.get(str(i), "") for i in range(len(COLUMNS))]
            writer.writerow(values + [extraction_ts, "Layoffs.fyi (Airtable embed)", SOURCE_PAGE_URL])

    meta = {
        "extraction_timestamp": extraction_ts,
        "source": "Layoffs.fyi",
        "source_url": SOURCE_PAGE_URL,
        "embed_url": EMBED_URL,
        "rows_collected": len(all_rows),
        "reported_total_records": total_records,
        "missing_row_indices": missing,
    }
    with open(RAW_DIR / "extraction_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(json.dumps(meta, indent=2))
    print(f"Saved raw dataset to {out_path}")


if __name__ == "__main__":
    main()
