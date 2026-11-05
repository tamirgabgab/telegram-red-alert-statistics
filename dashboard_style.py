"""Visual layer of the dashboard: design tokens, global CSS and the page header.

Kept out of dashboard.py so the UI file stays about data and charts.
Palette decisions are documented in handoff.md (stage 2.5). The categorical alert-type colors
and the sequential ramp were checked with the dataviz skill's validate_palette.js against
the light (#FFFFFF) and dark (#111318) surfaces.
"""

from html import escape

from alerts_parser import EARLY_WARNING, EARTHQUAKE, INFILTRATION, ROCKET, UAV

FONT = '"Heebo", system-ui, -apple-system, "Segoe UI", Arial, sans-serif'

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
    --ra-hero: {t['hero']}; --ra-hero-ink: {t['hero_ink']};
    --ra-radius: 12px;
  }}

  /* RTL only on content; the app shell (sidebar drawer, header) stays LTR so it collapses correctly */
  [data-testid="stMain"], [data-testid="stSidebarUserContent"] {{ direction: rtl; text-align: right; }}
  [data-testid="stPlotlyChart"], [data-testid="stPlotlyChart"] *,
  [data-testid="stDataFrame"] {{ direction: ltr !important; text-align: initial; }}
  /* The date field breaks when mirrored: keep it LTR */
  [data-testid="stDateInput"] > div, [data-testid="stDateInput"] > div * {{ direction: ltr; }}
  [data-testid="stButtonGroup"] {{ direction: ltr; justify-content: flex-end; }}
  [data-testid="stMetricValue"] {{ font-variant-numeric: tabular-nums; }}
  .block-container {{ padding-top: 1.25rem; }}

  /* Charts sit on a framed card; the figure itself is transparent */
  [data-testid="stPlotlyChart"] {{
    background: var(--ra-card); border: 1px solid var(--ra-border); border-radius: var(--ra-radius);
    padding: 0; overflow: hidden;  /* Plotly sizes the SVG to this box; inner spacing comes from the figure margins */
  }}

  /* ---- Header band ---------------------------------------------------------------- */
  .ra-hero {{
    position: relative; overflow: hidden; isolation: isolate;
    background: var(--ra-hero); color: var(--ra-hero-ink);
    border-radius: 16px; padding: 28px 32px 24px; margin: 0 0 20px;
  }}
  .ra-hero__bg {{ position: absolute; inset: 0; width: 100%; height: 100%; z-index: -1; pointer-events: none; }}
  .ra-hero__map {{
    position: absolute; left: 3%; top: 7%; height: 86%; width: auto; z-index: -1; pointer-events: none;
  }}
  /* Siren waves are centered on the siren mark (right side, RTL) */
  .ra-hero__waves {{
    position: absolute; width: 500px; height: 500px; right: -196px; top: -187px; z-index: -1; pointer-events: none;
  }}
  .ra-hero__brand {{ display: flex; align-items: center; gap: 14px; }}
  .ra-hero__brand svg {{ flex: none; }}
  .ra-hero h1 {{
    font-family: {FONT}; font-weight: 700; font-size: clamp(1.5rem, 1.1rem + 1.6vw, 2rem); line-height: 1.2;
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

  /* ---- KPI cards ------------------------------------------------------------------ */
  .ra-kpis {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 0 0 8px; }}
  @media (min-width: 1600px) {{ .ra-kpis {{ grid-template-columns: repeat(6, minmax(0, 1fr)); }} }}
  .ra-kpi {{
    background: var(--ra-card); border: 1px solid var(--ra-border); border-radius: var(--ra-radius);
    padding: 14px 16px; min-width: 0;
  }}
  .ra-kpi--primary {{ border-inline-start: 4px solid var(--ra-brand); }}
  .ra-kpi__label {{ font-size: 0.85rem; line-height: 1.4; color: var(--ra-muted); margin: 0; }}
  .ra-kpi__value {{
    font-size: 1.75rem; font-weight: 700; line-height: 1.25; color: var(--ra-ink); margin: 4px 0 2px;
    font-variant-numeric: tabular-nums; overflow-wrap: anywhere;
  }}
  .ra-kpi__value--text {{ font-size: 1.25rem; padding-top: 6px; }}
  .ra-kpi__sub {{ font-size: 0.8rem; line-height: 1.45; color: var(--ra-ink2); margin: 0; }}

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

  @media (max-width: 640px) {{
    .ra-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
    .ra-kpi {{ padding: 12px; }}
    .ra-kpi__value {{ font-size: 1.4rem; }}
    .ra-kpi__value--text {{ font-size: 1.05rem; }}
    /* Leave room for the fixed app header (sidebar toggle) on narrow screens */
    .block-container {{ padding-top: 3.75rem; }}
    .ra-hero {{ padding: 20px 18px 18px; border-radius: 12px; }}
    .ra-hero__brand svg {{ width: 36px; height: 36px; }}
    .ra-hero__sub {{ font-size: 0.85rem; }}
    .ra-hero__map {{ left: 2%; opacity: 0.6; }}
    .ra-hero__waves {{ right: -214px; top: -200px; }}
    .ra-hero__meta {{ margin-top: 14px; }}
  }}
</style>
"""


def hero_html(title, subtitle, chips):
    """The page header: red band, siren mark, title and a row of context chips.

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
    <path d="M-40 250 Q 260 -30 600 170" opacity=".16"/>
    <path d="M60 270 Q 420 10 820 230" opacity=".11"/>
    <path d="M760 260 Q 650 120 520 128" opacity=".16"/>
  </g>
</svg>
<svg class="ra-hero__waves" viewBox="0 0 500 500" aria-hidden="true" focusable="false">
  <g fill="none" stroke="#fff" stroke-width="1.5">
    <circle cx="250" cy="250" r="56" opacity=".16"/>
    <circle cx="250" cy="250" r="100" opacity=".10"/>
    <circle cx="250" cy="250" r="150" opacity=".06"/>
    <circle cx="250" cy="250" r="205" opacity=".035"/>
  </g>
</svg>
"""
    israel = (f'<svg class="ra-hero__map" viewBox="0 0 180 460" aria-hidden="true" focusable="false">'
              f'<path d="{ISRAEL_PATH}" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.22)" '
              f'stroke-width="1.6" stroke-linejoin="round"/></svg>')

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


def _flatten(html):
    """st.markdown treats indented lines as a code block: strip indentation and blank lines."""
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


INFO_ICON = (
    '<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">'
    '<circle cx="10" cy="10" r="8.25" fill="none" stroke="currentColor" stroke-width="1.5"/>'
    '<path d="M10 9v5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>'
    '<circle cx="10" cy="6.3" r="1" fill="currentColor"/></svg>'
)


def kpi_cards_html(cards):
    """cards: list of dicts with label, value, sub, and optional primary / text (long word value) / ltr."""
    out = []
    for c in cards:
        cls = "ra-kpi" + (" ra-kpi--primary" if c.get("primary") else "")
        vcls = "ra-kpi__value" + (" ra-kpi__value--text" if c.get("text") else "")
        value = escape(str(c["value"]))
        if c.get("ltr"):
            value = f'<bdi dir="ltr">{value}</bdi>'
        sub = f'<div class="ra-kpi__sub">{escape(c["sub"])}</div>' if c.get("sub") else ""
        # divs, not <p>: Streamlit's markdown styles for p would override the sizes
        out.append(f'<div class="{cls}"><div class="ra-kpi__label">{escape(c["label"])}</div>'
                   f'<div class="{vcls}">{value}</div>{sub}</div>')
    return f'<section class="ra-kpis" aria-label="מדדים עיקריים">{"".join(out)}</section>'


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
