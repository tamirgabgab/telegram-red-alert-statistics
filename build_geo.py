"""Download Home Front Command locality coordinates + polygons and build ``data/geo/localities.geojson``.

Source: https://github.com/eladnava/pikud-haoref-api (Apache License 2.0), pinned to SOURCE_COMMIT.
The output is a modified, derived work (see data/geo/NOTICE.md); the license is copied next to it.

Usage:  python build_geo.py            # only needed to refresh the geo data
"""

import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
GEO_DIR = os.path.join(ROOT, "data", "geo")
GEOJSON_FILE = os.path.join(GEO_DIR, "localities.geojson")

SOURCE_REPO = "eladnava/pikud-haoref-api"
SOURCE_COMMIT = "b77f86bb1da42926704bb5f8677d527f15c4508d"
RAW_URL = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{{name}}"


def fetch_json(name):
    with urllib.request.urlopen(RAW_URL.format(name=name), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_text(name):
    with urllib.request.urlopen(RAW_URL.format(name=name), timeout=60) as r:
        return r.read().decode("utf-8")


def _ring_lnglat(points):
    """Source polygons are [[lat, lng], ...]; GeoJSON wants a closed [[lng, lat], ...] ring."""
    ring = [[round(lng, 5), round(lat, 5)] for lat, lng in points]
    if ring and ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def build_geojson(cities, polygons):
    """One feature per locality (id = Hebrew name). Polygon when available, otherwise Point."""
    features, seen = [], set()
    for c in cities:
        name = (c.get("name") or "").strip()
        if not name or not c.get("lat") or name in seen:  # skips the "בחר הכל" pseudo entry
            continue
        seen.add(name)
        ring = polygons.get(str(c["id"]))
        if ring and len(ring) >= 3:
            geometry = {"type": "Polygon", "coordinates": [_ring_lnglat(ring)]}
        else:
            geometry = {"type": "Point", "coordinates": [round(c["lng"], 5), round(c["lat"], 5)]}
        features.append({
            "type": "Feature",
            "id": name,
            "properties": {
                "name": name,
                "name_en": c.get("name_en", ""),
                "zone": c.get("zone", ""),
                "countdown": c.get("countdown"),
                "lat": c["lat"],
                "lng": c["lng"],
                "has_polygon": geometry["type"] == "Polygon",
            },
            "geometry": geometry,
        })
    return {"type": "FeatureCollection", "features": features}


NOTICE = f"""# data/geo — third-party data notice

`localities.geojson` is derived from **pikud-haoref-api** by Elad Nava
(https://github.com/{SOURCE_REPO}), files `cities.json` and `polygons.json`
at commit `{SOURCE_COMMIT}`, licensed under the Apache License 2.0
(copy: `LICENSE-pikud-haoref-api`).

Modifications made by `build_geo.py`:
- merged the two files into one GeoJSON FeatureCollection keyed by the Hebrew locality name;
- converted polygon coordinates from [lat, lng] to GeoJSON [lng, lat] and closed the rings;
- kept only the Hebrew/English name, zone, countdown (time to shelter, seconds) and centroid;
- localities without a polygon are stored as Point features.
"""


def main():
    cities = fetch_json("cities.json")
    polygons = fetch_json("polygons.json")
    geo = build_geojson(cities, polygons)
    os.makedirs(GEO_DIR, exist_ok=True)
    with open(GEOJSON_FILE, "w", encoding="utf-8") as f:
        json.dump(geo, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(GEO_DIR, "LICENSE-pikud-haoref-api"), "w", encoding="utf-8") as f:
        f.write(fetch_text("LICENSE"))
    with open(os.path.join(GEO_DIR, "NOTICE.md"), "w", encoding="utf-8") as f:
        f.write(NOTICE)
    n_poly = sum(f["properties"]["has_polygon"] for f in geo["features"])
    print(f"{len(geo['features']):,} localities ({n_poly:,} polygons) -> {GEOJSON_FILE}")


if __name__ == "__main__":
    main()
