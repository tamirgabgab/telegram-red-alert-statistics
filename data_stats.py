import os
import re
import json
import pickle
import random
import pandas as pd
import numpy as np
from ivsort import ivsort
from copy import deepcopy
from parameters import *
from coditions import *
from Cdatetime import CustomDateTime, CustomDateHour
from city_names import special_str, rep_str


def save_dict(data_dict, name):
    with open(name, "wb") as save_file:
        pickle.dump(data_dict, save_file)


def load_dict(name):
    data_out = None
    if os.path.exists(name):
        with open(name, "rb") as load_file:
            data_out = pickle.load(load_file)
    else:
        print(f"{name} not exist in directory")

    return data_out


def update_data(data, keys_list):
    dict_pointer = data
    last_key = keys_list[-1]
    for i, key_0 in enumerate(keys_list):
        if key_0 in dict_pointer.keys() and key_0 != last_key:
            pass
        elif key_0 in dict_pointer.keys() and key_0 == last_key:
            dict_pointer[key_0] += 1
        elif key_0 not in dict_pointer.keys() and key_0 != last_key:
            dict_pointer[key_0] = dict()
        else:
            dict_pointer[key_0] = 1
        dict_pointer = dict_pointer.get(key_0)
    return data


def get_cities_list(line):
    city_list = []
    for sp_st in special_str:
        if sp_st in line:
            line = line.replace(sp_st, "")
            city_list.append(sp_st)
    for str_city in line.split(sep=","):
        if str_city in rep_str.keys():
            str_city = rep_str[str_city]
        if str_city != " ":
            city_list.append(str_city.strip())
    return city_list


def valid_line(line):
    return len(line)


def process_message(date, text, time_data):
    valid_lines = [line for line in text.split(sep="\n") if valid_line(line=line)]
    date_stamp = CustomDateTime(day=date.day, month=date.month, year=date.year)
    hour_stamp = f"{date.hour:02d}:{date.minute:02d}"

    for line in valid_lines:
        line = line.lstrip().rstrip()
        zone, line = line.split(sep=":")
        zone.replace("_", "")
        city_list = get_cities_list(line=line)
        for city in city_list:
            city = city.strip()
            time_data = update_data(data=time_data,
                                    keys_list=[zone, city, date_stamp, hour_stamp])


def is_hebrew(z):
    return isinstance(z, str) and re.match(r"[א-ת]", z) is not None


def sort_func(y, kind=0):
    if is_hebrew(y):
        return ivsort(y[kind])
    else:
        return y[kind]


def sort_dict(dict_data, kind, reverse):
    dict_out = dict(sorted(dict_data.items(), key=lambda x: sort_func(x, kind=kind), reverse=reverse))
    return dict_out


def sum_dicts(dict_11, dict_22):
    keys = set(list(dict_11.keys()) + list(dict_22.keys()))
    dict_out = dict()
    for key in keys:
        dict_out[key] = dict_11.get(key, 0) + dict_22.get(key, 0)
    return dict_out


def group_by_cities_dates_hours(data_dict):
    copy_data = deepcopy(data_dict)
    city_dict = dict()
    for key_zone in copy_data.keys():
        city_dict = {**city_dict, **copy_data[key_zone]}
    for key_city in city_dict.keys():
        for key_time in city_dict[key_city].keys():
            city_dict[key_city][key_time] = sort_dict(dict_data=city_dict[key_city][key_time], kind=0, reverse=False)
    city_dict = generat_sort(data_dict=city_dict)
    return city_dict


def generat_sort(data_dict):
    if isinstance(data_dict, dict):
        data_dict = sort_dict(dict_data=data_dict, kind=0, reverse=False)
        for key in data_dict.keys():
            data_dict[key] = generat_sort(data_dict=data_dict[key])
    return data_dict


def group_by_zones_dates_hours(data_dict):
    copy_data = deepcopy(data_dict)
    for key_zone in copy_data.keys():
        zone_dict = dict()
        for key_city in copy_data[key_zone].keys():
            for key_date in copy_data[key_zone][key_city].keys():
                if key_date not in zone_dict.keys():
                    zone_dict[key_date] = dict()
                for key_hour in copy_data[key_zone][key_city][key_date].keys():
                    zone_dict[key_date][key_hour] = sum_dicts(dict_11=zone_dict[key_date].get(key_hour, dict()),
                                                              dict_22=copy_data[key_zone][key_city][key_date][key_hour])
        copy_data[key_zone] = zone_dict
    copy_data = generat_sort(data_dict=copy_data)
    return copy_data


def group_by_zones_cities_hours(data_dict):
    copy_data = deepcopy(data_dict)
    for key_zone in copy_data.keys():
        for key_city in copy_data[key_zone].keys():
            h_dict = dict()
            for key_date in copy_data[key_zone][key_city].keys():
                for key_hour in copy_data[key_zone][key_city][key_date].keys():
                    h_dict[key_hour] = sum_dicts(dict_11=h_dict.get(key_hour, dict()),
                                                 dict_22=copy_data[key_zone][key_city][key_date][key_hour])
            copy_data[key_zone][key_city] = h_dict

    copy_data = generat_sort(data_dict=copy_data)
    return copy_data


def group_by_zones_cities_dates(data_dict):
    copy_data = deepcopy(data_dict)
    for key_zone in copy_data.keys():
        for key_city in copy_data[key_zone].keys():
            for key_date in copy_data[key_zone][key_city].keys():
                copy_data[key_zone][key_city][key_date] = sum(copy_data[key_zone][key_city][key_date]["hour"].values())

    copy_data = generat_sort(data_dict=copy_data)
    return copy_data


def group_by_dates_hours(data_dict):
    copy_data = deepcopy(data_dict)
    date_dict = dict()
    for key_zone in copy_data.keys():
        for key_city in copy_data[key_zone].keys():
            for key_date in copy_data[key_zone][key_city].keys():
                if key_date not in date_dict:
                    date_dict[key_date] = dict()
                    # date_dict[key_date] = deepcopy(EMPTY_TIME_DICT_2)
                for key_hour in copy_data[key_zone][key_city][key_date].keys():
                    date_dict[key_date][key_hour] = sum_dicts(dict_11=date_dict[key_date].get(key_hour, {}),
                                                              dict_22=copy_data[key_zone][key_city][key_date][key_hour])
    date_dict = generat_sort(data_dict=date_dict)
    return date_dict


def group_by_cities_hours(data_dict):
    copy_data = deepcopy(data_dict)
    city_dict = dict()
    for key_zone in copy_data.keys():
        for key_city in copy_data[key_zone].keys():
            h_dict = dict()
            # h_dict[key_date] = deepcopy(EMPTY_TIME_DICT_2)
            for key_date in copy_data[key_zone][key_city].keys():
                for key_hour in copy_data[key_zone][key_city][key_date].keys():
                    h_dict[key_hour] = sum_dicts(dict_11=h_dict.get(key_hour, {}),
                                                 dict_22=copy_data[key_zone][key_city][key_date][key_hour])
            city_dict[key_city] = h_dict
    city_dict = generat_sort(data_dict=city_dict)
    return city_dict


def group_by_cities_dates(data_dict):
    copy_data = deepcopy(data_dict)
    city_dict = dict()
    for key_zone in copy_data.keys():
        for key_city in copy_data[key_zone].keys():
            amount_dict = dict()
            for key_date in copy_data[key_zone][key_city].keys():
                amount_dict[key_date] = sum(copy_data[key_zone][key_city][key_date]["hour"].values())
            city_dict[key_city] = amount_dict
    city_dict = generat_sort(data_dict=city_dict)
    return city_dict


def group_by_zones_hours(data_dict):
    copy_data = deepcopy(data_dict)
    for key_zone in copy_data.keys():
        h_dict = dict()
        # h_dict[key_date] = deepcopy(EMPTY_TIME_DICT_2)
        for key_city in copy_data[key_zone].keys():
            for key_date in copy_data[key_zone][key_city].keys():
                for key_hour in copy_data[key_zone][key_city][key_date].keys():
                    h_dict[key_hour] = sum_dicts(dict_11=h_dict.get(key_hour, {}),
                                                 dict_22=copy_data[key_zone][key_city][key_date][key_hour])

        copy_data[key_zone] = h_dict
    copy_data = generat_sort(data_dict=copy_data)
    return copy_data


def group_by_zones_dates(data_dict):
    copy_data = deepcopy(data_dict)
    for key_zone in copy_data.keys():
        date_dict = dict()
        for key_city in copy_data[key_zone].keys():
            for key_date in copy_data[key_zone][key_city].keys():
                curr_sum = sum(copy_data[key_zone][key_city][key_date]["hour"].values())
                date_dict[key_date] = date_dict.get(key_date, 0) + curr_sum
        copy_data[key_zone] = date_dict
    copy_data = generat_sort(data_dict=copy_data)
    return copy_data


def group_by_zones_cities(data_dict):
    copy_data = deepcopy(data_dict)
    for key_zone in copy_data.keys():
        for key_city in copy_data[key_zone].keys():
            total = 0
            for key_date in copy_data[key_zone][key_city].keys():
                total += sum(copy_data[key_zone][key_city][key_date]["hour"].values())
            copy_data[key_zone][key_city] = total
    copy_data = generat_sort(data_dict=copy_data)
    return copy_data


def group_by_hours(data_dict):
    copy_data = deepcopy(data_dict)
    h_dict = dict()
    # h_dict[key_date] = deepcopy(EMPTY_TIME_DICT_2)
    for key_zone in copy_data.keys():
        for key_city in copy_data[key_zone].keys():
            for key_date in copy_data[key_zone][key_city].keys():
                for key_hour in copy_data[key_zone][key_city][key_date].keys():
                    h_dict[key_hour] = sum_dicts(dict_11=h_dict.get(key_hour, {}),
                                                 dict_22=copy_data[key_zone][key_city][key_date][key_hour])

    h_dict = generat_sort(data_dict=h_dict)
    return h_dict


def group_by_dates(data_dict, from_date=datetime(day=7, month=10, year=2023)):
    copy_data = deepcopy(data_dict)
    date_dict = dict()
    for key_zone in copy_data.keys():
        for key_city in copy_data[key_zone].keys():
            for key_date in copy_data[key_zone][key_city].keys():
                if key_date < from_date:
                    continue
                curr_sum = sum(copy_data[key_zone][key_city][key_date]["hour"].values())
                date_dict[key_date] = date_dict.get(key_date, 0) + curr_sum
    date_dict = generat_sort(data_dict=date_dict)
    return date_dict


def group_by_cities(data_dict):
    copy_data = deepcopy(data_dict)
    city_dict = dict()
    for key_zone in copy_data.keys():
        for key_city in copy_data[key_zone].keys():
            total = 0
            for key_date in copy_data[key_zone][key_city].keys():
                total += sum(copy_data[key_zone][key_city][key_date]["hour"].values())
            city_dict[key_city] = total
    city_dict = generat_sort(data_dict=city_dict)
    return city_dict


def group_by_zones(data_dict):
    copy_data = deepcopy(data_dict)
    zone_dict = dict()
    for key_zone in copy_data.keys():
        total = 0
        for key_city in copy_data[key_zone].keys():
            for key_date in copy_data[key_zone][key_city].keys():
                total += sum(copy_data[key_zone][key_city][key_date]["hour"].values())
        zone_dict[key_zone] = total
    zone_dict = generat_sort(data_dict=zone_dict)
    return zone_dict


def get_total_alerts(data_dict):
    n_alerts = 0
    total_dict = dict()
    for key_zone in data_dict.keys():
        for key_city in data_dict[key_zone].keys():
            for key_day in data_dict[key_zone][key_city].keys():
                n_alerts += sum(data_dict[key_zone][key_city][key_day]["hour"].values())
    total_dict["total alerts"] = n_alerts
    return total_dict


def fix_hour_and_min(dict_data):
    copy_data = deepcopy(dict_data)
    for key_zone in copy_data.keys():
        for key_city in copy_data[key_zone].keys():
            for key_day in copy_data[key_zone][key_city].keys():
                h_dict = dict()
                m_dict = dict()
                for key_hour in copy_data[key_zone][key_city][key_day].keys():
                    val = copy_data[key_zone][key_city][key_day][key_hour]
                    hour, minute = key_hour.split(sep=":")
                    hour, minute = int(hour), int(minute)
                    h_dict[hour] = h_dict.get(hour, 0) + val
                    m_dict[minute] = m_dict.get(minute, 0) + val
                copy_data[key_zone][key_city][key_day] = {"hour": h_dict, "minute": m_dict}
    copy_data = generat_sort(data_dict=copy_data)
    return copy_data


def reduce_days(dict_data):
    copy_data = deepcopy(dict_data)
    copy_data_zones = deepcopy(dict_data)
    for key_zone in copy_data.keys():
        h_object_dict_zone = dict()
        for key_city in copy_data[key_zone].keys():
            h_object_dict = dict()
            for key_day in copy_data[key_zone][key_city].keys():
                for key_hour in copy_data[key_zone][key_city][key_day].keys():
                    val = copy_data[key_zone][key_city][key_day][key_hour]
                    hour, minute = key_hour.split(sep=":")
                    new_object = CustomDateHour(hour=int(hour), minute=int(minute))
                    h_object_dict[new_object] = h_object_dict.get(new_object, 0) + val
                    h_object_dict_zone[new_object] = h_object_dict_zone.get(new_object, 0) + val
            h_object_dict = generat_sort(data_dict=h_object_dict)
            copy_data[key_zone][key_city] = h_object_dict
        h_object_dict_zone = generat_sort(data_dict=h_object_dict_zone)
        copy_data_zones[key_zone] = h_object_dict_zone
    copy_data = generat_sort(data_dict=copy_data)
    copy_data_zones = generat_sort(data_dict=copy_data_zones)
    return copy_data, copy_data_zones


def group_with_condition(data_dict, cond_func):
    time_dict = {"hour": dict(), "minute": dict()}
    for key_zone in data_dict.keys():
        for key_city in data_dict[key_zone].keys():
            for key_date in data_dict[key_zone][key_city].keys():
                if cond_func(zone=key_zone, city=key_city, date=key_date):
                    for key_hour in data_dict[key_zone][key_city][key_date].keys():
                        time_dict[key_hour] = sum_dicts(dict_11=time_dict.get(key_hour, {}),
                                                        dict_22=data_dict[key_zone][key_city][key_date][key_hour])
    time_dict = generat_sort(data_dict=time_dict)
    return time_dict


def group_fix_with_condition(data_dict, cond_func):
    time_dict = dict()
    for key_zone in data_dict.keys():
        for key_city in data_dict[key_zone].keys():
            for key_date in data_dict[key_zone][key_city].keys():
                for key_hour, val in data_dict[key_zone][key_city][key_date].items():
                    key_date = key_date.replace(hour=int(key_hour[:2]), minute=int(key_hour[-2:]))
                    if cond_func(zone=key_zone, city=key_city, date=key_date):
                        if isinstance(key_hour, str):
                            key_hour = datetime.strptime(key_hour, "%H:%M")
                        time_dict[key_hour] = time_dict.get(key_hour, 0) + val
    time_dict = generat_sort(data_dict=time_dict)
    return time_dict


def read_my_data(file_name, sheet_name):
    df = pd.read_excel(file_name, sheet_name=sheet_name)
    df = df.dropna(subset=['text'])
    n_messages = len(df)
    data_time = dict()
    for idx, (da, mess) in enumerate(zip(df["date"], df["text"]), start=1):
        print(f"read message {idx} / {n_messages}")
        process_message(date=da, text=mess, time_data=data_time)

    data_time_h_count = fix_hour_and_min(dict_data=data_time)
    data_time_h_count = generat_sort(data_dict=data_time_h_count)
    data_time = generat_sort(data_dict=data_time)
    return data_time_h_count, data_time


def clean_red(data_dict):
    for key_zone in data_dict.keys():
        for city_zone in list(data_dict[key_zone].keys())[::-1]:
            if city_zone == "":
                data_dict[key_zone].pop(city_zone)
    return data_dict


def create_distribution(full_data, data_dict_fix, hours=1, minutes=0):
    dist_dict = dict()

    dist_dict_alert = dict()

    date_data = group_by_dates(data_dict=full_data, from_date=datetime(day=8, month=10, year=2023))

    arr = np.array(list(date_data.values()))
    mean = arr.mean()
    # std = arr.std()

    # mean_r = mean * np.sqrt(np.pi / 2)
    # std_r = std * np.sqrt((4 - np.pi) / 2)
    val_p = np.random.poisson(lam=mean, size=1)[0]
    # val_n = np.random.normal(loc=mean, scale=std, size=1)
    # val_r = np.random.rayleigh(scale=std_r, size=1)
    for key_zone in data_dict_fix.keys():
        for key_city in data_dict_fix[key_zone].keys():
            curr_key = (key_zone, key_city)
            curr_value = sum(data_dict_fix[key_zone][key_city].values())
            dist_dict_alert[curr_key] = dist_dict.get(curr_key, 0) + curr_value
            start_date = datetime(year=2020, month=1, day=1, hour=0, minute=0)
            time_delta = timedelta(hours=hours, minutes=minutes)
            final_date = start_date + time_delta
            while start_date.day == final_date.day:
                for key_hour in data_dict_fix[key_zone][key_city].keys():
                    if start_date <= key_hour < final_date:
                        val = data_dict_fix[key_zone][key_city][key_hour]
                        new_key = (key_zone, key_city, (start_date, final_date))
                        dist_dict[new_key] = dist_dict.get(new_key, 0) + val
                start_date += timedelta(minutes=1)
                final_date += timedelta(minutes=1)
        print(f"zone {key_zone} complete")

    seq = list(dist_dict.keys())
    wei = list(dist_dict.values())
    choose = random.choices(population=seq, weights=wei, k=val_p)

    dict_estimation = dict()
    for zone, city, date_range in choose:
        # hour_string = f"{start_date} - {end_date}"
        update_data(data=dict_estimation, keys_list=[zone, city, date_range])

    dict_estimation = generat_sort(data_dict=dict_estimation)

    return dist_dict, dict_estimation


def get_all_zones(data_dict_cities, n_alerts_min=-float("inf"), n_alerts_max=float("inf")):
    # HT_zones.txt is an optional HTML dump of the Home Front Command localities list.
    # Without it we can't list localities that had no alerts, so return empty results.
    if not os.path.exists("HT_zones.txt"):
        print("HT_zones.txt not found - skipping the all-localities report")
        return [], {0: dict(), 1: dict()}
    with open("HT_zones.txt", "r", encoding='utf-8') as file_0:
        all_lines = file_0.readlines()

    all_lines = all_lines[0]
    pattern_0 = re.compile(r'<li class="ui-menu-item" role="presentation">(.*?)</li>', re.DOTALL)
    pattern_1 = re.compile(r'<a id="ui-id-(\d+)" class="ui-corner-all" tabindex="-1">(.*?)</a>', re.DOTALL)
    matches = pattern_0.findall(all_lines)

    out_dict = {0: dict(), 1: dict()}
    out_all_cities = []
    dict_convert = {
        "עין חרוד איחוד": ["עין חרוד"],
        'בסמ"ה': ["מועאוויה", "עין סוהלה", "ברטעה"],
        "אשדות יעקב איחוד": ["אשדות יעקב"],
        "אשדות יעקב מאוחד": ["אשדות יעקב"],
        "אזור תעשייה צמח": ["צמח"],
        "שבלי": ["אום אל גנם"],
        "אום אלג'נם": ["אום אל גנם"],
        "אום אל-גנם": ["אום אל גנם"],
        "עין אל-סהלה": ["עין אל סהלה"],
        "טל-אל": ["טל - אל"],
        "תקומה וחוות יזרעם": ["תקומה, חוות יזרעם"],
        "תקומה": ["תקומה, חוות יזרעם"],
        "חיפה-מפרץ": ["חיפה - מפרץ"],
        "פרדס חנה-כרכור": ["פרדס חנה כרכור"],
        "ערב אל-נעים": ["תקומה, חוות יזרעם"],
        "קריית טבעון-בית זייד": ["קריית טבעון - בית זייד"]
    }
    for match in matches:
        f_0 = pattern_1.findall(match)
        f_0 = f_0[0][1]
        f_0 = f_0.replace("<b>", "").replace("</b>", "")
        if "האזורים" in f_0:
            continue
        elif "אשדוד" in f_0:
            out_all_cities.append(f_0)
            continue
        elif f_0 in dict_convert.keys():
            f_0 = dict_convert[f_0]
        else:
            f_0 = [f_0]
        for f_1 in f_0:
            if f_1 not in out_all_cities:
                n_alerts = data_dict_cities.get(f_1, 0)
                out_all_cities.append(f_1)
                out_dict[int(n_alerts_min <= n_alerts <= n_alerts_max)][f_1] = n_alerts

    out_dict[0] = dict(sorted(out_dict[0].items(), key=lambda item: item[1], reverse=True))
    out_dict[1] = dict(sorted(out_dict[1].items(), key=lambda item: item[1], reverse=True))

    return out_all_cities, out_dict


my_data_tzofer_red = None
my_data_tzofer_red_full = None


def collect_data():
    print(f"collect_data : COLLET {COLLET}")
    global my_data_tzofer_red
    global my_data_tzofer_red_full
    if COLLET:
        from telegram_alarms import collect_data_into_excel  # lazy: telethon is only needed for collection
        collect_data_into_excel(chat_group_name=chat_name_2)
        # collect_data_into_excel(chat_group_name=chat_name_1, collect=True)
        # data_1 = read_my_data(file_name=excel_out_file_1, sheet_name=excel_out_sheet)
        # save_dict(data_dict=data_1, name=pickle_out_file_1)
        # my_data_1 = load_dicts(name=pickle_out_file_1)

        # collect_data_into_excel(chat_group_name=chat_name_2, collect=True)
        my_data_tzofer_red, my_data_tzofer_red_full = read_my_data(file_name=excel_out_file_2,
                                                                   sheet_name=excel_out_sheet)

        # disty, val_dists = create_distribution(full_data=data_2, data_dict_fix=data_2_fix, hours=1, minutes=0)
        save_dict(data_dict=my_data_tzofer_red, name="my_data_tzofer_red.pkl")
        save_dict(data_dict=my_data_tzofer_red_full, name="my_data_tzofer_red_full.pkl")
        # my_data_2 = load_dicts(name=pickle_out_file_2)
    print(f"collect_data : done")


def load_data():
    print(f"load data : my_data_tzofer_red_full.pkl.xlsx")
    global my_data_tzofer_red
    global my_data_tzofer_red_full
    my_data_tzofer_red = load_dict(name="my_data_tzofer_red.pkl")
    my_data_tzofer_red_full = load_dict(name="my_data_tzofer_red_full.pkl")
    print(121)


def get_data():
    return load_dict(name="my_data_tzofer_red_full.pkl")


def get_data_tzofer_red():
    return load_dict(name="my_data_tzofer_red.pkl")


def apply_collect_data():
    collect_data()
    load_data()

    """
    my_data_red_0 = group_by_cities_dates_hours(data_dict=my_data_tzofer_red)
    my_data_red_1 = group_by_zones_dates_hours(data_dict=my_data_tzofer_red)
    my_data_red_2 = group_by_zones_cities_hours(data_dict=my_data_tzofer_red)
    my_data_red_3 = group_by_zones_cities_dates(data_dict=my_data_tzofer_red)
    my_data_red_4 = group_by_dates_hours(data_dict=my_data_tzofer_red)
    my_data_red_5 = group_by_cities_hours(data_dict=my_data_tzofer_red)
    my_data_red_6 = group_by_cities_dates(data_dict=my_data_tzofer_red)
    my_data_red_7 = group_by_zones_hours(data_dict=my_data_tzofer_red)
    my_data_red_8 = group_by_zones_dates(data_dict=my_data_tzofer_red)
    my_data_red_9 = group_by_zones_cities(data_dict=my_data_tzofer_red)
    my_data_red_10 = group_by_hours(data_dict=my_data_tzofer_red)
    """

    my_data_red_11 = group_by_dates(data_dict=my_data_tzofer_red)
    my_data_red_12 = group_by_cities(data_dict=my_data_tzofer_red)
    my_data_red_13 = group_by_zones(data_dict=my_data_tzofer_red)
    my_data_red_14, my_data_red_15 = reduce_days(dict_data=my_data_tzofer_red_full)

    my_data_red_conditional = group_with_condition(data_dict=my_data_tzofer_red, cond_func=condition_func_1)

    my_data_red_16 = [group_fix_with_condition(data_dict=my_data_tzofer_red_full, cond_func=condition_func_1),
                      group_fix_with_condition(data_dict=my_data_tzofer_red_full, cond_func=condition_func_2),
                      group_fix_with_condition(data_dict=my_data_tzofer_red_full, cond_func=condition_func_3),
                      group_fix_with_condition(data_dict=my_data_tzofer_red_full, cond_func=condition_func_4)]

    my_data_red_16_tiltes = ["Shfela zone", "All zones", "Ashkelon cities", "TLV cities"]

    total_alerts = get_total_alerts(data_dict=my_data_tzofer_red)
    all_cities, all_cities_cond_dict = get_all_zones(data_dict_cities=group_by_cities(data_dict=my_data_tzofer_red),
                                                     n_alerts_min=1, n_alerts_max=float("inf"))

    with open("zones.txt", "w") as file:
        file.write(f"cities (total : {len(my_data_red_13)})\n\n")
        file.write("\n".join(list(my_data_red_13.keys())))

    with open("cities.txt", "w") as file:
        file.write(f"cities (total : {len(my_data_red_12)})\n\n")
        file.write("\n".join(list(my_data_red_12.keys())))

    with open("zones_cities.txt", "w") as file:
        for key_zone_0 in my_data_tzofer_red_full.keys():
            file.write(f"\n{key_zone_0} : \n")
            for key_city_0 in my_data_tzofer_red_full[key_zone_0].keys():
                file.write(f"    {key_city_0}\n")

    with open("dates.txt", "w") as file:
        file.write(f"dates (total : {len(my_data_red_11)})\n\n")
        dates = [str(x) for x in my_data_red_11.keys()]
        file.write("\n".join(dates))

    with open("all_cities.txt", "w") as file:
        file.write(f"all cities (total : {len(all_cities)})\n\n")
        file.write("\n".join(all_cities))

    with open("all_cities_with_condition.txt", "w") as file:
        file.write(f"all cities with condition (total : {len(all_cities_cond_dict[1])})\n\n")
        for i_i, city_key in enumerate(all_cities_cond_dict[1].keys(), start=1):
            str_val = all_cities_cond_dict[1][city_key] = f"{i_i}) {city_key} : {all_cities_cond_dict[1][city_key]}\n"
            file.write(str_val)

    with open("all_cities_without_condition.txt", "w") as file:
        file.write(f"all cities without condition (total : {len(all_cities_cond_dict[0])})\n\n")
        for i_i, city_key in enumerate(all_cities_cond_dict[0].keys(), start=1):
            str_val = all_cities_cond_dict[0][city_key] = f"{i_i}) {city_key} : {all_cities_cond_dict[0][city_key]}\n"
            file.write(str_val)

