import os
import datetime
from typing import List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain.tools import Tool
from dateutil import parser
from config import CALENDAR_LABELS

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CREDENTIALS_FILE = 'client_secret_reader.json'
TOKEN_FILE = 'token_reader.json'

JST = datetime.timezone(datetime.timedelta(hours=9))

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

def list_accessible_calendars(service) -> List[Dict]:
    result = service.calendarList().list().execute()
    return [
        {
            "id": item["id"],
            "summary": item.get("summary", "(no name)"),
            "accessRole": item.get("accessRole")
        }
        for item in result.get("items", [])
    ]

def fetch_events(service, calendar_id: str, start_iso: str, end_iso: str) -> List[Dict]:
    result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_iso,
        timeMax=end_iso,
        singleEvents=True,
        orderBy='startTime',
    ).execute()
    return result.get("items", [])

def iso_range_from_now(hours=24):
    now = datetime.datetime.utcnow()
    end = now + datetime.timedelta(hours=hours)
    return now.isoformat() + 'Z', end.isoformat() + 'Z'

def describe_calendar(summary: str, access: str) -> str:
    summary_lower = summary.lower()
    for label in CALENDAR_LABELS:
        if any(keyword.lower() in summary_lower for keyword in label["keywords"]):
            return label["description"]
    return f"（他のカレンダー・アクセス権限: {access}）"

def get_calendar_summary(hours: str) -> str:
    """
    指定された時間範囲（hours）で予定を取得します。
    カレンダーごとに、用途・編集可否のラベルも付与します。
    """
    try:
        hrs = int(hours)
        service = authorize_google_calendar()
        timeMin, timeMax = iso_range_from_now(hrs)
        calendars = list_accessible_calendars(service)

        lines = []
        lines.append(
            "以下は、マスターに関連するすべてのGoogleカレンダーから取得した予定です。\n"
            "カレンダーごとに用途と編集権限を明示しています。\n"
            "あかりが予定を追加・削除できるのは『あかり専用カレンダー』のみです。\n"
        )

        for cal in calendars:
            label = describe_calendar(cal["summary"], cal["accessRole"])
            lines.append(f"\n📅 カレンダー: {cal['summary']} {label}")
            events = fetch_events(service, cal['id'], timeMin, timeMax)
            if not events:
                lines.append("  - 予定なし")
            for event in events:
                start_raw = event["start"]
                summary = event.get("summary", "(無題)")
                event_id = event.get("id", "不明")

                # JST日時処理
                if "date" in start_raw:
                    start_date = parser.isoparse(start_raw["date"]).date()
                    start_str = f"{start_date.strftime('%Y年%m月%d日')}（終日）"
                else:
                    start_dt = parser.isoparse(start_raw["dateTime"]).astimezone(JST)
                    start_str = start_dt.strftime('%Y年%m月%d日 %H時%M分')

                lines.append(f"  - {start_str}: {summary}（ID: {event_id}）")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ カレンダー読み取り中にエラー: {e}"

calendar_read_tool = Tool.from_function(
    name="CalendarReader",
    func=get_calendar_summary,
    description="マスターの関連カレンダーから予定を読み取ります。引数に「今から何時間先まで」を指定してください（例: '24' や '48'）。",
)
