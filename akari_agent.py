import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts.chat import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain.schema.runnable import RunnableSequence
from langchain.callbacks.base import BaseCallbackHandler
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType, AgentExecutor
from datetime import datetime

import requests

from akari_tools import tools


load_dotenv()

with open("prompt.txt", encoding="utf-8") as f:
    system_prompt = f.read()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.environ["GEMINI_API_KEY"],
    temperature=0.7
)

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    output_key="output"
)

class SearchAnnounceHandler(BaseCallbackHandler):
    def __init__(self, ctx):
        self.ctx = ctx
        self.search_count = 0

    async def on_tool_start(self, tool, input_str, **kwargs):
        tool_name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", None)
        if tool_name == "WebSearch":
            self.search_count += 1
            await self.ctx.send("🔍 マスターの代わりに検索してみるね！")


prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10,
    return_intermediate_steps=True,
    memory=None
)

refiner = RunnableSequence(prompt | llm)
