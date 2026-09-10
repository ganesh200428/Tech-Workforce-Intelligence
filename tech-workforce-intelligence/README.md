# Tech Workforce Intelligence

Interactive Streamlit dashboard for analyzing technology workforce layoffs.

## Run locally

```bash
pip install -r requirements.txt
streamlit run src/dashboard/app.py
```

## Deployment

This project is a Python Streamlit application. Netlify hosts static sites and
does not run a persistent Streamlit server, so this dashboard cannot be
deployed directly to Netlify as an interactive app.

Deploy it on Streamlit Community Cloud, Render, Railway, or another Python
hosting service using:

```text
streamlit run src/dashboard/app.py
```

For Streamlit Community Cloud, select `src/dashboard/app.py` as the main file
and use this repository's `requirements.txt`.

## Project output

- `data/raw/`: untouched extracted data and extraction metadata
- `data/processed/`: cleaned analysis-ready dataset
- `docs/`: data-quality report
- `src/extraction/`: public-data extraction workflow
- `src/transformation/`: cleaning and validation workflow
- `src/dashboard/`: Streamlit dashboard