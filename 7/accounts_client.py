import mcp
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters
from agents import FunctionTool
import json
from pydantic import AnyUrl
from mcp.types import TextResourceContents

params = StdioServerParameters(command='uv', args=['run', 'accounts_server.py'], env=None)


async def list_accounts_tools():
    async with stdio_client(params) as streams: 
        # streams = (read_stream, write_stream)
        async with mcp.ClientSession(*streams) as session:
            await session.initialize() # 等待握手
            tools_results = await session.list_tools()
            return tools_results.tools

async def call_account_tool(tool_name, tool_args):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            return result

async def read_accounts_resource(name):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.read_resource(AnyUrl(f"accounts://accounts_server/{name}"))
            content = result.contents[0]
            if isinstance(content, TextResourceContents):
                return content.text
            raise ValueError(f"Expected text, got binary blob")
        
async def read_strategy_resource(name):
    async with stdio_client(params) as streams:
        async with mcp.ClientSession(*streams) as session:
            await session.initialize()
            result = await session.read_resource(AnyUrl(f"accounts://strategy/{name}"))
            content = result.contents[0]
            if isinstance(content, TextResourceContents):
                return content.text
            raise ValueError(f"Expected text, got binary blob")

async def get_accounts_tools_openai():
    openai_tools = []
    for tool in await list_accounts_tools():
        schema = {**tool.inputSchema, "additionalProperties": False}
        openai_tool = FunctionTool(
            name=tool.name,
            description=tool.description or 'tool without description',
            params_json_schema=schema,
            on_invoke_tool=lambda ctx, args, toolname=tool.name: call_account_tool(toolname, json.loads(args))
        )
        openai_tools.append(openai_tool)
    return openai_tools