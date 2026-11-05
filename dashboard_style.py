"""Visual layer of the dashboard: design tokens, global CSS and the page header.

Kept out of dashboard.py so the UI file stays about data and charts.
Palette decisions are documented in handoff.md (stage 2.5). The categorical alert-type colors
and the sequential ramp were checked with the dataviz skill's validate_palette.js against
the light (#FFFFFF) and dark (#111318) surfaces.
"""

from html import escape

from alerts_parser import EARLY_WARNING, EARTHQUAKE, INFILTRATION, ROCKET, UAV

FONT = '"Heebo", system-ui, -apple-system, "Segoe UI", Arial, sans-serif'
# Headings and big numbers: a more technical, institutional voice; body text stays Heebo.
DISPLAY = '"IBM Plex Sans Hebrew", "Heebo", system-ui, sans-serif'

# Light and dark are each selected, not flipped. Text tokens keep >= 4.5:1 on their surface.
THEMES = {
    "light": {
        "page": "#FFFFFF", "card": "#FFFFFF", "surface": "#F6F6F7", "border": "#E5E7EB",
        "ink": "#1F2328", "ink2": "#424A53", "muted": "#5E6670",
        "grid": "#ECEDEF", "axis": "#C9CDD3",
        "brand": "#C8102E", "brand_strong": "#A50D26", "brand_tint": "#FDECEE",
        "hero": "#C8102E", "hero_ink": "#FFFFFF",
        "types": {ROCKET: "#C8102E", UAV: "#7C3AED", INFILTRATION: "#3A6EA5", EARLY_WARNING: "#D97706",
                  EARTHQUAKE: "#14876B"},
        "other": "#6B7280",
        # Sequential: one red hue, light -> dark (monotone lightness, validated as ordinal).
        "seq": ["#FFF1F1", "#FDE4E4", "#FBC4C4", "#F69A9A", "#EE6B6E", "#DC3D45", "#BB1F2E", "#8E1422", "#5F0D17"],
    },
    "dark": {
        "page": "#111318", "card": "#161920", "surface": "#181B21", "border": "#2A2E36",
        "ink": "#F0F1F3", "ink2": "#C9CDD3", "muted": "#9AA1AB",
        "grid": "#23262D", "axis": "#3A3F48",
        "brand": "#E5484D", "brand_strong": "#F87171", "brand_tint": "#2A1215",
        "hero": "#A8152A", "hero_ink": "#FFFFFF",
        "types": {ROCKET: "#E5484D", UAV: "#A855F7", INFILTRATION: "#3D88B8", EARLY_WARNING: "#BC8212",
                  EARTHQUAKE: "#1E9C7C"},
        "other": "#8B919C",
        "seq": ["#1C1517", "#3A1A1E", "#5C1F27", "#82232F", "#A92D38", "#CC4048", "#E2676C", "#F09596", "#F9C6C6"],
    },
}

# Simplified outline of Israel (projected lon/lat, viewBox 0 0 180 460). Decorative only.
ISRAEL_PATH = (
    "M95 31 L107 30 L125 33 L142 8 L153 12 L167 6 L175 27 L171 51 L170 71 L151 79 L142 112 L140 148 "
    "L138 169 L137 185 L130 218 L125 254 L115 289 L100 336 L90 384 L82 431 L80 454 L75 455 L58 407 "
    "L40 360 L25 301 L12 251 L7 240 L22 224 L34 208 L40 198 L48 183 L55 165 L61 150 L65 136 L70 120 "
    "L73 106 L74 100 L78 77 L81 63 L87 60 L92 51 L94 41Z"
)

# Siren mark: a source point with sound waves on both sides.
SIREN_ICON = """
<svg viewBox="0 0 48 48" width="44" height="44" aria-hidden="true" focusable="false">
  <circle cx="24" cy="24" r="23" fill="rgba(255,255,255,0.14)"/>
  <path d="M17 31v-7a7 7 0 0 1 14 0v7z" fill="#fff"/>
  <rect x="14" y="31" width="20" height="3.5" rx="1.75" fill="#fff"/>
  <g fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round">
    <path d="M11.5 19.5a14 14 0 0 0 0 9"/><path d="M36.5 19.5a14 14 0 0 1 0 9"/>
    <path d="M7.5 16a20 20 0 0 0 0 16" opacity=".6"/><path d="M40.5 16a20 20 0 0 1 0 16" opacity=".6"/>
  </g>
</svg>
"""


MOTIF_ALPHA = {"light": 0.04, "dark": 0.035}


def margin_motifs(t):
    """CSS background-image value: radar rings (left margin) and dashed trajectory arcs (right margin).

    Stroke = the theme's ink at 3.5-4% opacity: visible as texture, far below any text contrast.
    """
    from urllib.parse import quote

    alpha = MOTIF_ALPHA["dark" if t is THEMES["dark"] else "light"]
    ink = t["ink"]
    rings = "".join(f'<circle cx="60" cy="300" r="{r}"/>' for r in range(70, 460, 70))
    radar = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 760"><g fill="none" stroke="{ink}" '
             f'stroke-opacity="{alpha}" stroke-width="1.5">{rings}'
             f'<path d="M60 300 L420 120 M60 -100 V700 M-340 300 H460" stroke-dasharray="3 7"/></g></svg>')
    arcs = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 760"><g fill="none" stroke="{ink}" '
            f'stroke-opacity="{alpha * 1.25:.3f}" stroke-width="2" stroke-linecap="round" stroke-dasharray="2 10">'
            f'<path d="M440 720 Q 160 300 -20 380"/><path d="M440 560 Q 230 140 40 250"/>'
            f'<path d="M440 420 Q 300 40 120 120"/></g></svg>')
    return ", ".join(f'url("data:image/svg+xml,{quote(svg)}")' for svg in (radar, arcs))


# A shape per alert type, so the type never depends on color alone (color-blind readers, print).
TYPE_SHAPES = {ROCKET: "●", UAV: "▲", INFILTRATION: "■", EARLY_WARNING: "◆", EARTHQUAKE: "▼"}
OTHER_SHAPE = "✕"


def type_shape(alert_type):
    return TYPE_SHAPES.get(alert_type, OTHER_SHAPE)


def type_color(theme, alert_type):
    return theme["types"].get(alert_type, theme["other"])


def global_css(t):
    """Tokens as CSS variables plus the component styles. RTL applies to content only."""
    return f"""
<style>
  :root {{
    --ra-page: {t['page']}; --ra-card: {t['card']}; --ra-surface: {t['surface']}; --ra-border: {t['border']};
    --ra-ink: {t['ink']}; --ra-ink2: {t['ink2']}; --ra-muted: {t['muted']};
    --ra-brand: {t['brand']}; --ra-brand-strong: {t['brand_strong']}; --ra-brand-tint: {t['brand_tint']};
    --ra-hero: {t['hero']}; --ra-hero-ink: {t['hero_ink']}; --ra-axis: {t['axis']};
    --ra-radius: 12px;
    --ra-display: {DISPLAY};
  }}

  /* RTL only on content; the app shell (sidebar drawer, header) stays LTR so it collapses correctly */
  [data-testid="stMain"], [data-testid="stSidebarUserContent"] {{ direction: rtl; text-align: right; }}
  [data-testid="stPlotlyChart"], [data-testid="stPlotlyChart"] *,
  [data-testid="stDataFrame"] {{ direction: ltr !important; text-align: initial; }}
  /* The date field breaks when mirrored: keep it LTR */
  [data-testid="stDateInput"] > div, [data-testid="stDateInput"] > div * {{ direction: ltr; }}
  [data-testid="stButtonGroup"] {{ direction: ltr; justify-content: flex-end; }}
  [data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}
  .block-container {{ padding-top: 1.25rem; max-width: 1240px; }}

  /* ---- Charts: no box. A short title and subtitle above, a source line below ------------ */
  .ra-chart-head {{ margin: 28px 0 2px; }}
  .ra-chart-head h3 {{
    font-family: var(--ra-display); font-size: 1.1rem; font-weight: 600; line-height: 1.35; color: var(--ra-ink);
    margin: 0; padding: 0;
  }}
  .ra-chart-head p {{ margin: 2px 0 0; font-size: 0.82rem; line-height: 1.45; color: var(--ra-muted); }}
  .ra-chart-head [data-testid="stHeaderActionElements"] {{ display: none; }}
  .ra-icon {{
    font-family: "Material Symbols Rounded"; font-weight: 400; font-style: normal; font-size: 1.2em; line-height: 1;
    display: inline-block; vertical-align: -0.2em; margin-inline-end: 6px; color: var(--ra-muted);
    font-feature-settings: "liga"; -webkit-font-smoothing: antialiased; user-select: none;
  }}
  /* Tab icons: secondary gray, also on the active tab (red stays for the active label and underline) */
  [data-testid="stTabs"] [role="tab"] span[role="img"] {{ color: var(--ra-muted); margin-inline-end: 2px; }}
  .ra-tab-source {{
    margin: 32px 0 0; padding-top: 10px; border-top: 1px solid var(--ra-border);
    font-size: 0.75rem; line-height: 1.4; color: var(--ra-muted);
  }}
  /* ---- Sidebar: data coverage strip and the type legend -------------------------------- */
  .ra-coverage {{ margin: 2px 0 14px; }}
  .ra-coverage__title {{ font-size: 0.875rem; color: var(--ra-ink); margin-bottom: 6px; }}
  .ra-coverage svg {{ display: block; width: 100%; height: 44px; }}
  /* Time runs left to right, like every chart: the first date sits under the first bar */
  .ra-coverage__axis {{
    direction: ltr; display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--ra-muted); margin-top: 3px;
    font-variant-numeric: tabular-nums;
  }}
  .ra-coverage__note {{ font-size: 0.75rem; color: var(--ra-muted); margin-top: 4px; line-height: 1.4; }}
  .st-key-type_legend [data-testid="stButton"] button {{
    width: 100%; justify-content: flex-start; min-height: 32px; padding: 2px 6px; gap: 8px;
  }}
  .st-key-type_legend [data-testid="stButton"] button p {{ font-size: 0.875rem; font-variant-numeric: tabular-nums; }}
  .st-key-type_legend [data-testid="stButton"] button::before {{ font-size: 0.8rem; line-height: 1; flex: none; }}
  /* Selection bar: the main controls, right under the header */
  .st-key-filterbar {{ padding: 4px 0 2px; }}
  .st-key-reset_top button {{ color: var(--ra-brand-strong); }}
  /* Facts list (records): label / value / detail in a hairline grid, no boxes */
  .ra-facts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0 28px; margin: 4px 0 8px; }}
  .ra-fact {{ border-top: 1px solid var(--ra-border); padding: 12px 0 10px; min-width: 0; }}
  .ra-fact__label {{ font-size: 0.8rem; color: var(--ra-muted); line-height: 1.4; }}
  .ra-fact__value {{
    font-family: var(--ra-display); font-size: 1.3rem; font-weight: 600; color: var(--ra-ink); line-height: 1.3;
    margin: 4px 0 2px; font-variant-numeric: tabular-nums; overflow-wrap: anywhere;
  }}
  .ra-fact__sub {{ font-size: 0.8rem; color: var(--ra-ink2); line-height: 1.45; }}
  .ra-rule {{ border: 0; border-top: 1px solid var(--ra-border); margin: 28px 0 4px; }}
  .ra-group-title {{
    font-family: var(--ra-display); font-size: 1.35rem; font-weight: 600; color: var(--ra-ink); margin: 8px 0 0;
  }}

  /* ---- Header band ---------------------------------------------------------------- */
  .ra-hero {{
    position: relative; overflow: hidden; isolation: isolate;
    background: var(--ra-hero); color: var(--ra-hero-ink);
    border-radius: 16px; padding: 28px 32px 24px; margin: 0 0 20px;
  }}
  .ra-hero__bg {{ position: absolute; inset: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none; }}
  .ra-hero__map {{
    position: absolute; left: 3%; top: 4%; height: 92%; width: auto; z-index: -1; pointer-events: none;
  }}
  /* Siren waves are centered on the siren mark (right side, RTL) */
  .ra-hero__waves {{
    position: absolute; width: 500px; height: 500px; right: -196px; top: -187px; z-index: -1; pointer-events: none;
  }}
  .ra-hero__brand {{ display: flex; align-items: center; gap: 14px; }}
  .ra-hero__brand svg {{ flex: none; }}
  .ra-hero h1 {{
    font-family: {DISPLAY}; font-weight: 700; font-size: clamp(1.5rem, 1.1rem + 1.6vw, 2rem); line-height: 1.2;
    color: var(--ra-hero-ink); margin: 0; padding: 0; letter-spacing: 0;
  }}
  .ra-hero__sub {{ margin: 4px 0 0; font-size: 0.95rem; line-height: 1.5; color: rgba(255,255,255,0.88); }}
  .ra-hero__meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }}
  .ra-chip {{
    display: inline-flex; align-items: center; gap: 6px; min-height: 28px; padding: 2px 12px;
    border-radius: 999px; font-size: 0.85rem; line-height: 1.4;
    background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.24); color: #fff;
  }}
  .ra-chip bdi {{ font-variant-numeric: tabular-nums; }}
  .ra-dot {{ width: 8px; height: 8px; border-radius: 50%; background: #fff; flex: none; }}
  /* Streamlit adds a hover anchor to headings; not useful in the banner */
  .ra-hero [data-testid="stHeaderActionElements"] {{ display: none; }}

  /* ---- Motion: only transform/opacity, and only when the user has not asked for less motion.
     Siren waves expand and fade in a slow loop; trajectory arcs glide in once when the header renders. */
  .ra-waves-anim {{ display: none; }}
  @media (prefers-reduced-motion: no-preference) {{
    .ra-waves-anim {{ display: inline; }}
    .ra-waves-static circle:not(:first-child) {{ display: none; }}
    .ra-wave {{
      transform-box: fill-box; transform-origin: center; opacity: 0;
      animation: ra-wave 6s cubic-bezier(0.2, 0.6, 0.35, 1) infinite;
    }}
    .ra-wave:nth-child(2) {{ animation-delay: 2s; }}
    .ra-wave:nth-child(3) {{ animation-delay: 4s; }}
    .ra-traj {{ animation: ra-traj 1.8s cubic-bezier(0.2, 0.6, 0.35, 1) both; }}
    .ra-traj:nth-child(2) {{ animation-delay: 0.35s; }}
    .ra-traj--intercept {{ animation-name: ra-traj-in; animation-delay: 0.9s; }}
  }}
  @keyframes ra-wave {{
    0% {{ transform: scale(0.25); opacity: 0; }}
    15% {{ opacity: 0.16; }}
    100% {{ transform: scale(1); opacity: 0; }}
  }}
  @keyframes ra-traj {{ from {{ opacity: 0; transform: translate(-36px, 22px); }} }}
  @keyframes ra-traj-in {{ from {{ opacity: 0; transform: translate(36px, 22px); }} }}

  /* ---- Locator: where the selected places are, next to the place picker -------------------- */
  .ra-locator {{ margin: 0; display: flex; flex-direction: column; align-items: center; gap: 2px; }}
  .ra-locator svg {{ height: 92px; width: auto; display: block; }}
  .ra-locator figcaption {{
    font-size: 0.7rem; line-height: 1.3; color: var(--ra-muted); text-align: center; max-width: 9em;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }}

  /* ---- Wide screens: faint radar rings and trajectory arcs in the empty margins.
     The content column gets a solid page background, so the motifs never sit behind charts or text. */
  @media (min-width: 1500px) {{
    [data-testid="stMain"] {{
      background-image: {margin_motifs(t)};
      background-repeat: no-repeat, no-repeat;
      background-position: left -40px top 140px, right -30px bottom 60px;
      background-size: 420px auto, 420px auto;
    }}
    .block-container {{ background: var(--ra-page); }}
  }}
  /* An open sidebar (~300px) eats the margin: then the motifs need a wider screen to have room */
  @media (min-width: 1500px) and (max-width: 1859px) {{
    .stApp:has([data-testid="stSidebar"][data-collapsed="false"]) [data-testid="stMain"] {{ background-image: none; }}
  }}

  /* ---- Recent barrages feed ------------------------------------------------------------ */
  .ra-feed {{ list-style: none; margin: 0; padding: 0; border: 1px solid var(--ra-border); border-radius: var(--ra-radius);
             background: var(--ra-card); overflow: hidden; }}
  .ra-feed li {{
    display: grid; grid-template-columns: 9.5rem minmax(0, 1fr) auto; gap: 4px 16px; align-items: baseline;
    padding: 12px 16px; border-top: 1px solid var(--ra-border); margin: 0;
  }}
  .ra-feed li:first-child {{ border-top: 0; }}
  .ra-feed__time {{ font-variant-numeric: tabular-nums; color: var(--ra-ink); font-weight: 500; font-size: 0.95rem; }}
  .ra-feed__time small {{ display: block; color: var(--ra-muted); font-weight: 400; font-size: 0.8rem; }}
  .ra-feed__where {{ color: var(--ra-ink); font-size: 0.95rem; line-height: 1.5; min-width: 0; }}
  .ra-feed__where small {{ display: block; color: var(--ra-muted); font-size: 0.8rem; }}
  .ra-tag {{
    display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; font-size: 0.8rem; color: var(--ra-ink2);
    border: 1px solid var(--ra-border); border-radius: 999px; padding: 1px 10px;
  }}
  .ra-tag i {{ font-style: normal; font-size: 0.75rem; line-height: 1; flex: none; }}

  /* ---- KPI row: typographic, no boxes. Hairlines between cells ------------------------- */
  .ra-kpis {{
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 4px 0 8px;
    border-top: 1px solid var(--ra-border); border-bottom: 1px solid var(--ra-border);
  }}
  .ra-kpi {{ padding: 16px 20px 14px; min-width: 0; border-inline-start: 1px solid var(--ra-border); }}
  .ra-kpi:first-child {{ border-inline-start: 0; padding-inline-start: 0; }}
  .ra-kpi__label {{ font-size: 0.82rem; line-height: 1.4; color: var(--ra-muted); }}
  .ra-kpi__value {{
    font-family: var(--ra-display); font-size: 2.25rem; font-weight: 600; line-height: 1.15; color: var(--ra-ink);
    margin: 6px 0 4px; font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; overflow-wrap: anywhere;
  }}
  .ra-kpi__value--text {{ font-size: 1.25rem; padding-top: 8px; padding-bottom: 6px; white-space: nowrap; }}
  .ra-kpi__sub {{ font-size: 0.8rem; line-height: 1.45; color: var(--ra-ink2); }}
  .ra-kpi__viz {{ margin-top: 8px; height: 28px; }}
  .ra-kpi__viz svg {{ display: block; width: 100%; max-width: 160px; height: 28px; }}
  .ra-ratio {{ height: 6px; max-width: 160px; border-radius: 3px; background: var(--ra-surface); overflow: hidden; margin-top: 18px; }}
  .ra-ratio i {{ display: block; height: 100%; background: var(--ra-brand); }}

  /* ---- Notice (neutral replacement for st.info) -------------------------------------- */
  .ra-notice {{
    display: flex; gap: 12px; align-items: flex-start; margin: 4px 0 12px;
    background: var(--ra-surface); border: 1px solid var(--ra-border); border-radius: var(--ra-radius);
    padding: 14px 16px; color: var(--ra-ink2); font-size: 0.95rem; line-height: 1.55;
  }}
  .ra-notice svg {{ flex: none; margin-top: 2px; color: var(--ra-muted); }}
  .ra-notice strong {{ display: block; color: var(--ra-ink); font-weight: 700; margin-bottom: 2px; }}

  /* ---- Footer ------------------------------------------------------------------------ */
  .ra-footer {{
    margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--ra-border);
    color: var(--ra-muted); font-size: 0.85rem; line-height: 1.6;
  }}
  .ra-footer p {{ margin: 0 0 8px; font-size: 0.85rem; color: var(--ra-muted); }}
  .ra-footer strong {{ color: var(--ra-ink2); }}
  .ra-footer a {{ color: var(--ra-brand-strong); }}
  .ra-side-meta {{ color: var(--ra-muted); font-size: 0.85rem; line-height: 1.6; margin: 0; }}

  /* Readable secondary text (Streamlit's default caption is ~4.3:1) */
  [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: var(--ra-muted); }}
  /* Segmented controls wrap instead of running off narrow screens */
  [data-testid="stButtonGroup"], [data-testid="stButtonGroup"] > div {{ flex-wrap: wrap; }}
  /* Button groups stay LTR, but each Hebrew label reads in its own direction ("30 ימים", not "ימים 30") */
  [data-testid="stButtonGroup"] button p {{ unicode-bidi: plaintext; }}

  @media (max-width: 640px) {{
    .ra-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .ra-kpi:nth-child(3) {{ border-inline-start: 0; padding-inline-start: 0; }}
    .ra-kpi:nth-child(n+3) {{ border-top: 1px solid var(--ra-border); }}
    .ra-feed li {{ grid-template-columns: minmax(0, 1fr) auto; padding: 10px 12px; }}
    /* six tabs fit on a 375px screen: text only */
    [data-testid="stTabs"] [role="tablist"] {{ gap: 8px; }}
    [data-testid="stTabs"] [role="tab"] span[role="img"] {{ display: none !important; }}
    [data-testid="stTabs"] [role="tab"] p {{ font-size: 0.9rem; }}
    .ra-feed__where {{ grid-column: 1 / -1; grid-row: 2; }}
    .ra-kpi {{ padding: 12px 12px 10px; }}
    .ra-kpi__value {{ font-size: 1.6rem; }}
    .ra-kpi__value--text {{ font-size: 1.05rem; }}
    /* Leave room for the fixed app header (sidebar toggle) on narrow screens */
    .block-container {{ padding-top: 3.75rem; }}
    .ra-hero {{ padding: 20px 18px 18px; border-radius: 12px; }}
    .ra-hero__brand svg {{ width: 36px; height: 36px; }}
    .ra-hero__sub {{ font-size: 0.85rem; }}
    .ra-hero__map {{ left: 2%; opacity: 0.45; }}
    .ra-hero__waves {{ right: -214px; top: -200px; }}
    .ra-hero__meta {{ margin-top: 14px; }}
    /* The locator needs width the phone does not have; the place names are in the picker anyway */
    [data-testid="stColumn"]:has(.ra-locator) {{ display: none; }}
  }}
</style>
"""


def hero_html(title, subtitle, chips, dots=None):
    """The page header: red band, siren mark, title and a row of context chips.

    dots: optional list of (x, y) array pairs from map_data.dot_levels (dimmest first). Each locality with
    alerts in the current selection becomes a white dot on the map outline, brighter with more alerts.

    chips: list of (text, kind) where kind is "plain", "ltr" (numbers/dates, isolated LTR) or "status".
    Background motifs (map outline, trajectory arcs, siren waves) are decorative and aria-hidden.
    """
    chip_html = []
    for text, kind in chips:
        body = f'<bdi dir="ltr">{escape(text)}</bdi>' if kind == "ltr" else escape(text)
        if kind == "status":
            body = f'<span class="ra-dot" aria-hidden="true"></span>{body}'
        chip_html.append(f'<span class="ra-chip">{body}</span>')

    # Trajectory arcs: thin dashed curves; one pair meets mid-air (interception), no explosions.
    background = """
<svg class="ra-hero__bg" viewBox="0 0 1200 240" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
  <g fill="none" stroke="#fff" stroke-linecap="round" stroke-dasharray="2 9" stroke-width="2">
    <path class="ra-traj" d="M-40 250 Q 260 -30 600 170" opacity=".16"/>
    <path class="ra-traj" d="M60 270 Q 420 10 820 230" opacity=".11"/>
    <path class="ra-traj ra-traj--intercept" d="M760 260 Q 650 120 520 128" opacity=".16"/>
  </g>
</svg>
<svg class="ra-hero__waves" viewBox="0 0 500 500" aria-hidden="true" focusable="false">
  <g fill="none" stroke="#fff" stroke-width="1.5">
    <g class="ra-waves-static">
      <circle cx="250" cy="250" r="56" opacity=".16"/>
      <circle cx="250" cy="250" r="100" opacity=".10"/>
      <circle cx="250" cy="250" r="150" opacity=".06"/>
      <circle cx="250" cy="250" r="205" opacity=".035"/>
    </g>
    <g class="ra-waves-anim">
      <circle class="ra-wave" cx="250" cy="250" r="205"/>
      <circle class="ra-wave" cx="250" cy="250" r="205"/>
      <circle class="ra-wave" cx="250" cy="250" r="205"/>
    </g>
  </g>
</svg>
"""
    dot_layers = ""
    levels = len(dots or [])
    for k, (x, y) in enumerate(dots or []):
        if len(x):
            width = 2.0 if k < levels - 1 else 2.6
            alpha = HERO_DOT_ALPHA[0] + (HERO_DOT_ALPHA[1] - HERO_DOT_ALPHA[0]) * k / max(levels - 1, 1)
            dot_layers += (f'<path d="{dots_path(x, y)}" stroke="#fff" stroke-opacity="{alpha:.2f}" '
                           f'stroke-width="{width}" stroke-linecap="round" vector-effect="non-scaling-stroke"/>')
    outline_alpha = 0.14 if dot_layers else 0.22
    israel = (f'<svg class="ra-hero__map" viewBox="0 0 180 460" aria-hidden="true" focusable="false">'
              f'<path d="{ISRAEL_PATH}" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,{outline_alpha})" '
              f'stroke-width="1.6" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>{dot_layers}</svg>')

    html = f"""
<header class="ra-hero">
  {background}
  {israel}
  <div class="ra-hero__brand">
    {SIREN_ICON}
    <div>
      <h1>{escape(title)}</h1>
      <p class="ra-hero__sub">{escape(subtitle)}</p>
    </div>
  </div>
  <div class="ra-hero__meta">{''.join(chip_html)}</div>
</header>
"""
    return _flatten(html)


HERO_DOT_ALPHA = (0.3, 0.92)  # dimmest and brightest level; levels in between are interpolated


def dots_path(x, y):
    """One SVG path of zero-length segments: with round caps each segment draws a dot (compact markup)."""
    return "".join(f"M{a:g} {b:g}h0" for a, b in zip(x, y))


def locator_html(all_xy, selected_xy, label, faint=False):
    """Small silhouette of Israel made of every locality (gray) with the selected places in brand red.

    faint: the highlighted dots are a light tint (used for "localities with alerts" when nothing is picked).
    """
    sel = ""
    if len(selected_xy[0]):
        look = 'stroke-opacity="0.45" stroke-width="2"' if faint else 'stroke-width="4.5"'
        sel = (f'<path d="{dots_path(*selected_xy)}" stroke="var(--ra-brand)" {look} '
               f'stroke-linecap="round" vector-effect="non-scaling-stroke"/>')
    return _flatten(f"""
<figure class="ra-locator" role="img" aria-label="{escape(label)}">
<svg viewBox="0 0 180 460" focusable="false" aria-hidden="true">
<path d="{ISRAEL_PATH}" fill="var(--ra-surface)" stroke="var(--ra-axis)" stroke-width="1" stroke-linejoin="round"
 vector-effect="non-scaling-stroke"/>
<path d="{dots_path(*all_xy)}" stroke="var(--ra-axis)" stroke-width="1.4" stroke-linecap="round"
 vector-effect="non-scaling-stroke"/>
{sel}
</svg>
<figcaption>{escape(label)}</figcaption>
</figure>
""")


def _flatten(html):
    """st.markdown treats indented lines as a code block: strip indentation and blank lines."""
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


INFO_ICON = (
    '<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">'
    '<circle cx="10" cy="10" r="8.25" fill="none" stroke="currentColor" stroke-width="1.5"/>'
    '<path d="M10 9v5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
    '<circle cx="10" cy="6.3" r="1" fill="currentColor"/></svg>'
)


def kpi_row_html(items):
    """Typographic KPI row. items: dicts with label, value, and optional sub, viz (inline SVG/HTML),
    ltr (isolate the value LTR), text (a word rather than a number)."""
    out = []
    for c in items:
        vcls = "ra-kpi__value" + (" ra-kpi__value--text" if c.get("text") else "")
        value = escape(str(c["value"]))
        if c.get("ltr"):
            value = f'<bdi dir="ltr">{value}</bdi>'
        sub = f'<div class="ra-kpi__sub">{escape(c["sub"])}</div>' if c.get("sub") else ""
        viz = f'<div class="ra-kpi__viz" aria-hidden="true">{c["viz"]}</div>' if c.get("viz") else ""
        # divs, not <p>: Streamlit's markdown styles for p would override the sizes
        out.append(f'<div class="ra-kpi"><div class="ra-kpi__label">{escape(c["label"])}</div>'
                   f'<div class="{vcls}">{value}</div>{sub}{viz}</div>')
    return f'<section class="ra-kpis" aria-label="מדדים עיקריים">{"".join(out)}</section>'


# Detail cards (map locality panel) keep the same typographic row.
kpi_cards_html = kpi_row_html


def sparkline_svg(values, color, width=160, height=28):
    """Tiny line + soft area, no axes. Time runs left to right like every other time axis."""
    vals = [float(v) for v in values]
    if len(vals) < 2 or max(vals) <= 0:
        return ""
    top = max(vals)
    step = width / (len(vals) - 1)
    pts = [(i * step, height - 2 - (v / top) * (height - 4)) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{height} {line} {width},{height}"
    return (f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" focusable="false">'
            f'<polygon points="{area}" fill="{color}" opacity="0.12"/>'
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.6" '
            f'stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>')


def hour_bars_svg(counts, peak, color, rest, width=160, height=28):
    """24 mini bars (00..23, left to right); the peak hour in the accent color, the rest muted."""
    vals = [float(v) for v in counts]
    top = max(vals) if vals and max(vals) > 0 else 1
    bw = width / 24
    bars = []
    for h, v in enumerate(vals):
        bh = max(1.5, (v / top) * height)
        bars.append(f'<rect x="{h * bw + 0.6:.1f}" y="{height - bh:.1f}" width="{bw - 1.2:.1f}" height="{bh:.1f}" '
                    f'rx="1" fill="{color if h == peak else rest}"/>')
    return f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" focusable="false">{"".join(bars)}</svg>'


def ratio_bar_html(ratio):
    return f'<div class="ra-ratio"><i style="width:{max(0.0, min(1.0, ratio)) * 100:.1f}%"></i></div>'


def icon_html(name):
    """A Material Symbols glyph (the font ships with Streamlit), decorative."""
    return f'<span class="ra-icon" aria-hidden="true">{escape(name)}</span>'


def chart_head_html(title, subtitle="", icon=None):
    sub = f"<p>{escape(subtitle)}</p>" if subtitle else ""
    mark = icon_html(icon) if icon else ""
    return f'<div class="ra-chart-head"><h3>{mark}{escape(title)}</h3>{sub}</div>'


def tab_source_html(text):
    """The source line, once at the end of a tab."""
    return f'<div class="ra-tab-source">{escape(text)}</div>'


def coverage_html(values, in_range, on_color, off_color, first, last, note=""):
    """Daily bars over the whole data period; days inside the selected range in ``on_color``.

    values: daily counts; in_range: booleans of the same length; first/last: dates for the axis.
    """
    n = len(values)
    vmax = max(max(values, default=0), 1)
    w = 4.0
    bars = {True: [], False: []}
    for i, (v, on) in enumerate(zip(values, in_range)):
        if v > 0:
            h = max(1.5, 40 * (v / vmax) ** 0.5)  # sqrt: one huge day must not flatten the rest
            bars[bool(on)].append(f"M{i * w + 0.5:g} 44v-{h:.1f}h{w - 1:g}v{h:.1f}z")
    svg = (f'<svg viewBox="0 0 {max(n, 1) * w:g} 44" preserveAspectRatio="none" aria-hidden="true" focusable="false">'
           f'<path d="M0 43.5H{max(n, 1) * w:g}" stroke="{off_color}" stroke-width="1" vector-effect="non-scaling-stroke"/>'
           f'<path d="{"".join(bars[False])}" fill="{off_color}"/><path d="{"".join(bars[True])}" fill="{on_color}"/></svg>')
    note_html = f'<div class="ra-coverage__note">{escape(note)}</div>' if note else ""
    return _flatten(f"""
<div class="ra-coverage" role="img" aria-label="כיסוי הנתונים: התרעות בכל יום, הטווח שנבחר מודגש">
<div class="ra-coverage__title">כיסוי הנתונים</div>
{svg}
<div class="ra-coverage__axis"><bdi dir="ltr">{first:%d/%m/%Y}</bdi><bdi dir="ltr">{last:%d/%m/%Y}</bdi></div>
{note_html}
</div>
""")


def legend_css(entries):
    """Per-row shape and color for the sidebar type legend (buttons keyed legend_<i>).

    entries: list of (key, shape, color, active). Inactive rows are dimmed.
    """
    rules = []
    for key, shape, color, active in entries:
        rules.append(f'.st-key-{key} button::before {{ content: "{shape}"; color: {color}; }}')
        if not active:
            rules.append(f".st-key-{key} button {{ opacity: 0.5; }}")
    return "<style>" + " ".join(rules) + "</style>"


def notice_html(title, body):
    """Neutral message block: what happened and what to do next."""
    return (f'<div class="ra-notice" role="status">{INFO_ICON}'
            f'<div><strong>{escape(title)}</strong>{escape(body)}</div></div>')


def footer_html(data_until):
    return _flatten(f"""
<footer class="ra-footer">
  <p><strong>מקור:</strong> ערוץ הטלגרם "צופר - צבע אדום". הנתונים מעודכנים עד
    <bdi dir="ltr">{data_until:%d/%m/%Y %H:%M}</bdi>.</p>
  <p><strong>איך סופרים:</strong> "התרעות ביישובים" סופר כל יישוב שבו הופעלה התרעה. התרעה אחת יכולה להפעיל
    עשרות יישובים, ולכן זה לא מספר הרקטות. "אירועים" סופר כל דקה וסוג התרעה פעם אחת.</p>
  <p><strong>האתר אינו רשמי</strong> ואינו מחליף את התרעות פיקוד העורף. בזמן אמת יש לפעול לפי ההנחיות
    <a href="https://www.oref.org.il" target="_blank" rel="noopener">באתר פיקוד העורף</a> ובאפליקציה הרשמית.</p>
</footer>
""")


def sidebar_meta_html(data_min, data_max, n_rows):
    return (f'<div class="ra-side-meta">נתונים: <bdi dir="ltr">{data_min:%d/%m/%Y} – {data_max:%d/%m/%Y}</bdi>'
            f'<br><bdi dir="ltr">{n_rows:,}</bdi> רשומות</div>')


def feed_html(barrages, color_of, label_of):
    """Compact list of barrages (newest first): time, where, and a type tag with its color dot."""
    if barrages.empty:
        return notice_html("אין מטחים בטווח", "אפשר להרחיב את טווח התאריכים או את הסינון.")
    items = []
    for b in barrages.itertuples(index=False):
        when = f"{b.start:%d/%m/%Y %H:%M}"
        span = "" if b.end == b.start else f"<small>עד <bdi dir=\"ltr\">{b.end:%H:%M}</bdi></small>"
        zones = list(b.zones)
        where = escape(", ".join(zones[:3])) + (f" ועוד {len(zones) - 3}" if len(zones) > 3 else "")
        n = f"{b.localities:,} יישובים" if b.localities > 1 else "יישוב אחד"
        tag = (f'<span class="ra-tag"><i style="color:{color_of(b.alert_type)}" aria-hidden="true">'
               f'{type_shape(b.alert_type)}</i>{escape(label_of(b.alert_type))}</span>')
        items.append(f'<li><div class="ra-feed__time"><bdi dir="ltr">{when}</bdi>{span}</div>'
                     f'<div class="ra-feed__where">{where}<small>{n}</small></div>{tag}</li>')
    return f'<ul class="ra-feed" aria-label="מטחים אחרונים">{"".join(items)}</ul>'


def facts_html(items, label="שיאים"):
    """A hairline grid of plain facts. items: dicts with label, value, optional sub and ltr."""
    out = []
    for c in items:
        value = escape(str(c["value"]))
        if c.get("ltr"):
            value = f'<bdi dir="ltr">{value}</bdi>'
        sub = f'<div class="ra-fact__sub">{escape(c["sub"])}</div>' if c.get("sub") else ""
        out.append(f'<div class="ra-fact"><div class="ra-fact__label">{escape(c["label"])}</div>'
                   f'<div class="ra-fact__value">{value}</div>{sub}</div>')
    return f'<section class="ra-facts" aria-label="{escape(label)}">{"".join(out)}</section>'


def with_alpha(hex_color, alpha):
    """'#RRGGBB' -> 'rgba(r,g,b,a)' for translucent fills."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"
