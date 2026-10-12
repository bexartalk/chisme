"""Chisme's legal contact, in ONE place: the /dmca agent box (social_api.py) and the /terms, /privacy and
/community-rules pages (tools/make_legal_pages.py) both use it.

To stop showing the street address (Goonie may want this later): set SHOW_STREET_ADDRESS = False, or put a P.O. box
in ADDRESS_LINES, then rebuild the pages (./venv/bin/python tools/make_legal_pages.py). The legal .md files keep
Plato's wording untouched; the address lines are dropped when the pages are built. Note: the DMCA safe harbor needs a
mailing address for the designated agent on the site, so use a P.O. box rather than nothing, and update the U.S.
Copyright Office registration to match."""

AGENT_NAME = "Arnulfo Ledezma (Chisme)"
ADDRESS_LINES = ["912 FM 2537 Lot #5", "San Antonio, TX 78221"]
SHOW_STREET_ADDRESS = True
PHONE = "(210) 837-2281"
EMAIL = "Arnulfoled@outlook.com"
DMCA_REG = "DMCA-1082743"

ADDRESS = ", ".join(ADDRESS_LINES) if SHOW_STREET_ADDRESS else ""
STREET_LINE = ADDRESS_LINES[0]   # the line the page builder removes when SHOW_STREET_ADDRESS is False
