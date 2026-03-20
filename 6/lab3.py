from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio, MCPServerStdioParams
import os
from datetime import datetime
import asyncio

load_dotenv(override=True)


# local MCP
def build_mcp_params() -> dict[str, MCPServerStdioParams]:
    return {
        'introduction': MCPServerStdioParams(
            command='npx',
            args=["-y", "mcp-memory-libsql"],
            env={**os.environ, "LIBSQL_URL": "file:./memory/ed.db"} # 直接指定 LIBSQL_URL = file:./memory/ed.db
        ),
        'stocker_price_searcher': MCPServerStdioParams(
            command='uv',
            args=["run", "market_server.py"],
            env={**os.environ}
        )
    }

async def run_local_mcp():
    instructions = "You use your entity tools as a persistent memory to store and recall information about your conversations."
    request = "My name's Ed. I'm an LLM engineer. I'm teaching a course about AI Agents, including the incredible MCP protocol. \
        MCP is a protocol for connecting agents with tools, resources and prompt templates, and makes it easy to integrate AI agents with capabilities."
    model = "gpt-4.1-mini"
    mcp_params = build_mcp_params()
    async with MCPServerStdio(params=mcp_params['introduction'], client_session_timeout_seconds=30) as mcp_server:
        agent = Agent(name='agent', instructions=instructions, model=model, mcp_servers=[mcp_server])
        with trace('conversation'):
            result = await Runner.run(agent, request)
        print('Result_1:', result.final_output)



## polygon (Massive)
polygon_api_key = os.getenv("POLYGON_API_KEY")
if not polygon_api_key:
    print('POLYGON_API_KEY not found !')

from polygon import RESTClient
client = RESTClient(polygon_api_key)
result = client.get_previous_close_agg("AAPL")


from market import get_share_price
# get_share_price('AAPL')

async def check_stock_price():
    INSTRUCTIONS = "You answer questions about the stock market."
    request = "What's the share price of Apple?"
    LLM_MODEL = 'gpt-4.1-mini'
    mcp_params = build_mcp_params()
    async with MCPServerStdio(params=mcp_params['stocker_price_searcher'], client_session_timeout_seconds=30) as mcp_server:
        agent = Agent(name='agent', instructions=INSTRUCTIONS, model=LLM_MODEL, mcp_servers=[mcp_server])
        with trace('check_price'):
            result = await Runner.run(agent, request)
        print('check_price:', result.final_output)



if __name__ == '__main__':
    # asyncio.run(run_local_mcp())
    asyncio.run(check_stock_price())

