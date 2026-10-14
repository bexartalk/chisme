#!/usr/bin/env python3
"""v49.23 freely licensed Starship / Starbase photos for the SpaceX launch cards (Wikipedia lead photos on Wikimedia
Commons, PD / CC0 / CC BY / CC BY-SA only), credited. Writes static/launch/photos.json.  python3 tools/make_launch_photos.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_places_gallery as G
G.OUT = os.path.join(G.ROOT, "static", "launch")
G.PLACES = [("starship", "SpaceX Starship", "SpaceX Starship", "Starbase, Texas"),
            ("starbase", "Starbase, Texas", "Starbase", "Boca Chica, Texas"),
            ("super-heavy", "SpaceX Super Heavy", "Super Heavy booster", "Starbase, Texas")]
G.main()
d = json.load(open(os.path.join(G.OUT, "places.json"))); os.remove(os.path.join(G.OUT, "places.json"))
for p in d["photos"]: p["file"] = p["file"].replace("/static/places/", "/static/launch/"); p["thumb"] = p["thumb"].replace("/static/places/", "/static/launch/")
json.dump({"about": "Starship / Starbase photos for the launch cards: Wikipedia lead photos, freely licensed on Wikimedia Commons, resized by Chisme.",
           "photos": d["photos"]}, open(os.path.join(G.OUT, "photos.json"), "w"), ensure_ascii=False, indent=1)
