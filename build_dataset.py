"""Build the flat alerts table used by the dashboard.

Sources (in priority order):
1. ``data/raw_messages.jsonl`` - raw Telegram messages saved by ``collect_alerts.py`` (all alert types).
2. ``tzofar_red_color.xlsx``   - the legacy export (red alerts only), used for any period that
   the raw messages don't cover.

Outputs:
- ``data/alerts.csv.gz``      timestamp, alert_type, zone, city, shelter_sec, message_id, source
- ``data/alert_ends.csv.gz``  timestamp, zone, city, message_id   ("סיום אירוע" messages)

Usage:  python build_dataset.py
"""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from alerts_parser import parse_messages, parse_legacy_text

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
RAW_MESSAGES = os.path.join(DATA_DIR, "raw_messages.jsonl")
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.csv.gz")
ENDS_FILE = os.path.join(DATA_DIR, "alert_ends.csv.gz")
LEGACY_XLSX = os.path.join(ROOT, "tzofar_red_color.xlsx")

ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")
ALERT_COLUMNS = ["timestamp", "alert_type", "zone", "city", "shelter_sec", "message_id", "source"]
END_COLUMNS = ["timestamp", "zone", "city", "message_id"]
DEDUP_KEYS = ["timestamp", "alert_type", "zone", "city"]


def to_israel_naive(iso_utc):
    """'2026-06-14T09:55:12+00:00' -> datetime(2026, 6, 14, 12, 55, 12) in Israel local time, naive."""
    dt = datetime.fromisoformat(iso_utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ISRAEL_TZ).replace(tzinfo=None)


def load_raw_messages(path=RAW_MESSAGES):
    if not os.path.exists(path):
        return []
    messages = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                msg = json.loads(line)
                msg["date"] = to_israel_naive(msg["date"])
                messages.append(msg)
    messages.sort(key=lambda m: (m["date"], m["id"]))
    return messages


def load_legacy_alerts(path=LEGACY_XLSX):
    if not os.path.exists(path):
        return pd.DataFrame(columns=ALERT_COLUMNS)
    df = pd.read_excel(path).dropna(subset=["text"])
    rows = []
    for ts, text in zip(df["date"], df["text"]):
        rows += parse_legacy_text(pd.Timestamp(ts).to_pydatetime(), text)
    out = pd.DataFrame(rows, columns=ALERT_COLUMNS[:-1])
    out["source"] = "legacy_xlsx"
    return out


def build(raw_path=RAW_MESSAGES, legacy_path=LEGACY_XLSX):
    """Return (alerts_df, ends_df, unparsed) without writing anything."""
    messages = load_raw_messages(raw_path)
    alerts, ends, unparsed = parse_messages(messages)
    alerts_df = pd.DataFrame(alerts, columns=ALERT_COLUMNS[:-1])
    alerts_df["source"] = "telegram"
    ends_df = pd.DataFrame(ends, columns=END_COLUMNS)

    legacy_df = load_legacy_alerts(legacy_path)
    if not legacy_df.empty:
        if messages:
            # Only use the legacy export for the period before the raw messages start.
            first_raw = messages[0]["date"].replace(second=0, microsecond=0)
            legacy_df = legacy_df[pd.to_datetime(legacy_df["timestamp"]) < first_raw]
        alerts_df = pd.concat([legacy_df, alerts_df], ignore_index=True) if len(alerts_df) else legacy_df

    alerts_df["timestamp"] = pd.to_datetime(alerts_df["timestamp"])
    alerts_df["shelter_sec"] = pd.to_numeric(alerts_df["shelter_sec"], errors="coerce").astype("Int64")
    alerts_df["message_id"] = pd.to_numeric(alerts_df["message_id"], errors="coerce").astype("Int64")
    alerts_df = (alerts_df.drop_duplicates(subset=DEDUP_KEYS, keep="first")
                 .sort_values(["timestamp", "zone", "city"])
                 .reset_index(drop=True))

    if len(ends_df):
        ends_df["timestamp"] = pd.to_datetime(ends_df["timestamp"])
        ends_df = ends_df.drop_duplicates(subset=["timestamp", "city"]).sort_values("timestamp")
    return alerts_df[ALERT_COLUMNS], ends_df, unparsed


def save(alerts_df, ends_df):
    os.makedirs(DATA_DIR, exist_ok=True)
    alerts_df.to_csv(ALERTS_FILE, index=False, encoding="utf-8")
    ends_df.to_csv(ENDS_FILE, index=False, encoding="utf-8")


def load_alerts(path=ALERTS_FILE):
    """Load the flat alerts table (building it from the sources if it doesn't exist yet)."""
    if not os.path.exists(path):
        alerts_df, ends_df, _ = build()
        save(alerts_df, ends_df)
        return alerts_df
    df = pd.read_csv(path, parse_dates=["timestamp"], dtype={"zone": str, "city": str, "alert_type": str})
    df["shelter_sec"] = df["shelter_sec"].astype("Int64")
    df["message_id"] = df["message_id"].astype("Int64")
    return df


def main():
    alerts_df, ends_df, unparsed = build()
    save(alerts_df, ends_df)
    print(f"alerts : {len(alerts_df):,} rows -> {ALERTS_FILE}")
    if len(alerts_df):
        print(f"range  : {alerts_df['timestamp'].min()} .. {alerts_df['timestamp'].max()}")
        print("types  : " + ", ".join(f"{k}={v:,}" for k, v in alerts_df["alert_type"].value_counts().items()))
        print("source : " + ", ".join(f"{k}={v:,}" for k, v in alerts_df["source"].value_counts().items()))
    print(f"ends   : {len(ends_df):,} rows -> {ENDS_FILE}")
    if unparsed:
        print(f"\n{len(unparsed)} lines could not be parsed. Most common:")
        for line, n in Counter(ln for _, ln in unparsed).most_common(15):
            print(f"  {n:>5} x {line[:100]}")


if __name__ == "__main__":
    main()
