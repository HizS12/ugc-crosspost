"""
Google Drive inbox: drop videos from your phone into a Drive folder and they get posted.

Caption: rename the file in the Drive app to the caption you want
("obsessed with this serum 😍 #skincare.mp4"). Camera names like IMG_1234 / VID_2026...
fall back to DEFAULT_CAPTION. A .txt file with the same name also works as the caption.
Once a video is posted everywhere it's moved into a "Posted" subfolder.
"""

import io
import os
import re
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from platforms.google_auth import credentials

POSTED_FOLDER = "Posted"
CAMERA_PREFIXES = {"img", "vid", "pxl", "mov", "dsc", "dji", "video", "trim", "rpreplay", "screenrecording", "screen", "recording"}


def is_camera_name(stem):
    """IMG_1234, VID_20261104_1011, RPReplay_Final1699, trim.8F2A, 20261104_101112 ..."""
    tokens = [t for t in re.split(r"[\s_\-.]+", stem.lower()) if t]
    if not tokens:
        return True
    rest = tokens[1:] if tokens[0] in CAMERA_PREFIXES else tokens
    return all(re.search(r"\d", t) for t in rest)


def _service():
    return build("drive", "v3", credentials=credentials(), cache_discovery=False)


def _folder_id():
    return os.environ["DRIVE_FOLDER_ID"]


def _children(svc, query):
    files, token = [], None
    while True:
        resp = svc.files().list(
            q=f"'{_folder_id()}' in parents and trashed = false and ({query})",
            fields="nextPageToken, files(id, name, mimeType, createdTime, description)",
            orderBy="createdTime", pageToken=token, pageSize=100,
        ).execute()
        files += resp.get("files", [])
        token = resp.get("nextPageToken")
        if not token:
            return files


def caption_from_name(name, sidecar_text=None):
    if sidecar_text and sidecar_text.strip():
        return sidecar_text.strip()
    stem = Path(name).stem.strip()
    if is_camera_name(stem):
        return os.getenv("DEFAULT_CAPTION") or ""
    return stem


def list_new():
    """Videos waiting in the inbox folder, oldest first."""
    svc = _service()
    videos = _children(svc, "mimeType contains 'video/'")
    texts = {Path(f["name"]).stem: f for f in _children(svc, "mimeType = 'text/plain'")}
    items = []
    for v in videos:
        txt = texts.get(Path(v["name"]).stem)
        sidecar = svc.files().get_media(fileId=txt["id"]).execute().decode("utf-8", "replace") if txt else None
        items.append({
            "id": v["id"],
            "name": v["name"],
            "caption": caption_from_name(v["name"], sidecar or v.get("description")),
            "sidecar_id": txt["id"] if txt else None,
        })
    return items


def download(item, dest_dir):
    dest_dir.mkdir(exist_ok=True)
    path = dest_dir / f"{item['id']}{Path(item['name']).suffix.lower() or '.mp4'}"
    request = _service().files().get_media(fileId=item["id"])
    with io.FileIO(path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request, chunksize=16 * 1024 * 1024)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return path


def mark_done(item):
    """Move the video (and its caption .txt) into the Posted subfolder."""
    svc = _service()
    found = _children(svc, f"mimeType = 'application/vnd.google-apps.folder' and name = '{POSTED_FOLDER}'")
    posted = found[0]["id"] if found else svc.files().create(
        body={"name": POSTED_FOLDER, "mimeType": "application/vnd.google-apps.folder", "parents": [_folder_id()]},
        fields="id",
    ).execute()["id"]
    for fid in filter(None, [item["id"], item.get("sidecar_id")]):
        svc.files().update(fileId=fid, addParents=posted, removeParents=_folder_id(), fields="id").execute()
