"""Shared helpers for the Meta Graph API (Instagram + Facebook)."""

import os

import requests

GRAPH = "https://graph.facebook.com"
RUPLOAD = "https://rupload.facebook.com"


def version():
    return (os.getenv("META_GRAPH_VERSION") or "v23.0")


def graph(method, path, **params):
    r = requests.request(method, f"{GRAPH}/{version()}/{path}", params=params, timeout=60)
    data = r.json()
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(data.get("error", {}).get("message", r.text))
    return data


def upload_bytes(url, path, token):
    """Push the local file to Meta's resumable upload host in one request."""
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        r = requests.post(
            url,
            headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size)},
            data=f,
            timeout=600,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"upload failed: {r.text}")
    return r.json()
