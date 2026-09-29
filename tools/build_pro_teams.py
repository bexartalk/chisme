"""Build data/pro_teams.json: NBA + NFL teams (ESPN ids/names from ESPN's public teams API) with the
home venue's approximate coordinates, state and (NBA) conference, so Chisme can pick the nearest teams.
MLB/MiLB don't need this: the MLB Stats API returns venue coordinates itself.
Usage: ./venv/bin/python tools/build_pro_teams.py"""
import json, pathlib, urllib.request

# abbr -> (lat, lon, state)  (arena / stadium, approximate)
NBA = {"ATL": (33.757, -84.396, "GA"), "BOS": (42.366, -71.062, "MA"), "BKN": (40.683, -73.975, "NY"), "CHA": (35.225, -80.839, "NC"),
       "CHI": (41.881, -87.674, "IL"), "CLE": (41.496, -81.688, "OH"), "DAL": (32.790, -96.810, "TX"), "DEN": (39.749, -105.008, "CO"),
       "DET": (42.341, -83.055, "MI"), "GS": (37.768, -122.388, "CA"), "HOU": (29.751, -95.362, "TX"), "IND": (39.764, -86.156, "IN"),
       "LAC": (33.945, -118.341, "CA"), "LAL": (34.043, -118.267, "CA"), "MEM": (35.138, -90.051, "TN"), "MIA": (25.781, -80.188, "FL"),
       "MIL": (43.045, -87.917, "WI"), "MIN": (44.979, -93.276, "MN"), "NO": (29.949, -90.082, "LA"), "NY": (40.751, -73.993, "NY"),
       "OKC": (35.463, -97.515, "OK"), "ORL": (28.539, -81.384, "FL"), "PHI": (39.901, -75.172, "PA"), "PHX": (33.446, -112.071, "AZ"),
       "POR": (45.532, -122.667, "OR"), "SAC": (38.580, -121.500, "CA"), "SA": (29.427, -98.438, "TX"), "TOR": (43.643, -79.379, "ON"),
       "UTAH": (40.768, -111.901, "UT"), "WSH": (38.898, -77.021, "DC")}
WEST = {"DAL", "DEN", "GS", "HOU", "LAC", "LAL", "MEM", "MIN", "NO", "OKC", "PHX", "POR", "SAC", "SA", "UTAH"}
NFL = {"ARI": (33.528, -112.263, "AZ"), "ATL": (33.755, -84.401, "GA"), "BAL": (39.278, -76.623, "MD"), "BUF": (42.774, -78.787, "NY"),
       "CAR": (35.226, -80.853, "NC"), "CHI": (41.862, -87.617, "IL"), "CIN": (39.095, -84.516, "OH"), "CLE": (41.506, -81.700, "OH"),
       "DAL": (32.748, -97.093, "TX"), "DEN": (39.744, -105.020, "CO"), "DET": (42.340, -83.046, "MI"), "GB": (44.501, -88.062, "WI"),
       "HOU": (29.685, -95.411, "TX"), "IND": (39.760, -86.164, "IN"), "JAX": (30.324, -81.637, "FL"), "KC": (39.049, -94.484, "MO"),
       "LV": (36.091, -115.184, "NV"), "LAC": (33.953, -118.339, "CA"), "LAR": (33.953, -118.339, "CA"), "MIA": (25.958, -80.239, "FL"),
       "MIN": (44.974, -93.258, "MN"), "NE": (42.091, -71.264, "MA"), "NO": (29.951, -90.081, "LA"), "NYG": (40.813, -74.074, "NJ"),
       "NYJ": (40.813, -74.074, "NJ"), "PHI": (39.901, -75.168, "PA"), "PIT": (40.447, -80.016, "PA"), "SF": (37.403, -121.970, "CA"),
       "SEA": (47.595, -122.332, "WA"), "TB": (27.976, -82.503, "FL"), "TEN": (36.166, -86.771, "TN"), "WSH": (38.908, -76.864, "MD")}


def teams(path):
    with urllib.request.urlopen(f"https://site.api.espn.com/apis/site/v2/sports/{path}/teams", timeout=20) as r:
        d = json.load(r)
    return [t["team"] for t in d["sports"][0]["leagues"][0]["teams"]]


out = {"_about": "NBA/NFL teams: ESPN ids + names (ESPN public teams API) with approximate home venue coordinates. Built by tools/build_pro_teams.py.",
       "nba": [], "nfl": []}
for lg, path, table in (("nba", "basketball/nba", NBA), ("nfl", "football/nfl", NFL)):
    for t in teams(path):
        a = t["abbreviation"]
        lat, lon, st = table[a]
        row = {"id": str(t["id"]), "abbr": a, "name": t["displayName"], "short": t["shortDisplayName"], "slug": t.get("slug"),
               "location": t.get("location"), "state": st, "lat": lat, "lon": lon}
        if lg == "nba":
            row["conf"] = "West" if a in WEST else "East"
        out[lg].append(row)
p = pathlib.Path(__file__).resolve().parent.parent / "data" / "pro_teams.json"
p.write_text(json.dumps(out, indent=1))
print(p, len(out["nba"]), len(out["nfl"]))
