"""Interactive red-alert statistics dashboard.

Run:  streamlit run dashboard.py
Data: data/alerts.csv.gz (built by build_dataset.py / collect_alerts.py; built automatically if missing).
"""

import os
from html import escape
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import dashboard_data as dd
import dashboard_style as ds
import map_data as md
from alerts_parser import ALERT_TYPE_LABELS
from build_dataset import load_alerts

st.set_page_config(page_title="סטטיסטיקת התרעות", page_icon="🔴", layout="wide")

# ?dev=1 shows maintainer hints (collection commands). End users never see shell commands.
DEV = st.query_params.get("dev") == "1"

# --------------------------------------------------------------------------------------
# Theme: tokens live in dashboard_style.py. Light / dark are each selected, not flipped.
# Each alert type keeps its own color whatever the filter.
# --------------------------------------------------------------------------------------
TYPE_ORDER = list(ALERT_TYPE_LABELS.keys())  # rocket, uav, infiltration, early_warning, ...
FONT = ds.FONT
PLOTLY_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}


def current_theme():
    try:
        return ds.THEMES["dark" if st.context.theme.type == "dark" else "light"]
    except Exception:  # older Streamlit / no theme info
        return ds.THEMES["light"]


T = current_theme()


def type_color(alert_type):
    return ds.type_color(T, alert_type)


def single_color(frame):
    """Color for a one-series chart: the type's own color when one type is shown, else the brand red."""
    present = frame["alert_type"].unique()
    return type_color(present[0]) if len(present) == 1 else T["brand"]


def seq_scale():
    steps = T["seq"]
    return [[i / (len(steps) - 1), c] for i, c in enumerate(steps)]


def style(fig, height=380, legend=True):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=10, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",  # the card behind it carries the surface
        font=dict(family=FONT, color=T["ink2"], size=13),
        hoverlabel=dict(font_family=FONT, bgcolor=T["card"], font_color=T["ink"], bordercolor=T["axis"]),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text=""),
        bargap=0.15,
    )
    axis = dict(automargin=True, gridcolor=T["grid"], linecolor=T["axis"], zerolinecolor=T["axis"], tickfont=dict(color=T["muted"]),
                title_font=dict(color=T["ink2"]))
    fig.update_xaxes(**axis, showgrid=False)  # horizontal gridlines only
    fig.update_yaxes(**axis, showline=False)
    return fig


def show(fig, title=None, subtitle="", note=None, fixed_width=False, icon=None):
    """Chart with its title and subtitle above. The source line is shown once per tab (tab_source)."""
    if title:
        st.markdown(ds.chart_head_html(title, subtitle, icon), unsafe_allow_html=True)
    st.plotly_chart(fig, width="content" if fixed_width else "stretch", config=PLOTLY_CONFIG, theme=None)
    if note:
        st.markdown(ds.chart_foot_html(note), unsafe_allow_html=True)


def head(title, subtitle="", icon=None):
    st.markdown(ds.chart_head_html(title, subtitle, icon), unsafe_allow_html=True)


def tab_source():
    st.markdown(ds.tab_source_html(f"מקור: ערוץ הטלגרם צופר - צבע אדום. עודכן {SOURCE_UPDATED}."),
                unsafe_allow_html=True)


def type_name(alert_type):
    """Type label with its shape, for pills and legends."""
    return f"{ds.type_shape(alert_type)} {dd.type_label(alert_type)}"


# --------------------------------------------------------------------------------------
# Global CSS (RTL on content only; charts and tables stay LTR because time runs left to right).
# --------------------------------------------------------------------------------------
st.markdown(ds.global_css(T), unsafe_allow_html=True)


@st.cache_data(show_spinner="טוען נתונים...")
def get_alerts():
    df = load_alerts()
    df["zone"] = df["zone"].fillna("")
    df["city"] = df["city"].fillna("")
    return df


def notice(title, body):
    st.markdown(ds.notice_html(title, body), unsafe_allow_html=True)


@st.cache_resource(show_spinner="טוען את מפת היישובים...")
def get_geo():
    polygons, localities = md.load_geo()
    return polygons, localities, md.build_matcher(localities.index)


@st.cache_data
def city_mapping(cities):
    return md.map_cities(cities, get_geo()[2])


@st.cache_resource
def dot_base():
    """Projection of every locality into the outline's viewBox (header dots and locator)."""
    localities = get_geo()[1]
    proj = md.dot_projection(localities["lat"], localities["lng"])
    return proj, md.project(localities["lat"], localities["lng"], proj)


def geo_names_of(frame):
    return frame["city"].map(city_mapping(ALL_CITIES)).dropna()


def hero_dots(frame):
    """Brightness levels of the localities with alerts in ``frame`` (counted in the current mode)."""
    if frame.empty:
        return None
    dfg = frame.assign(geo=geo_names_of(frame)).dropna(subset=["geo"])
    counts = md.counts_by_locality(dfg, mode, sorted(dfg["alert_type"].unique())).sum(axis=1)
    return md.dot_levels(counts, get_geo()[1], dot_base()[0])


def locator(zones, cities, frame):
    """Locator figure: all localities in gray, the picked zones and localities in red.

    With no place picked, the localities with alerts in ``frame`` are tinted instead."""
    proj, localities = dot_base()[0], get_geo()[1]
    if not (zones or cities):
        alerted = md.dot_points(geo_names_of(frame.drop_duplicates("city")), localities, proj)
        return ds.locator_html(dot_base()[1], alerted, "כל הארץ", faint=True)
    picked = alerts[alerts["zone"].isin(zones) | alerts["city"].isin(cities)].drop_duplicates("city")
    selected = md.dot_points(geo_names_of(picked), localities, proj)
    if len(zones) + len(cities) == 1:
        label = (zones or cities)[0]
    else:
        label = f"{len(zones) + len(cities)} מקומות"
    return ds.locator_html(dot_base()[1], selected, label)


def toggle_type(alert_type):
    """Legend click: add or remove one type from the type selection in the bar."""
    cur = list(st.session_state.get("types") or [])
    cur = [t for t in cur if t != alert_type] if alert_type in cur else cur + [alert_type]
    st.session_state["types"] = [t for t in TYPE_ORDER if t in cur]


def sidebar_overview():
    """Data coverage (whole period, current place and types; picked range in red) and the type legend."""
    all_days = dd.filter_places(dd.filter_alerts(alerts, data_min, data_max, types), zones, cities)
    daily = dd.time_series(all_days, "1D", mode, data_min, data_max).sum(axis=1)
    in_range = [(start <= d.date() <= end) for d in daily.index]
    st.markdown(ds.coverage_html(daily.values, in_range, T["brand"], T["axis"], data_min, data_max,
                                 note="באדום: הטווח שנבחר"), unsafe_allow_html=True)
    in_period = dd.filter_places(dd.filter_alerts(alerts, start, end, []), zones, cities)
    by_type = dd.time_series(in_period, "1D", mode, start, end).sum() if len(in_period) else pd.Series(dtype=int)
    chosen = set(types)
    entries = []
    st.markdown(f'<div class="ra-coverage__title">סוגי התרעות · {escape(unit)}</div>', unsafe_allow_html=True)
    with st.container(key="type_legend"):
        for i, t in enumerate(present_types):
            key = f"legend_{i}"
            entries.append((key, ds.type_shape(t), type_color(t), not chosen or t in chosen))
            st.button(f"{dd.type_label(t)} · {int(by_type.get(t, 0)):,}", key=key, type="tertiary",
                      on_click=toggle_type, args=(t,),
                      help="לחיצה מוסיפה את הסוג לבחירה או מסירה אותו ממנה")
    st.markdown(ds.legend_css(entries), unsafe_allow_html=True)


TITLE = "סטטיסטיקת התרעות"
SUBTITLE = "נתוני התרעות פיקוד העורף מערוץ הטלגרם \"צופר - צבע אדום\""

alerts = get_alerts()
if alerts.empty:
    st.markdown(ds.hero_html(TITLE, SUBTITLE, []), unsafe_allow_html=True)
    notice("עדיין אין נתונים להצגה", "נתוני ההתרעות יופיעו כאן אחרי העדכון הבא.")
    if DEV:
        st.caption("לאיסוף: `python collect_alerts.py --since 2026-02-26`")
    st.stop()

data_min = alerts["timestamp"].min().date()
SOURCE_UPDATED = f'{alerts["timestamp"].max():%d/%m/%Y %H:%M}'
data_max = alerts["timestamp"].max().date()

# --------------------------------------------------------------------------------------
# Filters. The main choices (place, type, period) sit in a bar under the header; the sidebar keeps
# only advanced options (count mode). Places: one picker for zones and localities ("z|name" / "c|name").
# --------------------------------------------------------------------------------------
MODES = {"יישובים": dd.MODE_LOCALITIES, "אירועים": dd.MODE_EVENTS, "מטחים": dd.MODE_BARRAGES}
UNITS = {dd.MODE_LOCALITIES: "התרעות ביישובים", dd.MODE_EVENTS: "אירועי התרעה", dd.MODE_BARRAGES: "מטחים"}
ALL_TIME, CUSTOM = "הכל", "מותאם"
PRESETS = {ALL_TIME: None, "7 ימים": 7, "30 ימים": 30, "90 ימים": 90, CUSTOM: "custom"}
CITY_ZONE = dd.city_zones(alerts)
ALL_CITIES = tuple(sorted(alerts["city"].unique()))


def place_label(key):
    kind, name = key.split("|", 1)
    if kind == "z":
        return f"אזור {name}"
    zone = CITY_ZONE.get(name)
    return f"{name} ({zone})" if zone else name


def apply_preset():
    choice = st.session_state.get("preset") or ALL_TIME
    st.session_state["preset"] = choice
    days = PRESETS[choice]
    if days == "custom":
        return  # keep the current range; the date field appears
    lo = data_min if days is None else max(data_min, data_max - timedelta(days=days - 1))
    st.session_state["date_range"] = (lo, data_max)


def reset_filters():
    st.session_state["place_sel"] = []
    st.session_state["types"] = []
    st.session_state["preset"] = ALL_TIME
    apply_preset()


def set_places(zones=(), cities=()):
    st.session_state["place_sel"] = [f"z|{z}" for z in zones] + [f"c|{c}" for c in cities]


if "date_range" not in st.session_state:
    st.session_state["date_range"] = (data_min, data_max)
st.session_state.setdefault("preset", ALL_TIME)

with st.sidebar:
    st.header("אפשרויות")
    mode_label = st.radio(
        "אופן ספירה", list(MODES), horizontal=True,
        help="יישובים: כל יישוב שהופעלה בו התרעה נספר בנפרד.\n\n"
             "אירועים: כל דקה עם התרעה (מכל סוג) נספרת פעם אחת, לא משנה בכמה יישובים.\n\n"
             f"מטחים: התרעות מאותו סוג בהפרש של עד {dd.BARRAGE_GAP_MIN} דקות נספרות כמטח אחד.",
    )
    mode = MODES[mode_label]
    st.divider()
    side_slot = st.container()  # coverage strip and type legend, filled once the selection is known
    st.markdown(ds.sidebar_meta_html(data_min, data_max, len(alerts)), unsafe_allow_html=True)
    sources = alerts["source"].value_counts()
    if "telegram" not in sources:
        st.caption("בשלב זה מוצגים נתוני צבע אדום בלבד. סוגי התרעות נוספים יתווספו בעדכון הבא.")
        if DEV:
            st.caption("לאיסוף כל סוגי ההתרעות: `python collect_alerts.py --since 2026-02-26`")

data_until = alerts["timestamp"].max()
chips = []
if mode != dd.MODE_LOCALITIES:
    chips.append((f"ספירה לפי {mode_label}", "plain"))
chips.append((f"הנתונים מעודכנים עד {data_until:%d/%m/%Y %H:%M}", "status"))
hero_slot = st.empty()  # filled once the selection is known (the dots follow it)

# --- Selection bar ---------------------------------------------------------------------
zone_keys = [f"z|{z}" for z in sorted(alerts["zone"].unique()) if z]
city_keys = [f"c|{c}" for c in sorted(alerts["city"].unique()) if c]
present_types = [t for t in TYPE_ORDER if t in set(alerts["alert_type"])]
with st.container(key="filterbar"):
    c_place, c_type, c_period, c_locator = st.columns([1.9, 1.1, 3, 0.45], vertical_alignment="bottom")
    with c_place:
        place_sel = st.multiselect("אזור או יישוב", zone_keys + city_keys, key="place_sel", format_func=place_label,
                                   placeholder="כל הארץ (הקלידו לחיפוש)")
    with c_type:
        types = st.pills("סוג התרעה", present_types, selection_mode="multi", key="types",
                         format_func=type_name, help="בלי בחירה מוצגים כל הסוגים") or []
    with c_period:
        # LTR button group: listed so that "הכל" ends up on the right (the start, in RTL reading).
        st.segmented_control("תקופה", list(reversed(PRESETS)), key="preset", on_change=apply_preset,
                             help="הימים נספרים אחורה מהיום האחרון שיש עליו נתונים")
    if st.session_state.get("preset") == CUSTOM:
        st.date_input("טווח תאריכים", key="date_range", min_value=data_min, max_value=data_max,
                      format="DD/MM/YYYY")

picked = st.session_state["date_range"]
start, end = (picked[0], picked[1]) if isinstance(picked, (list, tuple)) and len(picked) == 2 else (data_min, data_max)
zones = [k.split("|", 1)[1] for k in place_sel if k.startswith("z|")]
cities = [k.split("|", 1)[1] for k in place_sel if k.startswith("c|")]
filtered = bool(place_sel or types) or (start, end) != (data_min, data_max)
if filtered:
    st.button("ניקוי בחירה", on_click=reset_filters, key="reset_top", type="tertiary",
              icon=":material/filter_alt_off:")

df = dd.filter_places(dd.filter_alerts(alerts, start, end, types), zones, cities)
unit = UNITS[mode]
hero_slot.markdown(ds.hero_html(TITLE, SUBTITLE, chips, dots=hero_dots(df)), unsafe_allow_html=True)
with c_locator:
    st.markdown(locator(zones, cities, df), unsafe_allow_html=True)
with side_slot:
    sidebar_overview()

if df.empty:
    notice("אין התרעות שמתאימות לבחירה", "אפשר להרחיב את התקופה, או להסיר חלק מהסוגים, האזורים והיישובים.")
    st.markdown(ds.footer_html(data_until), unsafe_allow_html=True)
    st.stop()

# --- KPI row ---------------------------------------------------------------------------
k = dd.kpis(df, mode)
last = dd.last_alert(df)
daily_total = dd.time_series(df, "1D", mode, start, end).sum(axis=1)
hours_total = dd.hour_of_day(df, mode).sum(axis=1)
n_days = (end - start).days + 1
last_where = last["place"] + (f", {last['localities']:,} יישובים" if last["localities"] > 1 else "")
st.markdown(ds.kpi_row_html([
    {"label": unit, "value": f"{k['total']:,}",
     "sub": {dd.MODE_LOCALITIES: f"ב-{k['localities']:,} יישובים",
             dd.MODE_EVENTS: "כל דקה וסוג נספרים פעם אחת",
             dd.MODE_BARRAGES: f"התרעות בהפרש של עד {dd.BARRAGE_GAP_MIN} דקות"}[mode],
     "viz": ds.sparkline_svg(daily_total.values, single_color(df))},
    {"label": "ימים עם התרעות", "value": f"{k['active_days']:,}", "sub": f"מתוך {n_days:,} ימים בתקופה",
     "viz": ds.ratio_bar_html(k["active_days"] / n_days if n_days else 0)},
    {"label": "שעת שיא", "value": f"{k['peak_hour']:02d}:00", "ltr": True,
     "sub": f"ממוצע ליום פעיל: {round(k['per_active_day']):,}",
     "viz": ds.hour_bars_svg(hours_total.values, k["peak_hour"], single_color(df), T["axis"])},
    {"label": "התרעה אחרונה", "value": f"{last['timestamp']:%d/%m/%Y %H:%M}", "ltr": True, "text": True,
     "sub": last_where},
]), unsafe_allow_html=True)

TAB_NAMES = [":material/insights: סקירה", ":material/map: מפה", ":material/location_on: אזורים",
             ":material/schedule: זמנים", ":material/notifications: אחרונות", ":material/table: נתונים"]
try:
    # Lazy tabs: the heavy map is only built while its tab is open (Streamlit >= 1.5x).
    tabs = st.tabs(TAB_NAMES, key="tab", on_change="rerun")
except TypeError:
    tabs = st.tabs(TAB_NAMES)
tab_time, tab_map, tab_places, tab_hours, tab_recent, tab_data = tabs
tab_days = tab_shelter = tab_hours  # "times" holds hours, the day x hour grid and shelter time


def tab_is_open(tab):
    if os.getenv("DASHBOARD_ALL_TABS") == "1":  # tests: build every lazy tab
        return True
    is_open = getattr(tab, "open", None)
    return True if is_open is None else bool(is_open)


def stacked_bars(wide, x_title, height=380, hover_x="%{x}"):
    fig = go.Figure()
    # A thin surface-colored gap between stacked segments, unless the bars are too dense for it.
    gap = 1.5 if len(wide.columns) > 1 and len(wide) <= 200 else 0
    for t in [t for t in TYPE_ORDER if t in wide.columns]:
        fig.add_bar(x=wide.index, y=wide[t], name=type_name(t), marker_color=type_color(t),
                    marker_line_width=gap, marker_line_color=T["card"],
                    hovertemplate=f"{hover_x}<br>{dd.type_label(t)}: %{{y:,}}<extra></extra>")
    fig.update_layout(barmode="stack", barcornerradius=4)
    style(fig, height=height, legend=len(wide.columns) > 1)
    fig.update_yaxes(rangemode="tozero")
    return fig


# --- Time series ----------------------------------------------------------------------
with tab_time:
    res_label = st.segmented_control("רזולוציה", list(dd.RESOLUTIONS), default="יום", key="res") or "יום"
    freq = dd.RESOLUTIONS[res_label]
    eff = dd.effective_resolution(df, freq)
    if eff != freq:
        eff_label = next(k for k, v in dd.RESOLUTIONS.items() if v == eff)
        st.caption(f"הטווח ארוך מדי לרזולוציה של {res_label}, ולכן הגרף מוצג ברזולוציה של {eff_label}. "
                   f"כדי לראות רזולוציה עדינה יותר צריך לצמצם את טווח התאריכים.")
    ts = dd.time_series(df, eff, mode, start, end)
    hover_fmt = "%{x|%d/%m/%Y}" if eff in ("1D", "W") else "%{x|%d/%m/%Y %H:%M}"
    fig = stacked_bars(ts, "", height=420, hover_x=hover_fmt)
    fig.update_layout(hovermode="x unified" if len(ts.columns) > 1 else "closest")
    fig.update_xaxes(tickformat="%d/%m" if eff in ("1D", "W", "6h") else "%d/%m %H:%M")
    peak = dd.busiest(ts)
    if peak:
        ts_peak, val = peak
        fig.add_annotation(x=ts_peak, y=val, text=f"שיא: {val:,}", showarrow=True, arrowhead=0, ax=0, ay=-28,
                           font=dict(color=T["ink"], size=12), arrowcolor=T["axis"])
    eff_name = next(k for k, v in dd.RESOLUTIONS.items() if v == eff)
    show(fig, f"{unit} לאורך זמן", f"לפי {eff_name}, {start:%d/%m/%Y} עד {end:%d/%m/%Y}", icon="show_chart")

    # Records: plain facts about the current selection
    rec = dd.records(df, mode, start, end)
    facts = []
    day, n = rec["busiest_day"]
    facts.append({"label": "היום העמוס ביותר", "value": f"{day:%d/%m/%Y}", "ltr": True, "sub": f"{n:,} {unit}"})
    hour, n = rec["busiest_hour"]
    facts.append({"label": "השעה העמוסה ביותר", "value": f"{hour:%d/%m/%Y %H}:00", "ltr": True, "sub": f"{n:,} {unit}"})
    ts_max, n = rec["largest_minute"]
    if n > 1:
        facts.append({"label": "הכי הרבה יישובים בדקה אחת", "value": f"{n:,} יישובים",
                      "sub": f"ב-{ts_max:%d/%m/%Y} בשעה {ts_max:%H:%M}"})
    if "worst_zone_day" in rec:
        zone, day, n = rec["worst_zone_day"]
        facts.append({"label": "האזור עם הכי הרבה התרעות ביום אחד", "value": zone,
                      "sub": f"{n:,} {unit} ב-{day:%d/%m/%Y}"})
    q, q_from, q_to = rec["longest_quiet"]
    facts.append({"label": "הרצף הארוך ביותר של ימים בלי התרעות",
                  "value": "אין ימים שקטים" if q == 0 else ("יום אחד" if q == 1 else f"{q} ימים"),
                  "sub": "בכל יום בתקופה הייתה לפחות התרעה אחת" if q == 0 else f"{q_from:%d/%m} עד {q_to:%d/%m/%Y}"})
    head("שיאים", "לפי התקופה, הסוגים והמקומות שנבחרו", icon="leaderboard")
    st.markdown(ds.facts_html(facts), unsafe_allow_html=True)

    # Calendar: one square per day, weeks as columns
    cal = dd.calendar_matrix(df, mode, start, end)
    dates = [[(w + timedelta(days=i)).strftime("%d/%m/%Y") for w in cal.columns] for i in range(7)]
    fig = go.Figure(go.Heatmap(
        z=cal.values, x=[f"{w:%d/%m}" for w in cal.columns], y=cal.index, customdata=dates,
        colorscale=seq_scale(), xgap=3, ygap=3, hoverongaps=False,
        hovertemplate="%{customdata}, יום %{y}<br>" + unit + ": %{z:,}<extra></extra>",
        colorbar=dict(thickness=8, len=0.9, outlinewidth=0, tickfont=dict(color=T["muted"]))))
    n_weeks = cal.shape[1]
    cell = 30 if n_weeks <= 20 else 18
    fixed = n_weeks * cell <= 880  # short ranges: square cells at a fixed size; long ranges: fill the width
    style(fig, height=7 * cell + 70, legend=False)
    fig.update_layout(margin=dict(l=8, r=8, t=34, b=8))
    if fixed:
        fig.update_layout(width=n_weeks * cell + 150)
    # Week labels ("22/02") are wider than a cell: short ranges show the first and last week only,
    # longer ones every second (narrow cells: every third) week.
    ticks = sorted({0, n_weeks - 1}) if n_weeks <= 6 else list(range(0, n_weeks, 2 if cell >= 30 else 3))
    fig.update_yaxes(autorange="reversed", type="category", ticksuffix="  ", showgrid=False)
    fig.update_xaxes(type="category", side="top", showgrid=False, tickangle=0,
                     tickvals=ticks, ticktext=[f"{cal.columns[i]:%d/%m}" for i in ticks])
    show(fig, "לוח שנה", f"{unit} בכל יום. עמודה היא שבוע שמתחיל ביום ראשון", fixed_width=fixed,
         icon="calendar_month")
    tab_source()

# --- Recent barrages -----------------------------------------------------------------
with tab_recent:
    recent = dd.barrage_table(df).head(40)
    st.caption(f"המטחים האחרונים בטווח, מהחדש לישן. מטח הוא רצף התרעות מאותו סוג בהפרש של עד "
               f"{dd.BARRAGE_GAP_MIN} דקות.")
    st.markdown(ds.feed_html(recent, type_color, dd.type_label), unsafe_allow_html=True)
    tab_source()

# --- Map ------------------------------------------------------------------------------
# Base map tiles (no API key). Set MAP_STYLE=white-bg to use the map without internet tiles.
MAP_STYLE = {"light": "carto-positron", "dark": "carto-darkmatter"}
MAP_ZERO = {"light": "#DDE0E4", "dark": "#2F333B"}  # "no alerts" fill, neutral gray


def layer_ramp(alert_type):
    """Single-hue ramp for one layer, low -> high, selected separately for light and dark maps."""
    base = type_color(alert_type)
    if T is ds.THEMES["dark"]:
        return md.ramp(base, md.mix(base, T["surface"], 0.6), md.mix(base, "#ffffff", 0.6))
    return md.ramp(base, md.mix(base, "#ffffff", 0.8), md.mix(base, "#000000", 0.35))


def map_figure(frames_counts, layers, poly_names, point_names, poly_text, point_text, frame_labels, selected):
    """Polygon + point traces sharing one piecewise colorscale; optional animation frames."""
    theme_key = "dark" if T is ds.THEMES["dark"] else "light"
    scale = md.colorscale(MAP_ZERO[theme_key], [layer_ramp(t) for t in layers])
    vmax = max((w.sum(axis=1).max() for w in frames_counts if len(w)), default=0)
    labels = [dd.type_label(t) for t in layers]
    hover = "<b>%{text}</b><br>" + "<br>".join(f"{lab}: %{{customdata[{i}]:,}}" for i, lab in enumerate(labels))
    if len(layers) > 1:
        hover += f"<br>סה\"כ: %{{customdata[{len(layers)}]:,}}"
    hover += "<extra></extra>"

    def trace_values(wide):
        pc, pcounts = md.encode(wide, poly_names, layers, vmax)
        qc, qcounts = md.encode(wide, point_names, layers, vmax)
        add_total = (lambda c: [list(r) + [int(sum(r))] for r in c]) if len(layers) > 1 else (lambda c: c.tolist())
        return pc, add_total(pcounts), qc, add_total(qcounts)

    polygons = get_geo()[0]
    pc, pcd, qc, qcd = trace_values(frames_counts[0])
    fig = go.Figure([
        go.Choroplethmap(
            geojson=polygons, locations=poly_names, featureidkey="id", z=pc, zmin=0, zmax=1, colorscale=scale,
            showscale=False, marker_opacity=0.85, marker_line_width=0.4, marker_line_color=T["card"],
            selected=dict(marker=dict(opacity=0.85)), unselected=dict(marker=dict(opacity=0.85)),
            text=poly_text, customdata=pcd, hovertemplate=hover, name=""),
        go.Scattermap(
            lat=get_geo()[1].loc[point_names, "lat"], lon=get_geo()[1].loc[point_names, "lng"], mode="markers",
            marker=dict(size=6, color=qc, cmin=0, cmax=1, colorscale=scale, opacity=0.9),
            selected=dict(marker=dict(opacity=0.9)), unselected=dict(marker=dict(opacity=0.9)),
            text=point_text, customdata=qcd, hovertemplate=hover, name=""),
    ])
    if selected and selected in set(poly_names):
        fig.add_trace(go.Choroplethmap(
            geojson=polygons, locations=[selected], featureidkey="id", z=[1],
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False,
            marker_line_width=2.5, marker_line_color=T["ink"], hoverinfo="skip", name=""))
    elif selected and selected in set(point_names):
        loc = get_geo()[1].loc[selected]
        fig.add_trace(go.Scattermap(lat=[loc["lat"]], lon=[loc["lng"]], mode="markers", hoverinfo="skip",
                                    marker=dict(size=16, color="rgba(0,0,0,0)"), name=""))

    if len(frames_counts) > 1:
        frames = []
        for label, wide in zip(frame_labels, frames_counts):
            pc, pcd, qc, qcd = trace_values(wide)
            frames.append(go.Frame(name=label, traces=[0, 1], data=[
                go.Choroplethmap(z=pc, customdata=pcd), go.Scattermap(marker=dict(color=qc), customdata=qcd)]))
        fig.frames = frames
        play = dict(frame=dict(duration=700, redraw=True), fromcurrent=True, transition=dict(duration=0))
        fig.update_layout(
            updatemenus=[dict(type="buttons", direction="left", x=0.01, y=0.99, xanchor="left", yanchor="top",
                              pad=dict(r=6, t=6), bgcolor=T["card"], bordercolor=T["axis"],
                              font=dict(color=T["ink"]), buttons=[
                                  dict(label="▶ הפעלה", method="animate", args=[None, play]),
                                  dict(label="⏸ עצירה", method="animate",
                                       args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
            sliders=[dict(active=0, x=0.02, len=0.96, y=0.02, yanchor="bottom", pad=dict(t=0, b=6),
                          bgcolor=T["grid"], bordercolor=T["axis"],
                          # Too many frames -> step labels collide; hide them and rely on the current value.
                          font=dict(color=T["ink2"] if len(frame_labels) <= 31 else "rgba(0,0,0,0)", size=11),
                          currentvalue=dict(prefix="", font=dict(color=T["ink"], size=14), xanchor="right"),
                          steps=[dict(label=lab, method="animate",
                                      args=[[lab], dict(frame=dict(duration=0, redraw=True), mode="immediate")])
                                 for lab in frame_labels])])
    fig.update_layout(
        map=dict(style=os.getenv("MAP_STYLE") or MAP_STYLE[theme_key], center=dict(lat=31.75, lon=35.0), zoom=6.95),
        height=680, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=T["card"], showlegend=False,
        uirevision="map",  # keep zoom/pan when the app reruns (e.g. after a click)
        hoverlabel=dict(font_family=FONT, bgcolor=T["card"], font_color=T["ink"], bordercolor=T["axis"]),
        font=dict(family=FONT, color=T["ink2"]))
    return fig


def map_legend(layers):
    def strip(colors):
        return (f'<span style="display:inline-block;width:96px;height:10px;border-radius:2px;vertical-align:middle;'
                f'background:linear-gradient(to left, {", ".join(colors)})"></span>')
    theme_key = "dark" if T is ds.THEMES["dark"] else "light"
    parts = [f'<span style="white-space:nowrap"><span style="color:{type_color(t)}" aria-hidden="true">'
             f'{ds.type_shape(t)}</span> {dd.type_label(t)}: מעט {strip(layer_ramp(t))} הרבה</span>' for t in layers]
    parts.append(f'<span style="white-space:nowrap"><span style="display:inline-block;width:12px;height:10px;'
                 f'border-radius:2px;vertical-align:middle;background:{MAP_ZERO[theme_key]}"></span> אין התרעות</span>')
    note = "צבע = סוג ההתרעה הנפוץ ביישוב · " if len(layers) > 1 else ""
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:6px 20px;font-size:0.85rem;color:{T["ink2"]}">'
                f'{"".join(parts)}</div><div style="font-size:0.8rem;color:{T["muted"]};margin-top:2px">'
                f'{note}עוצמת הצבע בסקאלת שורש ריבועי, כדי להבחין גם בין יישובים עם כמויות דומות</div>',
                unsafe_allow_html=True)


def select_city_from_map(event, poly_names, point_names):
    """Turn a map click into st.session_state['map_city'] (only when the click changed)."""
    points = (event or {}).get("selection", {}).get("points", []) if isinstance(event, dict) else \
        getattr(getattr(event, "selection", None), "points", []) or []
    if not points:
        return
    pt = points[0]
    name = pt.get("location")
    if name is None and pt.get("curve_number") == 1:
        idx = pt.get("point_index", pt.get("point_number"))
        name = point_names[idx] if idx is not None and idx < len(point_names) else None
    click_id = (name, pt.get("curve_number"), pt.get("point_index"))
    if name and st.session_state.get("_map_last_click") != click_id:
        st.session_state["_map_last_click"] = click_id
        st.session_state["map_city"] = name


def focus_dashboard_on(our_cities):
    set_places(cities=sorted(our_cities))


def locality_details(geo_name, dfg, layers, localities):
    info = localities.loc[geo_name]
    sub = dfg[(dfg["geo"] == geo_name) & dfg["alert_type"].isin(layers)]
    shelter = info.get("countdown")
    shelter_txt = ""
    if pd.notna(shelter):
        s = int(shelter)
        shelter_txt = " · זמן התגוננות: " + ("מיידי" if s == 0 else f"{s} שניות" if s < 60 else
                                             "דקה" if s == 60 else "דקה וחצי" if s == 90 else f"{s // 60} דקות")
    st.subheader(geo_name)
    st.caption(f"{info.get('zone', '')}{shelter_txt}")
    if sub.empty:
        notice("אין התרעות ביישוב הזה", "לא היו התרעות בטווח ובשכבות שנבחרו. אפשר להרחיב את טווח התאריכים.")
        return
    cards = [{"label": type_name(t), "value": f"{int((sub['alert_type'] == t).sum()):,}", "sub": "התרעות ביישוב"}
             for t in layers]
    cards.append({"label": "התרעה אחרונה", "value": f"{sub['timestamp'].max():%d/%m/%Y %H:%M}", "ltr": True,
                  "text": True})
    st.markdown(ds.kpi_cards_html(cards), unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        fig = stacked_bars(dd.hour_of_day(sub), "שעה ביום", height=280, hover_x="%{x}:00")
        fig.update_xaxes(tickmode="array", tickvals=list(range(0, 24, 3)), ticktext=[f"{h:02d}" for h in range(0, 24, 3)])
        show(fig, "לפי שעה ביום", "התרעות ביישוב", icon="schedule")
    with right:
        daily = dd.time_series(sub, "1D", start=start, end=end)
        fig = stacked_bars(daily, "", height=280, hover_x="%{x|%d/%m/%Y}")
        fig.update_xaxes(tickformat="%d/%m")
        show(fig, "לפי יום", "התרעות ביישוב", icon="calendar_today")
    our_names = sorted(sub["city"].unique())
    st.button(f"הצג את כל הדשבורד עבור {geo_name}", on_click=focus_dashboard_on, args=(our_names,),
              help="מסנן את כל הלשוניות ליישוב הזה (אפשר לבטל ב'ניקוי בחירה')")


with tab_map:
    if tab_is_open(tab_map):
        polygons, localities, _ = get_geo()
        mapping = city_mapping(ALL_CITIES)
        dfg, unmatched = md.attach_geo(df, mapping)

        present = [t for t in TYPE_ORDER if t in set(df["alert_type"])]
        c_layers, c_anim, c_res = st.columns([3, 1.4, 2])
        with c_layers:
            layers = st.pills("שכבות", present, selection_mode="multi", default=present, key="map_layers",
                              format_func=type_name, help="אפשר להדליק ולכבות כל סוג התרעה")
        with c_anim:
            animate = st.toggle("אנימציה לאורך זמן", key="map_anim")
        frame_freq = None
        if animate:
            with c_res:
                fr_label = st.segmented_control("כל תמונה מציגה", list(md.FRAME_RESOLUTIONS), default="יום",
                                                key="map_frame") or "יום"
            frame_freq = md.effective_frame_freq(start, end, md.FRAME_RESOLUTIONS[fr_label])
            if frame_freq != md.FRAME_RESOLUTIONS[fr_label]:
                eff = next(k for k, v in md.FRAME_RESOLUTIONS.items() if v == frame_freq)
                st.caption(f"הטווח ארוך מדי לתמונה לכל {fr_label}, ולכן כל תמונה מציגה {eff}. "
                           "לרזולוציה עדינה יותר צריך לצמצם את טווח התאריכים.")

        layers = [t for t in TYPE_ORDER if t in (layers or [])]
        if not layers:
            notice("לא נבחרה שכבה", "בחרו לפחות סוג התרעה אחד בשכבות כדי לראות את המפה.")
        else:
            poly_names = [f["id"] for f in polygons["features"]]
            point_names = list(localities.index[~localities["has_polygon"].astype(bool)])
            text_for = lambda names: [f"{n} · {localities.at[n, 'zone']}" for n in names]  # noqa: E731
            if frame_freq:
                by_frame = md.counts_by_frame(dfg, mode, layers, frame_freq, start, end)
                fmt = "%d/%m/%Y" if frame_freq == "1D" else "%d/%m %H:%M"
                frame_labels = [f.strftime(fmt) for f in by_frame]
                frames_counts = list(by_frame.values())
            else:
                frame_labels, frames_counts = [""], [md.counts_by_locality(dfg, mode, layers)]

            # The click from the previous interaction is already in session_state: apply it before drawing,
            # so the highlight shows immediately.
            select_city_from_map(st.session_state.get("map_chart"), poly_names, point_names)
            selected = st.session_state.get("map_city")
            fig = map_figure(frames_counts, layers, poly_names, point_names, text_for(poly_names),
                             text_for(point_names), frame_labels, selected)
            head("התרעות לפי יישוב", f"{unit}, {start:%d/%m/%Y} עד {end:%d/%m/%Y}. "
                                     "לחיצה על יישוב פותחת את הפרטים שלו", icon="map")
            st.plotly_chart(fig, width="stretch", config={**PLOTLY_CONFIG, "scrollZoom": True},
                            theme=None, on_select="rerun", selection_mode="points", key="map_chart")
            map_legend(layers)
            if len(unmatched):
                st.caption(f"{len(unmatched)} יישובים ({int(unmatched.sum()):,} התרעות) לא מופיעים על המפה "
                           f"כי לא נמצא להם מיקום: {', '.join(unmatched.index[:5])}")

            st.divider()
            with_alerts = dfg[dfg["alert_type"].isin(layers)]["geo"].value_counts()
            options = list(with_alerts.index) + sorted(set(localities.index) - set(with_alerts.index))
            if st.session_state.get("map_city") not in options:
                st.session_state["map_city"] = None
            chosen = st.selectbox("פרטי יישוב", options, key="map_city", index=None,
                                  placeholder="לחצו על יישוב במפה או בחרו מהרשימה",
                                  format_func=lambda n: f"{n} ({with_alerts.get(n, 0):,})")
            if chosen:
                locality_details(chosen, dfg, layers, localities)
        tab_source()

# --- Hours of day ---------------------------------------------------------------------
with tab_hours:
    per_locality = len(cities) == 1 and not zones
    gs = dd.gap_stats(df, per_locality)
    between = f"בין התרעות ב{cities[0]}" if per_locality else "בין מטחים"
    night = dd.night_share(df, mode)
    head("מרווחים בין התרעות",
         f"{between} בבחירה הנוכחית" + ("" if per_locality else
                                         f". מטח: התרעות מאותו סוג בהפרש של עד {dd.BARRAGE_GAP_MIN} דקות"),
         icon="timer")
    longest_sub = (f"התחילה ב-{gs['longest_from']:%d/%m/%Y} בשעה {gs['longest_from']:%H:%M}"
                   if gs["longest"] is not None else "צריך לפחות שתי התרעות")
    st.markdown(ds.kpi_row_html([
        {"label": "מרווח חציוני", "value": dd.format_duration(gs["median"]),
         "sub": "חצי מהמרווחים קצרים מזה"},
        {"label": "ההפסקה הארוכה ביותר", "value": dd.format_duration(gs["longest"]), "sub": longest_sub},
        {"label": "בלילה", "value": f"{round((night or 0) * 100)}%", "ltr": True,
         "sub": "בין 22:00 ל-06:00"},
        {"label": "התרעות בפועל" if per_locality else "מטחים", "value": f"{gs['moments']:,}",
         "sub": "דקות עם התרעה ביישוב" if per_locality else "בבחירה הנוכחית"},
    ]), unsafe_allow_html=True)
    if len(gs["gaps"]):
        hist = dd.gap_histogram(gs["gaps"])
        fig = go.Figure(go.Bar(x=list(hist.index), y=hist.values, marker_color=single_color(df), marker_line_width=0,
                               hovertemplate="%{x}<br>%{y:,} מרווחים<extra></extra>"))
        fig.update_layout(barcornerradius=4)
        style(fig, height=300, legend=False)
        fig.update_xaxes(type="category")
        show(fig, "כמה זמן עובר עד ההתרעה הבאה", f"מספר המרווחים {between} לפי משך", icon="hourglass_empty")

    hod = dd.hour_of_day(df, mode)
    fig = stacked_bars(hod, "שעה ביום", hover_x="%{x}:00")
    fig.update_xaxes(tickmode="array", tickvals=list(range(0, 24, 2)), ticktext=[f"{h:02d}" for h in range(0, 24, 2)])
    show(fig, "לפי שעה ביממה", f"{unit}, שעון ישראל", icon="schedule")

    left, right = st.columns(2)
    with left:
        m = dd.weekday_hour_matrix(df, mode)
        fig = go.Figure(go.Heatmap(
            z=m.values, x=[f"{h:02d}" for h in m.columns], y=m.index, colorscale=seq_scale(), xgap=2, ygap=2,
            hovertemplate="יום %{y}, %{x}:00<br>" + unit + ": %{z:,}<extra></extra>",
            colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=T["muted"]))))
        style(fig, height=340, legend=False)
        fig.update_yaxes(autorange="reversed", showgrid=False, type="category", ticksuffix="  ")
        fig.update_xaxes(showgrid=False, type="category")
        show(fig, "יום בשבוע ושעה", f"{unit}. שורות: ימי השבוע, עמודות: שעות", icon="date_range")
    with right:
        minute_bin = st.segmented_control("חלון דקות", [5, 10, 15, 20, 30], default=10, key="mbin") or 10
        m = dd.hour_minute_matrix(df, minute_bin, mode)
        fig = go.Figure(go.Heatmap(
            z=m.values, x=[f":{c:02d}" for c in m.columns], y=[f"{h:02d}" for h in m.index],
            colorscale=seq_scale(), xgap=1, ygap=1,
            hovertemplate="%{y}%{x}<br>" + unit + ": %{z:,}<extra></extra>",
            colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=T["muted"]))))
        style(fig, height=520, legend=False)
        fig.update_yaxes(autorange="reversed", showgrid=False, type="category")
        fig.update_xaxes(showgrid=False, type="category")
        show(fig, "שעה ודקה", f"{unit}. שורות: שעות, עמודות: חלונות של {minute_bin} דקות", icon="grid_on")

# --- Day x hour calendar --------------------------------------------------------------
with tab_days:
    m = dd.date_hour_matrix(df, mode, start, end)
    n_days = len(m)
    fig = go.Figure(go.Heatmap(
        z=m.values, x=[f"{h:02d}" for h in m.columns], y=[d.strftime("%d/%m/%Y") for d in m.index],
        colorscale=seq_scale(), xgap=1, ygap=1,
        hovertemplate="%{y} %{x}:00<br>" + unit + ": %{z:,}<extra></extra>",
        colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=T["muted"]))))
    style(fig, height=min(1600, max(320, 18 * n_days + 80)), legend=False)
    fig.update_yaxes(autorange="reversed", showgrid=False, type="category",
                     dtick=max(1, n_days // 40))
    fig.update_xaxes(showgrid=False, side="top", type="category")
    fig.update_layout(margin=dict(t=28))
    show(fig, "כל יום בתקופה לפי שעה", f"{unit}. שורות: ימים, עמודות: שעות ביממה", icon="calendar_view_week")
    daily = m.sum(axis=1)
    quiet = int((daily == 0).sum())
    st.caption(f"{n_days} ימים בטווח · {quiet} ימים בלי התרעות · היום העמוס ביותר: "
               f"{daily.idxmax():%d/%m/%Y} ({int(daily.max()):,})")

# --- Zones & cities -------------------------------------------------------------------
def select_place(level):
    """Row click in a top-places table filters the whole dashboard to that place."""
    rows = st.session_state[f"top_{level}"].selection.rows
    if not rows:
        return
    name = st.session_state[f"_top_{level}_names"][rows[0]]
    if level == "zone":
        set_places(zones=[name])
    else:
        set_places(cities=[name])


with tab_places:
    if tab_is_open(tab_places):
        st.caption("לחיצה על שורה מסננת את כל הדשבורד לאותו אזור או יישוב.")
        zt = dd.zone_table(df, mode, start, end)
        st.session_state["_top_zone_names"] = list(zt["zone"])
        zview = pd.DataFrame({
            "daily": zt["daily"], "top_type": zt["top_type"].map(dd.type_label),
            "median_gap": zt["median_gap"].map(dd.format_duration), "night": zt["night_share"] * 100,
            "localities": zt["localities"], "total": zt["total"], "zone": zt["zone"],
        })
        head("השוואת אזורים", f"{unit} בכל אזור, מהגבוה לנמוך", icon="location_on")
        st.dataframe(
            zview, hide_index=True, key="top_zone", on_select=lambda: select_place("zone"),
            selection_mode="single-row", height=min(560, 35 * len(zview) + 38),
            column_order=["daily", "top_type", "median_gap", "night", "localities", "total", "zone"],  # LTR grid
            column_config={
                "zone": st.column_config.TextColumn("אזור"),
                "total": st.column_config.ProgressColumn(unit, format="localized", min_value=0,
                                                         max_value=int(zt["total"].max()) if len(zt) else 1),
                "localities": st.column_config.NumberColumn("יישובים", help="יישובים שקיבלו התרעה באזור"),
                "night": st.column_config.NumberColumn("בלילה", format="%.0f%%", help="אחוז ההתרעות בין 22:00 ל-06:00"),
                "median_gap": st.column_config.TextColumn(
                    "מרווח חציוני", help=f"הזמן החציוני בין מטחים באזור (מטח: התרעות מאותו סוג בהפרש של עד "
                                         f"{dd.BARRAGE_GAP_MIN} דקות)"),
                "top_type": st.column_config.TextColumn("סוג נפוץ"),
                "daily": st.column_config.LineChartColumn("מגמה יומית", y_min=0),
            })

        # Small multiples: the busiest zones on one shared time axis, read right to left like the table
        top = zt.head(12)
        if len(top) > 1:
            n_cols = 4 if len(top) > 6 else 3
            n_rows = -(-len(top) // n_cols)
            days = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="1D")
            # RTL: the busiest zone at the top right. Titles are given in plotly's row-major, left-to-right order.
            cell = {idx: (idx // n_cols + 1, n_cols - idx % n_cols) for idx in top.index}
            titles = [" "] * (n_rows * n_cols)
            for idx, row in top.iterrows():
                r, c = cell[idx]
                titles[(r - 1) * n_cols + (c - 1)] = f"<b>{row['zone']}</b>  {row['total']:,}"
            fig = make_subplots(rows=n_rows, cols=n_cols, shared_xaxes=True, shared_yaxes=True,
                                horizontal_spacing=0.03, vertical_spacing=0.14, subplot_titles=titles)
            color = single_color(df)
            for idx, row in top.iterrows():
                r, c = cell[idx]
                fig.add_trace(go.Scatter(
                    x=days, y=row["daily"], mode="lines", line=dict(color=color, width=1.6), fill="tozeroy",
                    fillcolor=ds.with_alpha(color, 0.14), name=row["zone"],
                    hovertemplate=f"{row['zone']}<br>%{{x|%d/%m/%Y}}: %{{y:,}}<extra></extra>"), row=r, col=c)
            style(fig, height=150 * n_rows + 40, legend=False)
            fig.update_layout(margin=dict(l=8, r=8, t=36, b=8))
            fig.update_annotations(font=dict(size=12, color=T["ink"]))
            fig.update_xaxes(showticklabels=True, tickformat="%d/%m", nticks=4)
            fig.update_yaxes(rangemode="tozero", nticks=3)
            show(fig, "מגמה לפי אזור", f"{unit} ביום ב-{len(top)} האזורים עם הכי הרבה התרעות, על אותו ציר",
                 icon="stacked_line_chart")

        top_city = dd.top_counts(df, "city", 20, mode)
        st.session_state["_top_city_names"] = list(top_city.index)
        city_label = unit if mode == dd.MODE_BARRAGES else "התרעות ביישוב"
        ctable = pd.DataFrame({"rank": range(1, len(top_city) + 1), "name": top_city.index,
                               "zone": [CITY_ZONE.get(c, "") for c in top_city.index], "count": top_city.values})
        head("יישובים עם הכי הרבה התרעות", city_label, icon="home_pin")
        st.dataframe(
            ctable, hide_index=True, key="top_city", on_select=lambda: select_place("city"),
            selection_mode="single-row", height=35 * len(ctable) + 38,
            column_order=["count", "zone", "name", "rank"],  # LTR grid: the rank ends up on the right
            column_config={
                "rank": st.column_config.NumberColumn("#", width="small"),
                "name": st.column_config.TextColumn("יישוב"),
                "zone": st.column_config.TextColumn("אזור"),
                "count": st.column_config.ProgressColumn(
                    city_label, format="localized", min_value=0, max_value=int(top_city.max()) if len(top_city) else 1),
            })
        tab_source()

# --- Shelter time ---------------------------------------------------------------------
with tab_shelter:
    sd = dd.shelter_distribution(df)
    if sd.empty:
        notice("עדיין אין נתוני זמן התגוננות",
               "הם יופיעו אחרי העדכון הבא של הנתונים. המקור הנוכחי (ארכיון ישן של הערוץ) לא שמר אותם.")
        if DEV:
            st.caption("כדי להשלים: `python collect_alerts.py --since 2026-02-26`")
    else:
        def fmt(sec):
            return "מיידי" if sec == 0 else (f"{sec} שניות" if sec < 60 else
                                             ("דקה" if sec == 60 else ("דקה וחצי" if sec == 90 else f"{sec // 60} דקות")))
        fig = go.Figure(go.Bar(x=[fmt(s) for s in sd.index], y=sd.values, marker_color=single_color(df),
                               marker_line_width=0, hovertemplate="%{x}<br>%{y:,} התרעות ביישובים<extra></extra>"))
        fig.update_layout(barcornerradius=4)
        style(fig, legend=False)
        fig.update_xaxes(type="category")
        show(fig, "זמן התגוננות", "התרעות ביישובים לפי הזמן שיש לתושבים להגיע למרחב מוגן", icon="shield")
    tab_source()

# --- Raw data -------------------------------------------------------------------------
with tab_data:
    view = df.assign(alert_type=df["alert_type"].map(dd.type_label)).rename(columns={
        "timestamp": "זמן", "alert_type": "סוג", "zone": "אזור", "city": "יישוב", "shelter_sec": "זמן התגוננות (שניות)",
    })[["זמן התגוננות (שניות)", "יישוב", "אזור", "סוג", "זמן"]].sort_values("זמן", ascending=False)  # LTR grid: time ends up on the right
    if view["זמן התגוננות (שניות)"].isna().all():  # old archive rows carry no shelter time
        view = view.drop(columns="זמן התגוננות (שניות)")
    st.caption(f"{len(view):,} רשומות (כל שורה היא יישוב שהופעלה בו התרעה בדקה מסוימת)")
    st.dataframe(view, width="stretch", hide_index=True, height=480,
                 column_config={"זמן": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm")})
    st.download_button("הורדת הנתונים המסוננים (CSV)", view.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"alerts_{start:%Y%m%d}_{end:%Y%m%d}.csv", mime="text/csv")
    tab_source()

with st.expander("איך חישבנו"):
    st.markdown(
        f"""
- **המקור היחיד** הוא הודעות ערוץ הטלגרם "צופר - צבע אדום": איזה יישוב, באיזו דקה ואיזה סוג התרעה.
- **התרעות ביישובים**: כל יישוב שהופעלה בו התרעה נספר פעם אחת בכל דקה. יישוב שהופיע פעמיים באותה דקה נספר פעם אחת.
- **אירועים**: כל דקה וסוג התרעה נספרים פעם אחת, לא משנה בכמה יישובים.
- **מטחים**: התרעות מאותו סוג בהפרש של עד {dd.BARRAGE_GAP_MIN} דקות נספרות כמטח אחד, ולכן מטח יכול להימשך יותר מ-{dd.BARRAGE_GAP_MIN} דקות.
- **לילה**: 22:00 עד 06:00. כל הזמנים בשעון ישראל.
- **מרווחים**: כשנבחר יישוב אחד, המרווח נמדד בין דקות ההתרעה שלו. אחרת הוא נמדד בין מטחים.
- **לא נספרות** הודעות "סיום אירוע".
- **התרעה ביישוב איננה רקטה**, ואזור התרעה איננו נקודת פגיעה. התרעה אחת יכולה להפעיל עשרות יישובים.
- **הנתונים נכונים** עד {SOURCE_UPDATED}.
""")

st.markdown(ds.footer_html(data_until), unsafe_allow_html=True)
