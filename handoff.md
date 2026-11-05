# Handoff — מצב הפרויקט ואיך להמשיך

> עודכן לאחרונה: 2026-11-05
> הנחיות העבודה הקבועות נמצאות ב-[`CLAUDE.md`](CLAUDE.md).

---

## 1. מה קיים היום

### Pipeline
```
Telegram ("צופר - צבע אדום")
   │  telegram_alarms.py  (Telethon, iter_messages מ-min_date עד max_date)
   ▼
tzofar_red_color.xlsx   [date, text]   כל שורה = שעה אחת, וכל שורת טקסט = "אזור: יישובים"
   │  data_stats.read_my_data()
   ▼
my_data_tzofer_red_full.pkl   zone → city → CustomDateTime(date) → "HH:MM" → count
my_data_tzofer_red.pkl        zone → city → date → {"hour": {h: n}, "minute": {m: n}}
   │  data_plots.py  (matplotlib)
   ▼
partial_plots/*.png + *.txt
```

> שימו לב: השמות של שני קובצי ה-pickle מבלבלים. הקובץ `_full` הוא דווקא הגרסה **ברזולוציית דקה**, והקובץ בלי `_full` הוא הגרסה המקובצת לפי שעה ולפי דקה בנפרד.

### נתונים שנאספו
- טווח: **28/02/2026 עד 27/03/2026** (28 ימים, `dates.txt`).
- 1,798 רשומות שעה ב-`tzofar_red_color.xlsx`.
- רק **צבע אדום**. חדירת כלי טיס וחדירת מחבלים מסוננות היום במכוון (`FILTER_ALERTS` ב-`telegram_alarms.py`).
- צילומי המסך מהערוץ (06/2026) מראים שהערוץ ממשיך לפרסם. הנתונים בריפו לא כוללים את התקופה שאחרי 27/03/2026.

### גרפים קיימים (`data_plots.py`)
- `bar_0_1` … `bar_14`: עמודות לפי אזור, יישוב, תאריך ושעה, top-N, ותבניות חוזרות.
- `bar_15`, `bar_16`: צפיפות התרעות לפי חלונות זמן ביום.
- `bar_16_color_general`: **heatmap של שעה × דקה** לכל תנאי סינון, עם hover אינטראקטיבי ושמירת טבלת דירוג ל-txt.
- `partial_plot.py` מריץ כרגע רק `plot_16_color` עם `properties_18_general` (אשקלון, ראשון, נתניה).

### סינונים (`coditions.py`)
יישובים ספציפיים (אשקלון, ת"א, ראשון, נתניה, חיפה, באקה), אזורים (צפון/מרכז/דרום), עוטף עזה וקו העימות.

---

## 2. בעיות ידועות (לטפל קודם)

| # | בעיה | מיקום | חומרה |
|---|---|---|---|
| 1 | **פרטי Telegram API ומספר טלפון נמצאים ב-commit בריפו** | `parameters.py` | 🔴 גבוהה: מומלץ לבטל את ה-api_hash ב-my.telegram.org, להעביר ל-`.env` ולהוסיף ל-`.gitignore` |
| 2 | חסר פסיק ברשימה: `"🔓 חשש לחדירת מחבלים" "🔴 התרעה"` מתחברים למחרוזת אחת | `telegram_alarms.py` (`ALERTS`) | 🟠 בינונית: התרעות חדירת מחבלים לא מזוהות |
| 3 | אין `requirements.txt`. חסרות התלויות `matplotlib`, `ivsort`, `telethon` | שורש הריפו | 🟠 |
| 4 | התיקיות `partial_plots/` ו-`graphs/` לא קיימות, ולכן `savefig` / `os.listdir` קורסים | `data_plots.py`, `telegram_alarms.py` | 🟠 |
| 5 | `get_all_zones` קוראת `HT_zones.txt`, שלא קיים בריפו | `data_stats.py` | 🟠: `apply_collect_data()` נכשל |
| 6 | השעות מסומנות כ-UTC אבל בפועל הן שעון ישראל | `telegram_alarms.update_state` | 🟡: לא משפיע על הגרפים, אבל מטעה |
| 7 | `import *` בשרשרת (`data_plots` ← `data_stats` ← `parameters`) ומשתנים גלובליים | כללי | 🟡 |
| 8 | כפילויות: אותה הודעה יכולה להופיע גם כטקסט וגם כ-caption של תמונה. הבדיקה `[date, text] in all_data` היא O(n²) | `telegram_alarms.py` | 🟡 |
| 9 | אין בדיקות (tests) לפענוח ההודעות | — | 🟡 |

---

## 3. איך להתקדם: Roadmap מוצע

### שלב 0: יציבות (קטן, מומלץ ראשון)
- [ ] להעביר credentials ל-`.env` (`python-dotenv`) ולהוסיף `.gitignore` (`*.session`, `.env`, `partial_plots/`).
- [ ] `requirements.txt`.
- [ ] לתקן את הפסיק החסר ב-`ALERTS`.
- [ ] `os.makedirs(directory, exist_ok=True)` לפני כל שמירה.
- [ ] לטפל ב-`HT_zones.txt`: להוסיף לריפו או לדלג אם הקובץ חסר.

### שלב 1: מודל נתונים שטוח + סוג התרעה
המבנה המקונן קשה להרחבה. מומלץ טבלה שטוחה אחת (Parquet או SQLite):

| timestamp (Asia/Jerusalem) | alert_type | zone | city | shelter_sec | message_id |
|---|---|---|---|---|---|

- `alert_type` ∈ {`rocket` (צבע אדום), `uav` (כלי טיס עוין), `infiltration` (חדירת מחבלים)}.
- במקום לסנן `FILTER_ALERTS`, לשמור את כל הסוגים ולסנן רק בשלב הניתוח.
- לחלץ גם את זמן ההתגוננות `(15 שניות)` / `(דקה וחצי)`, שכרגע נזרק.
- אפשר לשמור גם אירועי "סיום אירוע" בטבלה נפרדת (events), כדי למדוד משך אירוע.
- `message_id` מטלגרם משמש כמפתח למניעת כפילויות ולאיסוף אינקרמנטלי (`min_id=last_id` במקום לאסוף מחדש מ-`min_date`).
- את כל ה-`group_by_*` אפשר להחליף ב-`df.groupby([...]).size()` / `pd.Grouper(freq="1h")`.
- להוסיף `tests/test_parser.py` עם ההודעות מצילומי המסך כ-fixtures.

### שלב 2: דשבורד אינטראקטיבי
- **Streamlit** (הכי מהיר) או Plotly Dash.
- פקדים: טווח תאריכים, סוג התרעה, אזור או יישוב (multi-select), רזולוציה (דקה/שעה/יום/שבוע).
- גרפים מומלצים:
  - סדרת זמן (line/area) של כמות התרעות לפי הרזולוציה, stacked לפי סוג.
  - heatmap של יום בשבוע × שעה, ושל תאריך × שעה (ממשיך את `bar_16_color`).
  - top-N יישובים ואזורים (bar אופקי).
  - התפלגות זמני התגוננות.
  - KPI: סה"כ התרעות, ימים עם התרעות, שעת שיא, היישוב המותקף ביותר.

### שלב 3: מפה אינטראקטיבית של ישראל (הבקשה של המשתמש)
- **גאוקודינג של יישובים**: צריך קואורדינטות (או פוליגונים) לכל יישוב ואזור התרעה של פיקוד העורף.
  מקורות אפשריים: רשימת הפוליגונים של אזורי ההתרעה (בפרויקטים פתוחים כמו `pikud-haoref-api` / רשימות cities.json בקוד פתוח), או גאוקודינג חד-פעמי (OSM Nominatim) שנשמר כ-`data/cities_geo.csv`.
  יש לבדוק את הרישיון של כל מקור לפני שמשתמשים בו.
- **ספרייה**: `pydeck` / `folium` בתוך Streamlit, או Plotly `scatter_mapbox` / `choropleth_mapbox`.
- **פיצ'רים**:
  - בחירת טווח זמן (slider) ← צביעת יישובים או אזורים לפי כמות ההתרעות (choropleth או bubble).
  - אנימציה לאורך זמן (play): התרעות לפי שעה או יום.
  - לחיצה על יישוב ← גרף סדרת זמן והתפלגות שעות של אותו יישוב.
  - שכבות נפרדות לכל סוג התרעה (צבע אדום / כלי טיס / מחבלים).
- אופציונלי: פרסום כאתר סטטי (GitHub Pages) עם קובץ JSON מצטבר, או Streamlit Community Cloud.

### שלב 4: אוטומציה
- סקריפט איסוף אינקרמנטלי שרץ מתוזמן (cron / GitHub Actions עם session מוצפן), כך שהדשבורד מתעדכן בלי איסוף ידני.

---

## 4. איך מריצים היום

```bash
pip install telethon pandas openpyxl matplotlib numpy ivsort
mkdir -p partial_plots graphs
# ב-parameters.py: COLLET=False, STATISTICS=False כדי לעבוד רק מה-pickle הקיים
python partial_plot.py
```

---

## 5. יומן סשנים

| תאריך | מה נעשה |
|---|---|
| 2026-11-05 | סקירת הקוד הקיים. נוצרו `CLAUDE.md` (הנחיות) ו-`handoff.md` (מצב ו-roadmap). תועדו בעיות ידועות, כולל credentials שנמצאים ב-commit. עדיין לא בוצעו שינויים בקוד. |
