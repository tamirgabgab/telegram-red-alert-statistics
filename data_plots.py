import os.path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.dates import date2num
from Cdatetime import CustomDateTime, CustomDateHour
from data_stats import *
from matplotlib.colors import LinearSegmentedColormap
from parameters import SHOW, SAVE

directory = "./partial_plots/"

hours_tick = range(0, 24, 2)
minutes_tick = range(0, 60, 5)
tick_fontsize = 8


def add_zeros(time_dict):
    copy_data = deepcopy(time_dict)
    for ho in range(24):
        if ho not in copy_data["hour"].keys():
            copy_data["hour"][ho] = 0
    for mi in range(60):
        if mi not in copy_data["minute"].keys():
            copy_data["minute"][mi] = 0
    copy_data["hour"] = sort_dict(dict_data=copy_data["hour"], kind=0, reverse=False)
    copy_data["minute"] = sort_dict(dict_data=copy_data["minute"], kind=0, reverse=False)
    return copy_data


def get_dates(time_dict):
    all_dates = list(time_dict.keys())
    start_date = min(all_dates)
    end_date = max(all_dates)
    out_data = dict()
    for n in range(int((end_date - start_date).days) + 1):
        current_date = start_date + timedelta(n)
        out_data[current_date] = time_dict.get(current_date, 0)
    out_data = sort_dict(dict_data=out_data, kind=0, reverse=False)
    return out_data


def get_hours(time_dict, interval_minute=10):
    start_date = datetime(year=2020, month=1, day=1, hour=0, minute=0)
    final_date = start_date + timedelta(minutes=10)
    dict_out = dict()
    while start_date.day == 1:
        dict_out[start_date] = 0
        start_date += timedelta(minutes=interval_minute)
        final_date += timedelta(minutes=interval_minute)

    dict_out_keys = list(dict_out.keys())
    for key_hour, val in time_dict.items():
        n = int((60 * key_hour.hour + key_hour.minute) / interval_minute)
        dict_out[dict_out_keys[n]] += val
    return dict_out


def get_2d_histogram(time_dict, dt_h=24, dt_m=60):
    n_hours = 24 // dt_h
    n_minutes = 60 // dt_m
    h_tick = [n * dt_h for n in range(n_hours)]
    m_tick = [n * dt_m for n in range(n_minutes)]
    out_array = np.zeros(shape=(n_hours, n_minutes), dtype=int)

    total = 0
    for key_hour, val in time_dict.items():
        r = int(key_hour.hour / dt_h)
        c = int(key_hour.minute / dt_m)
        out_array[r, c] += val
        total += val
    return out_array, total, h_tick, m_tick


def bar_0_1(kind="zone", num=2, num_dates=3):
    # kind = zone or city
    fig_idx = 0
    my_data_red_0 = group_by_cities_dates_hours(data_dict=get_data_tzofer_red())
    my_data_red_1 = group_by_zones_dates_hours(data_dict=get_data_tzofer_red())
    data_to_plot = my_data_red_1 if kind == "zone" else my_data_red_0
    key_areas = random.sample(list(data_to_plot.keys()), num)
    for key_area in key_areas:
        all_dates = list(data_to_plot[key_area].keys())
        while all_dates:
            next_dates, all_dates = all_dates[:num_dates], all_dates[num_dates:]
            n_dates = len(next_dates)
            fig, ax = plt.subplots(figsize=(10, 8), nrows=2, ncols=n_dates, squeeze=False)
            plt.suptitle(f"{kind} : {key_area[::-1]}", fontsize=16)
            for i, key_date in enumerate(next_dates):
                padded_dict = add_zeros(time_dict=data_to_plot[key_area][key_date])
                h_dict, m_dict = padded_dict["hour"], padded_dict["minute"]
                x_1 = list(h_dict.keys())
                y_1 = list(h_dict.values())
                x_2 = list(m_dict.keys())
                y_2 = list(m_dict.values())

                ax[0, i].bar(x_1, y_1, align="edge")
                ax[0, i].set_title(f"(H) {str(key_date)}")
                ax[0, i].set_xlim([-0.5, len(x_1) - 0.001])
                ax[0, i].set_xticks(hours_tick)
                ax[0, i].set_xticklabels(hours_tick, fontsize=tick_fontsize)
                ax[0, i].set_ylim([0, 1.1 * max(y_1)])
                ax[0, i].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
                ax[0, i].yaxis.set_major_locator(MaxNLocator(integer=True))

                ax[1, i].bar(x_2, y_2, align="edge")
                ax[1, i].set_title(f"(M) {str(key_date)}")
                ax[1, i].set_xlim([-0.5, len(x_2) - 0.001])
                ax[1, i].set_xticks(minutes_tick)
                ax[1, i].set_xticklabels(minutes_tick, fontsize=tick_fontsize)
                ax[1, i].set_ylim([0, 1.1 * max(y_2)])
                ax[1, i].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
                ax[1, i].yaxis.set_major_locator(MaxNLocator(integer=True))

            fig.subplots_adjust(wspace=0.1, hspace=0.3)
            plt.tight_layout()
            if SAVE:
                print(f"save : bar_0_1_{fig_idx}.png")
                plt.savefig(os.path.join(directory, f"bar_0_1_{fig_idx}.png"))
            if SHOW:
                plt.show()
            fig_idx += 1
            plt.close(fig)


def bar_2(num_zones=4, num_cities=3):
    fig_idx = 0
    my_data_red_2 = group_by_zones_cities_hours(data_dict=get_data_tzofer_red())
    key_zones = random.sample(list(my_data_red_2.keys()), num_zones)
    for key_zone in key_zones:
        n_cities_total = len(my_data_red_2[key_zone].keys())
        fig, ax = plt.subplots(figsize=(10, 10), nrows=2, ncols=min(num_cities, n_cities_total), squeeze=False)
        plt.suptitle(f"{key_zone[::-1]}", fontsize=16)
        rand_cities = random.sample(list((my_data_red_2[key_zone].keys())), min(n_cities_total, num_cities))
        for i, key_city in enumerate(rand_cities):
            padded_dict = add_zeros(time_dict=my_data_red_2[key_zone][key_city])
            h_dict, m_dict = padded_dict["hour"], padded_dict["minute"]
            x_1 = list(h_dict.keys())
            y_1 = list(h_dict.values())
            x_2 = list(m_dict.keys())
            y_2 = list(m_dict.values())

            ax[0, i].bar(x_1, y_1, align="edge")
            ax[0, i].set_title(f"(H) {key_city[::-1]}")
            ax[0, i].set_xlim([-0.5, len(x_1) - 0.001])
            ax[0, i].set_xticks(hours_tick)
            ax[0, i].set_xticklabels(hours_tick, fontsize=tick_fontsize)
            ax[0, i].set_ylim([0, 1.1 * max(y_1)])
            ax[0, i].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
            ax[0, i].yaxis.set_major_locator(MaxNLocator(integer=True))
            # for j, v in enumerate(y_1):
            #    ax[0, i].text(x_1[j], v, str(v), ha='center', va='bottom')

            ax[1, i].bar(x_2, y_2, align="edge")
            ax[1, i].set_title(f"(M) {key_city[::-1]}")
            ax[1, i].set_xlim([-0.5, len(x_2) - 0.001])
            ax[1, i].set_xticks(minutes_tick)
            ax[1, i].set_xticklabels(minutes_tick, fontsize=tick_fontsize)
            ax[1, i].set_ylim([0, 1.1 * max(y_2)])
            ax[1, i].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
            ax[1, i].yaxis.set_major_locator(MaxNLocator(integer=True))
            # for j, v in enumerate(y_2):
            #    ax[1, i].text(x_2[j], v, str(v), ha='center', va='bottom')
        fig.subplots_adjust(wspace=0.1, hspace=0.3)
        plt.tight_layout()
        if SAVE:
            print(f"save : bar_2_{fig_idx}.png")
            plt.savefig(os.path.join(directory, f"bar_2_{fig_idx}.png"))
        if SHOW:
            plt.show()
        fig_idx += 1
        plt.close(fig)


def bar_3(num_zones=4, num_cities=4):
    fig_idx = 0
    my_data_red_3 = group_by_zones_cities_dates(data_dict=get_data_tzofer_red())
    key_zones = random.sample(list(my_data_red_3.keys()), num_zones)
    for key_zone in key_zones:
        all_cities = list(my_data_red_3[key_zone].keys())
        while all_cities:
            next_cities, all_cities = all_cities[:num_cities], all_cities[num_cities:]
            n_cities = len(next_cities)
            n_rows = int(np.ceil(np.sqrt(n_cities)))
            n_cols = int(np.ceil(n_cities / n_rows))
            fig, ax = plt.subplots(figsize=(10, 8), nrows=n_rows, ncols=n_cols, squeeze=False)
            plt.suptitle(f"{key_zone[::-1]}", fontsize=16)
            for i, key_city in enumerate(next_cities):
                r = i // n_cols
                c = i % n_cols
                padded_dict = get_dates(time_dict=my_data_red_3[key_zone][key_city])

                x_1 = list(padded_dict.keys())
                y_1 = list(padded_dict.values())

                num_dates = date2num(x_1)

                ax[r, c].bar(x_1, y_1)
                ax[r, c].set_title(f"(D) {key_city[::-1]}")
                ax[r, c].set_xlim([date2num(min(x_1)) - 0.5, date2num(max(x_1)) + 0.5])
                ax[r, c].set_xticks(num_dates)
                ax[r, c].set_xticklabels([date_0.strftime("%d/%m/%Y") for date_0 in x_1], rotation=60, size=6)
                ax[r, c].set_ylim([0, 1.1 * max(y_1)])
                ax[r, c].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
                ax[r, c].yaxis.set_major_locator(MaxNLocator(integer=True))
                for j, v in enumerate(y_1):
                    ax[r, c].text(x_1[j], v, str(v), ha='center', va='bottom')

            for j in range(n_cities, n_rows * n_cols):
                r = j // n_cols
                c = j % n_cols
                ax[r, c].axis("off")
            fig.subplots_adjust(wspace=0.1, hspace=0.3)
            plt.tight_layout()
            if SAVE:
                print(f"save : bar_3_{fig_idx}.png")
                plt.savefig(os.path.join(directory, f"bar_3_{fig_idx}.png"))
            if SHOW:
                plt.show()
            fig_idx += 1
            fig.subplots_adjust(wspace=0.1, hspace=0.3)
            plt.close(fig)


def bar_4(num_dates=3):
    fig_idx = 0
    my_data_red_4 = group_by_dates_hours(data_dict=get_data_tzofer_red())
    all_dates = sorted(list(my_data_red_4.keys()))
    while all_dates:
        rand_dates, all_dates = all_dates[:num_dates], all_dates[num_dates:]
        fig, ax = plt.subplots(figsize=(10, 8), nrows=2, ncols=len(rand_dates), squeeze=False)
        plt.suptitle(f"Dates", fontsize=16)
        for i, key_date in enumerate(rand_dates):
            padded_dict = add_zeros(time_dict=my_data_red_4[key_date])
            h_dict, m_dict = padded_dict["hour"], padded_dict["minute"]
            x_1 = list(h_dict.keys())
            y_1 = list(h_dict.values())
            x_2 = list(m_dict.keys())
            y_2 = list(m_dict.values())

            ax[0, i].bar(x_1, y_1, align="edge")
            ax[0, i].set_title(f"(H) {key_date}")
            ax[0, i].set_xlim([-0.5, len(x_1) - 0.001])
            ax[0, i].set_xticks(hours_tick)
            ax[0, i].set_xticklabels(hours_tick, fontsize=tick_fontsize)
            ax[0, i].set_ylim([0, 1.1 * max(y_1)])
            ax[0, i].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
            ax[0, i].yaxis.set_major_locator(MaxNLocator(integer=True))
            # for j, v in enumerate(y_1):
            #    ax[0, i].text(x_1[j], v, str(v), ha='center', va='bottom')

            ax[1, i].bar(x_2, y_2, align="edge")
            ax[1, i].set_title(f"(M) {key_date}")
            ax[1, i].set_xlim([-0.5, len(x_2) - 0.001])
            ax[1, i].set_xticks(minutes_tick)
            ax[1, i].set_xticklabels(minutes_tick, fontsize=tick_fontsize)
            ax[1, i].set_ylim([0, 1.1 * max(y_2)])
            ax[1, i].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
            ax[1, i].yaxis.set_major_locator(MaxNLocator(integer=True))
            # for j, v in enumerate(y_2):
            #    ax[1, i].text(x_2[j], v, str(v), ha='center', va='bottom')
        fig.subplots_adjust(wspace=0.1, hspace=0.3)
        plt.tight_layout()
        if SAVE:
            print(f"save : bar_4_{fig_idx}.png")
            plt.savefig(os.path.join(directory, f"bar_4_{fig_idx}.png"))
        if SHOW:
            plt.show()
        fig_idx += 1
        plt.close(fig)


def bar_5_7(kind="zone", num=3, n_repeat=4):
    fig_idx = 0
    my_data_red_5 = group_by_cities_hours(data_dict=get_data_tzofer_red())
    my_data_red_7 = group_by_zones_hours(data_dict=get_data_tzofer_red())
    # kind = zone or city
    data_to_plot = my_data_red_7 if kind == "zone" else my_data_red_5
    all_areas = list(data_to_plot.keys())
    random.shuffle(all_areas)
    n = 0
    while all_areas and n < n_repeat:
        rand_ares, all_areas = all_areas[:num], all_areas[num:]
        fig, ax = plt.subplots(figsize=(10, 8), nrows=2, ncols=len(rand_ares), squeeze=False)
        plt.suptitle(f"{kind}", fontsize=16)
        for i, key_city in enumerate(rand_ares):
            padded_dict = add_zeros(time_dict=data_to_plot[key_city])
            h_dict, m_dict = padded_dict["hour"], padded_dict["minute"]

            x_1 = list(h_dict.keys())
            y_1 = list(h_dict.values())
            x_2 = list(m_dict.keys())
            y_2 = list(m_dict.values())

            ax[0, i].bar(x_1, y_1, align="edge")
            ax[0, i].set_title(f"(H) {key_city[::-1]}")
            ax[0, i].set_xlim([-0.5, len(x_1) - 0.001])
            ax[0, i].set_xticks(hours_tick)
            ax[0, i].set_xticklabels(hours_tick, fontsize=tick_fontsize)
            ax[0, i].set_ylim([0, 1.1 * max(y_1)])
            ax[0, i].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
            ax[0, i].yaxis.set_major_locator(MaxNLocator(integer=True))
            # for j, v in enumerate(y_1):
            #    ax[0, i].text(x_1[j], v, str(v), ha='center', va='bottom')

            ax[1, i].bar(x_2, y_2, align="edge")
            ax[1, i].set_title(f"(M) {key_city[::-1]}")
            ax[1, i].set_xlim([-0.5, len(x_2) - 0.001])
            ax[1, i].set_xticks(minutes_tick)
            ax[1, i].set_xticklabels(minutes_tick, fontsize=tick_fontsize)
            ax[1, i].set_ylim([0, 1.1 * max(y_2)])
            ax[1, i].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
            ax[1, i].yaxis.set_major_locator(MaxNLocator(integer=True))
            # for j, v in enumerate(y_2):
            #    ax[1, i].text(x_2[j], v, str(v), ha='center', va='bottom')
        fig.subplots_adjust(wspace=0.1, hspace=0.3)
        plt.tight_layout()
        if SAVE:
            print(f"save : bar_5_7_{fig_idx}.png")
            plt.savefig(os.path.join(directory, f"bar_5_7_{fig_idx}.png"))
        if SHOW:
            plt.show()
        fig_idx += 1
        n += 1
        plt.close(fig)


def bar_6_8(kind="zone", num=4, n_repeat=3):
    fig_idx = 0
    my_data_red_6 = group_by_cities_dates(data_dict=get_data_tzofer_red())
    my_data_red_8 = group_by_zones_dates(data_dict=get_data_tzofer_red())
    # kind = zone or city
    data_to_plot = my_data_red_8 if kind == "zone" else my_data_red_6
    all_areas = list(data_to_plot.keys())
    random.shuffle(all_areas)
    n = 0
    while all_areas and n < n_repeat:
        next_ares, all_areas = all_areas[:num], all_areas[num:]
        n_areas = len(next_ares)
        n_rows = int(np.ceil(np.sqrt(n_areas)))
        n_cols = int(np.ceil(n_areas / n_rows))
        fig, ax = plt.subplots(figsize=(10, 8), nrows=n_rows, ncols=n_cols, squeeze=False)
        plt.suptitle(f"{kind}", fontsize=16)
        for i, key_city in enumerate(next_ares):
            r = i // n_cols
            c = i % n_cols
            padded_dict = get_dates(time_dict=data_to_plot[key_city])

            x_1 = list(padded_dict.keys())
            y_1 = list(padded_dict.values())

            num_dates = date2num(x_1)

            ax[r, c].bar(x_1, y_1)
            ax[r, c].set_title(f"(D) {key_city[::-1]}")
            ax[r, c].set_xlim([date2num(min(x_1)) - 0.5, date2num(max(x_1)) + 0.5])
            ax[r, c].set_xticks(num_dates)
            ax[r, c].set_xticklabels([date_0.strftime("%d/%m/%Y") for date_0 in x_1], rotation=60, size=6)
            ax[r, c].set_ylim([0, max(1.1 * max(y_1), 1)])
            ax[r, c].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
            ax[r, c].yaxis.set_major_locator(MaxNLocator(integer=True))
            for j, v in enumerate(y_1):
                ax[r, c].text(x_1[j], v, str(v), ha='center', va='bottom')
        for j in range(n_areas, n_rows * n_cols):
            r = j // n_cols
            c = j % n_cols
            ax[r, c].axis("off")
        fig.subplots_adjust(wspace=0.1, hspace=0.3)
        plt.tight_layout()
        if SAVE:
            print(f"save : bar_6_8_{fig_idx}.png")
            plt.savefig(os.path.join(directory, f"bar_6_8_{fig_idx}.png"))
        if SHOW:
            plt.show()
        fig_idx += 1
        fig.subplots_adjust(wspace=0.1, hspace=0.3)
        plt.close(fig)
        n += 1


def bar_9(num_zones=3, num_cities=40):
    fig_idx = 0
    my_data_red_9 = group_by_zones_cities(data_dict=get_data_tzofer_red())
    rand_zones = random.sample(list(my_data_red_9.keys()), num_zones)
    for key_zone in rand_zones:
        all_cities = list(my_data_red_9[key_zone].keys())
        while all_cities:
            next_cities, all_cities = all_cities[:num_cities], all_cities[num_cities:]
            fig, ax = plt.subplots(figsize=(10, 8), nrows=1, ncols=1, squeeze=False)

            tmp = {ct: my_data_red_9[key_zone][ct] for ct in next_cities}

            x_1 = [f"({str(tmp[q_0])}) {q_0[::-1]}" for q_0 in list(tmp.keys())[::-1]]
            y_1 = list(tmp.values())[::-1]

            ax[0, 0].barh(x_1, y_1)
            ax[0, 0].set_title(f"{key_zone[::-1]}")
            ax[0, 0].set_ylim([-0.5, len(x_1) - 0.5])
            ax[0, 0].grid(True, axis='x', which='both', linestyle='--', linewidth=0.5)
            ax[0, 0].xaxis.set_major_locator(MaxNLocator(integer=True))
            plt.tight_layout()
            if SAVE:
                print(f"save : bar_9_{fig_idx}.png")
                plt.savefig(os.path.join(directory, f"bar_9_{fig_idx}.png"))
            if SHOW:
                plt.show()
            fig_idx += 1
            plt.close(fig)


def bar_10(kind="normal"):
    fig_idx = 0
    my_data_red_10 = group_by_hours(data_dict=get_data_tzofer_red())
    my_data_red_conditional = group_with_condition(data_dict=get_data_tzofer_red(), cond_func=condition_func_1)
    data_to_plot = my_data_red_10 if kind == "normal" else my_data_red_conditional
    fig, ax = plt.subplots(figsize=(10, 8), nrows=2, ncols=1, squeeze=False)

    padded_dict = add_zeros(time_dict=data_to_plot)
    h_dict, m_dict = padded_dict["hour"], padded_dict["minute"]

    plt.suptitle(f"{kind}", fontsize=16)

    x_1 = list(h_dict.keys())
    y_1 = list(h_dict.values())
    x_2 = list(m_dict.keys())
    y_2 = list(m_dict.values())

    ax[0, 0].bar(x_1, y_1, align="edge")
    ax[0, 0].set_title("Hours")
    ax[0, 0].set_xlim([-0.5, len(x_1) - 0.001])
    ax[0, 0].set_xticks(hours_tick)
    ax[0, 0].set_xticklabels(hours_tick, fontsize=tick_fontsize)
    ax[0, 0].set_ylim([0, 1.1 * max(y_1)])
    ax[0, 0].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
    ax[0, 0].yaxis.set_major_locator(MaxNLocator(integer=True))

    ax[1, 0].bar(x_2, y_2, align="edge")
    ax[1, 0].set_title("Minutes")
    ax[1, 0].set_xlim([-0.5, len(x_2) - 0.001])
    ax[1, 0].set_xticks(minutes_tick)
    ax[1, 0].set_xticklabels(minutes_tick, fontsize=tick_fontsize)
    ax[1, 0].set_ylim([0, 1.1 * max(y_2)])
    ax[1, 0].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
    ax[1, 0].yaxis.set_major_locator(MaxNLocator(integer=True))

    plt.tight_layout()
    if SAVE:
        print(f"save : bar_10(kind={kind})_{fig_idx}.png")
        plt.savefig(os.path.join(directory, f"bar_10(kind={kind})_{fig_idx}.png"))
    if SHOW:
        plt.show()
    fig_idx += 1
    plt.close(fig)


def bar_11():
    my_data_red_11 = group_by_dates(data_dict=get_data_tzofer_red())
    fig, ax = plt.subplots(figsize=(10, 8), nrows=1, ncols=1, squeeze=False)

    padded_dict = get_dates(time_dict=my_data_red_11)

    x_1 = list(padded_dict.keys())
    y_1 = list(padded_dict.values())

    num_dates = date2num(x_1)

    ax[0, 0].bar(x_1, y_1)
    ax[0, 0].set_title("Days")
    ax[0, 0].set_xlim([date2num(min(x_1)) - 0.5, date2num(max(x_1)) + 0.5])
    ax[0, 0].set_xticks(num_dates)
    ax[0, 0].set_xticklabels([date_0.strftime("%d/%m/%Y") for date_0 in x_1], rotation=45, size=8)
    ax[0, 0].set_ylim([0, max(1.1 * max(y_1), 1)])
    ax[0, 0].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
    ax[0, 0].yaxis.set_major_locator(MaxNLocator(integer=True))

    for x_t, y_t in zip(x_1, y_1):
        ax[0, 0].text(x_t, y_t + 50, str(y_t), ha='center', va='center', size=12)
    plt.tight_layout()
    if SAVE:
        print(f"save : bar_11_0.png")
        plt.savefig(os.path.join(directory, f"bar_11_0.png"))
    if SHOW:
        plt.show()
    plt.close(fig)


def bar_12(num_cities=50):
    fig_idx = 0
    my_data_red_12 = group_by_cities(data_dict=get_data_tzofer_red())
    all_cities = list(my_data_red_12.keys())
    while all_cities:
        next_cities, all_cities = all_cities[:num_cities], all_cities[num_cities:]
        fig, ax = plt.subplots(figsize=(10, 8), nrows=1, ncols=1, squeeze=False)

        x_1 = [f"({str(my_data_red_12[q_0])}) {q_0[::-1]}" for q_0 in next_cities[::-1]]
        y_1 = [my_data_red_12[ct] for ct in next_cities][::-1]

        ax[0, 0].barh(x_1, y_1)
        ax[0, 0].set_title(f"Cities")
        ax[0, 0].set_xlim([0, max(1.1 * max(y_1), 1)])
        ax[0, 0].set_ylim([-0.5, len(y_1) - 0.5])
        ax[0, 0].set_yticks(x_1)
        ax[0, 0].grid(True, axis='x', which='both', linestyle='--', linewidth=0.5)
        ax[0, 0].xaxis.set_major_locator(MaxNLocator(integer=True))
        plt.tight_layout()
        if SAVE:
            print(f"save : bar_12_{fig_idx}.png")
            plt.savefig(os.path.join(directory, f"bar_12_{fig_idx}.png"))
        if SHOW:
            plt.show()
        fig_idx += 1
        plt.close(fig)


def bar_13():
    my_data_red_13 = group_by_zones(data_dict=get_data_tzofer_red())
    fig, ax = plt.subplots(figsize=(10, 8), nrows=1, ncols=1, squeeze=False)

    x_1 = [f"({str(my_data_red_13[q_0])}) {q_0[::-1]}" for q_0 in list(my_data_red_13.keys())[::-1]]
    y_1 = list(my_data_red_13.values())[::-1]

    ax[0, 0].barh(x_1, y_1)
    ax[0, 0].set_title(f"Zones")
    ax[0, 0].set_xlim([0, max(1.1 * max(y_1), 1)])
    ax[0, 0].set_ylim([-0.5, len(y_1) - 0.5])
    ax[0, 0].set_yticks(x_1)
    ax[0, 0].grid(True, axis='x', which='both', linestyle='--', linewidth=0.5)
    ax[0, 0].xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.tight_layout()
    if SAVE:
        plt.savefig(os.path.join(directory, f"bar_13_0.png"))
    if SHOW:
        plt.show()
    plt.close(fig)


def bar_14(num_zones=3, num_cities=4, n_repeat=3):
    fig_idx = 0
    my_data_red_14, my_data_red_15 = reduce_days(dict_data=get_data())
    rand_zones = random.sample(list(my_data_red_14.keys()), num_zones)
    for key_zone in rand_zones:
        all_cities = list(my_data_red_14[key_zone].keys())
        random.shuffle(all_cities)
        n = 0
        while all_cities and n < n_repeat:
            next_cities, all_cities = all_cities[:num_cities], all_cities[num_cities:]
            n_cities = len(next_cities)
            n_rows = int(np.ceil(np.sqrt(n_cities)))
            n_cols = int(np.ceil(n_cities / n_rows))
            fig, ax = plt.subplots(figsize=(10, 8), nrows=n_rows, ncols=n_cols, squeeze=False)
            plt.suptitle(f"zone : {key_zone[::-1]}")
            for i, key_city in enumerate(next_cities):
                r = i // n_cols
                c = i % n_cols
                padded_dict = get_hours(time_dict=my_data_red_14[key_zone][key_city], interval_minute=10)

                x_dates = list(padded_dict.keys())
                x_1 = list(range(len(padded_dict)))
                y_1 = list(padded_dict.values())

                ax[r, c].bar(x_1, y_1, align="edge")
                ax[r, c].set_title(f"{key_city[::-1]}")
                ax[r, c].set_xlim([-0.5, len(x_1) + 0.5])

                ax[r, c].set_xticks([x_1[m] for m in range(0, len(x_1), 6)])
                ax[r, c].set_xticklabels([x_dates[m].strftime("%H:%M")
                                          for m in range(0, len(x_dates), 6)], rotation=90, size=6)
                if len(y_1) > 0 and max(y_1) > 0:
                    ax[r, c].set_ylim([0, max(1.1 * max(y_1), 1)])
                else:
                    ax[r, c].set_ylim([0, 1])
                ax[r, c].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
                ax[r, c].yaxis.set_major_locator(MaxNLocator(integer=True))

            for j in range(n_cities, n_rows * n_cols):
                r = j // n_cols
                c = j % n_cols
                ax[r, c].axis("off")
            fig.subplots_adjust(wspace=0.1, hspace=0.3)
            plt.tight_layout()
            if SAVE:
                print(f"save : bar_14_{fig_idx}.png")
                plt.savefig(os.path.join(directory, f"bar_14_{fig_idx}.png"))
            if SHOW:
                plt.show()
            fig_idx += 1
            n += 1
            plt.close(fig)


def bar_15(num_zones=2, interval_minute=10):
    fig_idx = 0
    my_data_red_14, my_data_red_15 = reduce_days(dict_data=get_data())
    all_zones = list(my_data_red_15.keys())
    dt = max(60 // interval_minute, 1)
    while all_zones:
        next_zones, all_zones = all_zones[:num_zones], all_zones[num_zones:]
        n_zones = len(next_zones)
        n_rows = int(np.ceil(np.sqrt(n_zones)))
        n_cols = int(np.ceil(n_zones / n_rows))
        fig, ax = plt.subplots(figsize=(10, 8), nrows=n_rows, ncols=n_cols, squeeze=False)
        plt.suptitle(f"Zones")
        for i, key_zone in enumerate(next_zones):
            r = i // n_cols
            c = i % n_cols

            padded_dict = get_hours(time_dict=my_data_red_15[key_zone], interval_minute=interval_minute)

            x_dates = list(padded_dict.keys())
            x_1 = list(range(len(padded_dict)))
            y_1 = list(padded_dict.values())

            ax[r, c].bar(x_1, y_1, align="edge")
            ax[r, c].set_title(f"{key_zone[::-1]}")
            ax[r, c].set_xlim([-0.5, len(x_1) - 0.001])

            ax[r, c].set_xticks([x_1[m] for m in range(0, len(x_1), dt)])
            ax[r, c].set_xticklabels([x_dates[m].strftime("%H:%M")
                                      for m in range(0, len(x_dates), dt)], rotation=90, size=6)
            if len(y_1) > 0 and max(y_1) > 0:
                ax[r, c].set_ylim([0, max(1.1 * max(y_1), 1)])
            else:
                ax[r, c].set_ylim([0, 1])
            ax[r, c].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
            ax[r, c].yaxis.set_major_locator(MaxNLocator(integer=True))

        for j in range(n_zones, n_rows * n_cols):
            r = j // n_cols
            c = j % n_cols
            ax[r, c].axis("off")
        fig.subplots_adjust(wspace=0.1, hspace=0.3)
        plt.tight_layout()
        if SAVE:
            print(f"save : bar_15_{fig_idx}.png")
            plt.savefig(os.path.join(directory, f"bar_15_{fig_idx}.png"))
        if SHOW:
            plt.show()
        fig_idx += 1
        plt.close(fig)


def bar_16_general(data, titles, interval_minute=10, show=True):
    fig_idx = 0
    dt = max(60 // interval_minute, 1)
    if len(titles) != len(data):
        print(f"ILVALID text param, len(text) = {len(titles)}, len(my_data_red_16) = {len(data)}")
        titles = ["" for _ in data]
    for text, data_to_plot in zip(titles, data):
        fig, ax = plt.subplots(figsize=(10, 8), nrows=1, ncols=1, squeeze=False)
        padded_dict = get_hours(time_dict=data_to_plot, interval_minute=interval_minute)
        text += f", total alerts : {sum(padded_dict.values())}"
        x_dates = list(padded_dict.keys())
        x_1 = list(range(len(padded_dict)))
        y_1 = list(padded_dict.values())

        ax[0, 0].bar(x_1, y_1, align="edge")
        ax[0, 0].set_title(text)
        ax[0, 0].set_xlim([-0.5, len(x_1) - 0.001])
        ax[0, 0].set_xticks([x_1[m] for m in range(0, len(x_1), dt)])
        ax[0, 0].set_xticklabels([x_dates[m].strftime("%H:%M")
                                  for m in range(0, len(x_dates), dt)], rotation=90, size=6)
        if len(y_1) > 0 and max(y_1) > 0:
            ax[0, 0].set_ylim([0, max(1.1 * max(y_1), 1)])
        else:
            ax[0, 0].set_ylim([0, 1])
        ax[0, 0].grid(True, axis='y', which='both', linestyle='--', linewidth=0.5)
        ax[0, 0].yaxis.set_major_locator(MaxNLocator(integer=True))
        fig.subplots_adjust(wspace=0.1, hspace=0.3)
        plt.tight_layout()
        if SAVE:
            print(f"save : bar_16_{fig_idx}.png")
            plt.savefig(os.path.join(directory, f"bar_16_{fig_idx}.png"))
        if show:
            plt.show()
        plt.close(fig)
        fig_idx += 1


def bar_16(interval_minute=10, show=SHOW):
    my_data_red_16 = [group_fix_with_condition(data_dict=get_data(), cond_func=condition_func_1),
                      group_fix_with_condition(data_dict=get_data(), cond_func=condition_func_2),
                      group_fix_with_condition(data_dict=get_data(), cond_func=condition_func_3),
                      group_fix_with_condition(data_dict=get_data(), cond_func=condition_func_4)]
    my_data_red_16_tiltes = ["Shfela zone", "All zones", "Ashkelon cities", "TLV cities"]
    bar_16_general(data=my_data_red_16, titles=my_data_red_16_tiltes, interval_minute=interval_minute, show=show)


def get_my_seq(arr, n_1, thr=0.1):
    # n_1 >= 2
    val_max = arr.max()
    dn = 0
    while True:
        if (val_max / (n_1 - 1 - dn)) % 1 < thr:
            return np.linspace(start=0, stop=val_max, num=n_1 - dn, endpoint=True, dtype=int)
        if (val_max / (n_1 - 1 + dn)) % 1 < thr:
            return np.linspace(start=0, stop=val_max, num=n_1 + dn, endpoint=True, dtype=int)
        dn += 1


def credt_count_dict(data, dt_h=1, dt_m=5):
    count_dict = {}
    for i in range(0, 24, dt_h):
        for j in range(0, 60, dt_m):
            new_date = datetime(year=1900, month=1, day=1, hour=i, minute=j)
            count_dict[new_date] = 0
    for key, val in data.items():
        curr_hour = dt_h * int(key.hour / dt_h)
        curr_min = dt_m * int(key.minute / dt_m)
        curr_date = datetime(year=1900, month=1, day=1, hour=curr_hour, minute=curr_min)
        count_dict[curr_date] += val

    return count_dict


def bar_16_color_general(data, titles, dt_h=1, dt_m=5, show=True):
    # dt_h = [1, 2, 3, 4, 6, 8, 12, 24] (must divie 24)
    # dt_m = [1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60] (must divie 60)
    fig_idx = 0
    if len(titles) != len(data):
        print(f"ILVALID text param, len(text) = {len(titles)}, len(my_data_red_16) = {len(data)}")
        titles = ["" for _ in data]
    for text, data_to_plot in zip(titles, data):
        fig, ax = plt.subplots(figsize=(12, 8), nrows=1, ncols=1, squeeze=False)
        padded_array, total, y_tick, x_tick = get_2d_histogram(time_dict=data_to_plot, dt_h=dt_h, dt_m=dt_m)
        text_plot = text + f", total alerts : {total}"
        txt_file_name = text.replace(" ", "_")
        extent = [0, len(x_tick), len(y_tick), 0]

        plasma = plt.cm.get_cmap('plasma')
        new_colors = plasma(np.linspace(0, 1, 256))
        new_colors[0] = [0, 0, 0, 1]
        cmap = LinearSegmentedColormap.from_list('custom_plasma', new_colors)

        im = ax[0, 0].imshow(padded_array, cmap=cmap, interpolation='none', aspect='auto',
                             extent=extent, vmin=0, vmax=padded_array.max())
        cbar = fig.colorbar(im, cax=fig.add_axes([0.94, 0.15, 0.02, 0.7]), orientation='vertical')
        cbar.set_ticks(get_my_seq(arr=padded_array, n_1=10, thr=0.1))

        cbar.update_ticks()
        ax[0, 0].set_title(text_plot)
        ax[0, 0].set_xticks(range(len(x_tick)))
        ax[0, 0].set_xticklabels(x_tick, size=min(dt_m / 10 + 7.5, 10))
        ax[0, 0].set_xlabel("Minute", fontweight='bold')
        ax[0, 0].set_yticks(range(len(y_tick)))
        ax[0, 0].set_yticklabels(y_tick, size=10)
        ax[0, 0].set_ylabel("Hour", fontweight='bold')
        ax[0, 0].grid(True, color='white', linestyle=':', linewidth=0.5)

        fig.subplots_adjust(top=0.90, bottom=0.05, left=0.05, right=0.90)

        annotation = ax[0, 0].annotate(text='', xy=(0, 0), xytext=(6, 12), fontsize=10, ha='left', va='bottom',
                                       textcoords='offset points',
                                       bbox={'boxstyle': 'round', 'fc': 'w'})

        def motion_hover(event):
            # contains, _ = im.contains(event)
            # annotation.set_visible(contains)
            annotation.set_visible(True)

            if event.inaxes == ax[0, 0]:
                x_ann, y_ann = int(event.xdata), int(event.ydata)

                if x_ann < 0 or y_ann < 0 or x_ann >= 60 / dt_m or y_ann >= 24 / dt_h:
                    return

                new_text = f"Times  = "
                for dd_hh in range(dt_h):
                    minute_hv = dt_m * x_ann
                    hour_hv = (dt_h * y_ann + dd_hh) % 24

                    minute_hv_next = (dt_m * x_ann + dt_m) % 60
                    hour_hv_next = (dt_h * y_ann + (dt_m * x_ann + dt_m) // 60 + dd_hh) % 24
                    new_text += f"{hour_hv:02d}:{minute_hv:02d} - {hour_hv_next:02d}:{minute_hv_next:02d}\n"
                    new_text += 15 * " "

                data_z = padded_array[y_ann, x_ann]
                new_text = new_text[:-15]
                new_text += f"Alerts  = {data_z}"
                # annotation.xy = (x_ann, y_ann)
                annotation.set_text(new_text)

            fig.canvas.draw_idle()

        if SAVE:
            print("save file : " + os.path.join(directory, f"{txt_file_name}_plot_{fig_idx}.png"))
            plt.savefig(os.path.join(directory, f"{txt_file_name}_plot_{fig_idx}.png"), bbox_inches='tight')
        if show:
            fig.canvas.mpl_connect('motion_notify_event', motion_hover)
            plt.show()
        plt.close(fig)

        file_text = f"{text}, dt_h = {dt_h}, dt_m = {dt_m} \n\n"

        alla_dict = credt_count_dict(data=data_to_plot, dt_h=dt_h, dt_m=dt_m)

        alla_dict = dict(sorted(alla_dict.items(), key=lambda z: z[1], reverse=True))
        for i, (key, val) in enumerate(alla_dict.items(), start=1):
            file_text += f"{i:<4} {key.hour:02d}:{key.minute:02d} : {val}\n"

        print("save file : " + os.path.join(directory, f"{txt_file_name}.txt"))
        with open(os.path.join(directory, f"{txt_file_name}.txt"), "w") as file:
            file.write(file_text)
        fig_idx += 1


def bar_16_color(dt_h=1, dt_m=5, show=SHOW):
    my_data_red_16 = [group_fix_with_condition(data_dict=get_data(), cond_func=condition_func_1),
                      group_fix_with_condition(data_dict=get_data(), cond_func=condition_func_2),
                      group_fix_with_condition(data_dict=get_data(), cond_func=condition_func_3),
                      group_fix_with_condition(data_dict=get_data(), cond_func=condition_func_4)]

    my_data_red_16_tiltes = ["Shfela zone", "All zones", "Ashkelon cities", "TLV cities"]
    bar_16_color_general(data=my_data_red_16, titles=my_data_red_16_tiltes, dt_h=dt_h, dt_m=dt_m, show=show)


def make_plots(plt_properties):
    print("Making plots...\n")
    for prop in plt_properties:
        func, kwargs = prop["func"], prop.get("kwargs", dict())
        print(f"runnig...\n"
              f"function : {func}\n"
              f"kwargs   : {kwargs}\n")
        func(**kwargs)
