"""Pure helpers for the interactive map: locality matching, per-locality/per-frame counts, color encoding.

Kept free of Streamlit/Plotly so it can be unit tested (tests/test_map_data.py).

Color encoding
--------------
Every locality gets one number in [0, 1] (``code``) that a single piecewise colorscale turns into a color:

    [0, 1/S)           gray      - no alerts (in the selected layers)
    [k/S, (k+1)/S)     ramp of layer k (light -> dark) - the locality's dominant alert type is layer k,
                       position inside the segment = sqrt-scaled total of the selected layers

With one layer this is a plain single-hue sequential scale; with several layers hue = dominant type and
lightness = amount. The same code drives both the polygon trace and the point trace, and animation frames
only have to update the codes.
"""

import json
import os
import re

import numpy as np
import pandas as pd

from dashboard_data import MODE_EVENTS, _floor

ROOT = os.path.dirname(os.path.abspath(__file__))
GEOJSON_FILE = os.path.join(ROOT, "data", "geo", "localities.geojson")

# Our name (as it appears in the channel) -> name in the geo source, for renamed localities.
ALIASES = {
    "אשדוד - אזור תעשייה צפוני ונמל": "אשדוד - איזור תעשייה צפוני",
    "מרכז אזורי מרום הגליל": "מרכז אזורי מרום גליל",
    "מרכז אזורי מבואות החרמון": "מרכז אזורי מבואות חרמון",
}

FRAME_RESOLUTIONS = {"יום": "1D", "6 שעות": "6h", "שעה": "1h"}
MAX_FRAMES = 100  # each frame carries a value per locality; keep the figure payload reasonable
_EPS = 0.02       # keep codes away from segment edges so float rounding can't change the hue


# --------------------------------------------------------------------------------------
# Geo data + name matching
# --------------------------------------------------------------------------------------
def name_key(name):
    """Normalize a locality name for matching: quote marks, hyphens, spacing, אזור/איזור."""
    n = re.sub(r"[\"'״׳`]", "", str(name))
    n = n.replace("-", " ").replace("איזור", "אזור")
    return re.sub(r"\s+", " ", n).strip()


def load_geo(path=GEOJSON_FILE):
    """Return (polygon_geojson, localities) where localities is a DataFrame indexed by geo name."""
    with open(path, encoding="utf-8") as f:
        geo = json.load(f)
    rows = [f["properties"] for f in geo["features"]]
    localities = pd.DataFrame(rows).set_index("name", drop=False)
    polygons = {"type": "FeatureCollection",
                "features": [f for f in geo["features"] if f["geometry"]["type"] == "Polygon"]}
    return polygons, localities


def build_matcher(geo_names):
    """key -> geo name. Combined source names ("נוף איילון, שעלבים") are also indexed by each part."""
    matcher = {}
    for name in geo_names:
        matcher.setdefault(name_key(name), name)
    for name in geo_names:
        if ", " in name:
            for part in name.split(", "):
                matcher.setdefault(name_key(part), name)
    return matcher


def match_city(city, matcher):
    city = ALIASES.get(city, city)
    key = name_key(city)
    if key in matcher:
        return matcher[key]
    if ", " in city:  # our combined name ("תקומה, חוות יזרעם") vs a single source name
        for part in city.split(", "):
            if name_key(part) in matcher:
                return matcher[name_key(part)]
    return None


def map_cities(cities, matcher):
    """{our city name: geo name or None} for every distinct city."""
    return {c: match_city(c, matcher) for c in pd.unique(pd.Series(list(cities)))}


def attach_geo(df, mapping):
    """Add a ``geo`` column (geo locality name); rows that couldn't be matched are dropped.

    Returns (df_with_geo, unmatched_counts) where unmatched_counts is a Series city -> rows.
    """
    geo = df["city"].map(mapping)
    unmatched = df.loc[geo.isna(), "city"].value_counts()
    return df.assign(geo=geo)[geo.notna()], unmatched


# --------------------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------------------
def counts_by_locality(df, mode, types):
    """geo x alert_type counts (wide). In events mode a locality counts each (minute, type) once."""
    d = df[df["alert_type"].isin(types)]
    if mode == MODE_EVENTS:
        d = d.drop_duplicates(subset=["timestamp", "alert_type", "geo"])
    if d.empty:
        return pd.DataFrame(columns=list(types), dtype=int)
    wide = d.groupby(["geo", "alert_type"]).size().unstack(fill_value=0)
    return wide.reindex(columns=list(types), fill_value=0)


def effective_frame_freq(start, end, freq):
    """Requested frame freq, or the next coarser one that keeps the frame count <= MAX_FRAMES."""
    span = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timestamp(start)
    freqs = list(FRAME_RESOLUTIONS.values())
    for f in freqs[freqs.index(freq)::-1]:  # 1h -> 6h -> 1D
        if span / pd.Timedelta(f) <= MAX_FRAMES:
            return f
    return "1D"


def frame_starts(start, end, freq):
    lo = pd.Timestamp(start)
    hi = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(minutes=1)
    return pd.date_range(lo, hi, freq=freq)


def counts_by_frame(df, mode, types, freq, start, end):
    """{frame start: geo x type wide counts} for every frame in [start, end] (empty frames included)."""
    d = df[df["alert_type"].isin(types)]
    if mode == MODE_EVENTS:
        d = d.drop_duplicates(subset=["timestamp", "alert_type", "geo"])
    frames = frame_starts(start, end, freq)
    out = {f: pd.DataFrame(columns=list(types), dtype=int) for f in frames}
    if d.empty:
        return out
    d = d.assign(frame=_floor(d["timestamp"], freq))
    for frame, g in d.groupby("frame"):
        if frame in out:
            out[frame] = g.groupby(["geo", "alert_type"]).size().unstack(fill_value=0).reindex(
                columns=list(types), fill_value=0)
    return out


# --------------------------------------------------------------------------------------
# Color encoding
# --------------------------------------------------------------------------------------
def intensity(total, vmax):
    """Square-root scaled 0..1: spreads the many mid-range localities better than linear, without the
    log scale's flattening of the top (most localities in a long range sit at 50-150 alerts)."""
    if vmax <= 0:
        return np.zeros_like(np.asarray(total, dtype=float))
    return np.sqrt(np.asarray(total, dtype=float) / vmax)


def encode(wide, geo_names, layers, vmax):
    """Codes in [0, 1] aligned to ``geo_names`` plus the per-layer counts matrix (len(geo_names) x len(layers))."""
    n_seg = len(layers) + 1
    counts = wide.reindex(index=list(geo_names), columns=list(layers), fill_value=0).fillna(0).to_numpy(dtype=float)
    total = counts.sum(axis=1)
    dominant = counts.argmax(axis=1) if len(layers) else np.zeros(len(total), dtype=int)
    frac = intensity(total, vmax)
    codes = np.where(
        total > 0,
        (1 + dominant + _EPS + (1 - 2 * _EPS) * frac) / n_seg,
        0.5 / n_seg,
    )
    return codes.round(4), counts.astype(int)


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def mix(c1, c2, t):
    """Linear mix of two hex colors: t=0 -> c1, t=1 -> c2."""
    a, b = _hex_to_rgb(c1), _hex_to_rgb(c2)
    return _rgb_to_hex(tuple(x + (y - x) * t for x, y in zip(a, b)))


def ramp(base, light_end, dark_end, steps=5):
    """Single-hue ramp from a pale tint of ``base`` to a deep shade (order: low -> high)."""
    lo, hi = light_end, dark_end
    pts = [mix(lo, base, i / (steps // 2)) for i in range(steps // 2 + 1)]
    pts += [mix(base, hi, i / (steps - steps // 2 - 1)) for i in range(1, steps - steps // 2)]
    return pts


def colorscale(zero_color, layer_ramps):
    """Piecewise Plotly colorscale: gray segment, then one ramp segment per layer (hard edges between)."""
    n_seg = len(layer_ramps) + 1
    scale = [[0.0, zero_color], [1 / n_seg, zero_color]]
    for k, steps in enumerate(layer_ramps, start=1):
        lo, hi = k / n_seg, (k + 1) / n_seg
        for i, c in enumerate(steps):
            scale.append([lo + (hi - lo) * i / (len(steps) - 1), c])
    scale[-1][0] = 1.0
    return scale
