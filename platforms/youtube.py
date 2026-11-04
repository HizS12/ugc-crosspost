"""YouTube Shorts upload via the YouTube Data API v3."""

import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .google_auth import credentials


def post(path, title, description):
    body = {
        "snippet": {"title": title, "description": description, "categoryId": (os.getenv("YT_CATEGORY_ID") or "22")},
        "status": {"privacyStatus": (os.getenv("YT_PRIVACY") or "public"), "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(path), mimetype="video/mp4", chunksize=-1, resumable=True)
    client = build("youtube", "v3", credentials=credentials(), cache_discovery=False)
    request = client.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return f"https://youtube.com/shorts/{response['id']}"
