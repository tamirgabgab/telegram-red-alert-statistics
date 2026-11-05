"""Locality-name tables shared by the legacy pipeline and the new parser.

The Home Front Command (and the Tzofar channel) use some locality names that contain
commas, e.g. "זמרת, שובה". A naive split on "," would break them into two fake localities,
so every such name must be listed in ``special_str``. ``rep_str`` maps spelling variants
to one canonical name.

When you notice a locality that is split or spelled inconsistently, add it here.
"""

special_str = [
    "אשדוד - א,ב,ד,ה",
    "אשדוד - ג,ו,ז",
    "אשדוד - ח,ט,י,יג,יד,טז",
    "אשדוד - יא,יב,טו,יז,מרינה,סיטי",
    "שדרות, איבים, ניר עם",
    "גבים, מכללת ספיר",
    "קריית גת, כרמי גת",
    "מעגלים, גבעולים, מלילות",
    "זמרת, שובה",
    "מבטחים, עמיעוז, ישע",
    "צוחר, אוהד",
    "אל עמארני, אל מסק",
    "תקומה, חוות יזרעם"
]

rep_str = {
    'אבו-גוש': 'אבו גוש',
    'בת-ים': 'בת - ים',
    'בת ים': 'בת - ים',
    'חיפה-מפרץ': 'חיפה - מפרץ',
    'פרדס חנה-כרכור': 'פרדס חנה כרכור',
    'פרדס חנה - כרכור': 'פרדס חנה כרכור',
    'תקומה וחוות יזרעם': 'תקומה, חוות יזרעם',
    'תקומה': 'תקומה, חוות יזרעם'
}

# Suffixes the channel appends to some names that are not part of the locality name.
_DROP_SUFFIXES = [" והפזורה"]


def normalize_city(name):
    """Strip whitespace/suffixes and map known spelling variants to the canonical name."""
    name = name.strip()
    for suffix in _DROP_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    return rep_str.get(name, name)


def split_cities(text):
    """Split a comma separated list of localities, keeping names that contain commas intact.

    >>> split_cities("כפר עזה, זמרת, שובה, סעד")
    ['כפר עזה', 'זמרת, שובה', 'סעד']
    """
    # Protect comma-containing names with a placeholder, longest first, so a shorter
    # special name can't match inside a longer one.
    protected = {}
    for i, special in enumerate(sorted(special_str, key=len, reverse=True)):
        if special in text:
            token = f"\x00{i}\x00"
            protected[token] = special
            text = text.replace(special, token)

    cities = []
    for part in text.split(","):
        for token, special in protected.items():
            part = part.replace(token, special)
        part = normalize_city(part)
        if part:
            cities.append(part)
    return cities
