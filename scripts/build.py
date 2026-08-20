#!/usr/bin/env python3
"""Χτίζει το στατικό σάιτ από τα JSON άρθρα στο data/articles/.

Χρήση:  python3 scripts/build.py
Έξοδος: site/ (index.html, κατηγορίες, άρθρα, style.css, feed.xml)
"""
import json, pathlib, html, re, datetime, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ART_DIR = ROOT / "data" / "articles"
SITE = ROOT / "site"
CFG = json.loads((ROOT / "scripts" / "feeds.json").read_text(encoding="utf-8"))

SITE_NAME = "Ροή"
SITE_TAGLINE = "Διεθνείς ειδήσεις τεχνολογίας και οικονομίας, στα ελληνικά."
BASE_URL = ""  # π.χ. "https://example.com" για απόλυτα links στο RSS

GR_MONTHS = ["Ιανουαρίου", "Φεβρουαρίου", "Μαρτίου", "Απριλίου", "Μαΐου", "Ιουνίου",
             "Ιουλίου", "Αυγούστου", "Σεπτεμβρίου", "Οκτωβρίου", "Νοεμβρίου", "Δεκεμβρίου"]
CAT_LABEL = {k: v["label"] for k, v in CFG.items()}
CAT_SLUG = {k: v["slug"] for k, v in CFG.items()}


def e(s):
    return html.escape(str(s or ""), quote=True)


def gr_date(iso):
    try:
        d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return ""
    return f"{d.day} {GR_MONTHS[d.month - 1]} {d.year}"


def load_articles():
    arts = []
    for p in sorted(ART_DIR.glob("*.json")):
        a = json.loads(p.read_text(encoding="utf-8"))
        a.setdefault("category", "tech")
        a.setdefault("sources", [])
        arts.append(a)
    arts.sort(key=lambda a: a.get("published", ""), reverse=True)
    return arts


def render_body(blocks):
    out = []
    for b in blocks:
        if isinstance(b, str):
            b = {"type": "p", "text": b}
        t = b.get("type", "p")
        if t == "p":
            out.append(f"<p>{inline(b['text'])}</p>")
        elif t == "h":
            out.append(f"<h2>{e(b['text'])}</h2>")
        elif t == "quote":
            who = f"<cite>{e(b['who'])}</cite>" if b.get("who") else ""
            out.append(f"<blockquote><p>{inline(b['text'])}</p>{who}</blockquote>")
        elif t == "ul":
            lis = "".join(f"<li>{inline(x)}</li>" for x in b["items"])
            out.append(f"<ul>{lis}</ul>")
        elif t == "facts":
            rows = "".join(
                f"<div class='fact'><dt>{e(k)}</dt><dd>{inline(v)}</dd></div>"
                for k, v in b["items"])
            out.append(f"<dl class='facts'><p class='facts-title'>Με μια ματιά</p>{rows}</dl>")
    return "\n".join(out)


def inline(s):
    s = e(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s


def shell(title, desc, body, depth=0, active=None):
    up = "../" * depth
    nav = "".join(
        f'<a href="{up}{CAT_SLUG[k]}/" class="{"on" if active == k else ""}">{e(v)}</a>'
        for k, v in CAT_LABEL.items())
    year = datetime.date.today().year
    return f"""<!DOCTYPE html>
<html lang="el">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="stylesheet" href="{up}style.css">
<link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{up}feed.xml">
</head>
<body>
<header class="site">
  <div class="wrap">
    <a class="brand" href="{up}index.html"><span class="mark"></span>{SITE_NAME}</a>
    <nav>{nav}<a href="{up}feed.xml" class="rss">RSS</a></nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="site">
  <div class="wrap">
    <p>{SITE_NAME} — {SITE_TAGLINE}</p>
    <p class="fine">Τα κείμενα συντάσσονται αυτόματα από AI agents με βάση διεθνείς πηγές, οι οποίες αναφέρονται σε κάθε άρθρο. Ενδέχεται να περιέχουν λάθη· για κρίσιμες αποφάσεις ανατρέξτε στην πρωτότυπη πηγή. © {year}</p>
  </div>
</footer>
</body>
</html>"""


def card(a, depth=0):
    up = "../" * depth
    cat = a["category"]
    return f"""<article class="card">
  <a class="cat" href="{up}{CAT_SLUG[cat]}/">{e(CAT_LABEL[cat])}</a>
  <h2><a href="{up}arthro/{e(a['slug'])}.html">{e(a['title'])}</a></h2>
  <p class="dek">{e(a.get('dek',''))}</p>
  <p class="meta"><time datetime="{e(a.get('published',''))}">{gr_date(a.get('published',''))}</time> · {e(a.get('reading','3 λεπτά ανάγνωση'))}</p>
</article>"""


def build():
    if not ART_DIR.exists():
        print("Δεν υπάρχουν άρθρα.", file=sys.stderr)
        return
    arts = load_articles()
    # Δεν σβήνουμε τον φάκελο (σε συνδεδεμένους δίσκους η διαγραφή μπορεί να
    # απαγορεύεται) — γράφουμε από πάνω και καθαρίζουμε ό,τι περισσεύει best-effort.
    (SITE / "arthro").mkdir(parents=True, exist_ok=True)
    keep = {f"{a['slug']}.html" for a in arts}
    for old in (SITE / "arthro").glob("*.html"):
        if old.name not in keep:
            try:
                old.unlink()
            except OSError:
                pass
    (SITE / "style.css").write_text(CSS, encoding="utf-8")

    # --- home ---
    lead = arts[0] if arts else None
    rest = arts[1:]
    body = f"""<section class="hero">
  <p class="kicker">Ενημέρωση από διεθνείς πηγές</p>
  <h1>{SITE_NAME}</h1>
  <p class="tagline">{SITE_TAGLINE}</p>
</section>"""
    if lead:
        body += f"""<a class="lead" href="arthro/{e(lead['slug'])}.html">
  <span class="cat">{e(CAT_LABEL[lead['category']])}</span>
  <h2>{e(lead['title'])}</h2>
  <p>{e(lead.get('dek',''))}</p>
  <p class="meta">{gr_date(lead.get('published',''))}</p>
</a>"""
    body += '<div class="grid">' + "".join(card(a) for a in rest) + "</div>"
    (SITE / "index.html").write_text(
        shell(f"{SITE_NAME} — {SITE_TAGLINE}", SITE_TAGLINE, body), encoding="utf-8")

    # --- categories ---
    for k, label in CAT_LABEL.items():
        sub = [a for a in arts if a["category"] == k]
        d = SITE / CAT_SLUG[k]
        d.mkdir(exist_ok=True)
        b = f'<section class="hero"><p class="kicker">Κατηγορία</p><h1>{e(label)}</h1><p class="tagline">{len(sub)} άρθρα</p></section>'
        b += '<div class="grid">' + "".join(card(a, 1) for a in sub) + "</div>"
        (d / "index.html").write_text(
            shell(f"{label} — {SITE_NAME}", label, b, depth=1, active=k), encoding="utf-8")

    # --- articles ---
    for i, a in enumerate(arts):
        srcs = "".join(
            f'<li><a href="{e(s["url"])}" rel="nofollow noopener" target="_blank">{e(s["title"])}</a>'
            f'<span class="pub">{e(s.get("publisher",""))}</span></li>' for s in a["sources"])
        related = [x for x in arts if x["slug"] != a["slug"] and x["category"] == a["category"]][:3]
        rel = "".join(f'<li><a href="{e(x["slug"])}.html">{e(x["title"])}</a></li>' for x in related)
        b = f"""<article class="post">
  <p class="crumbs"><a href="../{CAT_SLUG[a['category']]}/">{e(CAT_LABEL[a['category']])}</a></p>
  <h1>{e(a['title'])}</h1>
  <p class="dek">{e(a.get('dek',''))}</p>
  <p class="meta"><time datetime="{e(a.get('published',''))}">{gr_date(a.get('published',''))}</time>
     · {e(a.get('reading','3 λεπτά ανάγνωση'))} · Σύνταξη: {e(a.get('author','AI agent'))}</p>
  <div class="body">{render_body(a.get('body', []))}</div>
  <section class="sources">
    <h2>Πηγές στα αγγλικά</h2>
    <ul>{srcs}</ul>
  </section>
  {'<section class="related"><h2>Σχετικά</h2><ul>' + rel + '</ul></section>' if rel else ''}
</article>"""
        (SITE / "arthro" / f"{a['slug']}.html").write_text(
            shell(f"{a['title']} — {SITE_NAME}", a.get("dek", ""), b, depth=1,
                  active=a["category"]), encoding="utf-8")

    # --- RSS ---
    items = "".join(f"""<item>
<title>{e(a['title'])}</title>
<link>{BASE_URL}/arthro/{e(a['slug'])}.html</link>
<guid isPermaLink="false">{e(a['slug'])}</guid>
<description>{e(a.get('dek',''))}</description>
<category>{e(CAT_LABEL[a['category']])}</category>
<pubDate>{e(a.get('published',''))}</pubDate>
</item>""" for a in arts)
    (SITE / "feed.xml").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>{SITE_NAME}</title><link>{BASE_URL}/</link>
<description>{SITE_TAGLINE}</description><language>el</language>
{items}
</channel></rss>""", encoding="utf-8")

    print(f"OK: {len(arts)} άρθρα → {SITE}")


CSS = """
:root{
  --bg:#fbfaf8; --panel:#fff; --ink:#16181d; --muted:#6b7180; --line:#e7e4de;
  --accent:#12603f; --accent-soft:#e8f1ec;
}
@media (prefers-color-scheme:dark){
  :root{--bg:#111316;--panel:#181b20;--ink:#e9eaed;--muted:#9aa1ae;--line:#282c33;
        --accent:#5fd39b;--accent-soft:#16302588;}
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font:16px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:1040px;margin:0 auto;padding:0 20px}
a{color:inherit}
header.site{border-bottom:1px solid var(--line);background:var(--panel);position:sticky;top:0;z-index:5}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;height:62px;flex-wrap:wrap}
.brand{font-weight:700;font-size:20px;letter-spacing:-.02em;text-decoration:none;display:flex;align-items:center;gap:9px}
.mark{width:11px;height:11px;border-radius:50%;background:var(--accent);display:inline-block}
header nav{display:flex;gap:6px;flex-wrap:wrap}
header nav a{text-decoration:none;color:var(--muted);font-size:14px;padding:6px 11px;border-radius:99px}
header nav a:hover{background:var(--accent-soft);color:var(--ink)}
header nav a.on{background:var(--accent-soft);color:var(--ink);font-weight:600}
header nav a.rss{border:1px solid var(--line)}
.hero{padding:52px 0 18px;border-bottom:1px solid var(--line);margin-bottom:28px}
.kicker{margin:0;color:var(--accent);font-size:12.5px;font-weight:700;letter-spacing:.11em;text-transform:uppercase}
.hero h1{margin:.25em 0 .1em;font-size:clamp(34px,6vw,52px);letter-spacing:-.03em;line-height:1.08}
.tagline{margin:0;color:var(--muted);font-size:17px}
.lead{display:block;text-decoration:none;background:var(--panel);border:1px solid var(--line);
 border-radius:16px;padding:30px;margin-bottom:30px;transition:.15s}
.lead:hover{border-color:var(--accent);transform:translateY(-2px)}
.lead h2{margin:.35em 0 .3em;font-size:clamp(24px,3.6vw,34px);line-height:1.2;letter-spacing:-.02em}
.lead p{margin:0;color:var(--muted)}
.cat{display:inline-block;font-size:11.5px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;
 color:var(--accent);background:var(--accent-soft);padding:4px 10px;border-radius:99px;text-decoration:none}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:18px;padding-bottom:50px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px;transition:.15s}
.card:hover{border-color:var(--accent)}
.card h2{margin:.55em 0 .35em;font-size:20px;line-height:1.3;letter-spacing:-.01em}
.card h2 a{text-decoration:none}
.card h2 a:hover{color:var(--accent)}
.dek{color:var(--muted);margin:0 0 12px}
.meta{color:var(--muted);font-size:13.5px;margin:0}
.post{max-width:700px;margin:0 auto;padding:42px 0 60px}
.crumbs{margin:0 0 14px}
.crumbs a{color:var(--accent);text-decoration:none;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.08em}
.post h1{font-size:clamp(29px,4.6vw,44px);line-height:1.14;letter-spacing:-.025em;margin:0 0 .3em}
.post .dek{font-size:19px;line-height:1.55}
.post .meta{padding-bottom:22px;border-bottom:1px solid var(--line)}
.body{font-size:17.5px}
.body p{margin:1.15em 0}
.body h2{font-size:23px;margin:1.8em 0 .5em;letter-spacing:-.015em}
.body ul{padding-left:1.15em}
.body li{margin:.5em 0}
blockquote{margin:1.6em 0;padding:2px 0 2px 20px;border-left:3px solid var(--accent);color:var(--ink)}
blockquote p{margin:0;font-size:19px;line-height:1.5}
blockquote cite{display:block;margin-top:9px;font-size:14px;color:var(--muted);font-style:normal}
.facts{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin:1.8em 0}
.facts-title{margin:0 0 12px;font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}
.fact{display:flex;gap:14px;padding:7px 0;border-top:1px solid var(--line);font-size:15.5px}
.fact:first-of-type{border-top:0}
.fact dt{flex:0 0 42%;color:var(--muted)}
.fact dd{margin:0;font-weight:600}
.sources,.related{margin-top:44px;padding-top:22px;border-top:1px solid var(--line)}
.sources h2,.related h2{font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 12px}
.sources ul,.related ul{list-style:none;padding:0;margin:0}
.sources li,.related li{padding:9px 0;border-bottom:1px solid var(--line);font-size:15px}
.sources a,.related a{color:var(--accent);text-decoration:none}
.sources a:hover,.related a:hover{text-decoration:underline}
.pub{display:block;color:var(--muted);font-size:13px}
footer.site{border-top:1px solid var(--line);background:var(--panel);padding:26px 0;margin-top:20px}
footer p{margin:0 0 6px;color:var(--muted);font-size:14px}
footer .fine{font-size:12.5px;line-height:1.6}
@media(max-width:600px){.post{padding-top:26px}.hero{padding-top:34px}}
"""

if __name__ == "__main__":
    build()
