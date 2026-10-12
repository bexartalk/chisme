"""Build static/legal/{terms,privacy,community-rules}.html from legal/terms.md, legal/privacy.md and
legal/rules-and-copyright.md (Plato's final text; served at /terms, /privacy and /community-rules).
Dev-only dependency: pip install markdown. Re-run after editing the .md files or legal_contact.py:
    ./venv/bin/python tools/make_legal_pages.py
The wording is never changed here. The builder only: points the .md cross-links at the live pages, keeps the line
breaks in address blocks, and drops the street address line if legal_contact.SHOW_STREET_ADDRESS is False.
Pages use the app's own look (style.css: turquoise bar, papel picado, cards). No yellow."""
import pathlib
import re
import sys

import markdown

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import legal_contact as LC  # noqa: E402

PAGES = (("terms", "terms.md", "Terms of Service"), ("privacy", "privacy.md", "Privacy Policy"),
         ("community-rules", "rules-and-copyright.md", "Community Rules and Copyright Policy"))
LINKS = {"terms.md": "/terms", "privacy.md": "/privacy", "rules-and-copyright.md": "/community-rules"}
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#00C9CD">
<title>{title} · Chisme</title>
<meta name="robots" content="index,follow">
<link rel="icon" href="/static/icons/favicon.ico" sizes="any">
<link rel="stylesheet" href="/static/style.css">
<link rel="stylesheet" href="/static/social.css">
</head>
<body class="sx sx-plain sx-legal">
<header class="topbar sx-modbar"><div class="wrap"><a href="/" class="sx-modlink">‹ Back to Chisme</a></div><div class="picado" aria-hidden="true"></div></header>
<main class="wrap">
<nav class="sx-legal-nav" aria-label="Chisme legal pages"><a href="/terms"{c_terms}>Terms</a><a href="/privacy"{c_privacy}>Privacy</a><a href="/community-rules"{c_rules}>Community Rules</a><a href="/dmca">Report copyright</a></nav>
<article class="card sx-legal-body">
{body}
</article>
<footer class="sx-legal-foot"><p>Questions: <a href="mailto:{email}">{email}</a>. Copyright notices: <a href="/dmca">the DMCA form</a>.</p></footer>
</main>
</body>
</html>
"""


def build(md: str) -> str:
    if not LC.SHOW_STREET_ADDRESS:
        md = "\n".join(l for l in md.split("\n") if LC.STREET_LINE not in l)
    html = markdown.markdown(md, extensions=["tables", "nl2br"], output_format="html")
    for k, v in LINKS.items():
        html = html.replace(f'href="{k}"', f'href="{v}"')
    return html


def main() -> None:
    for slug, src, title in PAGES:
        md = (ROOT / "legal" / src).read_text(encoding="utf-8")
        cur = {"c_terms": "", "c_privacy": "", "c_rules": ""}
        cur[{"terms": "c_terms", "privacy": "c_privacy", "community-rules": "c_rules"}[slug]] = ' aria-current="page"'
        out = PAGE.format(title=title, body=build(md), email=LC.EMAIL, **cur)
        (ROOT / "static" / "legal" / f"{slug}.html").write_text(out, encoding="utf-8")
        print("wrote", f"static/legal/{slug}.html")


def effective(src: str) -> str:
    """The **Effective date:** in a legal .md as YYYY-MM-DD (the consent record's version)."""
    from datetime import datetime
    m = re.search(r"\*\*Effective date:\*\*\s*([A-Z][a-z]+ \d{1,2}, \d{4})", (ROOT / "legal" / src).read_text(encoding="utf-8"))
    return datetime.strptime(m.group(1), "%B %d, %Y").strftime("%Y-%m-%d") if m else ""


if __name__ == "__main__":
    main()
