# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Performance dashboard for client **Smart GR** (aesthetic medicine / microneedling products) that integrates Google Ads API + Shopify REST API + Claude API. Published at [smartgr-dashboard.streamlit.app](https://smartgr-dashboard.streamlit.app).

## Common Commands

```bash
# Run dashboard locally
streamlit run dashboard.py

# Run Google Ads data fetch standalone
python google_ads_campaigns.py

# Run Shopify data fetch standalone
python shopify_test.py

# Run Claude analysis standalone (generates relatorio_smartgr.md)
python analyze.py

# Re-authorize Google Ads OAuth (opens browser)
python google_ads_auth.py

# Test Shopify token
python test_token.py

# Install dependencies
pip install -r requirements.txt
```

## Architecture

### Data Flow

```
shopify_test.py     ──┐
                       ├──▶ dashboard.py (Streamlit UI)
google_ads_campaigns.py─┘        │
                                  ▼
                             analyze.py ──▶ Claude API ──▶ relatorio_smartgr.md
```

### Module Responsibilities

- **`dashboard.py`** — Streamlit UI. Handles auth (password via `st.secrets`), date presets, `@st.cache_data` with auto-busting `CACHE_VERSION` (derived from module mtimes), metric cards, charts (Plotly), and all table rendering. Calls `shopify_test` and `google_ads_campaigns` for data, and `analyze` for Claude reports.

- **`shopify_test.py`** — Shopify REST API client (`2025-01`). Two entry points used by the dashboard:
  - `get_period_data(start, end)` — paid orders only, filtered to Google Ads attribution, returns channels, geo (states/cities), and top-20 products.
  - `get_full_period_data(start, end)` — all orders (any status), returns gross/net revenue, cancellations, refunds, customer stats, top-50 products, geo (top-20 states / top-100 cities), coupons, and revenue by weekday/hour.

- **`google_ads_campaigns.py`** — Google Ads API client. `get_period_data(start, end)` returns account-level totals (cost, revenue, ROAS, CTR, CPC, CPA) and per-campaign breakdown. Client is instantiated fresh per call (no singleton — avoids thread-safety issues in Streamlit).

- **`analyze.py`** — Builds the Claude API prompt and returns a structured markdown report. Key functions:
  - `build_report_data(...)` — assembles a markdown data table from Shopify + Google Ads data.
  - `build_messages(data_report)` — returns the messages list with **prompt caching**: static instructions block has `cache_control: ephemeral` (cached for 5 min), dynamic data is a separate uncached block.
  - `main()` — standalone runner that fetches data and streams the report to stdout + `relatorio_smartgr.md`.

- **`google_ads_auth.py`** — One-time OAuth2 flow. Run with `--code=CODE` after browser authorization to save `GOOGLE_ADS_REFRESH_TOKEN` to `.env`.

### Google Ads Attribution vs Shopify Attribution

The dashboard shows **two ROAS values** intentionally:
- **ROAS (GA)** — `conversions_value / cost` as reported by Google Ads platform.
- **ROAS Real (Shopify / GA)** — `shopify["google_revenue"] / gads["cost"]`: Shopify revenue attributed to Google Ads orders (last non-direct click, via `referring_site` / `landing_site` / `source_name` signals) divided by actual Google Ads spend.

The gap between the two is analyzed by Claude in every report.

### Caching Strategy

`dashboard.py` uses two cached loaders:
- `load_data(cur_start, cur_end, prev_start, prev_end, cache_version)` — current + previous periods for both APIs.
- `load_yago_data(ya_start, ya_end, cache_version)` — year-ago period, only loaded when the "Comparar com ano anterior" checkbox is active.

`CACHE_VERSION` is an 8-char MD5 hash of the mtimes of `shopify_test.py`, `google_ads_campaigns.py`, and `dashboard.py` — automatically busts cache when any module changes.

### Streamlit Cloud Deployment

- Secrets (`PASSWORD`, all API keys) are stored in Streamlit Cloud secrets manager, mirroring the local `.streamlit/secrets.toml` and `.env` files.
- `.streamlit/secrets.toml` and `.env` are gitignored.
- Auto-deploys on push to `main`.

## Environment Variables

Required in `.env` (local) and Streamlit Cloud secrets:

```
SHOPIFY_TOKEN
ANTHROPIC_API_KEY
GOOGLE_ADS_DEVELOPER_TOKEN
GOOGLE_ADS_CLIENT_ID
GOOGLE_ADS_CLIENT_SECRET
GOOGLE_ADS_REFRESH_TOKEN
GOOGLE_ADS_LOGIN_CUSTOMER_ID   # MCC customer ID
```

`CUSTOMER_ID` in `google_ads_campaigns.py` (Smart GR account: `4686170698`) is hardcoded — update if adding more accounts.

## Key Conventions

- **All monetary tables** must use `st.column_config.NumberColumn` with `format="R$ %.2f"` — never format currency as a string before passing to `st.dataframe`, as that breaks numeric sorting.
- **Default sort**: all dataframes with monetary columns are sorted descending by the primary revenue column via `.sort_values(..., ascending=False)` before display.
- **Prompt caching**: Claude API calls must use `build_messages(data_report)` from `analyze.py`, not a raw string `content`. The static instructions block carries `cache_control: ephemeral`.
- **No global client singletons** in modules used by Streamlit (thread-safety).
