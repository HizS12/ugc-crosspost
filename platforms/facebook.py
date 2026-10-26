"""Facebook Page Reels via the Graph API."""

import os

from .meta import graph, upload_bytes


def post(path, caption):
    page = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_TOKEN"]

    start = graph("POST", f"{page}/video_reels", upload_phase="start", access_token=token)
    upload_bytes(start["upload_url"], path, token)
    graph(
        "POST", f"{page}/video_reels",
        upload_phase="finish", video_id=start["video_id"], video_state="PUBLISHED",
        description=caption, access_token=token,
    )
    return f"https://www.facebook.com/reel/{start['video_id']}"
