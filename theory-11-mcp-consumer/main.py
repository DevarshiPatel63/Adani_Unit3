"""
Theory 11 — Consuming a real third-party MCP server.

We are NOT building an MCP server today.
We are learning to CONSUME one that someone else built.

Server: GitMCP — https://gitmcp.io
It exposes public GitHub repositories as MCP tools.
It requires NO API key, NO token, NO login.

Flow of this file (no LLM yet):
    Our Python app  ──▶  MCP Client  ──▶  GitMCP server  ──▶  GitHub
"""

import asyncio
import json
import os
import urllib.request

from dotenv import load_dotenv
from mcp import Client

load_dotenv()  # loads GITHUB_REPO (and any other vars) from .env

# ---------------------------------------------------------------------
# Change ONLY the GITHUB_REPO line in .env to point the whole demo at
# any public GitHub repo. GitMCP will template the tool names after
# the repo name (e.g. `search_langgraph_documentation` becomes
# `search_python_sdk_documentation`), and the code below picks the
# right tool by pattern — no other edits needed.
# ---------------------------------------------------------------------
REPO = os.environ.get("GITHUB_REPO", "langchain-ai/langgraph")
MCP_URL = f"https://gitmcp.io/{REPO}"


async def demo_mcp() -> None:
    # -----------------------------------------------------------------
    # STEP 1 — CONNECT
    #
    # `Client(url)` opens an MCP session over streamable HTTP.
    # The `async with` block also runs the MCP `initialize` handshake
    # for us automatically.
    # -----------------------------------------------------------------
    print(f"STEP 1 — connect: {MCP_URL}")

    async with Client(MCP_URL) as client:

        # -------------------------------------------------------------
        # STEP 2 — DISCOVER
        #
        # list_tools() asks the MCP server:
        #     "What can you do?"
        # -------------------------------------------------------------
        listing = await client.list_tools()
        print(f"\nSTEP 2 — list_tools() returned {len(listing.tools)} tools:")
        for tool in listing.tools:
            params = list((tool.input_schema or {}).get("properties", {}).keys())
            print(f"  - {tool.name}   params={params}")

        # -------------------------------------------------------------
        # STEP 3 — CALL
        #
        # call_tool() asks the MCP server:
        #     "Please do this."
        #
        # We pick the search-documentation tool by *pattern* rather than
        # hard-coding its name. GitMCP renames it per repo (e.g.
        # `search_langgraph_documentation`), so pattern-matching keeps
        # this demo working for any repo you point at.
        # -------------------------------------------------------------
        search_tool = next(
            t for t in listing.tools
            if t.name.startswith("search_") and t.name.endswith("_documentation")
        )
        arguments = {"query": "state graph"}

        print(f"\nSTEP 3 — call_tool({search_tool.name!r}, {arguments})")
        result = await client.call_tool(search_tool.name, arguments)

        # `result.content` is a list of content blocks. For text tools
        # the first block has `.text`.
        text = (
            result.content[0].text
            if result.content and hasattr(result.content[0], "text")
            else str(result.content)
        )
        print(text[:800])


# =====================================================================
# PART 4 — API vs MCP
#
# The lesson is NOT "MCP has less code".
# The lesson is that these are two DIFFERENT KINDS of interface:
#
#   API : a direct, service-specific way to talk to ONE service.
#         The developer knows the endpoint, the params, the response
#         shape. Good for deterministic backend integrations.
#
#   MCP : a standard, DISCOVERABLE way for an AI application to talk
#         to ANY compliant server. The AI can list the tools and pick
#         one at runtime. Good for agent workflows.
#
# Below we fetch the SAME repository two ways so students can see them
# side by side.
# =====================================================================
def demo_api_vs_mcp_direct_api() -> None:
    """Hit GitHub's public REST API directly. No auth needed for public data."""
    url = f"https://api.github.com/repos/{REPO}"
    print(f"[API]  GET {url}")
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.load(resp)
    summary = {k: data.get(k) for k in (
        "full_name", "description", "stargazers_count", "open_issues_count",
    )}
    print(json.dumps(summary, indent=2))


async def demo_api_vs_mcp_via_mcp() -> None:
    """Ask the MCP server for information about the same repo."""
    async with Client(MCP_URL) as client:
        listing = await client.list_tools()
        # Find the fetch-documentation tool the same way — by pattern.
        fetch_tool = next(
            t for t in listing.tools
            if t.name.startswith("fetch_") and t.name.endswith("_documentation")
        )
        print(f"[MCP]  call_tool({fetch_tool.name!r}, {{}})   via {MCP_URL}")
        result = await client.call_tool(fetch_tool.name, {})
        text = result.content[0].text if result.content else ""
        print(text[:400])


async def main() -> None:
    await demo_mcp()

    print("\nPART 4 — same repo, two interfaces\n")
    demo_api_vs_mcp_direct_api()
    print()
    await demo_api_vs_mcp_via_mcp()


if __name__ == "__main__":
    asyncio.run(main())
