from typing import Annotated, List
import aiohttp
from typing_extensions import TypedDict
from dotenv import load_dotenv
import gradio as gr
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
import requests
import os
from langchain_core.tools import tool, BaseTool
from langchain_openai import ChatOpenAI
# from langgraph.checkpoint.sqlite import SqliteSaver
# import sqlite3
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite
import asyncio
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from playwright.async_api import async_playwright, Playwright, Browser
import threading

# === Monkey Patch for aiosqlite (如果需要) ===
_original_aiosqlite_connect = aiosqlite.connect

async def _patched_aiosqlite_connect(*args, **kwargs):
    conn = await _original_aiosqlite_connect(*args, **kwargs)
    # 添加 is_alive 方法如果不存在
    if not hasattr(conn, 'is_alive'):
        conn.is_alive = lambda: True
    return conn

aiosqlite.connect = _patched_aiosqlite_connect

# === ENV ====
load_dotenv(override=True)
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
PUSHOVER_URL = os.getenv("PUSHOVER_URL")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_URL = "https://google.serper.dev/search"

required_env = {
    "PUSHOVER_TOKEN": PUSHOVER_TOKEN,
    "PUSHOVER_USER": PUSHOVER_USER,
    "PUSHOVER_URL": PUSHOVER_URL,
    "SERPER_API_KEY": SERPER_API_KEY,
    "OPENAI_API_KEY": OPENAI_API_KEY,
}
missing_env = [name for name, value in required_env.items() if not value]
if missing_env:
    for var in missing_env:
        print(f"Missing ENV setup: {var}")
    exit(1)


graph = None
even_loop = None
playwright_instance = None
browser_instance = None

## 寫function -> 工具 -> 註冊到LLM -> 使用memory -> 開啟graidio

## function 有哪些
# pushover (傳送通知)
# serper (搜尋)
# playwright (瀏覽器操作)

@tool
async def pushover_notify(message: str, title: str = 'lab3_test') -> str:
    """Used by required send something to user."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                PUSHOVER_URL,
                data={
                    'token': PUSHOVER_TOKEN,
                    'user': PUSHOVER_USER,
                    'title': title,
                    'message': message,
                },
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status == 200:
                    return 'Notification sent successfully'
                else:
                    return f'Failed to send notification, status code: {response.status}'
    
    except Exception as e:
        return f'Failed to send notification: {str(e)}'

@tool
async def serper_search(query: str, number_results: int =3) -> str:
    """使用 Serper API 搜尋網路資訊"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                SERPER_URL,
                headers= {
                    'X-API-KEY': SERPER_API_KEY,
                    'Content-Type': 'application/json',
                },
                json = {'q': query, 'num': number_results},
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results = []

                    for item in data.get('organic', [])[:number_results]:
                        results.append(
                            f"Title: {item.get('title')}\n"
                            f"Link: {item.get('link')}\n"
                            f"Snippet: {item.get('snippet')}\n"
                        )
                    return '\n'.join(results) if results else 'No relevant results found'
                else:
                    return f'Failed to fetch search results, status code: {response.status}'
    except Exception as e:
        return f'Failed to fetch search results: {str(e)}'

async def setup_browser():
    global playwright_instance, browser_instance
    playwright_instance = await async_playwright().start()
    browser_instance = await playwright_instance.chromium.launch(headless=False)

    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser_instance)
    browser_tools = toolkit.get_tools()

    return browser_tools

def assembly_tools(browser_tools: list) -> list:
    all_tools = browser_tools + [pushover_notify, serper_search]
    return all_tools


# == class of State ==
class State(TypedDict):
    messages: Annotated[list, add_messages]

# == Agent Servicve in OOP ===
class AgentService:
    def __init__(self):
        self.playwright: Playwright = None
        self.browser: Browser = None
        self.grph = None
        self.llm_with_tools = None
        self.tools: List[BaseTool] = []
        self.checkpointer = None
        self.db_conn = None

        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    async def setup(self):
        await self._setup_browser()
        self._assemble_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        await self._build_graph()

    async def _setup_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']  # 避免被偵測
        )

    def _assemble_tools(self):
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=self.browser)
        browser_tools = toolkit.get_tools()
        api_tools = [pushover_notify, serper_search]

        self.tools = browser_tools + api_tools

    def _chatbot_node(self, state: State):
        return {'messages': [self.llm_with_tools.invoke(state['messages'])]}
    
    async def _build_graph(self):
        graph_builder = StateGraph(State)

        graph_builder.add_node('chatbot', self._chatbot_node)
        graph_builder.add_node('tools', ToolNode(tools=self.tools))
        graph_builder.add_conditional_edges('chatbot', tools_condition)
        graph_builder.add_edge(START, 'chatbot')
        graph_builder.add_edge('tools', 'chatbot')
        
        self.db_conn = await aiosqlite.connect(
            'checkpoints.db',
            check_same_thread = False
        )
        self.checkpointer = AsyncSqliteSaver(self.db_conn)
        await self.checkpointer.setup()

        self.graph = graph_builder.compile(checkpointer=self.checkpointer)        
            
    async def process_message(self, message: str, thread_id: str = 'default'):
        # Business Logic
        if not self.graph:
            raise ValueError("Graph is not initialized. Please run setup() first.")

        config = {'configurable': {'thread_id': thread_id}}
        result = await self.graph.ainvoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config
        )

        return result['messages'][-1].content

    async def cleanup(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


service_instance: AgentService
background_loop: asyncio.AbstractEventLoop = None

def run_background_service():
    global background_loop, service_instance

    background_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(background_loop)

    service_instance = AgentService()

    try:
        background_loop.run_until_complete(service_instance.setup())
        background_loop.run_forever()
    except Exception as e:
        print(f"Error in background service: {str(e)}")
    finally:
        background_loop.run_until_complete(service_instance.cleanup())


# set UI
def gradio_chat_interface(message, history):
    if not service_instance or not background_loop:
        return 'serivce_instance or background_loop not ready'
    
    try:
        future = asyncio.run_coroutine_threadsafe(
            service_instance.process_message(message),
            background_loop
        )
        return future.result(timeout=120)
    except asyncio.TimeoutError:
        return 'asyncio TimeoutError'
    except Exception as e:
        return f'Error processing message: {str(e)}'


def main():
    service_thread = threading.Thread(
        target=run_background_service,
        daemon=True
        )
    service_thread.start()

    demo = gr.ChatInterface(
        gradio_chat_interface,
        title='Sidekick Browser Agent with Memory',
        description='An advanced AI agent that can browse the web, search for information, and send notifications using Pushover.',
        examples=['我是誰']
    )

    try:
        demo.launch(server_port=7860, share=False, theme=gr.themes.Soft(),)
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == "__main__":
    main()