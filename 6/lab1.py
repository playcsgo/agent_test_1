from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio, MCPServerStdioParams
import asyncio
import os
import sys


# .env
load_dotenv(override=True)


# helpers
def get_npx() -> str:
    """Windoes作業系統使用 npx.cmd, 其他平台使用npx"""
    return 'npx.cmd' if sys.platform == 'win32' else 'npx'

def get_sandbox_path() -> str:
    """取得sandbox 絕對路徑, 並自動建立資料夾"""
    path = os.path.abspath(os.path.join(os.getcwd(), 'sandbox'))
    os.makedirs(path, exist_ok=True)
    return path


# MCP servers config
# 應該可以用迴圈的方式寫
def build_mcp_params() -> dict[str, MCPServerStdioParams]:
    """集中管理MCP server參數, 若要新增MCP server可以在這裡新增"""
    return {
        'fetch':MCPServerStdioParams(
            command='uvx',
            args=['mcp-server-fetch']
        ),
        'browser': MCPServerStdioParams(
            command=get_npx(),
            args=['@playwright/mcp@latest']
        ),
        'filesystem': MCPServerStdioParams(
            command=get_npx(),
            args=['-y', '@modelcontextprotocol/server-filesystem', get_sandbox_path()],
        )
    }

# INSTRCTIONS 
INSTRUCTIONS = """
You browse the internet to accomplish your instructions.
You are highly capable at browsing the internet independently to accomplish your task,
including accepting all cookies and clicking 'not now' as appropriate to get to the content you need.
If one website isn't fruitful, try another. Be persistent until you have solved your assignment,
trying different options and sites as needed.
When you need to write files, you do that inside the sandbox folder only.
"""

ACTION = "Find a great recipe for Banoffee Pie, then summarize it in markdown to banoffee.md"


## build MCP client for session handling
## (client is built in openAI SDK after update)

# main
async def main():
    mcp_params = build_mcp_params()

    async with(
        MCPServerStdio(params=mcp_params['fetch'], client_session_timeout_seconds=30) as fetch_server,
        MCPServerStdio(params=mcp_params['browser'],    client_session_timeout_seconds=60) as browser_server,
        MCPServerStdio(params=mcp_params['filesystem'], client_session_timeout_seconds=30) as files_server,
    ):
        agent = Agent(
            name='investigator',
            instructions=INSTRUCTIONS,
            model='gpt-4o-mini',
            mcp_servers=[fetch_server, browser_server, files_server]
        )

        with trace('w6d1_investigate'):
            result = await Runner.run(agent, ACTION)
            print('FINAL REESULT:' + result.final_output)


if __name__  =='__main__':
    asyncio.run(main())