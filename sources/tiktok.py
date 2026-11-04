"""
TikTok profile watcher (SOURCE=tiktok). Uses yt-dlp to read your public profile.
Note: TikTok was blocking yt-dlp as of Nov 2026 (yt-dlp issues #17500 / #17393),
so this source may not work until yt-dlp ships a fix. `pip install -U yt-dlp` to check.
"""

import os
from pathlib import Path

import yt_dlp

# TikTok-only tags that look spammy (or get suppressed) elsewhere
TIKTOK_ONLY_TAGS = {"#fyp", "#foryou", "#foryoupage", "#fypシ", "#fypage", "#tiktok", "#viral", "#xyzbca", "#tiktokmademebuyit"}


def list_new(limit=10):
    """Newest videos on the profile, oldest first. Caption is filled in on download."""
    username = (os.getenv("TIKTOK_USERNAME") or "").lstrip("@")
    opts = {"quiet": True, "extract_flat": True, "playlistend": limit, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.tiktok.com/@{username}", download=False)
    items = [
        {"id": str(e["id"]), "url": e.get("url") or f"https://www.tiktok.com/@{username}/video/{e['id']}", "caption": None}
        for e in info.get("entries") or []
        if e and e.get("id")
    ]
    return list(reversed(items))


def download(item, dest_dir):
    dest_dir.mkdir(exist_ok=True)
    opts = {
        "quiet": True,
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        # prefer the clean (no watermark) h264 mp4 so every platform accepts it
        "format": "bv*[vcodec^=h264]+ba/b[ext=mp4]/b",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(item["url"], download=True)
        path = Path(ydl.prepare_filename(info)).with_suffix(".mp4")
    words = (info.get("description") or info.get("title") or "").split()
    item["caption"] = " ".join(w for w in words if w.lower() not in TIKTOK_ONLY_TAGS)
    return path


def mark_done(item):
    pass  # nothing to move; state.json remembers it
