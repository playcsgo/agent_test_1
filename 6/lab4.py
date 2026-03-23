import os
from dotenv import load_dotenv
from agents import Agent, Runner, trace, Tool
from agents.mcp import MCPServerStdio, MCPServerStdioParams
from datetime import datetime
from accounts_client import read_accounts_resource, read_strategy_resource
from accounts import Account
import asyncio

load_dotenv(override=True)


# gathering MCP params
polygon_api_key = os.getenv("POLYGON_API_KEY")
assert(polygon_api_key)
polygon_plan = os.getenv("POLYGON_PLAN")

is_paid_polygon = polygon_plan == 'paid'
is_realtime_polygon = polygon_plan == 'realtime'

market_mcp: MCPServerStdioParams
if is_paid_polygon or is_realtime_polygon:
    market_mcp = {"command": "uvx","args": ["--from", "git+https://github.com/polygon-io/mcp_polygon@master", "mcp_polygon"], "env": {"POLYGON_API_KEY": polygon_api_key}}
else:
    market_mcp = ({"command": "uv", "args": ["run", "market_server.py"]})

trader_mcp_server_params: list[MCPServerStdioParams] = [
    {"command": "uv", "args": ["run", "accounts_server.py"]},
    {"command": "uv", "args": ["run", "push_server.py"]},
    market_mcp,
]


# Research
serper_api_key = os.getenv("SERPER_API_KEY")
assert(serper_api_key)
serper_env: dict[str, str] = {"SERPER_API_KEY": serper_api_key}
researcher_mcp_server_params: list[MCPServerStdioParams] = [
    {"command": "uvx", "args": ["mcp-server-fetch"]},
    {"command": "npx", "args": ["-y", "serper-search-scrape-mcp-server"], "env": serper_env}
]


INITIAL_STRATEGY = "You are a day trader that aggressively buys and sells shares based on news and market conditions."
Account.get('Ed').reset(INITIAL_STRATEGY)


## Create Researcher
async def build_researcher(mcp_servers) -> Agent:
    INSTRUCTIONS = f"""You are a financial researcher. You are able to search the web for interesting financial news,
        look for possible trading opportunities, and help with research.
        Based on the request, you carry out necessary research and respond with your findings.
        Take time to make multiple searches to get a comprehensive overview, and then summarize your findings.
        If there isn't a specific request, then just respond with investment opportunities based on searching latest news.
        The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    """
    research = Agent(
        name='Researcher',
        instructions=INSTRUCTIONS,
        model='gpt-4.1-mini',
        mcp_servers=mcp_servers
    )
    return research

async def get_research_tool(mcp_servers) -> Tool:
    researcher = await build_researcher(mcp_servers)
    return researcher.as_tool(
        tool_name='Researcher',
        tool_description="This tool researches online for news and opportunities, \
                either based on your specific request to look into a certain stock, \
                or generally for notable financial news and opportunities. \
                Describe what kind of research you're looking for."
    )

from contextlib import AsyncExitStack

async def test_research_function(query):
    async with AsyncExitStack() as stack:
        servers = [
            await stack.enter_async_context(
                MCPServerStdio(params, client_session_timeout_seconds=30)
            )
            for params in researcher_mcp_server_params
        ]
        
        researcher = await build_researcher(servers)
        with trace('Researcher'):
            result = await Runner.run(researcher, query, max_turns=30)
            return result.final_output

    

## Create Trader
async def build_trader(trader_servers, researcher_servers) -> Agent:
    agent_name = 'Ed'
    account_details = await read_accounts_resource(agent_name)
    strategy = await read_strategy_resource(agent_name)

    INSTRCTIONS = f"""
        You are a trader that manages a portfolio of shares. Your name is {agent_name} and your account is under your name, {agent_name}.
        You have access to tools that allow you to search the internet for company news, check stock prices, and buy and sell shares.
        Your investment strategy for your portfolio is:
        {strategy}
        Your current holdings and balance is:
        {account_details}
        You have the tools to perform a websearch for relevant news and information.
        You have tools to check stock prices.
        You have tools to buy and sell shares.
        You have tools to save memory of companies, research and thinking so far.
        Please make use of these tools to manage your portfolio. Carry out trades as you see fit; do not wait for instructions or ask for confirmation.
        """

    researcher_tool = await get_research_tool(researcher_servers)
    trader = Agent(
        name=agent_name,
        instructions=INSTRCTIONS,
        tools=[researcher_tool],
        mcp_servers=trader_servers,
        model='gpt-4o-mini'
    )
    return trader


async def trade():
    async with AsyncExitStack() as stack:
        t_servers = [
            await stack.enter_async_context(MCPServerStdio(p, client_session_timeout_seconds=30))
            for p in trader_mcp_server_params
        ]
        r_servers = [
            await stack.enter_async_context(MCPServerStdio(p, client_session_timeout_seconds=30))
            for p in researcher_mcp_server_params
        ]
        trader = await build_trader(t_servers, r_servers)
        PROMPT = """
            Use your tools to make decisions about your portfolio.
            Investigate the news and the market, make your decision, make the trades, and respond with a summary of your actions.
            """
        with trace('Trader'):
            result = await Runner.run(trader, PROMPT, max_turns=30)
            return result.final_output

async def check():
    research_question = "What's the latest news on Amazon?"
    results = await test_research_function(research_question)
    print('result:', results)


if __name__ == '__main__':
    # asyncio.run(check())
    res = asyncio.run(trade())
    print(res)