"""X (Twitter) video post via API v2 chunked media upload. Needs a paid X API tier."""

import os
import time

import requests
from requests_oauthlib import OAuth1

API = "https://api.x.com/2"
CHUNK = 4 * 1024 * 1024


def _auth():
    return OAuth1(
        os.environ["X_API_KEY"], os.environ["X_API_SECRET"],
        os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_SECRET"],
    )


def _check(r):
    if r.status_code >= 400:
        raise RuntimeError(r.text)
    return r.json() if r.content else {}


def post(path, caption):
    auth = _auth()
    size = os.path.getsize(path)

    init = _check(requests.post(
        f"{API}/media/upload/initialize", auth=auth,
        json={"media_type": "video/mp4", "total_bytes": size, "media_category": "tweet_video"},
    ))
    media_id = init["data"]["id"]

    with open(path, "rb") as f:
        i = 0
        while chunk := f.read(CHUNK):
            _check(requests.post(
                f"{API}/media/upload/{media_id}/append", auth=auth,
                data={"segment_index": i}, files={"media": chunk},
            ))
            i += 1

    info = _check(requests.post(f"{API}/media/upload/{media_id}/finalize", auth=auth))["data"]
    while (state := info.get("processing_info", {}).get("state")) in ("pending", "in_progress"):
        time.sleep(info["processing_info"].get("check_after_secs", 5))
        info = _check(requests.get(f"{API}/media/upload", auth=auth, params={"command": "STATUS", "media_id": media_id}))["data"]
    if state == "failed":
        raise RuntimeError(f"X rejected the video: {info['processing_info']}")

    tweet = _check(requests.post(f"{API}/tweets", auth=auth, json={"text": caption, "media": {"media_ids": [media_id]}}))
    return f"https://x.com/i/status/{tweet['data']['id']}"
