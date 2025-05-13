import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain.tools import Tool
from datetime import datetime

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

def list_tasks(_: str) -> str:
    try:
        service = authorize_google_tasks()
        tasklists = service.tasklists().list().execute().get('items', [])
        if not tasklists:
            return "📭 タスクリストが見つかりません。"

        output = []
        for tasklist in tasklists:
            output.append(f"\n🗂 タスクリスト: {tasklist['title']}")
            tasks = service.tasks().list(tasklist=tasklist['id'], showCompleted=True).execute().get('items', [])
            if not tasks:
                output.append("  - タスクなし")
            for task in tasks:
                title = task.get('title', '(無題)')
                due = task.get('due')
                status = task.get('status', 'needsAction')
                done = "✅ 完了" if status == "completed" else "🕒 未完了"
                task_id = task.get('id')
                due_str = f"（期限: {due}）" if due else ""
                output.append(f"  - {title}{due_str} {done}（ID: {task_id}）")
        return "\n".join(output)

    except Exception as e:
        return f"❌ タスク一覧取得中にエラー: {e}"

tasks_read_tool = Tool.from_function(
    name="TasksReader",
    func=list_tasks,
    description=(
        "Google Tasks の全タスク一覧を表示します。\n"
        "期限・完了状態・IDも一緒に表示されるので、削除や確認に使ってください。\n"
    )
)