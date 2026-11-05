from telethon.sync import TelegramClient
from parameters import *
import pandas as pd
import re
import os

ALERTS = ["🔴 צבע אדום",
          "✈️ חדירת כלי טיס עוין",
          "🔓 חשש לחדירת מחבלים",
          "🔴 התרעה",
          "🔴 אזעקת צבע אדום"]

FILTER_ALERTS = ["✈️ חדירת כלי טיס עוין",
                 "🔓 חשש לחדירת מחבלים",
                 "עדכון פיקוד העורף - סיום אירוע"]

filter_alerts_2 = ["חדירת מחבלים", "התרעת חדירת כלי טיס"]

INVALID_WORDS = ["שלום רב", "אפליקציית", "בתקווה לימים שקטים יותר", "איתכם בכל זמן", "מערכת צופר"]


def remove_file(file_name):
    if os.path.exists(file_name):
        os.remove(file_name)
        print(f"The file {file_name} has been removed.")
    else:
        print(f"The file {file_name} does not exist.")


def get_entity(client, name):
    entity = None
    for dialog in client.iter_dialogs():
        if dialog.is_channel and dialog.name == name:
            entity = dialog.entity
            break

    return entity


def get_real_date(date_text):
    try:
        if date_text is None or filter_alerts_2[0] in date_text or filter_alerts_2[1] in date_text:
            return None, None
        print(date_text)
        all_dates = re.findall(pattern=r"\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}", string=date_text)
        all_dates += re.findall(pattern=r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}", string=date_text)
        if all_dates:
            append_text = "20" if len(all_dates[0]) == 17 else ""
            all_dates = f"{all_dates[0][:6]}{append_text}{all_dates[0][6:-3]}"
            current_date = pd.to_datetime(all_dates, format=date_format, utc=True)
            current_text = re.sub(pattern, "", date_text)
            current_text = current_text.replace("_", "").replace("*", "").replace("סיט", "סיטי")
            current_text = current_text.replace("•", "").replace("Warning", "").replace(".", ",").strip()
            current_text = f"{current_text[:-1]}\n"
            return current_date, current_text
        else:
            return None, None
    except TypeError:
        return None, None


def get_last_alert(date_text, last_date, alert):
    for al in ALERTS:
        if al in date_text:
            alert = al
            last_date = re.findall(pattern=r"\d{2}/\d{2}/\d{4}", string=date_text)[0]
            break
    return last_date, alert


def update_state(date_list, place_list, date, hour):
    current_date = pd.to_datetime(f"{date} {hour}", format=date_format, utc=True)
    date_list.append(current_date)
    place_list.append("")


def invalid_text(text):
    return text is None or len(text) == 0 or any(x in text for x in INVALID_WORDS)


def get_real_date_2(date_text, last_hour, last_date, last_alert):
    if invalid_text(text=date_text):
        return None, None, last_hour, last_date, last_alert
    if "האירוע הסתיים" in date_text:
        return None, None, last_hour, last_date, last_alert
    if "עדכון פיקוד העורף - סיום אירוע" in date_text:
        return None, None, last_hour, last_date, last_alert
    last_date, last_alert = get_last_alert(date_text=date_text, last_date=last_date, alert=last_alert)
    if last_alert in FILTER_ALERTS:
        print(f"last_alert = {last_alert}")
        return None, None, last_hour, last_date, last_alert

    all_my_dates = []
    all_my_places = []
    valid_lines = [line for line in date_text.split(sep="\n") if len(line)]
    for line in valid_lines:
        if re.match(pattern=r"__\d{2}:\d{2}:__", string=line):
            last_hour = line.replace("_", "")[:-1]
            update_state(date_list=all_my_dates, place_list=all_my_places, date=last_date, hour=last_hour)
        elif "•" in line:
            if "והפזורה" in line:
                print(121)
            if len(all_my_places) == 0:
                update_state(date_list=all_my_dates, place_list=all_my_places, date=last_date, hour=last_hour)
            line = line.split(sep="(")[0].replace("_", "").replace("*", "").replace("•", "").replace(" והפזורה", "")
            line = line.strip()
            all_my_places[-1] += f"{line}\n"

    return all_my_dates, all_my_places, last_hour, last_date, last_alert


def add_bug_messages(n_messaages, df, all_data):
    bug_dates = [pd.Timestamp(year=2023, month=10, day=31, hour=6, minute=8).replace(tzinfo=timezone.utc)]
    bug_texts = ["עוטף עזה: כיסופים"]
    for date, text in zip(bug_dates, bug_texts):
        if min_date <= date <= max_date:
            bug_dict = pd.DataFrame({"date": date, "text": text}, index=[1])
            df = pd.concat([df, bug_dict], ignore_index=True)
            all_data.append([date, text])
            n_messaages += 1
            print(f"@@@@@@@@ collect message {n_messaages} @@@@@@@@\n")
            print(text)
    return n_messaages, df, all_data


def collect_data_into_excel_tzofar_red_color():
    client = TelegramClient(session_name, api_id, api_hash)
    client.start(phone=phone_number)
    entity = get_entity(client=client, name="צופר - צבע אדום")

    df = pd.DataFrame()
    n_messaages = 0
    all_data = []

    n_messaages, df, all_data = add_bug_messages(n_messaages=n_messaages, df=df, all_data=all_data)

    last_date = None
    last_alert = None
    last_hour = None

    text_line = ""
    for message in client.iter_messages(entity=entity, offset_date=min_date, reverse=True):
        if min_date <= message.date <= max_date:
            if "האירוע הסתיים באזורים" in message.text:
                print(f"message.text = {message.text}")
            real_dates, real_texts, last_hour, last_date, last_alert = get_real_date_2(date_text=message.text,
                                                                                       last_hour=last_hour,
                                                                                       last_date=last_date,
                                                                                       last_alert=last_alert)
            if real_dates is None:
                continue
            for real_date, real_text in zip(real_dates, real_texts):
                if [real_date, real_text] in all_data:
                    continue
                all_data.append([real_date, real_text])
                n_messaages += 1
                data = {"date": real_date, "text": real_text}

                temp_df = pd.DataFrame(data, index=[1])
                df = pd.concat([df, temp_df], ignore_index=True)
                text_line += f"@@@@@@@@ collect message {n_messaages} date : {real_date} @@@@@@@@\n"
                print(f"@@@@@@@@ collect message {n_messaages} date : {real_date} @@@@@@@@\n")
                print(real_text)
        else:
            print(f"message {message.date} not in range")

    with open("telegram_log.txt", "w") as file:
        file.write(text_line)

    df['date'] = df['date'].dt.tz_localize(None)
    df = df.sort_values(by='date', ascending=False)
    df.to_excel("tzofar_red_color.xlsx", index=False)


def collect_data_into_excel_red_color():
    client = TelegramClient(session_name, api_id, api_hash)
    client.start(phone=phone_number)
    entity = get_entity(client=client, name="🔴 צבע אדום 🔴")

    df = pd.DataFrame()
    n_messaages = 0
    for message in client.iter_messages(entity=entity, reverse=True):
        if min_date <= message.date <= max_date:
            real_date, real_text = get_real_date(date_text=message.text)
            if real_date is None:
                continue
            n_messaages += 1
            data = {"date": real_date, "text": real_text}

            temp_df = pd.DataFrame(data, index=[1])
            df = pd.concat([df, temp_df], ignore_index=True)
            print(f"messages {n_messaages} :")
        else:
            print(f"message {message.date} not in range")

    df['date'] = df['date'].dt.tz_localize(None)
    df = df.sort_values(by='date', ascending=False)
    df.to_excel("red_color.xlsx", index=False)


def collect_data_into_excel(chat_group_name=chat_name_2):
    os.makedirs("./graphs/", exist_ok=True)
    for file in os.listdir("./graphs/"):
        os.remove(os.path.join("./graphs/", file))
    if chat_group_name == "🔴 צבע אדום 🔴":
        collect_data_into_excel_red_color()
    elif chat_group_name == "צופר - צבע אדום":
        collect_data_into_excel_tzofar_red_color()
    else:
        print(f"Invalid chat_name : {chat_group_name}")
