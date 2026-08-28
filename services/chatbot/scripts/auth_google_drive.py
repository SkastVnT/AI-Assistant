"""
One-time Google Drive OAuth setup.

Steps:
  1. Go to https://console.cloud.google.com/apis/credentials?project=ai-assistant-7dbb8
  2. Create credentials → OAuth client ID → Desktop app → Download JSON
  3. Save as: services/chatbot/config/google-oauth-client.json
  4. Run: python services/chatbot/scripts/auth_google_drive.py
  5. Browser opens → sign in with your Google account → allow Drive access
  6. Token saved to: services/chatbot/config/google-oauth-token.json  (auto-managed)
"""

import sys
from pathlib import Path

CHATBOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CHATBOT))

CLIENT_JSON = CHATBOT / "config" / "google-oauth-client.json"
TOKEN_JSON  = CHATBOT / "config" / "google-oauth-token.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

def main():
    if not CLIENT_JSON.exists():
        print(f"ERROR: Client secrets not found at {CLIENT_JSON}")
        print("\nSteps to get it:")
        print("  1. Go to: https://console.cloud.google.com/apis/credentials?project=ai-assistant-7dbb8")
        print("  2. Create credentials → OAuth client ID → Desktop app")
        print("  3. Download JSON → save as: services/chatbot/config/google-oauth-client.json")
        sys.exit(1)

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: Missing library. Run: pip install google-auth-oauthlib")
        sys.exit(1)

    creds = None
    if TOKEN_JSON.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_JSON), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing token...")
            creds.refresh(Request())
        else:
            print("Opening browser for Google authorization...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_JSON), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_JSON.write_text(creds.to_json(), encoding="utf-8")
        print(f"\nToken saved to: {TOKEN_JSON}")

    print("\nDone! Add this line to .env if not already there:")
    print("  GOOGLE_DRIVE_OAUTH_TOKEN_PATH=config/google-oauth-token.json")
    print("\nThen restart the server.")

if __name__ == "__main__":
    main()
