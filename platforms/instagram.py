"""Instagram Reels via the Instagram Graph API (Business or Creator account)."""

import os
import time

from .meta import RUPLOAD, graph, upload_bytes, version


def post(path, caption):
    ig_user = os.environ["IG_USER_ID"]
    token = os.environ["META_ACCESS_TOKEN"]

    container = graph(
        "POST", f"{ig_user}/media",
        media_type="REELS", upload_type="resumable", caption=caption,
        share_to_feed="true", access_token=token,
    )
    upload_bytes(f"{RUPLOAD}/ig-api-upload/{version()}/{container['id']}", path, token)

    # Instagram processes the video before it can be published
    for _ in range(60):
        status = graph("GET", container["id"], fields="status_code,status", access_token=token)
        if status.get("status_code") == "FINISHED":
            break
        if status.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram rejected the video: {status.get('status')}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram took too long to process the video")

    media = graph("POST", f"{ig_user}/media_publish", creation_id=container["id"], access_token=token)
    link = graph("GET", media["id"], fields="permalink", access_token=token)
    return link.get("permalink", media["id"])
