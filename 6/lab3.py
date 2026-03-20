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
            env={"LIBSQL_URL": "file:./memory/ed.db"} # 直接指定 LIBSQL_URL = file:./memory/ed.db
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


if __name__ == '__main__':
    asyncio.run(run_local_mcp())