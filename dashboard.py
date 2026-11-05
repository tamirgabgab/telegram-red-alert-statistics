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
import map_data as md
from alerts_parser import ALERT_TYPE_LABELS
from build_dataset import load_alerts

st.set_page_config(page_title="סטטיסטיקת התרעות", page_icon="🔴", layout="wide")

# --------------------------------------------------------------------------------------
# Theme tokens (light / dark are each selected, not flipped). Categorical slots are assigned
# to alert types in a fixed order so a type keeps its color whatever the filter.
# --------------------------------------------------------------------------------------
THEMES = {
    "light": {
        "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
        "grid": "#e1e0d9", "axis": "#c3c2b7",
        "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"],
        "seq": ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
    },
    "dark": {
        "surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
        "grid": "#2c2c2a", "axis": "#383835",
        "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9"],
        "seq": ["#1f2226", "#104281", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"],
    },
}
TYPE_ORDER = list(ALERT_TYPE_LABELS.keys())  # rocket, uav, infiltration, early_warning, ...
FONT = 'system-ui, -apple-system, "Segoe UI", Arial, sans-serif'
PLOTLY_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}


def current_theme():
    try:
        return THEMES["dark" if st.context.theme.type == "dark" else "light"]
    except Exception:  # older Streamlit / no theme info
        return THEMES["light"]


T = current_theme()


def type_color(alert_type):
    idx = TYPE_ORDER.index(alert_type) if alert_type in TYPE_ORDER else len(T["series"]) - 1
    return T["series"][min(idx, len(T["series"]) - 1)]


def seq_scale():
    steps = T["seq"]
    return [[i / (len(steps) - 1), c] for i, c in enumerate(steps)]


def style(fig, height=380, legend=True):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        paper_bgcolor=T["surface"], plot_bgcolor=T["surface"],
        font=dict(family=FONT, color=T["ink2"], size=13),
        title=dict(x=0.99, xanchor="right", font=dict(color=T["ink"], size=15)),  # RTL: title on the right
        hoverlabel=dict(font_family=FONT, bgcolor=T["surface"], font_color=T["ink"], bordercolor=T["axis"]),
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
# RTL layout. Charts and tables stay LTR (time runs left to right).
# --------------------------------------------------------------------------------------
st.markdown(
    """
    <style>
      /* RTL only on content; the app shell (sidebar drawer, header) stays LTR so it collapses correctly */
      [data-testid="stMain"], [data-testid="stSidebarUserContent"] { direction: rtl; text-align: right; }
      [data-testid="stPlotlyChart"], [data-testid="stPlotlyChart"] *,
      [data-testid="stDataFrame"] { direction: ltr !important; text-align: initial; }
      /* The date field breaks when mirrored: keep it LTR */
      [data-testid="stDateInput"] > div, [data-testid="stDateInput"] > div * { direction: ltr; }
      [data-testid="stButtonGroup"] { direction: ltr; justify-content: flex-end; }
      [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
      .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="טוען נתונים...")
def get_alerts():
    df = load_alerts()
    df["zone"] = df["zone"].fillna("")
    df["city"] = df["city"].fillna("")
    return df


alerts = get_alerts()
if alerts.empty:
    st.title("סטטיסטיקת התרעות פיקוד העורף")
    st.warning("אין עדיין נתונים. הריצו `python collect_alerts.py --since 2026-02-26` כדי לאסוף הודעות מהערוץ.")
    st.stop()

data_min = alerts["timestamp"].min().date()
data_max = alerts["timestamp"].max().date()

# --------------------------------------------------------------------------------------
# Sidebar filters
# --------------------------------------------------------------------------------------
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
        "אופן ספירה", ["יישובים", "אירועים"], horizontal=True,
        help="יישובים: כל יישוב שהופעלה בו התרעה נספר בנפרד.\n\n"
             "אירועים: כל דקה עם התרעה (מכל סוג) נספרת פעם אחת, לא משנה בכמה יישובים.",
    )
    mode = dd.MODE_LOCALITIES if mode_label == "יישובים" else dd.MODE_EVENTS

    st.button("ניקוי סינון", on_click=reset_filters, width="stretch")

    st.divider()
    st.caption(f"נתונים: {data_min:%d/%m/%Y} – {data_max:%d/%m/%Y} · {len(alerts):,} רשומות")
    sources = alerts["source"].value_counts()
    if "telegram" not in sources:
        st.caption("כרגע יש רק נתוני צבע אדום מקובץ האקסל הישן. "
                   "לאיסוף כל סוגי ההתרעות: `python collect_alerts.py --since 2026-02-26`")

df = dd.filter_alerts(alerts, start, end, types, zones, cities)
unit = "התרעות ביישובים" if mode == dd.MODE_LOCALITIES else "אירועי התרעה"

# --------------------------------------------------------------------------------------
# Header + KPIs
# --------------------------------------------------------------------------------------
st.title("סטטיסטיקת התרעות פיקוד העורף")
scope = "כל הארץ"
if cities:
    scope = ", ".join(cities[:3]) + (f" ועוד {len(cities) - 3}" if len(cities) > 3 else "")
elif zones:
    scope = ", ".join(zones[:3]) + (f" ועוד {len(zones) - 3}" if len(zones) > 3 else "")
st.caption(f"{scope} · {start:%d/%m/%Y} – {end:%d/%m/%Y} · מקור: ערוץ הטלגרם \"צופר - צבע אדום\"")

if df.empty:
    st.info("אין התרעות שמתאימות לסינון הזה. אפשר להרחיב את טווח התאריכים או להסיר חלק מהאזורים והיישובים.")
    st.button("ניקוי סינון", on_click=reset_filters, key="reset_empty")
    st.stop()

k = dd.kpis(df, mode)
c1, c2, c3, c4 = st.columns(4)
c1.metric(unit, f"{k['total']:,}")
c2.metric("ימים עם התרעות", f"{k['active_days']:,}", help=f"מתוך {(end - start).days + 1} ימים בטווח")
c3.metric("ממוצע ליום פעיל", f"{k['per_active_day']:,.1f}")
c4.metric("שעת שיא", f"{k['peak_hour']:02d}:00",
          help=f"השעה ביום עם הכי הרבה התרעות: {k['peak_hour']:02d}:00 עד {k['peak_hour']:02d}:59")
if len(set(df["city"])) > 1:
    st.caption(f"היישוב עם הכי הרבה התרעות: **{k['top_city']}** ({k['top_city_count']:,}) · "
               f"{k['localities']:,} יישובים קיבלו התרעה בטווח")

TAB_NAMES = ["ציר זמן", "מפה", "שעות ביום", "לוח ימים × שעות", "אזורים ויישובים", "זמן התגוננות", "נתונים"]
try:
    # Lazy tabs: the heavy map is only built while its tab is open (Streamlit >= 1.5x).
    tabs = st.tabs(TAB_NAMES, key="tab", on_change="rerun")
except TypeError:
    tabs = st.tabs(TAB_NAMES)
tab_time, tab_map, tab_hours, tab_days, tab_places, tab_shelter, tab_data = tabs


def tab_is_open(tab):
    is_open = getattr(tab, "open", None)
    return True if is_open is None else bool(is_open)


def stacked_bars(wide, x_title, height=380, hover_x="%{x}"):
    fig = go.Figure()
    # A thin surface-colored gap between stacked segments, unless the bars are too dense for it.
    gap = 1.5 if len(wide.columns) > 1 and len(wide) <= 200 else 0
    for t in [t for t in TYPE_ORDER if t in wide.columns]:
        fig.add_bar(x=wide.index, y=wide[t], name=dd.type_label(t), marker_color=type_color(t),
                    marker_line_width=gap, marker_line_color=T["surface"],
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

# --- Map ------------------------------------------------------------------------------
# Base map tiles (no API key). Set MAP_STYLE=white-bg to use the map without internet tiles.
MAP_STYLE = {"light": "carto-positron", "dark": "carto-darkmatter"}
MAP_ZERO = {"light": "#dcdbd5", "dark": "#3a3a37"}


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
    if T is THEMES["dark"]:
        return md.ramp(base, md.mix(base, T["surface"], 0.6), md.mix(base, "#ffffff", 0.6))
    return md.ramp(base, md.mix(base, "#ffffff", 0.8), md.mix(base, "#000000", 0.35))


def map_figure(frames_counts, layers, poly_names, point_names, poly_text, point_text, frame_labels, selected):
    """Polygon + point traces sharing one piecewise colorscale; optional animation frames."""
    theme_key = "dark" if T is THEMES["dark"] else "light"
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
            showscale=False, marker_opacity=0.85, marker_line_width=0.4, marker_line_color=T["surface"],
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
                              pad=dict(r=6, t=6), bgcolor=T["surface"], bordercolor=T["axis"],
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
        height=680, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=T["surface"], showlegend=False,
        uirevision="map",  # keep zoom/pan when the app reruns (e.g. after a click)
        hoverlabel=dict(font_family=FONT, bgcolor=T["surface"], font_color=T["ink"], bordercolor=T["axis"]),
        font=dict(family=FONT, color=T["ink2"]))
    return fig


def map_legend(layers):
    def strip(colors):
        return (f'<span style="display:inline-block;width:96px;height:10px;border-radius:2px;vertical-align:middle;'
                f'background:linear-gradient(to left, {", ".join(colors)})"></span>')
    theme_key = "dark" if T is THEMES["dark"] else "light"
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
        st.info("לא היו התרעות ביישוב הזה בטווח ובשכבות שנבחרו.")
        return
    cols = st.columns(len(layers) + 1)
    for col, t in zip(cols, layers):
        col.metric(dd.type_label(t), f"{int((sub['alert_type'] == t).sum()):,}")
    cols[-1].metric("התרעה אחרונה", f"{sub['timestamp'].max():%d/%m %H:%M}")
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
            st.info("בחרו לפחות שכבה אחת כדי לראות את המפה.")
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
with tab_places:
    n_top = st.segmented_control("כמה להציג", [10, 20, 30, 50], default=20, key="ntop") or 20
    left, right = st.columns(2)
    for col, level, title in ((left, "zone", "אזורים"), (right, "city", "יישובים")):
        with col:
            top = dd.top_counts(df, level, n_top, mode)
            fig = go.Figure(go.Bar(
                x=top.values, y=top.index, orientation="h", marker_color=T["series"][0], marker_line_width=0,
                text=[f"{v:,}" for v in top.values], textposition="outside", cliponaxis=False,
                textfont=dict(color=T["ink2"], size=11),
                hovertemplate="%{y}<br>%{x:,}<extra></extra>"))
            fig.update_layout(barcornerradius=4)
            style(fig, height=max(300, 24 * len(top) + 80), legend=False)
            fig.update_yaxes(autorange="reversed", showgrid=False, ticksuffix="  ")
            fig.update_xaxes(title_text=unit if level == "zone" else "התרעות ביישוב",
                             range=[0, (top.max() if len(top) else 1) * 1.15])
            fig.update_layout(title_text=f"{title} עם הכי הרבה התרעות")
            show(fig)

# --- Shelter time ---------------------------------------------------------------------
with tab_shelter:
    sd = dd.shelter_distribution(df)
    if sd.empty:
        st.info("אין עדיין נתוני זמן התגוננות. הם נאספים רק בהודעות שנשמרו ב-`collect_alerts.py`, "
                "כי קובץ האקסל הישן לא שמר אותם. כדי להשלים: `python collect_alerts.py --since 2026-02-26`")
    else:
        def fmt(sec):
            return "מיידי" if sec == 0 else (f"{sec} שניות" if sec < 60 else
                                             ("דקה" if sec == 60 else ("דקה וחצי" if sec == 90 else f"{sec // 60} דקות")))
        fig = go.Figure(go.Bar(x=[fmt(s) for s in sd.index], y=sd.values, marker_color=T["series"][0],
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
    st.caption(f"{len(view):,} רשומות (כל שורה היא יישוב שהופעלה בו התרעה בדקה מסוימת)")
    st.dataframe(view, width="stretch", hide_index=True, height=480,
                 column_config={"זמן": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm")})
    st.download_button("הורדת הנתונים המסוננים (CSV)", view.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"alerts_{start:%Y%m%d}_{end:%Y%m%d}.csv", mime="text/csv")
