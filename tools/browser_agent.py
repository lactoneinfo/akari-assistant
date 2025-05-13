
import os
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
import asyncio
from browser_use import Agent

# === Browser検索 ===
async def run_browser_agent(task: str) -> str:
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-8b",
        google_api_key=os.environ["GEMINI_API_KEY"],
        temperature=0.7
    )
    agent = Agent(task=task, llm=llm)
    history = await agent.run()

    for step in reversed(list(history)):
        if isinstance(step, tuple) and len(step) == 2:
            step_type, payload = step
            if step_type == "done" and isinstance(payload, dict) and "text" in payload:
                return payload["text"]

    return "❌ 最終出力が見つかりませんでした。"


def run_browser_task_sync(task: str) -> str:
    """
    LangChain Tool用の同期ラッパー。
    Geminiとブラウザを使って日本語のWebサイトを調査し、結果だけを返します。
    """
    return asyncio.run(run_browser_agent(task))

browser_agent_tool = Tool(
    name="BrowserAgentSearch",
    func=run_browser_task_sync,
    description=(
        "実ブラウザ操作 (browser-use) を使って、任意のWebページを検索・調査するツールです。\n\n"
        "- UI操作を含むような場面（ページ遷移、検索フォームの入力など）ではこのツールを優先してください。\n"
        "- WebSearch Tool（Perplexity API）は英語圏ニュース・Wikipedia・簡易な要約向けなので、内容や精度が不十分な場合はこちらを使ってください。\n"
        "- 実行には数十秒かかることがあります。"
    )
)