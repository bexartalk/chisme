"""Build data/sa_neighborhoods.json: approximate centroids for San Antonio neighborhoods.
OpenStreetMap has almost no neighbourhood polygons for San Antonio, so reverse geocoding
returns only "San Antonio". This looks up each name once with Nominatim (1 req/s, per
the usage policy) and keeps results that land inside the San Antonio area.
Usage: ./venv/bin/python tools/build_sa_gazetteer.py"""
import json, time
from pathlib import Path
import httpx

OUT = Path(__file__).resolve().parent.parent / "data" / "sa_neighborhoods.json"
UA = "Chisme/1.0 (gazetteer build; local news+weather app)"
# (display name, Nominatim query, extra match terms)
PLACES = [
    ("Palm Heights", "Palm Heights, San Antonio, TX", []),
    ("Harlandale", "Harlandale High School, San Antonio, TX", ["Harlandale"]),
    ("Nogalitos", "Nogalitos Street, San Antonio, TX", ["Nogalitos"]),
    ("Quintana", "Quintana Road, San Antonio, TX", ["Quintana Road", "Quintana Rd"]),
    ("Port San Antonio (Kelly)", "Port San Antonio, San Antonio, TX", ["Port San Antonio", "Kelly Field", "KellyUSA", "former Kelly"]),
    ("Stinson", "Stinson Municipal Airport, San Antonio, TX", ["Stinson"]),
    ("South San", "South San Antonio High School, San Antonio, TX", ["South San"]),
    ("Collins Garden", "Collins Garden, San Antonio, TX", []),
    ("Loma Park", "Loma Park, San Antonio, TX", []),
    ("Las Palmas", "Las Palmas, San Antonio, TX", []),
    ("Villa Coronado", "Villa Coronado, San Antonio, TX", []),
    ("Mission San José", "Mission San Jose, San Antonio, TX", ["Mission San José", "Mission San Jose"]),
    ("Mission Espada", "Mission Espada, San Antonio, TX", []),
    ("Mission Concepción", "Mission Concepcion, San Antonio, TX", ["Mission Concepción", "Mission Concepcion"]),
    ("Roosevelt Park", "Roosevelt Park, San Antonio, TX", []),
    ("Highland Park", "Highland Park, San Antonio, TX", []),
    ("Lone Star", "Lone Star Brewery, San Antonio, TX", ["Lone Star Brewery", "Lone Star neighborhood"]),
    ("King William", "King William, San Antonio, TX", []),
    ("Southtown", "Southtown, San Antonio, TX", []),
    ("Lavaca", "Lavaca, San Antonio, TX", []),
    ("Denver Heights", "Denver Heights, San Antonio, TX", []),
    ("Dignowity Hill", "Dignowity Hill, San Antonio, TX", []),
    ("Government Hill", "Government Hill, San Antonio, TX", []),
    ("Tobin Hill", "Tobin Hill, San Antonio, TX", []),
    ("Monte Vista", "Monte Vista, San Antonio, TX", []),
    ("Beacon Hill", "Beacon Hill, San Antonio, TX", []),
    ("Prospect Hill", "Prospect Hill, San Antonio, TX", []),
    ("Edgewood", "Edgewood, San Antonio, TX", ["Edgewood ISD"]),
    ("Brooks", "Brooks, San Antonio, TX", ["Brooks City Base", "Brooks Development"]),
    ("Palo Alto", "Palo Alto College, San Antonio, TX", ["Palo Alto College"]),
    ("South Park Mall", "South Park Mall, San Antonio, TX", []),
    ("Pearl", "Pearl Brewery, San Antonio, TX", ["the Pearl", "Pearl District"]),
    ("Downtown San Antonio", "The Alamo, San Antonio, TX", ["downtown San Antonio"]),
    ("Medical Center", "University Hospital, San Antonio, TX", ["South Texas Medical Center", "Medical Center area"]),
    ("Stone Oak", "Stone Oak, San Antonio, TX", []),
    ("Alamo Heights", "Alamo Heights, TX", []),
    ("Leon Valley", "Leon Valley, TX", []),
    ("Lackland", "Joint Base San Antonio-Lackland, TX", ["Lackland"]),
    ("Westside", "Guadalupe Cultural Arts Center, San Antonio, TX", ["West Side", "Westside"]),
    ("Eastside", "St. Philip's College, Martin Luther King Drive, San Antonio", ["East Side", "Eastside"]),
]
BBOX = (29.15, 29.80, -98.85, -98.20)

out = []
with httpx.Client(headers={"User-Agent": UA}, timeout=20) as c:
    for name, q, extra in PLACES:
        r = c.get("https://nominatim.openstreetmap.org/search", params={"q": q, "format": "jsonv2", "limit": 1})
        time.sleep(1.1)
        res = r.json()
        if not res:
            print("MISS", name, "|", q); continue
        x = res[0]; lat, lon = float(x["lat"]), float(x["lon"])
        if not (BBOX[0] <= lat <= BBOX[1] and BBOX[2] <= lon <= BBOX[3]):
            print("OUT ", name, lat, lon, x["display_name"][:60]); continue
        out.append({"name": name, "lat": round(lat, 5), "lon": round(lon, 5),
                    "terms": [name] + extra if name not in extra else extra,
                    "osm": f'{x.get("category")}/{x.get("type")}', "resolved": x["display_name"][:120]})
        print("ok  ", name, lat, lon, x.get("category"), x.get("type"))
OUT.write_text(json.dumps({"source": "OpenStreetMap Nominatim lookups (approximate points)", "built": time.strftime("%Y-%m-%d"), "places": out}, indent=1, ensure_ascii=False))
print(len(out), "places ->", OUT)
