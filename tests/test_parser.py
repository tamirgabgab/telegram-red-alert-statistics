"""Tests for alerts_parser, using the message formats seen in the "צופר - צבע אדום" channel.

Run:  pytest -q
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alerts_parser import (  # noqa: E402
    ROCKET, UAV, INFILTRATION, OTHER,
    ParserState, parse_message, parse_messages, parse_shelter_time, parse_legacy_text,
)
from city_names import split_cities  # noqa: E402

# Telegram markdown as returned by Telethon's message.text (bold/italic markers + signature link).
ROCKET_GAZA = (
    "🔴 **צבע אדום** __(14/06/2026)__:\n\n"
    "__12:55:__\n"
    "• **עוטף עזה**: כפר עזה, זמרת, שובה, סעד (15 שניות)\n\n"
    "[צופר - צבע אדום](https://t.me/tzevaadom)"
)

UAV_ZARIT = (
    "✈️ **חדירת כלי טיס עוין** __(17/06/2026)__:\n\n"
    "__12:53:__\n"
    "• **קו העימות**: זרעית\n\n"
    "__12:56:__\n"
    "• **קו העימות**: זרעית\n\n"
    "[צופר - צבע אדום](https://t.me/tzevaadom)"
)

ROCKET_MULTI_ZONE = (
    "🔴 **צבע אדום** __(08/06/2026)__:\n\n"
    "__09:39:__\n"
    "• **דן**: תל אביב - דרום העיר ויפו, תל אביב - מזרח, בת ים, חולון (דקה וחצי)\n"
    "• **השפלה**: גיבתון, גן שלמה, נצר סרני (דקה וחצי)\n"
    "• **מרכז הגליל**: בית סוהר צלמון, טפחות, כלנית (דקה)\n"
)

END_EVENT = (
    "**סיום אירוע** (12:58 14/06/2026)\n\n"
    "האירוע הסתיים **בזמרת, שובה, כפר עזה, סעד**\n\n"
    "[צופר - צבע אדום](https://t.me/tzevaadom)"
)

INFILTRATION_MSG = (
    "🔓 **חשש לחדירת מחבלים** __(10/06/2026)__:\n\n"
    "__21:10:__\n"
    "• **עוטף עזה**: נחל עוז\n"
)


def test_rocket_single_zone():
    res = parse_message(ROCKET_GAZA, message_id=1)
    assert [a.city for a in res.alerts] == ["כפר עזה", "זמרת, שובה", "סעד"]
    a = res.alerts[0]
    assert a.alert_type == ROCKET
    assert a.zone == "עוטף עזה"
    assert a.timestamp == datetime(2026, 6, 14, 12, 55)
    assert a.shelter_sec == 15
    assert a.message_id == 1
    assert res.unparsed_lines == []


def test_uav_multiple_hours_in_one_message():
    res = parse_message(UAV_ZARIT)
    assert [(a.alert_type, a.city, a.timestamp) for a in res.alerts] == [
        (UAV, "זרעית", datetime(2026, 6, 17, 12, 53)),
        (UAV, "זרעית", datetime(2026, 6, 17, 12, 56)),
    ]
    assert res.alerts[0].shelter_sec is None


def test_multiple_zones_and_shelter_times():
    res = parse_message(ROCKET_MULTI_ZONE)
    zones = {a.zone for a in res.alerts}
    assert zones == {"דן", "השפלה", "מרכז הגליל"}
    assert {a.shelter_sec for a in res.alerts if a.zone == "דן"} == {90}
    assert {a.shelter_sec for a in res.alerts if a.zone == "מרכז הגליל"} == {60}
    assert "בת - ים" in [a.city for a in res.alerts]  # normalized via rep_str


def test_infiltration():
    res = parse_message(INFILTRATION_MSG)
    assert [(a.alert_type, a.city) for a in res.alerts] == [(INFILTRATION, "נחל עוז")]


def test_end_event_is_not_an_alert():
    res = parse_message(END_EVENT, message_id=7)
    assert res.alerts == []
    assert [e.city for e in res.ends] == ["זמרת, שובה", "כפר עזה", "סעד"]
    assert res.ends[0].timestamp == datetime(2026, 6, 14, 12, 58)


def test_signature_does_not_reset_alert_type():
    """The 'צופר - צבע אדום' signature must not turn a UAV continuation into a rocket alert."""
    state = ParserState()
    parse_message(UAV_ZARIT, state=state)
    assert state.alert_type == UAV
    continuation = "__13:05:__\n• **קו העימות**: שתולה\n"
    res = parse_message(continuation, state=state)
    assert [(a.alert_type, a.city, a.timestamp) for a in res.alerts] == [
        (UAV, "שתולה", datetime(2026, 6, 17, 13, 5)),
    ]


def test_zone_line_without_hour_uses_message_time():
    msg = "🔴 צבע אדום (01/03/2026):\n• דן: חולון\n"
    res = parse_message(msg, message_dt=datetime(2026, 3, 1, 8, 15, 42))
    assert res.alerts[0].timestamp == datetime(2026, 3, 1, 8, 15)


def test_unknown_header_type_is_other():
    msg = "⚠️ **התרעה כללית** (01/03/2026):\n__08:00:__\n• דן: חולון\n"
    res = parse_message(msg)
    assert res.alerts[0].alert_type == OTHER


def test_promo_message_ignored():
    res = parse_message("שלום רב, הורידו את אפליקציית צופר")
    assert res.alerts == [] and res.ends == []


def test_parse_messages_sequence():
    msgs = [
        {"id": 1, "date": datetime(2026, 6, 14, 12, 55), "text": ROCKET_GAZA},
        {"id": 2, "date": datetime(2026, 6, 14, 12, 55), "text": None},  # map image without caption
        {"id": 3, "date": datetime(2026, 6, 14, 12, 58), "text": END_EVENT},
    ]
    alerts, ends, unparsed = parse_messages(msgs)
    assert len(alerts) == 3 and len(ends) == 3 and unparsed == []


def test_shelter_time_phrases():
    assert parse_shelter_time("15 שניות") == 15
    assert parse_shelter_time("30 שניות") == 30
    assert parse_shelter_time("דקה") == 60
    assert parse_shelter_time("דקה וחצי") == 90
    assert parse_shelter_time("3 דקות") == 180
    assert parse_shelter_time("מיידי") == 0
    assert parse_shelter_time("") is None


def test_split_cities_keeps_comma_names():
    assert split_cities("שדרות, איבים, ניר עם, סעד") == ["שדרות, איבים, ניר עם", "סעד"]
    assert split_cities("אשדוד - יא,יב,טו,יז,מרינה,סיטי, יבנה") == ["אשדוד - יא,יב,טו,יז,מרינה,סיטי", "יבנה"]


def test_legacy_excel_row():
    ts = datetime(2026, 3, 27, 14, 20)
    rows = parse_legacy_text(ts, "לכיש: יבנה, כפר הנגיד\nעוטף עזה: זמרת, שובה, סעד\n")
    assert [(r["zone"], r["city"]) for r in rows] == [
        ("לכיש", "יבנה"), ("לכיש", "כפר הנגיד"), ("עוטף עזה", "זמרת, שובה"), ("עוטף עזה", "סעד"),
    ]
    assert all(r["alert_type"] == ROCKET for r in rows)
