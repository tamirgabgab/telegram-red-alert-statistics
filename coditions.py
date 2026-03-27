from datetime import datetime


def no_condition(zone, city, date):
    return True


def condition_func_1(zone, city, date):
    return any(elem in zone for elem in ["השפל"]) and date >= datetime(year=2023, month=10, day=7)


def condition_func_2(zone, city, date):
    return True


def condition_func_3(zone, city, date):
    return "אשקלון" in city and date >= datetime(year=2023, month=10, day=7)


def condition_func_4(zone, city, date):
    return "תל אביב" in city and date >= datetime(year=2023, month=10, day=7)


def condition_func_5(zone, city, date):
    return any(elem in city for elem in ["אשקלון - צפון"])


def condition_func_6(zone, city, date):
    return "תל אביב" in city


def condition_func_7(zone, city, date):
    my_cities = ["אשקלון", "תל אביב", "באר שבע", "אשדוד", "רחובות", "ירושלים", "באר גנים", "מבקיעים"]
    return date >= datetime(year=2023, month=10, day=8) and any(elem in city for elem in my_cities)


def condition_func_8(zone, city, date):
    return date >= datetime(year=2023, month=10, day=8) and any(elem in zone for elem in ["עוטף עזה", "קו העימות"])


def condition_func_9(zone, city, date):
    return city.startswith("א")


def condition_func_10(zone, city, date):
    return city.startswith("חיפה")


def condition_func_11(zone, city, date):
    return city.startswith("ירושלים")


def condition_func_12(zone, city, date):
    return city.startswith("באקה אל גרבייה")


def condition_func_north(zone, city, date):
    return zone in ["מנשה", "גליל עליון", "גליל תחתון", "מרכז הגליל", "עמק בית שאן", "העמקים",
                    "צפון הגולן", "דרום הגולן", "המפרץ", "הכרמל", "ואדי ערה", "קו העימות"]


def condition_func_south(zone, city, date):
    return zone in ["אילת", "דרום הנגב", "מרכז הנגב", "מערב הנגב", "עוטף עזה", "הערבה",
                    "ים המלח", "יהודה", "בקעה", "לכיש", "מערב לכיש"]


def condition_func_center(zone, city, date):
    return zone in ["ירושלים", "ירקון", "השפלה", "השרון", "דן", "שומרון", "שפלת יהודה"]


def condition_func_any_ashkelon(zone, city, date):
    return any(elem in city for elem in ["אשקלון"])


def condition_func_my_ashkelon(zone, city, date):
    return any(elem in city for elem in ["אשקלון - צפון"])


def condition_func_any_rishon(zone, city, date):
    return any(elem in city for elem in ["ראשון לציון"])


def condition_func_my_location(zone, city, date):
    return any(elem in city for elem in ["ראשון לציון - מערב"])


def condition_func_any_natanya(zone, city, date):
    return any(elem in city for elem in ["נתניה"])


def condition_func_my_natanya(zone, city, date):
    return any(elem in city for elem in ["נתניה - מערב"])


def condition_func_baka(zone, city, date):
    return any(elem in city for elem in ["באקה אל גרבייה"])
