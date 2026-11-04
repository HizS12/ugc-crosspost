"""
One-time Google login (covers YouTube uploads + your Drive inbox folder).
Opens your browser, you approve, and it prints 3 lines to paste into .env.

    python auth_google.py path\\to\\client_secret.json
"""

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

from platforms.google_auth import SCOPES

if len(sys.argv) != 2:
    sys.exit("Usage: python auth_google.py client_secret.json")

flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print("\nAdd these to your .env:\n")
print(f"GOOGLE_CLIENT_ID={creds.client_id}")
print(f"GOOGLE_CLIENT_SECRET={creds.client_secret}")
print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
