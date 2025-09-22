from __future__ import print_function
import os
import pickle
import google.auth.transport.requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scope Drive penuh (bisa baca/tulis file)
SCOPES = ["https://www.googleapis.com/auth/drive"]

def main():
    creds = None
    # Kalau sudah ada token.json (hasil login sebelumnya), pakai itu
    if os.path.exists("token.json"):
        import json
        with open("token.json", "r") as token:
            creds_data = json.load(token)
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)

    # Kalau belum ada token.json, lakukan login manual
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Simpan token.json untuk pemakaian berikutnya
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # Test koneksi ke Google Drive
    service = build("drive", "v3", credentials=creds)
    results = service.files().list(pageSize=5, fields="files(id, name)").execute()
    items = results.get("files", [])
    print("File di Drive:")
    for item in items:
        print(u"{0} ({1})".format(item["name"], item["id"]))


if __name__ == "__main__":
    main()
