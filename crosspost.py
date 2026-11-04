"""
UGC cross-posting agent.

Record on your phone, drop the video in your Google Drive inbox folder, and it gets
posted to every platform you've enabled (YouTube Shorts, Instagram Reels, Facebook Reels, X).

SOURCE=drive (default) watches the Drive folder. SOURCE=tiktok watches your TikTok profile
instead (currently blocked by TikTok, see sources/tiktok.py).

Usage:
    python crosspost.py            # run forever, checking every CHECK_EVERY_MINUTES
    python crosspost.py --once     # check one time and exit (what the cloud runs)
    python crosspost.py --dry-run  # show what would be posted, post nothing
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

import convert
from platforms import facebook, instagram, x_twitter, youtube
from sources import drive, tiktok

ROOT = Path(__file__).parent
DOWNLOADS = ROOT / "downloads"
STATE_FILE = ROOT / "state.json"

load_dotenv(ROOT / ".env")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles choke on emoji captions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(ROOT / "crosspost.log", encoding="utf-8")],
)
log = logging.getLogger("crosspost")

PLATFORMS = {
    "youtube": youtube,
    "instagram": instagram,
    "facebook": facebook,
    "x": x_twitter,
}

SOURCES = {"drive": drive, "tiktok": tiktok}


# ---------- state ----------

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"initialized": False, "videos": {}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------- captions ----------

def captions_for(caption):
    """Per-platform caption variants."""
    base = caption.strip()
    extra = (os.getenv("EXTRA_HASHTAGS") or "").strip()
    if extra:
        base = f"{base} {extra}".strip()
    hashtags_removed = re.sub(r"#\w+", "", base).strip()
    title = (hashtags_removed or (os.getenv("DEFAULT_TITLE") or "New video")).split("\n")[0][:90]
    return {
        "youtube": {"title": f"{title} #Shorts"[:100], "description": base},
        "instagram": {"caption": base[:2200]},
        "facebook": {"caption": base},
        "x": {"caption": base[:280]},
    }


# ---------- main loop ----------

def enabled_platforms():
    names = [p.strip().lower() for p in (os.getenv("POST_TO") or "youtube,instagram,facebook").split(",") if p.strip()]
    unknown = [n for n in names if n not in PLATFORMS]
    if unknown:
        log.warning("Ignoring unknown platforms in POST_TO: %s", ", ".join(unknown))
    return [n for n in names if n in PLATFORMS]


def process(source, item, state, platforms, dry_run):
    record = state["videos"].setdefault(item["id"], {"name": item.get("name") or item.get("url"), "posted": {}})
    todo = [p for p in platforms if p not in record["posted"]]
    if not todo:
        source.mark_done(item)
        return

    log.info("New video %s -> %s", item.get("name") or item["id"], ", ".join(todo))
    if dry_run:
        log.info("  caption: %r", item.get("caption"))
        return

    original = source.download(item, DOWNLOADS)
    path = convert.for_upload(original)
    caps = captions_for(item.get("caption") or "")

    for name in todo:
        try:
            result = PLATFORMS[name].post(path, **caps[name])
            record["posted"][name] = result
            record.get("errors", {}).pop(name, None)
            log.info("  %-9s OK  %s", name, result)
        except Exception as e:  # keep going so one broken platform doesn't block the others
            record.setdefault("errors", {})[name] = str(e)
            log.error("  %-9s FAILED  %s", name, e)
        save_state(state)

    if all(p in record["posted"] for p in platforms):
        source.mark_done(item)
        if (os.getenv("DELETE_AFTER_POST") or "true").lower() == "true":
            for f in {original, path}:
                f.unlink(missing_ok=True)


def check_once(dry_run=False, backfill=False):
    source_name = (os.getenv("SOURCE") or "drive").lower()
    source = SOURCES[source_name]
    needed = "DRIVE_FOLDER_ID" if source_name == "drive" else "TIKTOK_USERNAME"
    if not os.getenv(needed):
        # exit quietly so the cloud schedule doesn't fail every 15 min before secrets are added
        log.warning("%s isn't set (in .env, or as a GitHub secret). Nothing to do.", needed)
        return

    platforms = enabled_platforms()
    state = load_state()
    items = source.list_new()
    log.info("Checked %s: %d video(s) waiting", source_name, len(items))

    # TikTok only: on first run, remember what's already there so your backlog isn't reposted.
    # (The Drive inbox only holds what you put there, so everything in it gets posted.)
    if source_name == "tiktok" and not state["initialized"] and not backfill:
        if dry_run:
            log.info("First run (dry run): would mark %d existing videos as already posted.", len(items))
            return
        for v in items:
            state["videos"].setdefault(v["id"], {"name": v["url"], "posted": {p: "skipped (existed before agent)" for p in platforms}})
        state["initialized"] = True
        save_state(state)
        log.info("First run: marked %d existing videos as already posted.", len(items))
        return

    state["initialized"] = True
    for item in items:
        try:
            process(source, item, state, platforms, dry_run)
        except Exception as e:
            log.error("Couldn't process %s: %s", item.get("name") or item["id"], e)
    if not dry_run:
        save_state(state)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="check one time and exit")
    ap.add_argument("--dry-run", action="store_true", help="don't post anything")
    ap.add_argument("--backfill", action="store_true", help="(tiktok) on first run, also post videos that already exist")
    args = ap.parse_args()

    if args.once or args.dry_run:
        check_once(args.dry_run, args.backfill)
        return

    minutes = int((os.getenv("CHECK_EVERY_MINUTES") or "15"))
    log.info("Checking every %d min. Ctrl+C to stop.", minutes)
    while True:
        try:
            check_once(backfill=args.backfill)
        except Exception as e:
            log.error("Check failed: %s", e)
        time.sleep(minutes * 60)


if __name__ == "__main__":
    main()
