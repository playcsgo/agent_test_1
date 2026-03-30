import os
from dotenv import load_dotenv
from market import is_paid_polygon, is_realtime_polygon
import sys

load_dotenv(override=True)

NPX = 'npx.cmd' if sys.platform == 'win32' else 'npx'

serper_api_key = os.getenv('SERPER_API_KEY') or ''
polygon_api_key = os.getenv("POLYGON_API_KEY") or ''
is_pushover_activate = os.getenv("PUSH_OVER_ON", "false").strip().lower() == "true"

if is_paid_polygon or is_realtime_polygon:
    market_mcp = {
        "command": "uvx",
        "args": ["--from", "git+https://github.com/polygon-io/mcp_polygon@v0.1.0", "mcp_polygon"],
        "env": {"POLYGON_API_KEY": polygon_api_key},
    }
else:
    market_mcp = {"command": "uv", "args": ["run", "market_server.py"]}


trader_mcp_server_params = [
    {'command': 'uv', 'args': ['run', 'accounts_server.py']},
    *([ {"command": "uv", "args": ["run", "push_server.py"]} ] if is_pushover_activate else []),
    market_mcp,
]

def researcher_mcp_server_params(name: str):
    return [
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        {
            "command": "uvx",
            "args": ["serper-mcp-server"],
            "env": {'SERPER_API_KEY': serper_api_key},
        },
        {
            "command": NPX,
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
        },
    ]