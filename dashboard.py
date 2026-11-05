"""Interactive red-alert statistics dashboard.

Run:  streamlit run dashboard.py
Data: data/alerts.csv.gz (built by build_dataset.py / collect_alerts.py; built automatically if missing).
"""

import os
from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
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
        margin=dict(l=14, r=16, t=44, b=12),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",  # the card behind it carries the surface
        font=dict(family=FONT, color=T["ink2"], size=13),
        title=dict(xref="paper", x=1, xanchor="right", font=dict(color=T["ink"], size=15)),  # RTL: title on the right
        hoverlabel=dict(font_family=FONT, bgcolor=T["card"], font_color=T["ink"], bordercolor=T["axis"]),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text=""),
        bargap=0.15,
    )
    axis = dict(automargin=True, gridcolor=T["grid"], linecolor=T["axis"], zerolinecolor=T["axis"], tickfont=dict(color=T["muted"]),
                title_font=dict(color=T["ink2"]))
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig


def show(fig):
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG, theme=None)


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
data_max = alerts["timestamp"].max().date()

# --------------------------------------------------------------------------------------
# Sidebar filters
# --------------------------------------------------------------------------------------
MODES = {"יישובים": dd.MODE_LOCALITIES, "אירועים": dd.MODE_EVENTS, "מטחים": dd.MODE_BARRAGES}
UNITS = {dd.MODE_LOCALITIES: "התרעות ביישובים", dd.MODE_EVENTS: "אירועי התרעה", dd.MODE_BARRAGES: "מטחים"}
PRESETS = {"כל התקופה": None, "7 הימים האחרונים": 7, "30 הימים האחרונים": 30, "90 הימים האחרונים": 90}


def apply_preset():
    days = PRESETS[st.session_state["preset"]]
    lo = data_min if days is None else max(data_min, data_max - timedelta(days=days - 1))
    st.session_state["date_range"] = (lo, data_max)


def reset_filters():
    for key in ("types", "zones", "cities"):
        st.session_state[key] = []
    st.session_state["preset"] = "כל התקופה"
    apply_preset()


if "date_range" not in st.session_state:
    st.session_state["date_range"] = (data_min, data_max)

with st.sidebar:
    st.header("סינון")
    st.selectbox("טווח מהיר", list(PRESETS), key="preset", on_change=apply_preset,
                 help="הימים האחרונים נספרים מהיום האחרון שיש עליו נתונים")
    picked = st.date_input("טווח תאריכים", key="date_range", min_value=data_min, max_value=data_max,
                           format="DD/MM/YYYY")
    start, end = (picked[0], picked[1]) if isinstance(picked, (list, tuple)) and len(picked) == 2 else (data_min, data_max)

    present_types = [t for t in TYPE_ORDER if t in set(alerts["alert_type"])]
    types = st.multiselect("סוג התרעה", present_types, key="types", format_func=dd.type_label,
                           placeholder="כל הסוגים")

    zone_options = sorted(alerts["zone"].unique())
    zones = st.multiselect("אזור", zone_options, key="zones", placeholder="כל האזורים")
    city_pool = alerts if not zones else alerts[alerts["zone"].isin(zones)]
    cities = st.multiselect("יישוב", sorted(city_pool["city"].unique()), key="cities", placeholder="כל היישובים")

    mode_label = st.radio(
        "אופן ספירה", list(MODES), horizontal=True,
        help="יישובים: כל יישוב שהופעלה בו התרעה נספר בנפרד.\n\n"
             "אירועים: כל דקה עם התרעה (מכל סוג) נספרת פעם אחת, לא משנה בכמה יישובים.\n\n"
             f"מטחים: התרעות מאותו סוג בהפרש של עד {dd.BARRAGE_GAP_MIN} דקות נספרות כמטח אחד.",
    )
    mode = MODES[mode_label]

    st.button("ניקוי סינון", on_click=reset_filters, width="stretch")

    st.divider()
    st.markdown(ds.sidebar_meta_html(data_min, data_max, len(alerts)), unsafe_allow_html=True)
    sources = alerts["source"].value_counts()
    if "telegram" not in sources:
        st.caption("בשלב זה מוצגים נתוני צבע אדום בלבד. סוגי התרעות נוספים יתווספו בעדכון הבא.")
        if DEV:
            st.caption("לאיסוף כל סוגי ההתרעות: `python collect_alerts.py --since 2026-02-26`")

df = dd.filter_alerts(alerts, start, end, types, zones, cities)
unit = UNITS[mode]

# --------------------------------------------------------------------------------------
# Header + KPIs
# --------------------------------------------------------------------------------------
scope = "כל הארץ"
if cities:
    scope = ", ".join(cities[:3]) + (f" ועוד {len(cities) - 3}" if len(cities) > 3 else "")
elif zones:
    scope = ", ".join(zones[:3]) + (f" ועוד {len(zones) - 3}" if len(zones) > 3 else "")
data_until = alerts["timestamp"].max()
chips = [(scope, "plain"), (f"{start:%d/%m/%Y} – {end:%d/%m/%Y}", "ltr")]
if types:
    chips.append((", ".join(dd.type_label(t) for t in types), "plain"))
if mode != dd.MODE_LOCALITIES:
    chips.append((f"ספירה לפי {mode_label}", "plain"))
chips.append((f"הנתונים מעודכנים עד {data_until:%d/%m/%Y %H:%M}", "status"))
st.markdown(ds.hero_html(TITLE, SUBTITLE, chips), unsafe_allow_html=True)

# On narrow screens the sidebar is closed: the chips show the active filter, and this clears it.
filtered = bool(types or zones or cities) or (start, end) != (data_min, data_max)
if filtered:
    st.button("ניקוי סינון", on_click=reset_filters, key="reset_top", icon=":material/filter_alt_off:")

if df.empty:
    notice("אין התרעות שמתאימות לסינון", "אפשר להרחיב את טווח התאריכים, או להסיר חלק מהסוגים, האזורים והיישובים.")
    st.markdown(ds.footer_html(data_until), unsafe_allow_html=True)
    st.stop()

k = dd.kpis(df, mode)
last = dd.last_alert(df)
last_where = last["place"] + (f" · {last['localities']:,} יישובים" if last["localities"] > 1 else "")
st.markdown(ds.kpi_cards_html([
    {"label": unit, "value": f"{k['total']:,}", "primary": True,
     "sub": {dd.MODE_LOCALITIES: f"{k['localities']:,} יישובים קיבלו התרעה",
             dd.MODE_EVENTS: "כל דקה וסוג נספרים פעם אחת",
             dd.MODE_BARRAGES: f"התרעות בהפרש של עד {dd.BARRAGE_GAP_MIN} דקות = מטח אחד"}[mode]},
    {"label": "ימים עם התרעות", "value": f"{k['active_days']:,}", "sub": f"מתוך {(end - start).days + 1:,} ימים בטווח"},
    {"label": "ממוצע ליום פעיל", "value": f"{round(k['per_active_day']):,}", "sub": unit},
    {"label": "שעת שיא", "value": f"{k['peak_hour']:02d}:00", "ltr": True,
     "sub": "השעה העמוסה ביותר ביממה"},
    {"label": "היישוב עם הכי הרבה התרעות", "value": k["top_city"], "text": True,
     "sub": f"{k['top_city_count']:,} התרעות ביישוב"},
    {"label": "התרעה אחרונה בטווח", "value": f"{last['timestamp']:%d/%m/%Y %H:%M}", "ltr": True, "text": True,
     "sub": last_where},
]), unsafe_allow_html=True)

TAB_NAMES = ["ציר זמן", "מפה", "אחרונות", "שעות", "מקומות", "התגוננות", "נתונים"]
try:
    # Lazy tabs: the heavy map is only built while its tab is open (Streamlit >= 1.5x).
    tabs = st.tabs(TAB_NAMES, key="tab", on_change="rerun")
except TypeError:
    tabs = st.tabs(TAB_NAMES)
tab_time, tab_map, tab_recent, tab_hours, tab_places, tab_shelter, tab_data = tabs
tab_days = tab_hours  # the day x hour calendar is the last chart of the hour-patterns tab


def tab_is_open(tab):
    is_open = getattr(tab, "open", None)
    return True if is_open is None else bool(is_open)


def stacked_bars(wide, x_title, height=380, hover_x="%{x}"):
    fig = go.Figure()
    # A thin surface-colored gap between stacked segments, unless the bars are too dense for it.
    gap = 1.5 if len(wide.columns) > 1 and len(wide) <= 200 else 0
    for t in [t for t in TYPE_ORDER if t in wide.columns]:
        fig.add_bar(x=wide.index, y=wide[t], name=dd.type_label(t), marker_color=type_color(t),
                    marker_line_width=gap, marker_line_color=T["card"],
                    hovertemplate=f"{hover_x}<br>{dd.type_label(t)}: %{{y:,}}<extra></extra>")
    fig.update_layout(barmode="stack", barcornerradius=4)
    style(fig, height=height, legend=len(wide.columns) > 1)
    fig.update_xaxes(title_text=x_title)
    fig.update_yaxes(title_text=unit, rangemode="tozero")
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
    fig.update_layout(title_text=f"{unit} לפי {next(k for k, v in dd.RESOLUTIONS.items() if v == eff)}")
    show(fig)

# --- Recent barrages -----------------------------------------------------------------
with tab_recent:
    recent = dd.barrage_table(df).head(40)
    st.caption(f"המטחים האחרונים בטווח, מהחדש לישן. מטח הוא רצף התרעות מאותו סוג בהפרש של עד "
               f"{dd.BARRAGE_GAP_MIN} דקות.")
    st.markdown(ds.feed_html(recent, type_color, dd.type_label), unsafe_allow_html=True)

# --- Map ------------------------------------------------------------------------------
# Base map tiles (no API key). Set MAP_STYLE=white-bg to use the map without internet tiles.
MAP_STYLE = {"light": "carto-positron", "dark": "carto-darkmatter"}
MAP_ZERO = {"light": "#DDE0E4", "dark": "#2F333B"}  # "no alerts" fill, neutral gray


@st.cache_resource(show_spinner="טוען את מפת היישובים...")
def get_geo():
    polygons, localities = md.load_geo()
    return polygons, localities, md.build_matcher(localities.index)


@st.cache_data
def city_mapping(cities):
    return md.map_cities(cities, get_geo()[2])


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
    parts = [f'<span style="white-space:nowrap">{dd.type_label(t)}: מעט {strip(layer_ramp(t))} הרבה</span>'
             for t in layers]
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
    st.session_state["zones"] = []
    st.session_state["cities"] = sorted(our_cities)


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
    cards = [{"label": dd.type_label(t), "value": f"{int((sub['alert_type'] == t).sum()):,}", "sub": "התרעות ביישוב"}
             for t in layers]
    cards.append({"label": "התרעה אחרונה", "value": f"{sub['timestamp'].max():%d/%m/%Y %H:%M}", "ltr": True,
                  "text": True})
    st.markdown(ds.kpi_cards_html(cards), unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        fig = stacked_bars(dd.hour_of_day(sub), "שעה ביום", height=280, hover_x="%{x}:00")
        fig.update_xaxes(tickmode="array", tickvals=list(range(0, 24, 3)), ticktext=[f"{h:02d}" for h in range(0, 24, 3)])
        fig.update_yaxes(title_text="התרעות")
        fig.update_layout(title_text="לפי שעה ביום")
        show(fig)
    with right:
        daily = dd.time_series(sub, "1D", start=start, end=end)
        fig = stacked_bars(daily, "", height=280, hover_x="%{x|%d/%m/%Y}")
        fig.update_xaxes(tickformat="%d/%m")
        fig.update_yaxes(title_text="התרעות")
        fig.update_layout(title_text="לפי יום")
        show(fig)
    our_names = sorted(sub["city"].unique())
    st.button(f"הצג את כל הדשבורד עבור {geo_name}", on_click=focus_dashboard_on, args=(our_names,),
              help="מסנן את כל הלשוניות ליישוב הזה (אפשר לבטל ב'ניקוי סינון')")


with tab_map:
    if tab_is_open(tab_map):
        polygons, localities, _ = get_geo()
        mapping = city_mapping(tuple(sorted(alerts["city"].unique())))
        dfg, unmatched = md.attach_geo(df, mapping)

        present = [t for t in TYPE_ORDER if t in set(df["alert_type"])]
        c_layers, c_anim, c_res = st.columns([3, 1.4, 2])
        with c_layers:
            layers = st.pills("שכבות", present, selection_mode="multi", default=present, key="map_layers",
                              format_func=dd.type_label, help="אפשר להדליק ולכבות כל סוג התרעה")
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

# --- Hours of day ---------------------------------------------------------------------
with tab_hours:
    hod = dd.hour_of_day(df, mode)
    fig = stacked_bars(hod, "שעה ביום", hover_x="%{x}:00")
    fig.update_xaxes(tickmode="array", tickvals=list(range(24)), ticktext=[f"{h:02d}" for h in range(24)])
    fig.update_layout(title_text="התפלגות לפי שעה ביום")
    show(fig)

    left, right = st.columns(2)
    with left:
        m = dd.weekday_hour_matrix(df, mode)
        fig = go.Figure(go.Heatmap(
            z=m.values, x=[f"{h:02d}" for h in m.columns], y=m.index, colorscale=seq_scale(), xgap=2, ygap=2,
            hovertemplate="יום %{y}, %{x}:00<br>" + unit + ": %{z:,}<extra></extra>",
            colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=T["muted"]))))
        style(fig, height=340, legend=False)
        fig.update_yaxes(autorange="reversed", showgrid=False, type="category", ticksuffix="  ")
        fig.update_xaxes(showgrid=False, title_text="שעה", type="category")
        fig.update_layout(title_text="יום בשבוע × שעה")
        show(fig)
    with right:
        minute_bin = st.segmented_control("חלון דקות", [5, 10, 15, 20, 30], default=10, key="mbin") or 10
        m = dd.hour_minute_matrix(df, minute_bin, mode)
        fig = go.Figure(go.Heatmap(
            z=m.values, x=[f":{c:02d}" for c in m.columns], y=[f"{h:02d}" for h in m.index],
            colorscale=seq_scale(), xgap=1, ygap=1,
            hovertemplate="%{y}%{x}<br>" + unit + ": %{z:,}<extra></extra>",
            colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=T["muted"]))))
        style(fig, height=520, legend=False)
        fig.update_yaxes(autorange="reversed", showgrid=False, title_text="שעה", type="category")
        fig.update_xaxes(showgrid=False, title_text="דקה", type="category")
        fig.update_layout(title_text=f"שעה × דקה (חלונות של {minute_bin} דקות)")
        show(fig)

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
    fig.update_layout(title_text="כל יום בטווח (שורות) לפי שעה ביום (עמודות)", margin=dict(t=64))
    show(fig)
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
        st.session_state["zones"], st.session_state["cities"] = [name], []
    else:
        st.session_state["cities"] = [name]


with tab_places:
    n_top = st.segmented_control("כמה להציג", [10, 20, 30, 50], default=20, key="ntop") or 20
    st.caption("לחיצה על שורה מסננת את כל הדשבורד לאותו אזור או יישוב.")
    left, right = st.columns(2)
    for col, level, title in ((left, "zone", "אזורים"), (right, "city", "יישובים")):
        with col:
            top = dd.top_counts(df, level, n_top, mode)
            st.session_state[f"_top_{level}_names"] = list(top.index)
            table = pd.DataFrame({"rank": range(1, len(top) + 1), "name": top.index, "count": top.values})
            count_label = unit if level == "zone" or mode == dd.MODE_BARRAGES else "התרעות ביישוב"
            st.markdown(f"**{title} עם הכי הרבה התרעות**")
            st.dataframe(
                table, hide_index=True, key=f"top_{level}", on_select=lambda lv=level: select_place(lv),
                selection_mode="single-row", height=35 * len(table) + 38,
                column_order=["count", "name", "rank"],  # LTR grid: the rank ends up on the right
                column_config={
                    "rank": st.column_config.NumberColumn("#", width="small"),
                    "name": st.column_config.TextColumn("אזור" if level == "zone" else "יישוב"),
                    "count": st.column_config.ProgressColumn(
                        count_label, format="localized", min_value=0, max_value=int(top.max()) if len(top) else 1),
                })

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
        fig.update_layout(barcornerradius=4, title_text="התרעות לפי זמן ההתגוננות של היישוב")
        style(fig, legend=False)
        fig.update_xaxes(type="category", title_text="זמן התגוננות")
        fig.update_yaxes(title_text="התרעות ביישובים")
        show(fig)

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

st.markdown(ds.footer_html(data_until), unsafe_allow_html=True)
