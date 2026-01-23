from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
import gradio as gr
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
import requests
import os
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI


## for Jupyter Notebook
# import nest_asyncio
# nest_asyncio.apply()

load_dotenv(override=True)

pushover_token=os.getenv("PUSHOVER_TOKEN")
pushover_user=os.getenv("PUSHOVER_USER")
pushover_url =os.getenv("PUSHOVER_URL")


class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

def push(text: str):
    requests.post(
        pushover_url,
        data={
            'token': pushover_token,
            'user': pushover_user,
            'message': text,
        })
tool_push = Tool(
    name='send_push_notification',
    func=push,
    description='useful for sending a push notification to your mobile device with a custom message',
)

## Playwright
import asyncio
from playwright.async_api import async_playwright
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit




async def main():
    playwright = await async_playwright().start()
    async_browser = await playwright.chromium.launch(headless=False)

    try:
        toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
        tools = toolkit.get_tools()
        for tool in tools:
            print(f"Tool name: {tool.name}, description: {tool.description}")
        
        tool_dict = {tool.name: tool for tool in tools}
        navigate_tool = tool_dict.get("navigate_browser")
        extract_text_tool = tool_dict.get("extract_text")

        await navigate_tool.arun({'url': 'http://www.cnn.com'})
        text = await extract_text_tool.arun({})

        import textwrap
        print(textwrap.fill(text))

    finally:
        await async_browser.close()
        await playwright.stop()





if __name__ == "__main__":
    asyncio.run(main())