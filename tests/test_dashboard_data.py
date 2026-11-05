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


def test_filter_places_is_an_or_of_zones_and_cities():
    df = make_df()
    assert len(dd.filter_places(df)) == len(df)
    both = dd.filter_places(df, zones=["עוטף עזה"], cities=["חולון"])
    assert len(both) == 4  # three Gaza-envelope rows + Holon
    assert dd.city_zones(df)["זרעית"] == "קו העימות"


def test_night_share_and_gaps():
    df = make_df()
    # night = 22:00-06:00: only the 23:10 Holon alert
    assert dd.night_share(df) == 1 / 6
    stats = dd.gap_stats(df)  # barrages: 14/06 12:55 rocket, 17/06 12:53-12:56 uav, 20/06 23:10 rocket
    assert stats["moments"] == 3
    assert stats["longest"] == pd.Timestamp("2026-06-20 23:10") - pd.Timestamp("2026-06-17 12:56")
    assert stats["longest_from"] == pd.Timestamp("2026-06-17 12:56")
    zar = dd.gap_stats(dd.filter_places(df, cities=["זרעית"]), per_locality=True)
    assert zar["moments"] == 2 and zar["median"] == pd.Timedelta(minutes=3)
    assert dd.gap_stats(df.iloc[0:1])["median"] is None


def test_format_duration():
    assert dd.format_duration(pd.Timedelta(seconds=20)) == "פחות מדקה"
    assert dd.format_duration(pd.Timedelta(minutes=3)) == "3 דקות"
    assert dd.format_duration(pd.Timedelta(hours=1)) == "שעה"
    assert dd.format_duration(pd.Timedelta(hours=5, minutes=30)) == "5.5 שעות"
    assert dd.format_duration(pd.Timedelta(days=3, hours=12)) == "3.5 ימים"
    assert dd.format_duration(None) == "-"


def test_records():
    df = make_df()
    r = dd.records(df, start=date(2026, 6, 13), end=date(2026, 6, 21))
    assert r["busiest_day"] == (pd.Timestamp("2026-06-14"), 3)
    assert r["largest_minute"] == (pd.Timestamp("2026-06-14 12:55"), 3)
    assert r["worst_zone_day"][0] == "עוטף עזה" and r["worst_zone_day"][2] == 3
    # quiet days: 13 | 15,16 | 18,19 | 21 -> longest run is 2 days, first one 15-16/06
    assert r["longest_quiet"] == (2, pd.Timestamp("2026-06-15"), pd.Timestamp("2026-06-16"))
    assert dd.records(df.iloc[0:0]) == {}


def test_calendar_matrix_weeks_by_weekday():
    df = make_df()
    m = dd.calendar_matrix(df, start=date(2026, 6, 14), end=date(2026, 6, 20))
    assert list(m.index) == ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    assert m.shape == (7, 1)  # 14/06/2026 is a Sunday: one full week
    assert m.loc["ראשון"].iloc[0] == 3 and m.loc["שבת"].iloc[0] == 1


def test_zone_table():
    df = make_df()
    t = dd.zone_table(df, start=date(2026, 6, 14), end=date(2026, 6, 20))
    assert list(t["zone"])[0] == "עוטף עזה" and t.loc[0, "total"] == 3 and t.loc[0, "localities"] == 3
    assert len(t.loc[0, "daily"]) == 7
    holon = t[t["zone"] == "דן"].iloc[0]
    assert holon["night_share"] == 1.0 and holon["median_gap"] is None


def test_gap_histogram_bins():
    g = pd.Series(pd.to_timedelta([3, 3, 20, 200, 3000], unit="min"))
    h = dd.gap_histogram(g)
    assert h["עד 5 דקות"] == 2 and h["15–30 דקות"] == 1 and h["3–6 שעות"] == 1 and h["יותר מיממה"] == 1
    assert int(h.sum()) == 5 and list(h.index)[0] == "עד 5 דקות"
    assert int(dd.gap_histogram(pd.Series(dtype="timedelta64[ns]")).sum()) == 0


def test_coverage_daily_covers_whole_period_and_marks_range():
    values, in_range = dd.coverage_daily(make_df(), dd.MODE_LOCALITIES, date(2026, 6, 13), date(2026, 6, 21),
                                         date(2026, 6, 14), date(2026, 6, 17))
    assert len(values) == len(in_range) == 9
    assert values[1] == 3 and values[4] == 2 and values[7] == 1 and sum(values) == 6
    assert in_range == [False, True, True, True, True, False, False, False, False]
    empty_values, _ = dd.coverage_daily(make_df().iloc[0:0], dd.MODE_EVENTS, date(2026, 6, 13), date(2026, 6, 14),
                                        date(2026, 6, 13), date(2026, 6, 14))
    assert empty_values == [0, 0]


def test_type_totals_follow_the_mode():
    df = make_df()
    assert dd.type_totals(df, dd.MODE_LOCALITIES).to_dict() == {"rocket": 4, "uav": 2}
    assert dd.type_totals(df, dd.MODE_EVENTS).to_dict() == {"rocket": 2, "uav": 2}
    assert dd.type_totals(df, dd.MODE_BARRAGES).to_dict() == {"rocket": 2, "uav": 1}  # 12:53 and 12:56: one barrage
    assert dd.type_totals(df.iloc[0:0], dd.MODE_EVENTS).empty


def test_toggle_type_isolates_then_returns_to_all():
    order = ["rocket", "uav", "infiltration"]
    assert dd.toggle_type([], "uav", order) == ["uav"]                    # all shown -> only this one
    assert dd.toggle_type(["uav"], "uav", order) == []                    # only this one -> all again
    assert dd.toggle_type(["uav"], "rocket", order) == ["rocket", "uav"]  # add, kept in order
    assert dd.toggle_type(["rocket", "uav"], "rocket", order) == ["uav"]  # remove
