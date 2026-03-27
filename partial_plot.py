from Cdatetime import CustomDateTime, CustomDateHour
from data_plots import *
from coditions import *


# from data_stats import CustomDateTime


def create_args(prop_data):
    data = []
    titles = []
    for prop in prop_data:
        func = prop.get("condition", no_condition)
        data.append(group_fix_with_condition(data_dict=get_data(), cond_func=func))
        titles.append(prop.get("title", "untitled"))
    return data, titles


def plot_16(prop_16, interval_minute=15, show=True):
    data, titles = create_args(prop_data=prop_16)
    bar_16_general(data=data, titles=titles, interval_minute=interval_minute, show=show)


def plot_16_color(prop_16_color, dt_h=1, dt_m=5, show=True):
    data, titles = create_args(prop_data=prop_16_color)
    bar_16_color_general(data=data, titles=titles, dt_h=dt_h, dt_m=dt_m, show=show)


properties = [{"func": bar_0_1, "kwargs": {"kind": "zone", "num": 3, "num_dates": 4}},
              {"func": bar_2, "kwargs": {"num_zones": 3, "num_cities": 3}},
              {"func": bar_3, "kwargs": {"num_zones": 1, "num_cities": 4}},
              {"func": bar_5_7, "kwargs": {"kind": "zone", "num": 3, "n_repeat": 2}},
              {"func": bar_6_8, "kwargs": {"kind": "zone", "num": 4}},
              {"func": bar_6_8, "kwargs": {"kind": "city", "num": 4, "n_repeat": 5}},
              {"func": bar_9, "kwargs": {"num_zones": 4, "num_cities": 20}},
              {"func": bar_10, "kwargs": {"kind": "normal"}},
              {"func": bar_10, "kwargs": {"kind": "conditional"}},
              {"func": bar_11},
              {"func": bar_12, "kwargs": {"num_cities": 40}},
              {"func": bar_13},
              {"func": bar_14, "kwargs": {"num_zones": 3, "num_cities": 4, "n_repeat": 3}},
              {"func": bar_15, "kwargs": {"num_zones": 2, "interval_minute": 10}},
              {"func": bar_16, "kwargs": {"interval_minute": 10}},
              {"func": bar_16_color, "kwargs": {"dt_h": 1, "dt_m": 5}}]
# {"func": bar_4, "kwargs": {"num_dates": 4}},
# {"func": bar_16, "kwargs": {"interval_minute": 10}
# {"func": bar_16_color, "kwargs": {"dt_h": 1, "dt_m": 5}}
properties_16 = [{"condition": condition_func_5, "title": "Ashkelon"},
                 {"condition": condition_func_10, "title": "Rishon"},
                 {"condition": condition_func_6, "title": "TLV"},
                 {"condition": condition_func_7, "title": "My friends"},
                 {"condition": condition_func_8, "title": "Close to Gaza"},
                 {"condition": condition_func_9, "title": "start with א"},
                 {"condition": no_condition, "title": "all"}]

properties_16_general = [{"condition": condition_func_5, "title": "Ashkelon Alerts"},
                         {"condition": condition_func_10, "title": "Haifa Alerts"},
                         {"condition": condition_func_6, "title": "Tel-Aviv Alerts"},
                         {"condition": condition_func_8, "title": "Close to Gaza Alerts"},
                         {"condition": condition_func_north, "title": "Tzafon Alerts"},
                         {"condition": condition_func_center, "title": "Merkaz Alerts"},
                         {"condition": condition_func_south, "title": "Darom Alerts"},
                         {"condition": no_condition, "title": "all Alerts"}]

properties_18_general = [{"condition": no_condition, "title": "all Alerts"},
                         {"condition": condition_func_any_ashkelon, "title": "any ashkelon Alerts"},
                         {"condition": condition_func_my_ashkelon, "title": "Ashkelon north Alerts"},
                         {"condition": condition_func_any_rishon, "title": "any rishon Alerts"},
                         {"condition": condition_func_my_location, "title": "Rishon west Alerts"},
                         {"condition": condition_func_any_natanya, "title": "any natanya Alerts"},
                         {"condition": condition_func_my_natanya, "title": "Natanya west Alerts"}]

if STATISTICS:
    apply_collect_data()
if EXTRA_STATISTICS:
    make_plots(plt_properties=properties)
# plot_16(prop_16=properties_16, interval_minute=10, show=True)
# dt_h must divide 24 and dt_m must divide 60
# dt_h = [1, 2, 3, 4, 6, 8, 12, 24] (must divie 24)
# dt_m = [1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60] (must divie 60)
# plot_16_color(prop_16_color=properties_16_general, dt_h=1, dt_m=60, show=SHOW)
plot_16_color(prop_16_color=properties_18_general, dt_h=1, dt_m=30, show=SHOW)
