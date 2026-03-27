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

- **Telegram data collection** — Connects to Telegram channels via the Telethon API and extracts structured alert messages
- **Smart message parsing** — Handles Hebrew text, special city name formats, duplicates, and edge cases
- **Multi-level data aggregation** — Groups alerts by zone, city, date, and hour in any combination
- **Flexible filtering** — Filter alerts by specific cities, regions (north / center / south), proximity to Gaza, date ranges, and more
- **Rich visualizations** — Generates over 18 types of bar charts and color-coded time-interval plots
- **Pickle-based caching** — Saves processed data locally to avoid redundant API calls
- **Excel export** — Exports raw alert data to `.xlsx` for further analysis

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
red-alert-analyzer/
├── main entry             # partial_plot.py — run configurations and plot triggers
├── telegram_alarms.py     # Telegram client: data collection & Excel export
├── data_stats.py          # Data parsing, aggregation, and filtering logic
├── data_plots.py          # All visualization functions
├── coditions.py           # Filter condition functions (by city / zone / date)
├── parameters.py          # API credentials, date ranges, and global flags
├── Cdatetime.py           # Custom datetime display classes
├── tzofar_red_color.xlsx  # Raw alert data (Excel output)
├── my_data_tzofer_red.pkl          # Processed alert data (cached)
├── my_data_tzofer_red_full.pkl     # Full alert data with hour resolution (cached)
├── zones_cities.txt       # Zone → city mapping output
├── all_cities_with_condition.txt   # Cities that received alerts
└── dates.txt              # List of dates with alert activity
```

---

## ⚙️ Configuration (`parameters.py`)

| Parameter | Description |
|---|---|
| `api_id` / `api_hash` | Telegram API credentials |
| `phone_number` | Phone number for Telegram login |
| `min_date` / `max_date` | Date range to collect and analyze |
| `COLLET` | Set to `True` to re-collect data from Telegram |
| `STATISTICS` | Set to `True` to reprocess raw data |
| `EXTRA_STATISTICS` | Set to `True` to generate all chart types |
| `SHOW` / `SAVE` | Display and/or save the generated plots |

---

## 🚀 Getting Started

### 1. Install dependencies

```bash
pip install telethon pandas openpyxl plotly
```

### 2. Configure credentials

Edit `parameters.py` with your Telegram API credentials and desired date range.

> Get your API credentials at [my.telegram.org](https://my.telegram.org)

### 3. Run the pipeline

```bash
# Collect data from Telegram + generate plots
python partial_plot.py
```

To control what runs, set the flags in `parameters.py`:
- `COLLET = True` → fetch fresh data from Telegram
- `STATISTICS = True` → reprocess and cache the data
- `EXTRA_STATISTICS = True` → generate all chart types

---

## 🗺️ Supported Regions & Filters

Built-in filter functions cover:

- **Specific cities** — Ashkelon, Tel Aviv, Rishon LeZion, Haifa, Netanya, Jerusalem, and more
- **Geographic regions** — North (`צפון`), Center (`מרכז`), South (`דרום`)
- **Proximity zones** — Gaza envelope (`עוטף עזה`), conflict line (`קו העימות`)
- **Custom conditions** — Any city/zone/date combination via `coditions.py`

---

## ⚠️ Disclaimer

This project is intended for **research and statistical analysis purposes only**.
All data is sourced from public Telegram channels.
This tool is not affiliated with the IDF Home Front Command (פיקוד העורף) or any official government body.
