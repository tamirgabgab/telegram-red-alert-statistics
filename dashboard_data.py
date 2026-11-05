"""Pure pandas aggregations used by the Streamlit dashboard (kept separate so they can be tested)."""

from datetime import timedelta

import numpy as np
import pandas as pd

from alerts_parser import ALERT_TYPE_LABELS

# Count modes
MODE_LOCALITIES = "localities"  # every locality that sounded counts (one row per locality per minute)
MODE_EVENTS = "events"          # one alert event per (minute, alert type), no matter how many localities
MODE_BARRAGES = "barrages"      # one per wave: same-type alert minutes no more than BARRAGE_GAP_MIN apart
BARRAGE_GAP_MIN = 3

# Time resolutions for the time series: label -> pandas offset
RESOLUTIONS = {
    "דקה": "1min",
    "15 דקות": "15min",
    "שעה": "1h",
    "6 שעות": "6h",
    "יום": "1D",
    "שבוע": "W",
}
MAX_BINS = 2500  # above this the bar chart gets unreadable and slow, so the resolution is coarsened

# Sunday-first Hebrew weekday names, indexed by pandas day_of_week (Monday=0)
WEEKDAYS_HE = {6: "ראשון", 0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת"}
WEEKDAY_ORDER = [6, 0, 1, 2, 3, 4, 5]


def type_label(alert_type):
    return ALERT_TYPE_LABELS.get(alert_type, alert_type)


def filter_alerts(df, start=None, end=None, types=None, zones=None, cities=None):
    """Filter by inclusive date range (dates), alert types, zones and cities. Empty/None = no filter."""
    mask = pd.Series(True, index=df.index)
    if start is not None:
        mask &= df["timestamp"] >= pd.Timestamp(start)
    if end is not None:
        mask &= df["timestamp"] < pd.Timestamp(end) + timedelta(days=1)
    if types:
        mask &= df["alert_type"].isin(types)
    if zones:
        mask &= df["zone"].isin(zones)
    if cities:
        mask &= df["city"].isin(cities)
    return df[mask]


def barrage_ids(df, gap_minutes=BARRAGE_GAP_MIN):
    """Barrage number for every row.

    Alert minutes of the same type that follow each other by at most ``gap_minutes`` belong to one
    barrage (a chain can therefore last longer than the gap). Computed on the rows given, so a
    zone/city filter yields the barrages as seen in that area.
    """
    if df.empty:
        return pd.Series(dtype="int64", index=df.index)
    ev = df[["alert_type", "timestamp"]].drop_duplicates().sort_values(["alert_type", "timestamp"])
    new = (ev["alert_type"] != ev["alert_type"].shift()) | (ev["timestamp"].diff() > pd.Timedelta(minutes=gap_minutes))
    ids = pd.Series(new.cumsum().to_numpy(), index=pd.MultiIndex.from_frame(ev))
    keys = pd.MultiIndex.from_frame(df[["alert_type", "timestamp"]])
    return pd.Series(ids.reindex(keys).to_numpy(), index=df.index, name="barrage")


def filter_places(df, zones=None, cities=None):
    """Rows in any of the chosen zones OR cities (one combined place picker). Nothing chosen = everything."""
    if not zones and not cities:
        return df
    mask = pd.Series(False, index=df.index)
    if zones:
        mask |= df["zone"].isin(zones)
    if cities:
        mask |= df["city"].isin(cities)
    return df[mask]


def city_zones(df):
    """Locality -> its most common zone (for labelling localities in the place picker)."""
    if df.empty:
        return {}
    return df.groupby("city")["zone"].agg(lambda z: z.value_counts().index[0]).to_dict()


def apply_mode(df, mode, extra_keys=()):
    """Collapse rows to the counting unit of the mode.

    events: one row per (timestamp, alert_type[, extra keys]).
    barrages: one row per (barrage[, extra keys]), stamped with the barrage's first minute.
    """
    if mode == MODE_EVENTS:
        return df.drop_duplicates(subset=["timestamp", "alert_type", *extra_keys])
    if mode == MODE_BARRAGES:
        d = df.assign(barrage=barrage_ids(df)).sort_values("timestamp")
        return d.drop_duplicates(subset=["barrage", *extra_keys])
    return df


def barrage_table(df, gap_minutes=BARRAGE_GAP_MIN):
    """One row per barrage, newest first: start, end, alert_type, localities, zones (most localities first)."""
    cols = ["start", "end", "alert_type", "localities", "zones"]
    if df.empty:
        return pd.DataFrame(columns=cols)
    d = df.assign(barrage=barrage_ids(df, gap_minutes))
    g = d.groupby("barrage")
    out = pd.DataFrame({
        "start": g["timestamp"].min(),
        "end": g["timestamp"].max(),
        "alert_type": g["alert_type"].first(),
        "localities": g["city"].nunique(),
        "zones": g["zone"].agg(lambda z: list(z.value_counts().index)),
    })
    return out.sort_values("start", ascending=False).reset_index(drop=True)[cols]


def effective_resolution(df, freq):
    """Return the requested freq, or the finest coarser one that keeps the series under MAX_BINS."""
    if df.empty:
        return freq
    span = df["timestamp"].max() - df["timestamp"].min()
    freqs = list(RESOLUTIONS.values())
    for f in freqs[freqs.index(freq):]:
        step = pd.Timedelta(weeks=1) if f == "W" else pd.Timedelta(pd.tseries.frequencies.to_offset(f))
        if span / step <= MAX_BINS:
            return f
    return freqs[-1]


def _floor(ts, freq):
    if freq == "W":  # weeks start on Sunday
        days = (ts.dt.day_of_week + 1) % 7
        return (ts - pd.to_timedelta(days, unit="D")).dt.normalize()
    return ts.dt.floor(freq)


def time_series(df, freq, mode=MODE_LOCALITIES, start=None, end=None):
    """Counts per time bin and alert type, with empty bins filled with 0 (wide frame: index=bin, cols=type)."""
    d = apply_mode(df, mode)
    if d.empty:
        return pd.DataFrame()
    bins = _floor(d["timestamp"], freq)
    wide = d.groupby([bins, d["alert_type"]]).size().unstack(fill_value=0)
    lo = pd.Timestamp(start) if start is not None else wide.index.min()
    hi = pd.Timestamp(end) + timedelta(days=1) - timedelta(minutes=1) if end is not None else wide.index.max()
    lo = _floor(pd.Series([lo]), freq).iloc[0]
    step = "7D" if freq == "W" else freq
    full = pd.date_range(lo, hi, freq=step)
    return wide.reindex(full.union(wide.index), fill_value=0)


def hour_of_day(df, mode=MODE_LOCALITIES):
    d = apply_mode(df, mode)
    counts = d.groupby([d["timestamp"].dt.hour, d["alert_type"]]).size().unstack(fill_value=0)
    return counts.reindex(range(24), fill_value=0)


def weekday_hour_matrix(df, mode=MODE_LOCALITIES):
    """7 x 24 matrix (rows Sunday..Saturday in Hebrew, columns hours 0..23)."""
    d = apply_mode(df, mode)
    m = d.groupby([d["timestamp"].dt.day_of_week, d["timestamp"].dt.hour]).size().unstack(fill_value=0)
    m = m.reindex(index=WEEKDAY_ORDER, columns=range(24), fill_value=0)
    m.index = [WEEKDAYS_HE[i] for i in m.index]
    return m


def date_hour_matrix(df, mode=MODE_LOCALITIES, start=None, end=None):
    """days x 24 matrix, every day in range present (quiet days are rows of zeros)."""
    d = apply_mode(df, mode)
    m = d.groupby([d["timestamp"].dt.normalize(), d["timestamp"].dt.hour]).size().unstack(fill_value=0)
    if m.empty:
        return m
    lo = pd.Timestamp(start) if start is not None else m.index.min()
    hi = pd.Timestamp(end) if end is not None else m.index.max()
    return m.reindex(index=pd.date_range(lo, hi, freq="1D"), columns=range(24), fill_value=0)


def hour_minute_matrix(df, minute_bin=10, mode=MODE_LOCALITIES):
    """24 x (60/minute_bin) matrix - the dashboard version of the legacy bar_16_color heatmap."""
    if 60 % minute_bin:
        raise ValueError("minute_bin must divide 60")
    d = apply_mode(df, mode)
    mins = (d["timestamp"].dt.minute // minute_bin) * minute_bin
    m = d.groupby([d["timestamp"].dt.hour, mins]).size().unstack(fill_value=0)
    return m.reindex(index=range(24), columns=range(0, 60, minute_bin), fill_value=0)


def top_counts(df, level, n=20, mode=MODE_LOCALITIES):
    """Top-n zones or cities. In events mode a zone counts each (minute, type) once."""
    if level == "zone" or mode == MODE_BARRAGES:
        d = apply_mode(df, mode, extra_keys=(level,))
    else:
        d = df
    return d[level].value_counts().head(n)


def shelter_distribution(df):
    s = df["shelter_sec"].dropna()
    if s.empty:
        return pd.Series(dtype=int)
    return s.astype(int).value_counts().sort_index()


def kpis(df, mode=MODE_LOCALITIES):
    d = apply_mode(df, mode)
    if d.empty:
        return {"total": 0, "active_days": 0, "per_active_day": 0.0, "peak_hour": None,
                "top_city": None, "top_city_count": 0, "localities": 0}
    days = d["timestamp"].dt.normalize().nunique()
    hours = d["timestamp"].dt.hour.value_counts()
    cities = df["city"].value_counts()
    return {
        "total": int(len(d)),
        "active_days": int(days),
        "per_active_day": float(len(d) / days) if days else 0.0,
        "peak_hour": int(hours.idxmax()),
        "top_city": cities.index[0],
        "top_city_count": int(cities.iloc[0]),
        "localities": int(df["city"].nunique()),
    }


def last_alert(df):
    """The most recent alert minute: its time, type(s) and where it sounded.

    Returns None for an empty frame. ``place`` is the locality when only one sounded,
    otherwise the zone with the most localities in that minute.
    """
    if df.empty:
        return None
    ts = df["timestamp"].max()
    rows = df[df["timestamp"] == ts]
    n = int(rows["city"].nunique())
    place = rows["city"].iloc[0] if n == 1 else rows["zone"].value_counts().index[0]
    types = [t for t in rows["alert_type"].value_counts().index]
    return {"timestamp": ts, "types": types, "localities": n, "place": place}


def busiest(series_or_frame):
    """(index, value) of the largest bin of a series / summed frame; None for empty input."""
    s = series_or_frame.sum(axis=1) if isinstance(series_or_frame, pd.DataFrame) else series_or_frame
    if s.empty or s.max() == 0:
        return None
    return s.idxmax(), int(s.max())


def as_int_matrix(m):
    return m.to_numpy(dtype=np.int64)
