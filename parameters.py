import os
from datetime import datetime, timezone, timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional; plain environment variables also work
    pass

# Telegram credentials are read from the environment / .env file (see .env.example).
# Never commit real values to this file.
api_id = os.getenv("TELEGRAM_API_ID", "")
api_hash = os.getenv("TELEGRAM_API_HASH", "")
phone_number = os.getenv("TELEGRAM_PHONE", "")

# Support only "🔴 צבע אדום 🔴" or  "צופר - צבע אדום"
# chat_name_1 = "🔴 צבע אדום 🔴"
chat_name_2 = "צופר - צבע אדום"

pattern = r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}"

date_format = "%d/%m/%Y %H:%M"

min_date = datetime(year=2026, month=2, day=26, hour=0, minute=0, second=0, tzinfo=timezone.utc)
# min_date = datetime(year=2026, month=3, day=27, hour=0, minute=0, second=0, tzinfo=timezone.utc)
max_date = datetime.now(tz=timezone.utc) + timedelta(hours=3)
# max_date = datetime(year=2024, month=10, day=2, hour=0, minute=0, second=0, tzinfo=timezone.utc)
session_name = os.getenv("TELEGRAM_SESSION", "test")

# excel_out_file_1 = "red_color.xlsx"
excel_out_file_2 = "tzofar_red_color.xlsx"
excel_out_sheet = "Sheet1"

# pickle_out_file_1 = "Tzeva_Adom.pkl"
pickle_out_file_2 = "Tzofar_Tzeva_Adom.pkl"

COLLET = False

STATISTICS = False
EXTRA_STATISTICS = False

SHOW = True
SAVE = True