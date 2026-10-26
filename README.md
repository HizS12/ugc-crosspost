# UGC Cross-Poster

Post on TikTok → it shows up on YouTube Shorts, Instagram Reels, Facebook Reels (and X if you want).

**How it works:** every 15 minutes it checks your public TikTok profile. When there's a video it hasn't seen,
it downloads the clean (no watermark) mp4, cleans the caption (drops `#fyp`, `#foryou`, etc.), and uploads it
to each platform. `state.json` remembers what's been posted so nothing double-posts, and if one platform fails
it retries just that one on the next check.

On the **first run** it marks your existing TikToks as "already done", so it won't flood your other accounts
with your backlog. Use `--backfill` if you actually want that.

---

## 1. Install

```
pip install -r requirements.txt
copy .env.example .env
```

Put your TikTok username in `.env`, then test it (posts nothing):

```
python crosspost.py --dry-run
```

## 2. Connect each platform

Only set up the ones you list in `POST_TO`.

### YouTube Shorts (free, ~10 min)
1. Go to <https://console.cloud.google.com> → new project → **APIs & Services → Library** → enable **YouTube Data API v3**.
2. **OAuth consent screen** → External → add your own Google email as a test user.
3. **Credentials → Create credentials → OAuth client ID → Desktop app** → download the JSON.
4. Run `python auth_youtube.py path\to\that.json`, log in, and paste the 3 lines it prints into `.env`.

> Heads-up: until Google verifies your app, uploads from unverified API projects may be forced to private.
> Request an audit in the console if that happens. Default quota is ~6 uploads/day.

### Instagram Reels + Facebook Reels (free, ~20 min)
Requirements: Instagram must be a **Business or Creator** account linked to a **Facebook Page**.

1. Go to <https://developers.facebook.com> → **Create app** → type *Business*.
2. Add the **Instagram Graph API** / **Facebook Login for Business** products.
3. Open **Graph API Explorer**, pick your app, and generate a User token with:
   `instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement, pages_manage_posts, business_management`
4. Swap it for a long-lived token (Access Token Debugger → *Extend*). Paste it as `META_ACCESS_TOKEN`.
5. In the Explorer run `me/accounts?fields=id,name,access_token,instagram_business_account`:
   - `id` → `FB_PAGE_ID`
   - `access_token` → `FB_PAGE_TOKEN`
   - `instagram_business_account.id` → `IG_USER_ID`

> Page tokens taken from a long-lived user token don't expire. The user token lasts ~60 days, so refresh
> `META_ACCESS_TOKEN` every couple months (the log will say "Session has expired" when it's time).

### X / Twitter (paid)
Posting video needs a paid X API plan. At <https://developer.x.com> create an app with **Read and write**
permissions, then paste the API key/secret and access token/secret into `.env` and add `x` to `POST_TO`.

## 3. Run it

Leave it running in a terminal:

```
python crosspost.py
```

**Or** have Windows run it automatically (no terminal needed): open **Task Scheduler → Create Basic Task**,
trigger *Daily*, then in the task's properties set *Repeat task every 15 minutes*. Action: *Start a program*
→ `run.bat`, arguments `--once`. Tick *Run whether user is logged on or not* if you want it running in the background.

Your PC has to be on for this to work. For 24/7 without your PC, use the free cloud option below.

## 4. Run it free in the cloud (GitHub Actions)

`.github/workflows/crosspost.yml` runs the agent every 15 minutes on GitHub's servers, free.

1. Push this folder to a GitHub repo. Make it **public** for unlimited free minutes (your tokens stay
   hidden in secrets; only the code and `state.json` are visible). A private repo gets 2,000 free
   minutes/month, so change the cron to `*/30 * * * *` if you go private.
2. Upload your filled-in `.env` as repo secrets in one command:
   ```
   gh secret set -f .env
   ```
3. On GitHub → **Actions** tab → **crosspost** → **Run workflow** to test it right away.

Notes: GitHub can run scheduled jobs a few minutes late. Whenever you change a token in `.env`, run
`gh secret set -f .env` again.

## Files

| File | What it is |
|---|---|
| `crosspost.py` | The agent: watch TikTok → download → post |
| `platforms/` | One uploader per platform |
| `state.json` | What's been posted where (delete a video's entry to repost it) |
| `crosspost.log` | Everything it did, with links to each post |

## Tips
- Captions: set `EXTRA_HASHTAGS` (e.g. `#ugc #ugccreator`) to add tags on every platform.
- Re-post one video: delete its entry (or just one platform inside it) from `state.json`.
- If TikTok downloads stop working, run `pip install -U yt-dlp`. TikTok changes things often and yt-dlp patches fast.
