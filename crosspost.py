"""
UGC cross-posting agent.

Watches your TikTok profile. When a new video shows up, it downloads it
and re-posts it to every platform you've enabled in .env
(YouTube Shorts, Instagram Reels, Facebook Reels, X).

Usage:
    python crosspost.py            # run forever, checking every CHECK_EVERY_MINUTES
    python crosspost.py --once     # check one time and exit (good for Task Scheduler)
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

import yt_dlp
from dotenv import load_dotenv

from platforms import facebook, instagram, x_twitter, youtube

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

# TikTok-only tags that look spammy (or get suppressed) elsewhere
TIKTOK_ONLY_TAGS = {"#fyp", "#foryou", "#foryoupage", "#fypシ", "#fypage", "#tiktok", "#viral", "#xyzbca", "#tiktokmademebuyit"}


# ---------- state ----------

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"initialized": False, "videos": {}}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------- tiktok ----------

def list_tiktok_videos(username, limit=10):
    """Return the newest videos on the profile, newest first."""
    opts = {"quiet": True, "extract_flat": True, "playlistend": limit, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.tiktok.com/@{username}", download=False)
    return [
        {"id": str(e["id"]), "url": e.get("url") or f"https://www.tiktok.com/@{username}/video/{e['id']}"}
        for e in info.get("entries") or []
        if e and e.get("id")
    ]


def download_tiktok(url):
    """Download one video. Returns (file_path, caption)."""
    DOWNLOADS.mkdir(exist_ok=True)
    opts = {
        "quiet": True,
        "outtmpl": str(DOWNLOADS / "%(id)s.%(ext)s"),
        # prefer the clean (no watermark) h264 mp4 so every platform accepts it
        "format": "bv*[vcodec^=h264]+ba/b[ext=mp4]/b",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info)).with_suffix(".mp4")
    caption = info.get("description") or info.get("title") or ""
    return path, caption


# ---------- captions ----------

def clean_caption(caption):
    words = [w for w in caption.split() if w.lower() not in TIKTOK_ONLY_TAGS]
    text = " ".join(words).strip()
    extra = (os.getenv("EXTRA_HASHTAGS") or "").strip()
    if extra:
        text = f"{text} {extra}".strip()
    return text


def captions_for(caption):
    """Per-platform caption variants."""
    base = clean_caption(caption)
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


def process(video, state, platforms, dry_run):
    vid = video["id"]
    record = state["videos"].setdefault(vid, {"url": video["url"], "posted": {}})
    todo = [p for p in platforms if p not in record["posted"]]
    if not todo:
        return

    log.info("New TikTok %s -> posting to %s", vid, ", ".join(todo))
    if dry_run:
        return

    path, caption = download_tiktok(video["url"])
    caps = captions_for(caption)

    for name in todo:
        try:
            result = PLATFORMS[name].post(path, **caps[name])
            record["posted"][name] = result
            log.info("  %-9s OK  %s", name, result)
        except Exception as e:  # keep going so one broken platform doesn't block the others
            record.setdefault("errors", {})[name] = str(e)
            log.error("  %-9s FAILED  %s", name, e)
        save_state(state)

    if all(p in record["posted"] for p in platforms) and (os.getenv("DELETE_AFTER_POST") or "true").lower() == "true":
        path.unlink(missing_ok=True)


def check_once(dry_run=False, backfill=False):
    username = (os.getenv("TIKTOK_USERNAME") or "").lstrip("@")
    if not username:
        # exit quietly so the cloud schedule doesn't fail every 15 min before secrets are added
        log.warning("TIKTOK_USERNAME isn't set (in .env, or as a GitHub secret). Nothing to do.")
        return

    platforms = enabled_platforms()
    state = load_state()
    videos = list_tiktok_videos(username)
    log.info("Checked @%s: %d recent videos", username, len(videos))

    # First run: remember what's already there so we don't dump your whole backlog everywhere.
    if not state["initialized"] and not backfill:
        if dry_run:
            log.info("First run (dry run): would mark %d existing videos as already posted.", len(videos))
            return
        for v in videos:
            state["videos"].setdefault(v["id"], {"url": v["url"], "posted": {p: "skipped (existed before agent)" for p in platforms}})
        state["initialized"] = True
        save_state(state)
        log.info("First run: marked %d existing videos as already posted. New ones will be cross-posted.", len(videos))
        return

    state["initialized"] = True
    for video in reversed(videos):  # oldest first so platforms keep the same order
        process(video, state, platforms, dry_run)
    if not dry_run:
        save_state(state)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="check one time and exit")
    ap.add_argument("--dry-run", action="store_true", help="don't post anything")
    ap.add_argument("--backfill", action="store_true", help="on first run, also post videos that already exist")
    args = ap.parse_args()

    if args.once or args.dry_run:
        check_once(args.dry_run, args.backfill)
        return

    minutes = int((os.getenv("CHECK_EVERY_MINUTES") or "15"))
    log.info("Watching TikTok every %d min. Ctrl+C to stop.", minutes)
    while True:
        try:
            check_once(backfill=args.backfill)
        except Exception as e:
            log.error("Check failed: %s", e)
        time.sleep(minutes * 60)


if __name__ == "__main__":
    main()
