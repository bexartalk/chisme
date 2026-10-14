#!/usr/bin/env python3
"""v49.23 "Our places & history": real photos of San Antonio + South Texas landmarks and community places.

For each place we take its English Wikipedia article's lead photo, but only when that file lives on Wikimedia Commons
under public domain / CC0 / CC BY / CC BY-SA (no NC/ND, no fair use). The history line is the article's own first
sentence(s) (Wikipedia REST summary), stored with its link — nothing is written by hand. Images become webp (<200 KB).
Writes static/places/places.json.   python3 tools/make_places_gallery.py   (needs the network)
"""
import io, json, os, re, sys, time, html, urllib.error, urllib.parse, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "places")
UA = {"User-Agent": "ChismePlacesGallery/1.0 (https://chisme.onrender.com; bexartalkradio@gmail.com)"}
OK = re.compile(r"^(Public domain|PD.*|CC0.*|CC BY(-SA)? \d\.\d.*)$", re.I)

# (slug, Wikipedia article, short label, area)
PLACES = [
    ("alamo", "Alamo Mission in San Antonio", "The Alamo", "San Antonio"),
    ("mission-san-jose", "Mission San José (Texas)", "Mission San José", "San Antonio"),
    ("mission-concepcion", "Mission Concepción", "Mission Concepción", "San Antonio"),
    ("mission-espada", "Mission Espada", "Mission Espada", "San Antonio"),
    ("mission-san-juan", "Mission San Juan Capistrano (Texas)", "Mission San Juan", "San Antonio"),
    ("san-fernando", "Cathedral of San Fernando (San Antonio)", "San Fernando Cathedral", "San Antonio"),
    ("river-walk", "San Antonio River Walk", "The River Walk", "San Antonio"),
    ("market-square", "Market Square (San Antonio)", "Historic Market Square", "San Antonio"),
    ("tower-americas", "Tower of the Americas", "Tower of the Americas", "San Antonio"),
    ("governors-palace", "Spanish Governor's Palace", "Spanish Governor's Palace", "San Antonio"),
    ("la-villita", "La Villita", "La Villita", "San Antonio"),
    ("pearl", "Pearl Brewery", "The Pearl", "San Antonio"),
    ("majestic", "Majestic Theatre (San Antonio)", "Majestic Theatre", "San Antonio"),
    ("tea-garden", "San Antonio Japanese Tea Garden", "Japanese Tea Garden", "San Antonio"),
    ("guadalupe-center", "Guadalupe Cultural Arts Center", "Guadalupe Cultural Arts Center", "San Antonio"),
    ("brackenridge", "Brackenridge Park", "Brackenridge Park", "San Antonio"),
    ("hemisfair", "HemisFair '68", "HemisFair '68 grounds", "San Antonio"),
    ("aquarium", "Texas State Aquarium", "Texas State Aquarium", "Corpus Christi"),
    ("lexington", "USS Lexington (CV-16)", "USS Lexington Museum", "Corpus Christi"),
    ("mirador", "Mirador de la Flor", "Mirador de la Flor (Selena memorial)", "Corpus Christi"),
    ("fulton-mansion", "Fulton Mansion", "Fulton Mansion", "Rockport-Fulton"),
    ("port-isabel-light", "Port Isabel Lighthouse", "Port Isabel Lighthouse", "Port Isabel"),
    ("san-juan-basilica", "Basilica of the National Shrine of Our Lady of San Juan del Valle", "Basilica of San Juan del Valle", "San Juan, Rio Grande Valley"),
    ("la-bahia", "Presidio La Bahía", "Presidio La Bahía", "Goliad"),
    ("padre-island", "Padre Island National Seashore", "Padre Island National Seashore", "Padre Island"),
    ("san-agustin-laredo", "Cathedral of San Agustin (Laredo, Texas)", "San Agustín Cathedral", "Laredo"),
    ("espiritu-santo", "Mission Nuestra Señora del Espíritu Santo de Zúñiga", "Mission Nuestra Señora del Espíritu Santo de Zúñiga", "Goliad"),
]


def get(url):
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: raise
            print("   retry", k + 1, e); time.sleep(3 * (k + 1))
        except Exception as e:
            print("   retry", k + 1, e); time.sleep(3 * (k + 1))
    raise RuntimeError("download failed " + url)


def strip(s): return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def first_sentences(extract, limit=260):
    out = ""
    for s in re.split(r"(?<=[.!?])\s+", extract.strip()):
        if out and len(out) + len(s) + 1 > limit: break
        out = (out + " " + s).strip()
    return out


def save_webp(raw, path, edge, cap=200 * 1024):
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((edge, edge), Image.LANCZOS)
    for q in (78, 72, 66, 60, 54, 48):
        im.save(path, "WEBP", quality=q, method=6)
        if os.path.getsize(path) < cap: break
    return im.size


def main():
    os.makedirs(OUT, exist_ok=True)
    items, skipped = [], []
    for slug, article, label, area in PLACES:
        try:
            s = json.loads(get("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(article.replace(" ", "_"), safe="")))
        except urllib.error.HTTPError:
            skipped.append((slug, "no such article")); continue
        img = (s.get("originalimage") or {}).get("source", "")
        if "/wikipedia/commons/" not in img:
            skipped.append((slug, "lead image not on Commons")); continue
        parts = img.split("?")[0].split("/")
        fname = urllib.parse.unquote(parts[-2] if "/thumb/" in img else parts[-1])
        q = json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(
            action="query", prop="imageinfo", iiprop="url|size|extmetadata", iiurlwidth=1280, titles="File:" + fname, format="json"))))
        page = next(iter(q["query"]["pages"].values()))
        if "imageinfo" not in page:
            skipped.append((slug, "no imageinfo")); continue
        ii = page["imageinfo"][0]; m = ii["extmetadata"]
        lic = strip(m.get("LicenseShortName", {}).get("value"))
        if not OK.match(lic) or re.search(r"\b(NC|ND)\b", lic):
            skipped.append((slug, "license " + lic)); continue
        author = re.sub(r"\s*\((talk|Talk)\s*·\s*contribs\)", "", strip(m.get("Artist", {}).get("value")))[:120].strip() or "Unknown"
        full, small = os.path.join(OUT, slug + ".webp"), os.path.join(OUT, slug + "-s.webp")
        if os.path.exists(full) and os.path.exists(small):
            (fw, fh), (sw, sh) = Image.open(full).size, Image.open(small).size
        else:
            raw = get(ii.get("thumburl") or ii["url"])
            fw, fh = save_webp(raw, full, 1200); sw, sh = save_webp(raw, small, 520, 60 * 1024)
        items.append({"id": slug, "title": label, "area": area, "history": first_sentences(s.get("extract", "")),
                      "history_source": "Wikipedia", "history_url": s["content_urls"]["desktop"]["page"],
                      "photographer": author, "license": lic, "license_url": strip(m.get("LicenseUrl", {}).get("value")) or "https://commons.wikimedia.org/wiki/Commons:Licensing",
                      "source_url": ii["descriptionurl"], "commons_title": fname, "file": f"/static/places/{slug}.webp", "w": fw, "h": fh,
                      "thumb": f"/static/places/{slug}-s.webp", "tw": sw, "th": sh, "resized": True})
        print(f"{slug:20} {lic:16} {author[:36]:36} {os.path.getsize(full)//1024}K")
        time.sleep(1)
    json.dump({"about": "San Antonio and South Texas places and their history: each photo is the Wikipedia article's lead photo, freely licensed on "
               "Wikimedia Commons (public domain, CC0, CC BY, CC BY-SA), resized to webp by Chisme; the history line is quoted from that article. "
               "Built by tools/make_places_gallery.py.", "photos": items}, open(os.path.join(OUT, "places.json"), "w"), ensure_ascii=False, indent=1)
    print(len(items), "photos;", "skipped:", skipped)


if __name__ == "__main__":
    main()
