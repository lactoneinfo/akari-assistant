import os
from datetime import datetime, timedelta, timezone
from typing import Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain.tools import Tool
from dateutil import parser

SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'client_secret_writer.json'
TOKEN_FILE = 'token_writer.json'
JST = timezone(timedelta(hours=9))

def authorize_google_calendar():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def parse_event_details(input_text: str) -> Dict:
    """
    シンプルな自然文から予定の情報を抽出する（暫定）
    形式例: "2025-05-13 14:00 あかりちゃんとおでかけ"
    """
    try:
        parts = input_text.strip().split(" ", 2)
        if len(parts) < 2:
            raise ValueError("日時とタイトルの両方を指定してください。")
        
        date_part = parts[0]
        time_part = parts[1]
        summary = parts[2] if len(parts) > 2 else "(無題)"

        start = parser.parse(f"{date_part} {time_part}").astimezone(JST)
        return {
            "start": start,
            "end": start + timedelta(hours=1),
            "summary": summary,
            "location": None,
            "description": None,
            "all_day": False
        }
    except Exception as e:
        raise ValueError(f"❌ 入力解析エラー: {e}")

def add_event_to_calendar(input_text: str) -> str:
    try:
        event_data = parse_event_details(input_text)
        service = authorize_google_calendar()

        if event_data["all_day"]:
            event = {
                "summary": event_data["summary"],
                "start": {"date": event_data["start"].date().isoformat()},
                "end": {"date": (event_data["start"].date() + timedelta(days=1)).isoformat()},
                "location": event_data["location"],
                "description": event_data["description"],
            }
        else:
            event = {
                "summary": event_data["summary"],
                "start": {"dateTime": event_data["start"].isoformat(), "timeZone": "Asia/Tokyo"},
                "end": {"dateTime": event_data["end"].isoformat(), "timeZone": "Asia/Tokyo"},
                "location": event_data["location"],
                "description": event_data["description"],
            }

        created = service.events().insert(calendarId='primary', body=event).execute()
        return f"✅ 予定を追加しました: {created.get('summary')}（{created['start'].get('dateTime') or created['start'].get('date')}）"

    except Exception as e:
        return f"❌ 予定の追加中にエラー: {e}"

calendar_write_tool = Tool.from_function(
    name="CalendarWriter",
    func=add_event_to_calendar,
    description=(
        "Googleカレンダーに予定を追加します。\n"
        "入力形式の例: '2025-05-13 14:00 あかりちゃんとおでかけ'\n"
        "開始時刻とタイトルを含めてください。"
    ),
)
