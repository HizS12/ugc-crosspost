"""
One-time YouTube login. Opens your browser, you approve, and it prints the
refresh token to paste into .env as YT_REFRESH_TOKEN.

    python auth_youtube.py path\\to\\client_secret.json
"""

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

if len(sys.argv) != 2:
    sys.exit("Usage: python auth_youtube.py client_secret.json")

flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], ["https://www.googleapis.com/auth/youtube.upload"])
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print("\nAdd these to your .env:\n")
print(f"YT_CLIENT_ID={creds.client_id}")
print(f"YT_CLIENT_SECRET={creds.client_secret}")
print(f"YT_REFRESH_TOKEN={creds.refresh_token}")
