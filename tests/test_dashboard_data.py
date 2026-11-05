import os
import sys
from datetime import date

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dashboard_data as dd  # noqa: E402


def make_df():
    rows = [
        # one rocket event at 12:55 covering three localities
        ("2026-06-14 12:55", "rocket", "עוטף עזה", "כפר עזה"),
        ("2026-06-14 12:55", "rocket", "עוטף עזה", "סעד"),
        ("2026-06-14 12:55", "rocket", "עוטף עזה", "זמרת, שובה"),
        # two UAV events in the same locality
        ("2026-06-17 12:53", "uav", "קו העימות", "זרעית"),
        ("2026-06-17 12:56", "uav", "קו העימות", "זרעית"),
        # Saturday night
        ("2026-06-20 23:10", "rocket", "דן", "חולון"),
    ]
    df = pd.DataFrame(rows, columns=["timestamp", "alert_type", "zone", "city"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["shelter_sec"] = pd.array([15, 15, 15, None, None, 90], dtype="Int64")
    return df


def test_filter_inclusive_end_date():
    df = make_df()
    out = dd.filter_alerts(df, start=date(2026, 6, 14), end=date(2026, 6, 17))
    assert len(out) == 5  # the 17th is included, the 20th is not


def test_filter_by_type_zone_city():
    df = make_df()
    assert len(dd.filter_alerts(df, types=["uav"])) == 2
    assert len(dd.filter_alerts(df, zones=["עוטף עזה"])) == 3
    assert len(dd.filter_alerts(df, cities=["חולון", "סעד"])) == 2


def test_events_mode_collapses_localities():
    df = make_df()
    assert dd.kpis(df, dd.MODE_LOCALITIES)["total"] == 6
    assert dd.kpis(df, dd.MODE_EVENTS)["total"] == 4  # 12:55 rocket, 12:53 uav, 12:56 uav, 23:10 rocket


def test_time_series_fills_quiet_days():
    df = make_df()
    ts = dd.time_series(df, "1D", start=date(2026, 6, 14), end=date(2026, 6, 20))
    assert len(ts) == 7
    assert ts.sum(axis=1).tolist() == [3, 0, 0, 2, 0, 0, 1]
    assert set(ts.columns) == {"rocket", "uav"}


def test_weekly_bins_start_on_sunday():
    df = make_df()
    ts = dd.time_series(df, "W")
    assert all(d.day_of_week == 6 for d in ts.index)  # Sunday


def test_effective_resolution_coarsens_long_ranges():
    df = make_df()
    assert dd.effective_resolution(df, "1D") == "1D"
    assert dd.effective_resolution(df, "1min") == "15min"  # 6 days of minutes > MAX_BINS


def test_hour_and_weekday_matrices():
    df = make_df()
    hod = dd.hour_of_day(df)
    assert hod.shape[0] == 24 and hod.loc[12].sum() == 5
    m = dd.weekday_hour_matrix(df)
    assert m.shape == (7, 24)
    assert list(m.index)[0] == "ראשון"
    assert m.loc["שבת", 23] == 1
    hm = dd.hour_minute_matrix(df, minute_bin=15)
    assert hm.shape == (24, 4) and hm.loc[12, 45] == 5


def test_date_hour_matrix_includes_every_day():
    df = make_df()
    m = dd.date_hour_matrix(df, start=date(2026, 6, 14), end=date(2026, 6, 20))
    assert m.shape == (7, 24)


def test_top_counts_and_shelter():
    df = make_df()
    assert dd.top_counts(df, "city", 1).to_dict() == {"זרעית": 2}
    assert dd.top_counts(df, "zone", 1, dd.MODE_EVENTS).to_dict() == {"קו העימות": 2}
    assert dd.shelter_distribution(df).to_dict() == {15: 3, 90: 1}


def test_last_alert():
    df = make_df()
    last = dd.last_alert(df)
    assert last["timestamp"] == pd.Timestamp("2026-06-20 23:10")
    assert last["place"] == "חולון" and last["localities"] == 1 and last["types"] == ["rocket"]

    gaza = dd.filter_alerts(df, zones=["עוטף עזה"])
    last = dd.last_alert(gaza)
    assert last["localities"] == 3 and last["place"] == "עוטף עזה"
    assert dd.last_alert(df.iloc[0:0]) is None


def test_barrages_group_close_minutes_per_type():
    df = make_df()
    ids = dd.barrage_ids(df)
    # 12:53 and 12:56 UAV are 3 minutes apart -> one barrage; rocket 12:55 is its own (other type)
    assert ids.nunique() == 3
    assert dd.kpis(df, dd.MODE_BARRAGES)["total"] == 3
    assert dd.barrage_ids(df, gap_minutes=2).nunique() == 4


def test_barrage_table_and_top_counts():
    df = make_df()
    t = dd.barrage_table(df)
    assert list(t["start"]) == sorted(t["start"], reverse=True)
    uav = t[t["alert_type"] == "uav"].iloc[0]
    assert uav["start"] == pd.Timestamp("2026-06-17 12:53") and uav["end"] == pd.Timestamp("2026-06-17 12:56")
    assert uav["localities"] == 1 and uav["zones"] == ["קו העימות"]
    gaza = t[t["alert_type"] == "rocket"].iloc[-1]
    assert gaza["localities"] == 3
    # in barrage mode a locality hit twice in one barrage counts once
    assert dd.top_counts(df, "city", mode=dd.MODE_BARRAGES)["זרעית"] == 1
    assert dd.barrage_table(df.iloc[0:0]).empty
