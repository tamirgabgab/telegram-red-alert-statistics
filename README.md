# 🚨 Red Alert (Tzeva Adom) Data Analyzer

**A data collection and analysis tool for Israeli rocket alert (Tzeva Adom) events**

[![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Telethon](https://img.shields.io/badge/Telethon-Telegram%20API-26A5E4?logo=telegram&logoColor=white)](https://docs.telethon.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🧠 What is this?

**Red Alert Analyzer** is a Python-based pipeline that collects real-time rocket alert data from Telegram channels (such as **"צופר - צבע אדום"**), parses and structures it by zone, city, date and hour, and generates detailed statistical visualizations.

The tool is designed to help analyze the spatial and temporal distribution of rocket alert events across Israel, with flexible filtering by region, city, or date range.

---

## ✨ Key Features

- **Interactive map of Israel** — every Home Front Command locality polygon colored by alert count for the selected period, a layer per alert type, play-through animation by day / 6 hours / hour, quiet localities in gray, and a click-for-details panel
- **Interactive dashboard** (Streamlit) — filter by date range, alert type, zone and locality; count by localities, events or barrages (same-type alerts ≤ 3 min apart); time series at minute → week resolution, recent-barrages feed, hour-of-day / weekday / day × hour heatmaps, top zones & localities (click to filter), time-to-shelter, CSV export. Red/white theme with light and dark mode, Hebrew RTL, mobile layout
- **All alert types** — 🔴 rockets (צבע אדום), ✈️ hostile aircraft (חדירת כלי טיס עוין), 🔓 terrorist infiltration (חדירת מחבלים)
- **Incremental Telegram collection** — raw messages are stored once (`data/raw_messages.jsonl`) and re-parsed any time
- **Smart message parsing** — Hebrew text, locality names that contain commas, time-to-shelter, end-of-event messages, de-duplication
- **Legacy matplotlib reports** — 18+ chart types (`partial_plot.py`)

---

## 📊 Supported Visualizations

| Chart | Description |
|---|---|
| `bar_0_1` | Top zones / cities by alert count |
| `bar_2` | Zone vs. city breakdown |
| `bar_5_7` / `bar_6_8` | Repeated alert patterns per zone or city |
| `bar_9` | Zone + city combined ranking |
| `bar_10` | Normal vs. conditional alert comparison |
| `bar_11–14` | Date, hour, and distribution analysis |
| `bar_15` | Time-interval alert density |
| `bar_16` | 24h alert heatmap by time slot |
| `bar_16_color` | Color-coded alert timeline by region |

---

## 🗂️ Project Structure

```
telegram-red-alert-statistics/
├── dashboard.py           # Streamlit dashboard (UI)
├── dashboard_data.py      # Aggregations used by the dashboard (pure pandas, tested)
├── dashboard_style.py     # Design tokens, global CSS, header band, KPI cards, feed and footer
├── tools/screenshots.js   # Visual check: screenshots of every tab, desktop/mobile, light/dark
├── collect_alerts.py      # Incremental Telegram collector -> data/raw_messages.jsonl
├── build_dataset.py       # Raw messages / legacy Excel -> data/alerts.csv.gz
├── alerts_parser.py       # Message parser (all alert types, shelter time, end events)
├── city_names.py          # Locality-name tables shared by old and new code
├── map_data.py            # Map helpers: locality matching, per-locality counts, color encoding
├── build_geo.py           # Builds data/geo/localities.geojson from pikud-haoref-api
├── data/
│   ├── alerts.csv.gz      # Flat table: timestamp, alert_type, zone, city, shelter_sec, ...
│   ├── alert_ends.csv.gz  # "סיום אירוע" messages
│   └── geo/               # Locality polygons + centroids (third-party, Apache 2.0 - see NOTICE.md)
├── tests/                 # pytest
│
│   Legacy pipeline (matplotlib, red alerts only)
├── partial_plot.py        # Entry point: run configurations and plot triggers
├── telegram_alarms.py     # Old collector -> tzofar_red_color.xlsx
├── data_stats.py          # Nested-dict aggregation & filtering
├── data_plots.py          # Visualization functions
├── coditions.py           # Filter condition functions (by city / zone / date)
├── parameters.py          # Date ranges and flags (credentials come from .env)
└── Cdatetime.py           # Custom datetime display classes
```

---

## ⚙️ Configuration (`parameters.py`)

| Parameter | Description |
|---|---|
| `api_id` / `api_hash` / `phone_number` | Read from `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` / `TELEGRAM_PHONE` in `.env` (see `.env.example`) |
| `min_date` / `max_date` | Date range to collect and analyze |
| `COLLET` | Set to `True` to re-collect data from Telegram |
| `STATISTICS` | Set to `True` to reprocess raw data |
| `EXTRA_STATISTICS` | Set to `True` to generate all chart types |
| `SHOW` / `SAVE` | Display and/or save the generated plots |

---

## 🚀 Getting Started

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Open the dashboard

```bash
streamlit run dashboard.py
```

The repo already contains `data/alerts.csv.gz` (red alerts, 28/02/2026 – 27/03/2026), so the dashboard works right away.
Theme colors and the font live in `.streamlit/config.toml` and `dashboard_style.py`; the app follows the device's light/dark setting.
Add `?dev=1` to the URL to see maintainer hints (data collection commands).

The **מפה** (map) tab loads base-map tiles from CARTO (no API key needed). Without internet access, run
`MAP_STYLE=white-bg streamlit run dashboard.py` to draw the polygons on a plain background.

### 3. Collect fresh data (all alert types)

```bash
cp .env.example .env             # fill in TELEGRAM_API_ID / TELEGRAM_API_HASH / TELEGRAM_PHONE
python collect_alerts.py --since 2026-02-26   # first run: asks for the Telegram login code
python collect_alerts.py                      # later runs: only new messages
```

> Get your API credentials at [my.telegram.org](https://my.telegram.org). Never commit `.env` or `*.session` files.

The collector rebuilds `data/alerts.csv.gz` automatically (or run `python build_dataset.py`).

### 4. Legacy matplotlib reports

```bash
python partial_plot.py
```

Controlled by the flags in `parameters.py` (`COLLET`, `STATISTICS`, `EXTRA_STATISTICS`, `SHOW`, `SAVE`).

### Tests

```bash
pytest -q
```

### Visual check (UI changes)

With the dashboard running, take screenshots of every tab at 1280px and 375px, light and dark:

```bash
npm install --no-save playwright && npx playwright install chromium   # once
node tools/screenshots.js                 # -> screenshots/ ; exits 1 on overflow or exceptions
```

---

## 🗺️ Supported Regions & Filters

Built-in filter functions cover:

- **Specific cities** — Ashkelon, Tel Aviv, Rishon LeZion, Haifa, Netanya, Jerusalem, and more
- **Geographic regions** — North (`צפון`), Center (`מרכז`), South (`דרום`)
- **Proximity zones** — Gaza envelope (`עוטף עזה`), conflict line (`קו העימות`)
- **Custom conditions** — Any city/zone/date combination via `coditions.py`

---

## 🙏 Credits

Locality coordinates and polygons come from [pikud-haoref-api](https://github.com/eladnava/pikud-haoref-api)
by Elad Nava, licensed under the Apache License 2.0. A modified copy is stored in `data/geo/`
(see `data/geo/NOTICE.md` for the changes and `data/geo/LICENSE-pikud-haoref-api` for the license).
To refresh it: `python build_geo.py`.

---

## ⚠️ Disclaimer

This project is intended for **research and statistical analysis purposes only**.
All data is sourced from public Telegram channels.
This tool is not affiliated with the IDF Home Front Command (פיקוד העורף) or any official government body.
