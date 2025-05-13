import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain.tools import Tool

SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'client_secret_writer.json'
TOKEN_FILE = 'token_writer.json'

def authorize_google_calendar():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def delete_event_by_id(event_id: str) -> str:
    try:
        service = authorize_google_calendar()
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return f"🗑️ 予定（ID: {event_id}）を削除しました。"
    except Exception as e:
        return f"❌ 削除エラー: {e}"

calendar_delete_tool = Tool.from_function(
    name="CalendarRemover",
    func=delete_event_by_id,
    description="予定のイベントID（例: 'xxxxxxxabcd123'）を指定して、Googleカレンダーから削除します。",
)
