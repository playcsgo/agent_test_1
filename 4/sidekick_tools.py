from playwright.async_api import async_playwright
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from dotenv import load_dotenv
import os
import requests
from langchain_core.tools import Tool
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_community.tools.wikipedia.tool import WikipediaQueryRun
from langchain_community.utilities.wikipedia import WikipediaAPIWrapper
from langchain_experimental.tools import PythonREPLTool
from langchain_community.utilities import GoogleSerperAPIWrapper


load_dotenv(override=True)

PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
PUSHOVER_URL = os.getenv("PUSHOVER_URL")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPER_URL = "https://google.serper.dev/search"

serper = GoogleSerperAPIWrapper()

async def playwright_tools():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=browser)
    return toolkit.get_tools(), browser, playwright


def push(text: str):
    """Send a push notitication to the user"""
    res = requests.post(PUSHOVER_URL, data = {'token': PUSHOVER_TOKEN, 'user': PUSHOVER_USER, 'message': text})
    return res.status_code


def get_file_tools():
    toolkit = FileManagementToolkit(root_dir='sandbox')
    return toolkit.get_tools()


async def other_tools():
    push_tool = Tool(name='send_push_notification', func=push, description='Use this tool when you want to send a push notification')
    file_tools = get_file_tools()

    tool_search = Tool(
        name='search',
        func=serper.run,
        description='Use this tool when you want to get the results of an online web search'
    )

    wikipedia = WikipediaAPIWrapper()
    wiki_tool = WikipediaQueryRun(api_wrapper=wikipedia)
    python_repl = PythonREPLTool()

    return file_tools + [push_tool, tool_search, python_repl, wiki_tool]
