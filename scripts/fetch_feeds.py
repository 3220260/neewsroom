#!/usr/bin/env python3
"""Κατεβάζει τα RSS feeds και βγάζει λίστα υποψήφιων άρθρων (αγγλικά)
που ΔΕΝ έχουν ήδη καλυφθεί. Output: data/candidates.json"""
import json, hashlib, sys, time, datetime, pathlib, re
import feedparser

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
FEEDS = json.loads((ROOT / "scripts" / "feeds.json").read_text(encoding="utf-8"))
SEEN_PATH = DATA / "seen.json"
MAX_AGE_HOURS = int(sys.argv[1]) if len(sys.argv) > 1 else 36
PER_CATEGORY = 12


def load_seen():
    if SEEN_PATH.exists():
        return json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    return {}


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", (t or "").lower())).strip()


def key(entry):
    return hashlib.sha1(norm(entry.get("title", "")).encode()).hexdigest()[:16]


def entry_time(e):
    for f in ("published_parsed", "updated_parsed"):
        if e.get(f):
            return time.mktime(e[f])
    return None


def clean(html):
    txt = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", txt).strip()[:900]


def main():
    seen = load_seen()
    now = time.time()
    out = {}
    for cat, cfg in FEEDS.items():
        items = []
        for url in cfg["feeds"]:
            try:
                d = feedparser.parse(url)
            except Exception as ex:
                print(f"[warn] {url}: {ex}", file=sys.stderr)
                continue
            src = clean(d.feed.get("title", "")) or url.split("/")[2]
            for e in d.entries[:25]:
                ts = entry_time(e)
                if ts and (now - ts) / 3600 > MAX_AGE_HOURS:
                    continue
                k = key(e)
                if not e.get("title") or k in seen:
                    continue
                items.append({
                    "key": k,
                    "title": e.get("title", "").strip(),
                    "url": e.get("link", ""),
                    "source": src,
                    "summary": clean(e.get("summary", "")),
                    "published": datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z" if ts else None,
                    "ts": ts or 0,
                })
        # dedupe within category, newest first
        uniq = {}
        for it in sorted(items, key=lambda x: -x["ts"]):
            uniq.setdefault(it["key"], it)
        out[cat] = list(uniq.values())[:PER_CATEGORY]
        print(f"[info] {cat}: {len(out[cat])} candidates", file=sys.stderr)

    (DATA / "candidates.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
