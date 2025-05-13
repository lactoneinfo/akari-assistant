import os
from datetime import datetime, timedelta
from dateutil import parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain.tools import Tool

SCOPES = ['https://www.googleapis.com/auth/tasks']
CREDENTIALS_FILE = 'client_secret_writer.json'
TOKEN_FILE = 'token_tasks.json'

def authorize_google_tasks():
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
    return build('tasks', 'v1', credentials=creds)

def add_task(input_text: str) -> str:
    """
    入力形式に応じて Google Tasks にタスクを追加する。
    優先度: 1) 期限＋時刻 → 2) 終日（期限のみ） → 3) 期限なし（拒否）
    """
    try:
        service = authorize_google_tasks()
        tasklists = service.tasklists().list().execute().get('items', [])
        if not tasklists:
            return "❌ タスクリストが存在しません。"
        tasklist_id = tasklists[0]['id']

        parts = input_text.strip().split(" ", 2)

        # 期限 + 時刻 + タイトル
        if len(parts) >= 3:
            try:
                dt = parser.parse(f"{parts[0]} {parts[1]}")
                due = dt.isoformat() + 'Z'
                title = parts[2]
            except Exception:
                raise ValueError("❌ 日付や時刻の解釈に失敗しました。例: '2025-05-15 18:00 レポート提出' のように明示してください。")

        # 期限 + タイトル（終日扱い）
        elif len(parts) == 2:
            try:
                dt = parser.parse(parts[0])
                due = dt.isoformat() + 'Z'
                title = parts[1]
            except Exception:
                raise ValueError("❌ 日付の解釈に失敗しました。例: '2025-05-15 買い物リスト作成' のように明示してください。")

        else:
            raise ValueError("❌ 入力が短すぎます。日付とタスク内容を含めてください。")

        task = {'title': title, 'due': due}
        created = service.tasks().insert(tasklist=tasklist_id, body=task).execute()
        return f"✅ タスクを追加しました: {created['title']}（ID: {created['id']}）"

    except Exception as e:
        return f"{e}"

tasks_write_tool = Tool.from_function(
    name="TasksWriter",
    func=add_task,
    description=(
        "Google Tasks に新しいタスクを追加します。\n"
        "【入力形式】\n"
        "・期限＋時刻あり: '2025-05-15 18:00 レポート提出'\n"
        "・期限のみ（終日）: '2025-05-15 買い物リスト作成'\n"
        "❌ '木曜の17時' や '明日の夜' のような曖昧な表現はサポートしていません。\n"
        "⚠️ 日付・時刻は明示的に入力してください。"
    )
)
