# data/geo — third-party data notice

`localities.geojson` is derived from **pikud-haoref-api** by Elad Nava
(https://github.com/eladnava/pikud-haoref-api), files `cities.json` and `polygons.json`
at commit `b77f86bb1da42926704bb5f8677d527f15c4508d`, licensed under the Apache License 2.0
(copy: `LICENSE-pikud-haoref-api`).

Modifications made by `build_geo.py`:
- merged the two files into one GeoJSON FeatureCollection keyed by the Hebrew locality name;
- converted polygon coordinates from [lat, lng] to GeoJSON [lng, lat] and closed the rings;
- kept only the Hebrew/English name, zone, countdown (time to shelter, seconds) and centroid;
- localities without a polygon are stored as Point features.
