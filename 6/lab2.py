from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.mcp import MCPServerStdio, MCPServerStdioParams


load_dotenv(override=True)

from accounts import Account
account = Account.get('Ed')
account.buy_shares("AMZN", 3, "Because this bookstore website looks promising")


# write MPC server
def build_ncp_server() -> dict[str, MCPServerStdioParams]:
    return {
        'account': MCPServerStdioParams(
            command='uv',
            args=['run', 'account_server.py'],
        )
    }

INSTRCTIONS = "You are able to manage an account for a client, and answer questions about the account."
REQUEST = "My name is Ed and my account is under the name Ed. What's my balance and my holdings?"
LLM_GPT_4O_MINI = model = "gpt-4.1-mini"

async def main():
    mcp_params = build_ncp_server()

    async with (
        MCPServerStdio(params=mcp_params['account'], client_session_timeout_seconds=30) as account_server
    ):
        agent = Agent(
            name='account_manager', instructions=INSTRCTIONS, model=LLM_GPT_4O_MINI, mcp_servers=[account_server]
        )
        with trace('account_manager'):
            result = await Runner.run(agent, REQUEST)
