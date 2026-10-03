"""v49.12: build static/legal/privacy.html and terms.html from legal/privacy.md and legal/terms.md (served at /privacy
and /terms). Dev-only dependency: pip install markdown. Re-run after editing the .md files:
    ./venv/bin/python tools/make_legal_pages.py
TODO markers (<mark class="todo">) are the owner's open items; they show highlighted on the page until filled in."""
import pathlib
import markdown

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Chisme</title>
<meta name="robots" content="index,follow">
<link rel="icon" href="/static/icons/favicon.ico" sizes="any">
<style>
  :root {{ color-scheme: light dark; --ink:#111; --bg:#fffaf3; --turq:#00a3a6; --pink:#d81b60; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --ink:#f2f2f2; --bg:#121212; --turq:#3fd6d9; --pink:#ff7aa8; }} }}
  body {{ margin:0; background:var(--bg); color:var(--ink); font:17px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
  main {{ max-width:760px; margin:0 auto; padding:20px 18px 64px; }}
  .top {{ display:flex; gap:14px; flex-wrap:wrap; align-items:center; margin-bottom:8px; font-weight:700; }}
  a {{ color:var(--pink); text-underline-offset:2px; }}
  .top a {{ display:inline-block; padding:10px 0; }}
  h1 {{ font-size:1.7rem; line-height:1.2; margin:.3em 0 .4em; }}
  h2 {{ font-size:1.2rem; margin:1.6em 0 .4em; border-bottom:3px solid var(--turq); padding-bottom:4px; }}
  table {{ border-collapse:collapse; width:100%; display:block; overflow-x:auto; font-size:.92rem; }}
  th, td {{ border:1px solid color-mix(in srgb, var(--ink) 25%, transparent); padding:8px; vertical-align:top; text-align:left; min-width:9em; }}
  mark.todo {{ background:#ffe08a; color:#000; padding:0 .25em; border-radius:4px; font-weight:700; }}
  footer {{ margin-top:40px; font-size:.9rem; }}   /* v49.12: no opacity (the email link was 4.0:1) */
</style>
</head>
<body>
<main>
<nav class="top" aria-label="Chisme"><a href="/">‹ Back to Chisme</a><a href="/privacy">Privacy Policy</a><a href="/terms">Terms of Use</a></nav>
{body}
<footer><p>Questions or a takedown request: <a href="mailto:bexartalkradio@gmail.com">bexartalkradio@gmail.com</a>. This page isn't legal advice.</p></footer>
</main>
</body>
</html>
"""

for name, title in (("privacy", "Privacy Policy"), ("terms", "Terms of Use")):
    md = (ROOT / "legal" / f"{name}.md").read_text(encoding="utf-8")
    body = markdown.markdown(md, extensions=["tables"], output_format="html")
    (ROOT / "static" / "legal" / f"{name}.html").write_text(PAGE.format(title=title, body=body), encoding="utf-8")
    print("wrote", f"static/legal/{name}.html")
