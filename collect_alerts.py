"""Incremental collector: save raw messages of the "צופר - צבע אדום" channel, then rebuild the dataset.

All alert types are kept (צבע אדום, חדירת כלי טיס עוין, חדירת מחבלים, ...) - filtering happens in
analysis, not in collection. Raw messages are stored as-is in ``data/raw_messages.jsonl`` so the
parser can be improved and re-run later without collecting again.

Requires TELEGRAM_API_ID / TELEGRAM_API_HASH / TELEGRAM_PHONE in the environment or in .env
(see .env.example). The first run asks for the login code Telegram sends to your phone and
creates a local ``<TELEGRAM_SESSION>.session`` file (never commit it).

Usage:
    python collect_alerts.py                       # continue from the last saved message
    python collect_alerts.py --since 2026-02-26    # first run / backfill from a date
    python collect_alerts.py --refresh-hours 48    # also re-fetch messages edited recently
"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone

from parameters import api_id, api_hash, phone_number, session_name, chat_name_2, min_date
import build_dataset

RAW_MESSAGES = build_dataset.RAW_MESSAGES
CHANNEL = os.getenv("TELEGRAM_CHANNEL", chat_name_2)  # dialog title or @username


def load_existing(path=RAW_MESSAGES):
    messages = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    msg = json.loads(line)
                    messages[msg["id"]] = msg
    return messages


def save_all(messages, path=RAW_MESSAGES):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for msg in sorted(messages.values(), key=lambda m: m["id"]):
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def get_entity(client, name):
    if name.startswith("@") or name.startswith("https://"):
        return client.get_entity(name)
    for dialog in client.iter_dialogs():
        if dialog.is_channel and dialog.name == name:
            return dialog.entity
    raise SystemExit(f"Channel '{name}' not found in your dialogs. Join it first or set TELEGRAM_CHANNEL=@username")


def to_record(message):
    return {
        "id": message.id,
        "date": message.date.astimezone(timezone.utc).isoformat(),
        "edit_date": message.edit_date.astimezone(timezone.utc).isoformat() if message.edit_date else None,
        "text": message.text or "",
    }


def collect(since=None, refresh_hours=24):
    from telethon.sync import TelegramClient  # imported here so the rest of the project works without telethon

    if not (api_id and api_hash):
        raise SystemExit("Missing TELEGRAM_API_ID / TELEGRAM_API_HASH. Copy .env.example to .env and fill it in.")

    messages = load_existing()
    client = TelegramClient(session_name, int(api_id), api_hash)
    client.start(phone=phone_number)
    try:
        entity = get_entity(client, CHANNEL)

        if messages and since is None:
            # Continue after the last message, but re-fetch the last `refresh_hours` because the
            # channel sometimes edits a message to append more alert times.
            last_date = max(datetime.fromisoformat(m["date"]) for m in messages.values())
            cutoff = last_date - timedelta(hours=refresh_hours)
            older = [m["id"] for m in messages.values() if datetime.fromisoformat(m["date"]) < cutoff]
            iterator = client.iter_messages(entity, min_id=max(older) if older else 0, reverse=True)
            print(f"Continuing from {cutoff:%Y-%m-%d %H:%M} UTC ({len(messages):,} messages saved so far)")
        else:
            start = since or min_date
            iterator = client.iter_messages(entity, offset_date=start, reverse=True)
            print(f"Collecting from {start:%Y-%m-%d}")

        n_new = n_updated = 0
        for i, message in enumerate(iterator, start=1):
            rec = to_record(message)
            old = messages.get(rec["id"])
            if old is None:
                n_new += 1
            elif old != rec:
                n_updated += 1
            messages[rec["id"]] = rec
            if i % 500 == 0:
                print(f"  {i:,} messages read (last: {message.date:%Y-%m-%d %H:%M})")
                save_all(messages)
    finally:
        client.disconnect()

    save_all(messages)
    print(f"Done: {n_new:,} new, {n_updated:,} updated, {len(messages):,} total -> {RAW_MESSAGES}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", type=lambda s: datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc),
                        help="collect from this date (YYYY-MM-DD), ignoring what was saved before")
    parser.add_argument("--refresh-hours", type=int, default=24,
                        help="re-fetch messages from the last N hours of saved data (default 24)")
    parser.add_argument("--no-build", action="store_true", help="don't rebuild data/alerts.csv.gz afterwards")
    args = parser.parse_args()

    collect(since=args.since, refresh_hours=args.refresh_hours)
    if not args.no_build:
        build_dataset.main()


if __name__ == "__main__":
    main()
