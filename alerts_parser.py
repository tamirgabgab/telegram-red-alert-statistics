"""Parse "צופר - צבע אדום" Telegram messages into flat alert records.

One record = one locality that received one alert at one minute:

    timestamp (naive, Israel local time) | alert_type | zone | city | shelter_sec | message_id

Message format (Telegram markdown; the parser strips ``*``/``_`` so bold/italic do not matter)::

    🔴 צבע אדום (14/06/2026):

    12:55:
    • עוטף עזה: כפר עזה, זמרת, שובה, סעד (15 שניות)

    ✈️ חדירת כלי טיס עוין (17/06/2026):
    12:53:
    • קו העימות: זרעית

    סיום אירוע (12:58 14/06/2026)
    האירוע הסתיים בזמרת, שובה, כפר עזה, סעד

A long alert can be split over several messages, so the parser carries the last alert type,
date and hour from one message to the next (like the legacy ``get_real_date_2``).
"""

import re
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, time
from typing import Optional

from city_names import split_cities, normalize_city

# --------------------------------------------------------------------------------------
# Alert types
# --------------------------------------------------------------------------------------
ROCKET = "rocket"
UAV = "uav"
INFILTRATION = "infiltration"
EARTHQUAKE = "earthquake"
HAZMAT = "hazmat"
EARLY_WARNING = "early_warning"
OTHER = "other"

ALERT_TYPE_LABELS = {
    ROCKET: "צבע אדום",
    UAV: "חדירת כלי טיס עוין",
    INFILTRATION: "חדירת מחבלים",
    EARLY_WARNING: "התרעה מקדימה",
    EARTHQUAKE: "רעידת אדמה",
    HAZMAT: "חומרים מסוכנים",
    OTHER: "אחר",
}

# Order matters: the first keyword found in the header wins.
_TYPE_KEYWORDS = [
    ("חדירת כלי טיס", UAV),
    ("כלי טיס עוין", UAV),
    ("חדירת מחבלים", INFILTRATION),
    ("בדקות הקרובות", EARLY_WARNING),
    ("התרעה מקדימה", EARLY_WARNING),
    ("רעידת אדמה", EARTHQUAKE),
    ("חומרים מסוכנים", HAZMAT),
    ("צבע אדום", ROCKET),
    ("ירי רקטות", ROCKET),
]

_END_KEYWORDS = ["סיום אירוע", "האירוע הסתיים"]

# Promotional / service messages of the channel - never alerts.
_INVALID_WORDS = ["שלום רב", "אפליקציית", "בתקווה לימים שקטים יותר", "איתכם בכל זמן", "מערכת צופר"]

_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})")
_HOUR_LINE_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*:?$")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
_SHELTER_RE = re.compile(r"\(([^()]*)\)\s*$")
_BULLETS = "•·●▪-"


# --------------------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------------------
@dataclass
class AlertRecord:
    timestamp: datetime
    alert_type: str
    zone: str
    city: str
    shelter_sec: Optional[int] = None
    message_id: Optional[int] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class EndRecord:
    """A "סיום אירוע" message: the event ended for these localities."""
    timestamp: datetime
    zone: str
    city: str
    message_id: Optional[int] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class ParserState:
    """Carried between consecutive messages (an alert may span several messages)."""
    alert_type: Optional[str] = None
    day: Optional[date] = None
    hour: Optional[time] = None


@dataclass
class ParseResult:
    alerts: list = field(default_factory=list)
    ends: list = field(default_factory=list)
    unparsed_lines: list = field(default_factory=list)


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def strip_markdown(text):
    """Remove Telegram markdown markers and invisible direction characters."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # [label](url) -> label
    for ch in ("**", "__", "~~", "`", "*", "‏", "‎", "‫", "‬"):
        text = text.replace(ch, "")
    return text


def parse_shelter_time(text):
    """Convert a time-to-shelter phrase to seconds: "15 שניות"->15, "דקה וחצי"->90, "מיידי"->0."""
    if text is None:
        return None
    t = text.strip()
    if not t:
        return None
    if "מיידי" in t:
        return 0
    num = re.search(r"\d+", t)
    n = int(num.group()) if num else None
    if "שני" in t:  # שניות / שנייה
        return n if n is not None else 1
    if "דק" in t:  # דקה / דקות
        if "וחצי" in t:
            return (n or 1) * 60 + 30
        if n is None:
            n = 2 if ("שתי" in t or "שתיים" in t) else 1
        return n * 60
    return None


def detect_alert_type(line):
    for keyword, alert_type in _TYPE_KEYWORDS:
        if keyword in line:
            return alert_type
    return None


def _parse_date(match):
    d, m, y = (int(g) for g in match.groups())
    if y < 100:
        y += 2000
    return date(y, m, d)


def _is_signature(line):
    """The channel signs every message with a link "צופר - צבע אדום" - not a header."""
    return "צופר" in line


def _is_header(line):
    """A header line names the alert type and/or carries a (DD/MM/YYYY) date, but no zone list."""
    if line.lstrip().startswith(tuple(_BULLETS)) or _is_signature(line):
        return False
    return detect_alert_type(line) is not None or _DATE_RE.search(line) is not None


def _split_zone_line(line):
    """'• עוטף עזה: כפר עזה, זמרת, שובה (15 שניות)' -> ('עוטף עזה', [...], 15)."""
    body = line.strip().lstrip(_BULLETS).strip()
    if ":" not in body:
        return None
    zone, cities_text = body.split(":", 1)
    zone = zone.strip()
    shelter = None
    m = _SHELTER_RE.search(cities_text)
    if m:
        shelter = parse_shelter_time(m.group(1))
        cities_text = cities_text[: m.start()]
    # Any other parenthesised remark inside the list is not part of a name.
    cities_text = re.sub(r"\([^()]*\)", "", cities_text)
    cities = split_cities(cities_text)
    if not zone or not cities:
        return None
    return zone, cities, shelter


def _local_fallback(message_dt):
    if message_dt is None:
        return None, None
    return message_dt.date(), message_dt.time().replace(second=0, microsecond=0)


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------
def is_invalid_message(text):
    return text is None or not text.strip() or any(w in text for w in _INVALID_WORDS)


def parse_end_message(text, message_dt=None, message_id=None):
    """Parse a "סיום אירוע" message into EndRecords (one per locality)."""
    clean = strip_markdown(text)
    ts = None
    m_date = _DATE_RE.search(clean)
    m_time = _TIME_RE.search(clean)
    if m_date and m_time:
        ts = datetime.combine(_parse_date(m_date), time(int(m_time.group(1)), int(m_time.group(2))))
    elif message_dt is not None:
        ts = message_dt.replace(second=0, microsecond=0, tzinfo=None)
    if ts is None:
        return []

    records = []
    lines = [ln.strip() for ln in clean.split("\n") if ln.strip()]
    zone_lines = [ln for ln in lines if ln[0] in _BULLETS and ":" in ln]
    if zone_lines:
        for ln in zone_lines:
            parsed = _split_zone_line(ln)
            if parsed:
                zone, cities, _ = parsed
                records += [EndRecord(ts, zone, c, message_id) for c in cities]
        return records

    for ln in lines:
        idx = ln.find("האירוע הסתיים")
        if idx < 0:
            continue
        rest = ln[idx + len("האירוע הסתיים"):].strip()
        if ":" in rest:  # "האירוע הסתיים באזורים: ..."
            rest = rest.split(":", 1)[1]
        elif rest.startswith("ב"):  # "האירוע הסתיים בזמרת, שובה" - drop the preposition
            rest = rest[1:]
        records += [EndRecord(ts, "", c, message_id) for c in split_cities(rest)]
    return records


def parse_message(text, state=None, message_dt=None, message_id=None):
    """Parse one Telegram message.

    :param text: raw ``message.text`` (markdown).
    :param state: ParserState carried from the previous message (mutated in place).
    :param message_dt: message datetime in Israel local time (naive or aware); used as a fallback
        when the message has no date/hour of its own.
    :param message_id: Telegram message id, stored on every record for de-duplication.
    :return: ParseResult
    """
    if state is None:
        state = ParserState()
    result = ParseResult()
    if is_invalid_message(text):
        return result
    if message_dt is not None and message_dt.tzinfo is not None:
        message_dt = message_dt.replace(tzinfo=None)

    clean = strip_markdown(text)
    if any(k in clean for k in _END_KEYWORDS):
        result.ends = parse_end_message(text, message_dt, message_id)
        return result

    for raw_line in clean.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        if _is_signature(line):
            continue

        if _is_header(line):
            state.alert_type = detect_alert_type(line) or OTHER
            m = _DATE_RE.search(line)
            state.day = _parse_date(m) if m else _local_fallback(message_dt)[0]
            state.hour = None
            continue

        m_hour = _HOUR_LINE_RE.match(line)
        if m_hour:
            state.hour = time(int(m_hour.group(1)), int(m_hour.group(2)))
            continue

        if line[0] in _BULLETS or ":" in line:
            parsed = _split_zone_line(line)
            if parsed is None:
                result.unparsed_lines.append(line)
                continue
            if state.alert_type is None:
                # Zone line without any header seen yet - we can't know the alert type.
                result.unparsed_lines.append(line)
                continue
            fb_day, fb_hour = _local_fallback(message_dt)
            day = state.day or fb_day
            hour = state.hour or fb_hour
            if day is None or hour is None:
                result.unparsed_lines.append(line)
                continue
            zone, cities, shelter = parsed
            ts = datetime.combine(day, hour)
            result.alerts += [AlertRecord(ts, state.alert_type, zone, c, shelter, message_id) for c in cities]
            continue

        result.unparsed_lines.append(line)

    return result


def parse_messages(messages):
    """Parse an iterable of dicts ``{"id", "date" (Israel local datetime), "text"}`` in chronological order.

    Returns (alerts, ends, unparsed) where alerts/ends are lists of dicts and ``unparsed`` is a list of
    (message_id, line) for lines that looked like content but could not be parsed.
    """
    state = ParserState()
    alerts, ends, unparsed = [], [], []
    for msg in messages:
        res = parse_message(msg.get("text"), state=state, message_dt=msg.get("date"), message_id=msg.get("id"))
        alerts += [a.to_dict() for a in res.alerts]
        ends += [e.to_dict() for e in res.ends]
        unparsed += [(msg.get("id"), ln) for ln in res.unparsed_lines]
    return alerts, ends, unparsed


def parse_legacy_text(timestamp, text, alert_type=ROCKET):
    """Parse one row of the legacy ``tzofar_red_color.xlsx`` ("zone: cities" per line, no shelter time)."""
    records = []
    for line in str(text).split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        zone, cities_text = line.split(":", 1)
        for city in split_cities(cities_text):
            records.append(AlertRecord(timestamp, alert_type, normalize_city(zone), city).to_dict())
    return records
