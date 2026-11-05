import os
import sys
from datetime import date

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import map_data as md  # noqa: E402
from dashboard_data import MODE_BARRAGES, MODE_EVENTS, MODE_LOCALITIES  # noqa: E402

GEO_NAMES = ["כפר חב'ד", "נוף איילון, שעלבים", "בת ים", "תקומה", "אשדוד - איזור תעשייה צפוני", "סעד"]


def test_name_key_normalizes_quotes_and_hyphens():
    assert md.name_key("כפר חב''ד") == md.name_key("כפר חב'ד") == md.name_key('כפר חב"ד')
    assert md.name_key("בת - ים") == md.name_key("בת ים")
    assert md.name_key("אזור תעשייה") == md.name_key("איזור תעשייה")


def test_match_city_variants():
    m = md.build_matcher(GEO_NAMES)
    assert md.match_city("כפר חב''ד", m) == "כפר חב'ד"
    assert md.match_city("בת - ים", m) == "בת ים"
    assert md.match_city("שעלבים", m) == "נוף איילון, שעלבים"       # part of a combined source name
    assert md.match_city("תקומה, חוות יזרעם", m) == "תקומה"          # our combined name
    assert md.match_city("אשדוד - אזור תעשייה צפוני ונמל", m) == "אשדוד - איזור תעשייה צפוני"  # alias
    assert md.match_city("לא קיים", m) is None


def make_df():
    rows = [
        ("2026-06-14 12:55", "rocket", "עוטף עזה", "סעד"),
        ("2026-06-14 12:55", "uav", "עוטף עזה", "סעד"),
        ("2026-06-15 09:00", "uav", "עוטף עזה", "סעד"),
        ("2026-06-14 12:55", "rocket", "לכיש", "נוף איילון"),
        ("2026-06-14 12:55", "rocket", "לכיש", "שעלבים"),  # same polygon, same minute
        ("2026-06-16 08:00", "rocket", "דן", "לא קיים"),
    ]
    df = pd.DataFrame(rows, columns=["timestamp", "alert_type", "zone", "city"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def test_attach_geo_reports_unmatched():
    df = make_df()
    mapping = md.map_cities(df["city"], md.build_matcher(GEO_NAMES))
    dfg, unmatched = md.attach_geo(df, mapping)
    assert len(dfg) == 5 and unmatched.to_dict() == {"לא קיים": 1}


def test_counts_by_locality_modes():
    df = make_df()
    dfg, _ = md.attach_geo(df, md.map_cities(df["city"], md.build_matcher(GEO_NAMES)))
    loc = md.counts_by_locality(dfg, MODE_LOCALITIES, ["rocket", "uav"])
    assert loc.loc["נוף איילון, שעלבים", "rocket"] == 2
    assert loc.loc["סעד"].tolist() == [1, 2]
    ev = md.counts_by_locality(dfg, MODE_EVENTS, ["rocket", "uav"])
    assert ev.loc["נוף איילון, שעלבים", "rocket"] == 1  # one event for the shared polygon
    only_uav = md.counts_by_locality(dfg, MODE_LOCALITIES, ["uav"])
    assert list(only_uav.columns) == ["uav"] and "נוף איילון, שעלבים" not in only_uav.index


def test_counts_by_frame_includes_empty_frames():
    df = make_df()
    dfg, _ = md.attach_geo(df, md.map_cities(df["city"], md.build_matcher(GEO_NAMES)))
    frames = md.counts_by_frame(dfg, MODE_LOCALITIES, ["rocket", "uav"], "1D", date(2026, 6, 14), date(2026, 6, 17))
    assert len(frames) == 4
    totals = [int(w.to_numpy().sum()) for w in frames.values()]
    assert totals == [4, 1, 0, 0]


def test_effective_frame_freq_caps_frames():
    assert md.effective_frame_freq(date(2026, 6, 1), date(2026, 6, 3), "1h") == "1h"     # 72 frames
    assert md.effective_frame_freq(date(2026, 6, 1), date(2026, 6, 10), "1h") == "6h"    # 240 -> 40
    assert md.effective_frame_freq(date(2026, 1, 1), date(2026, 6, 30), "1h") == "1D"


def test_encode_segments_and_dominant_type():
    wide = pd.DataFrame({"rocket": [4, 0], "uav": [1, 3]}, index=["a", "b"])
    codes, counts = md.encode(wide, ["a", "b", "c"], ["rocket", "uav"], vmax=5)
    n_seg = 3
    assert 1 / n_seg < codes[0] < 2 / n_seg      # a: rocket dominant -> segment 1
    assert 2 / n_seg < codes[1] < 1.0            # b: uav dominant -> segment 2
    assert codes[2] < 1 / n_seg                  # c: no alerts -> gray segment
    assert counts.tolist() == [[4, 1], [0, 3], [0, 0]]
    # more alerts -> further into the segment (darker)
    c_hi, _ = md.encode(pd.DataFrame({"rocket": [5]}, index=["a"]), ["a"], ["rocket"], vmax=5)
    c_lo, _ = md.encode(pd.DataFrame({"rocket": [1]}, index=["a"]), ["a"], ["rocket"], vmax=5)
    assert c_hi[0] > c_lo[0]


def test_colorscale_is_monotonic_and_spans_0_1():
    scale = md.colorscale("#dddddd", [md.ramp("#2a78d6", "#ffffff", "#000000"), md.ramp("#eb6834", "#ffffff", "#000000")])
    pos = [p for p, _ in scale]
    assert pos[0] == 0.0 and pos[-1] == 1.0
    assert all(b >= a for a, b in zip(pos, pos[1:]))


def test_geojson_file_is_valid():
    polygons, localities = md.load_geo()
    assert len(localities) > 1400
    assert all(f["geometry"]["type"] == "Polygon" for f in polygons["features"])
    ring = polygons["features"][0]["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]
    lng, lat = ring[0]
    assert 34 < lng < 36 and 29 < lat < 34  # [lng, lat] order, inside Israel


def test_all_current_dataset_localities_are_matched():
    path = os.path.join(md.ROOT, "data", "alerts.csv.gz")
    cities = pd.read_csv(path, usecols=["city"])["city"]
    _, localities = md.load_geo()
    mapping = md.map_cities(cities, md.build_matcher(localities.index))
    missing = [c for c, g in mapping.items() if g is None]
    assert missing == [], missing


def test_counts_by_locality_barrages():
    df = make_df()
    extra = pd.DataFrame({"timestamp": pd.to_datetime(["2026-06-14 12:57"]), "alert_type": ["rocket"],
                          "zone": ["עוטף עזה"], "city": ["סעד"]})
    df = pd.concat([df, extra], ignore_index=True)  # 2 minutes after 12:55 -> same rocket barrage
    dfg, _ = md.attach_geo(df, md.map_cities(df["city"], md.build_matcher(GEO_NAMES)))
    b = md.counts_by_locality(dfg, MODE_BARRAGES, ["rocket", "uav"])
    assert b.loc["סעד"].tolist() == [1, 2]  # one rocket barrage; two separate UAV alerts
    assert md.counts_by_locality(dfg, MODE_LOCALITIES, ["rocket"]).loc["סעד", "rocket"] == 2


def _localities():
    return pd.DataFrame({"lat": [29.5, 33.3, 32.0, 31.5], "lng": [34.9, 35.6, 34.8, 34.5]},
                        index=["אילת", "מטולה", "תל אביב", "שדרות"])


def test_dot_projection_fits_frame_and_keeps_north_up():
    loc = _localities()
    proj = md.dot_projection(loc["lat"], loc["lng"])
    x, y = md.project(loc["lat"], loc["lng"], proj)
    x0, y0, x1, y1 = md.DOT_FRAME
    assert (x >= x0 - 0.1).all() and (x <= x1 + 0.1).all()
    assert (y >= y0 - 0.1).all() and (y <= y1 + 0.1).all()
    assert y[1] < y[2] < y[0]          # Metula north of Tel Aviv north of Eilat
    assert x[3] < x[1]                 # Sderot west of Metula
    assert y.max() - y.min() == pytest.approx(y1 - y0, abs=0.2)  # the long side fills the frame


def test_dot_levels_buckets_by_count_and_skips_unknown_and_zero():
    loc = _localities()
    proj = md.dot_projection(loc["lat"], loc["lng"])
    counts = pd.Series({"שדרות": 100, "תל אביב": 1, "מטולה": 0, "לא קיים": 50})
    levels = md.dot_levels(counts, loc, proj, levels=4)
    assert len(levels) == 4
    assert [len(x) for x, _ in levels] == [1, 0, 0, 1]  # Tel Aviv dimmest, Sderot brightest
    assert sum(len(x) for x, _ in md.dot_levels(pd.Series(dtype=int), loc, proj)) == 0
