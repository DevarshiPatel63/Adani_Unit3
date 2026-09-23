"""
Theory 11 — Consuming a real third-party MCP server.

We are NOT building an MCP server today.
We are learning to CONSUME one that someone else already built.

Server: GitMCP (https://gitmcp.io) — a free public MCP server that turns
any public GitHub repo into a set of MCP tools. No API key, no login.

Flow (no LLM yet):
    Our Python app  ─▶  MCP Client  ─▶  GitMCP server  ─▶  GitHub
"""

import asyncio
import os

from dotenv import load_dotenv
from mcp import Client

# Read GITHUB_REPO from a local .env file so students can point the demo
# at any public repo without editing this file.
load_dotenv()

# GitMCP gives each repo its own MCP endpoint. Change GITHUB_REPO in .env
# to switch repos — everything else in this file adapts automatically.
REPO = os.environ.get("GITHUB_REPO", "langchain-ai/langgraph")
MCP_URL = f"https://gitmcp.io/{REPO}"


async def demo_mcp() -> None:
    # STEP 1 — Open a connection to the MCP server.
    # `Client(url)` speaks streamable HTTP under the hood. The `async with`
    # block also runs the MCP `initialize` handshake so the session is
    # ready to use as soon as we enter it.
    print(f"STEP 1 — connect: {MCP_URL}")

    async with Client(MCP_URL) as client:

        # STEP 2 — Ask the server: "what can you do?"
        # This is MCP's discovery step. We never hard-code tool names —
        # the server is the source of truth for what exists right now.
        listing = await client.list_tools()
        print(f"\nSTEP 2 — list_tools() returned {len(listing.tools)} tools:")
        for tool in listing.tools:
            params = list((tool.input_schema or {}).get("properties", {}).keys())
            print(f"  - {tool.name}   params={params}")

        # STEP 3 — Ask the server: "please do this."
        # We pick the search-documentation tool by *pattern* instead of by
        # name because GitMCP renames it per repo
        # (e.g. `search_langgraph_documentation` becomes
        # `search_react_documentation` if you switch repos).
        # Pattern-matching keeps this demo working for any repo.
        search_tool = next(
            t for t in listing.tools
            if t.name.startswith("search_") and t.name.endswith("_documentation")
        )
        arguments = {"query": "state graph"}

        print(f"\nSTEP 3 — call_tool({search_tool.name!r}, {arguments})")
        result = await client.call_tool(search_tool.name, arguments)

        # MCP results come back as a list of content blocks. For text tools,
        # the first block has `.text`. We print it so students can see that
        # real data actually flowed all the way from GitHub back to us.
        text = (
            result.content[0].text
            if result.content and hasattr(result.content[0], "text")
            else str(result.content)
        )
        print(text[:800])


if __name__ == "__main__":
    asyncio.run(demo_mcp())
