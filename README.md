# UGC Cross-Poster

Record on your phone → share it to a Google Drive folder → it posts to **YouTube Shorts, Instagram Reels,
Facebook Reels** (and X if you want). Runs free in the cloud, so your laptop can stay off.

**How it works:** every 15 minutes the agent checks your Drive "inbox" folder. Any video in there gets
converted so every platform accepts it (iPhone .mov/HEVC → .mp4), then posted everywhere. When it's
done, the video moves into a `Posted` subfolder. If one platform fails, the others still post and it
retries only the failed one next time. `state.json` remembers what went where so nothing double-posts.

TikTok you post yourself, like you do now. (Automatic TikTok posting needs TikTok to approve your app.)

---

## Daily use (phone only)

1. Record your video.
2. **Optional caption:** in the Google Drive app, rename the file to your caption,
   e.g. `obsessed with this serum 😍 #skincare #ugc`. If you leave the camera name (`IMG_1234`),
   it uses `DEFAULT_CAPTION`.
3. Photos/Gallery → **Share** → **Drive** → pick your inbox folder. Done.

Within about 15 minutes it's live everywhere.

> **iPhone tip:** Settings → Camera → Formats → **Most Compatible**, and turn off **HDR Video**.
> Videos upload faster and colors look right on every platform.

---

## One-time setup (laptop, ~30 min)

### 1. Install
```
pip install -r requirements.txt
copy .env.example .env
```

### 2. Make the Drive inbox
In Google Drive, create a folder (e.g. `UGC Inbox`). Open it; the link looks like
`drive.google.com/drive/folders/1AbC...xyz`. Put the `1AbC...xyz` part in `.env` as `DRIVE_FOLDER_ID`.

### 3. Google login (YouTube + Drive, free)
1. Go to <https://console.cloud.google.com> → create a project.
2. **APIs & Services → Library** → enable **YouTube Data API v3** and **Google Drive API**.
3. **OAuth consent screen** → External → fill in the app name and your email → add your email as a test user.
4. Then click **Publish app** (status: *In production*). Skip this and Google logs you out every 7 days.
   You don't need Google's verification for personal use; you'll just see an "unverified app" warning
   when you log in → **Advanced → Go to app**.
5. **Credentials → Create credentials → OAuth client ID → Desktop app** → download the JSON into this folder.
6. Run `python auth_google.py client_secret_....json`, log in with the Google account that owns your
   YouTube channel and the Drive folder, and paste the 3 lines it prints into `.env`.

> YouTube may force uploads from new, unaudited API projects to private. If that happens, request
> an audit in the Google Cloud console. Default quota is about 6 uploads/day.

### 4. Instagram + Facebook (free)
Requirements: Instagram must be a **Business or Creator** account linked to a **Facebook Page**.

1. <https://developers.facebook.com> → **Create app** → type *Business*.
2. Add the **Instagram Graph API** / **Facebook Login for Business** products.
3. **Graph API Explorer** → pick your app → generate a User token with:
   `instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement, pages_manage_posts, business_management`
4. Access Token Debugger → **Extend** → paste the long-lived token as `META_ACCESS_TOKEN`.
5. In the Explorer run `me/accounts?fields=id,name,access_token,instagram_business_account`:
   - `id` → `FB_PAGE_ID`
   - `access_token` → `FB_PAGE_TOKEN`
   - `instagram_business_account.id` → `IG_USER_ID`

> The user token lasts ~60 days. When the log says "Session has expired", redo steps 3–5.

### 5. X / Twitter (optional, paid)
Video posting needs a paid X API plan. At <https://developer.x.com> create an app with **Read and write**
permissions, paste the 4 keys into `.env`, and add `x` to `POST_TO`.

---

## Test it

Start safe: set `POST_TO=youtube` and `YT_PRIVACY=private` in `.env`, drop one video in the Drive folder, then:

```
python crosspost.py --dry-run     # shows what it found and the caption, posts nothing
python crosspost.py --once        # posts for real
```

Check `crosspost.log` for links. If YouTube worked, add `instagram,facebook` to `POST_TO`, set
`YT_PRIVACY=public`, and test again with another video.

## Run it in the cloud (free, GitHub Actions)

`.github/workflows/crosspost.yml` runs `python crosspost.py --once` every 15 minutes on GitHub.

1. Upload your filled-in `.env` as hidden repo secrets: `gh secret set -f .env`
2. Start a run now instead of waiting: `gh workflow run crosspost` (or the repo's **Actions** tab → **crosspost** → **Run workflow**).

Re-run `gh secret set -f .env` whenever you change `.env`. GitHub may start scheduled runs a few minutes late.

## Files

| File | What it is |
|---|---|
| `crosspost.py` | The agent: check inbox → convert → post |
| `sources/drive.py` | Google Drive inbox (default) |
| `sources/tiktok.py` | TikTok profile watcher (`SOURCE=tiktok`, currently blocked by TikTok) |
| `convert.py` | Converts phone videos to H.264 .mp4 |
| `platforms/` | One uploader per platform |
| `state.json` | What's been posted where (delete a video's entry to repost it) |
| `crosspost.log` | Everything it did, with links to each post |
