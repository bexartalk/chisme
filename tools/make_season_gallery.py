#!/usr/bin/env python3
"""v49.12 Día de Muertos gallery: downloads the chosen Wikimedia Commons photos, resizes them to webp and writes
static/season/gallery.json (title, place, year, photographer, license, license URL, Commons source URL, original).

Only freely reusable photos: public domain (US federal works: NPS, EPA/NARA; CC0) or CC BY / CC BY-SA. No NC/ND, no
news sites, agencies or social media. Every photo is shown with its credit line (photographer / license / Wikimedia
Commons, linked) and marked "(resized)", which is the change we make (CC BY / BY-SA ask us to say so).

    python3 tools/make_season_gallery.py            # re-download + rebuild (needs the network; ~25 files)
"""
import io, json, os, re, sys, time, html, urllib.parse, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "season", "gallery")
UA = {"User-Agent": "ChismeSeasonGallery/1.0 (https://chisme.onrender.com; bexartalkradio@gmail.com)"}
API = "https://commons.wikimedia.org/w/api.php?"
ALLOWED = {"Public domain", "CC0", "CC BY 2.0", "CC BY 3.0", "CC BY 4.0", "CC BY-SA 2.0", "CC BY-SA 2.5", "CC BY-SA 3.0", "CC BY-SA 4.0"}
PD_URL = {"nps": "https://commons.wikimedia.org/wiki/Template:PD-USGov-NPS", "epa": "https://commons.wikimedia.org/wiki/Template:PD-USGov-EPA"}
CASTELAZO = "© Tomas Castelazo, www.tomascastelazo.com"   # the attribution he asks for on the file pages

# (slug, Commons file, caption, place, year, photographer as credited, region, pd source)
PHOTOS = [
    ("sa-mission-ofrenda", "Ofrenda or Day of the Dead Altar at Mission Marquee Plaza. (586908b4-40dd-4be5-bc53-ababb89291f1).JPG",
     "Ofrenda at Mission Marquee Plaza", "Mission San José, San Antonio Missions", 2021, "National Park Service", "sa", "nps"),
    ("sa-mission-blessing", "Blessings of the Day of the Dead Altars Dia de los Muertos ofrendas. (3b0b7ff5-5efe-4f10-a0a0-91aabcae5873).JPG",
     "Blessing the ofrendas", "Mission San José, San Antonio Missions", 2021, "National Park Service", "sa", "nps"),
    ("sa-pearl-ofrenda", "Dia De Los Muertos Altar (49275273173).jpg",
     "Día de Muertos altar", "San Antonio", 2019, "Nan Palmero", "sa", None),
    ("sa-pearl-calavera", "Dia De Los Muertos Altar (49275282153).jpg",
     "A calavera altar", "San Antonio", 2019, "Nan Palmero", "sa", None),
    ("sa-pearl-mariachi", "Mariachi at The Historic Pearl Dia De Los Muertos (49275938082).jpg",
     "Mariachi at the Pearl's Día de Muertos", "The Pearl, San Antonio", 2019, "Nan Palmero", "sa", None),
    ("sa-pearl-night", "The Historic Pearl Dia De Los Muertos Celebration (49275938752).jpg",
     "Día de Muertos at the Pearl", "The Pearl, San Antonio", 2019, "Nan Palmero", "sa", None),
    ("sa-catrina-art", "Art Display at Dia De Los Muertos (49275741741).jpg",
     "A glowing catrina", "San Antonio", 2019, "Nan Palmero", "sa", None),
    ("sa-mi-tierra", "Day of the Dead Altar at Mi Tierra Café.jpg",
     "The altar at Mi Tierra Café y Panadería", "Market Square, San Antonio", 2019, "Adrianna Chavez", "sa", None),
    ("sa-lowrider", "Dia De Los Muertos Chicano Lowrider.jpg",
     "A Chicano lowrider on Día de Muertos", "San Antonio", 2015, "Nan Palmero", "sa", None),
    ("sa-1972-cemetery", 'MEXICAN CEMETERY NEAR SAN JUAN CAPISTRANO MISSION AFTER "DAY OF THE DEAD" (ALL SAINTS DAY) RITUALS - NARA - 547801.jpg',
     "Graves decorated for Día de Muertos near Mission San Juan Capistrano", "San Antonio", 1972,
     "Bob Smith, EPA DOCUMERICA (National Archives)", "sa", "epa"),
    ("mx-catrinas", "Catrinas and Catrines.jpg",
     "Catrinas and catrines, after José Guadalupe Posada", "Mexico", 2017, CASTELAZO, "mx", None),
    ("mx-graveyard-visit", "Graveyard visit.jpg",
     "A family visit to the graves", "León, Guanajuato", 2007, CASTELAZO, "mx", None),
    ("mx-alfenique", "Alfeniques of day of the dead.jpg",
     "Alfeñiques (sugar figures) in the plaza", "León, Guanajuato", 2009, CASTELAZO, "mx", None),
    ("mx-sugar-skulls", "Sugar skulls.jpg",
     "Sugar skulls", "Mexico", 2017, CASTELAZO, "mx", None),
    ("mx-mixquic", "Mixquic Mágico 17.jpg",
     "Candles and copal in Mixquic", "San Andrés Mixquic, Mexico City", 2014, "Jordi Cueto-Felgueroso Arocha", "mx", None),
    ("mx-janitzio", "Noche de Muertos en Janitzio.jpg",
     "Noche de Muertos on Janitzio island", "Lake Pátzcuaro, Michoacán", 2013, "Miguel Angel Mandujano Contreras", "mx", None),
    ("mx-pacanda", "Isla Pacanda, Noche de Muertos 14.jpg",
     "The cemetery on the Night of the Dead", "Isla Pacanda, Michoacán", 2013, "LBM1948", "mx", None),
    ("mx-tzintzuntzan", "Tzintzuntzan, cementerio 12.jpg",
     "Graves dressed in cempasúchil", "Tzintzuntzan, Michoacán", 2013, "LBM1948", "mx", None),
    ("mx-patzcuaro-plaza", "Pátzcuaro, plazas 03.jpg",
     "Plaza Vasco de Quiroga dressed for Día de Muertos", "Pátzcuaro, Michoacán", 2013, "LBM1948", "mx", None),
    ("mx-viejitos", "Pátzcuaro, viejitos 1.jpg",
     "La Danza de los Viejitos", "Pátzcuaro, Michoacán", 2013, "LBM1948", "mx", None),
    ("mx-cdmx-desfile", "Desfile día de muertos 2018 DSC 0146 (31766250088).jpg",
     "The Día de Muertos parade", "Mexico City", 2018, "Gobierno de la Ciudad de México", "mx", None),
    ("mx-reforma-skull", "Reforma skullsp1.jpg",
     "Mexicráneos: artists' skulls on Paseo de la Reforma", "Mexico City", 2017, "Carlos Valenzuela", "mx", None),
    ("mx-tonala", "Calaveras Tonalá (2).jpg",
     "Painted clay calaveras at the tianguis", "Tonalá, Jalisco", 2018, "Gzzz", "mx", None),
]

def strip(s): return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()

def api(params):
    params = dict(params, format="json")
    with urllib.request.urlopen(urllib.request.Request(API + urllib.parse.urlencode(params), headers=UA), timeout=60) as r:
        return json.load(r)

def fetch(url):
    for k in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r: return r.read()
        except Exception as e:
            print("   retry", k + 1, e); time.sleep(5 * (k + 1))
    raise SystemExit("could not download " + url)

def main():
    os.makedirs(OUT, exist_ok=True)
    items = []
    for slug, fname, caption, place, year, who, region, pd in PHOTOS:
        title = "File:" + fname
        d = api(dict(action="query", prop="imageinfo", iiprop="url|size|extmetadata", iiurlwidth=1280, titles=title))
        page = next(iter(d["query"]["pages"].values()))
        ii = page["imageinfo"][0]; m = ii["extmetadata"]
        lic = strip(m.get("LicenseShortName", {}).get("value"))
        if lic not in ALLOWED: raise SystemExit(f"{fname}: license {lic!r} is not allowed")
        if re.search(r"\b(NC|ND)\b", lic): raise SystemExit(f"{fname}: NC/ND")
        portrait = ii["height"] > ii["width"]
        src_w = 960 if portrait else 1280
        thumb = ii["thumburl"].replace("/1280px-", f"/{src_w}px-")
        full, small = os.path.join(OUT, slug + ".webp"), os.path.join(OUT, slug + "-s.webp")
        if not (os.path.exists(full) and os.path.exists(small)):
            im = Image.open(io.BytesIO(fetch(thumb))).convert("RGB")
            a = im.copy(); a.thumbnail((1200, 1200), Image.LANCZOS); a.save(full, "WEBP", quality=74, method=6)
            b = im.copy(); b.thumbnail((520, 520), Image.LANCZOS); b.save(small, "WEBP", quality=70, method=6)
            time.sleep(1.5)
        fw, fh = Image.open(full).size; sw, sh = Image.open(small).size
        lic_url = strip(m.get("LicenseUrl", {}).get("value")) or PD_URL.get(pd or "", "")
        items.append({
            "id": slug, "region": region, "title": caption, "place": place, "year": year,
            "photographer": who, "license": "Public domain" if pd else lic, "license_url": lic_url,
            "source_url": ii["descriptionurl"], "commons_title": fname,
            "original": strip(m.get("Credit", {}).get("value")) if "flickr.com" in (m.get("Credit", {}).get("value") or "") else None,
            "commons_author": strip(m.get("Artist", {}).get("value"))[:120],
            "file": f"/static/season/gallery/{slug}.webp", "w": fw, "h": fh,
            "thumb": f"/static/season/gallery/{slug}-s.webp", "tw": sw, "th": sh, "resized": True,
        })
        print(f"{slug:22} {lic:14} {who[:40]:40} {fw}x{fh} {os.path.getsize(full)//1024}K / {os.path.getsize(small)//1024}K")
    out = {"about": "Día de Muertos in San Antonio and Mexico: freely licensed photos from Wikimedia Commons "
                    "(public domain, CC0, CC BY, CC BY-SA), resized to webp by Chisme. Built by tools/make_season_gallery.py.",
           "photos": items}
    with open(os.path.join(ROOT, "static", "season", "gallery.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1); f.write("\n")
    print(len(items), "photos")

if __name__ == "__main__":
    main()
