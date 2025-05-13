import os
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

def delete_task(task_id: str) -> str:
    try:
        service = authorize_google_tasks()
        tasklists = service.tasklists().list().execute().get('items', [])
        if not tasklists:
            return "❌ タスクリストが存在しません。"

        tasklist_id = tasklists[0]['id']
        service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
        return f"🗑️ タスク（ID: {task_id}）を削除しました。"
    except Exception as e:
        return f"❌ タスク削除中にエラー: {e}"

tasks_delete_tool = Tool.from_function(
    name="TasksRemover",
    func=delete_task,
    description=(
        "Google Tasks からタスクを削除します。\n"
        "引数には TasksReader で表示されたタスクID（例: 'xxxxxx123456abcd'）を指定してください。\n"
    )
)
