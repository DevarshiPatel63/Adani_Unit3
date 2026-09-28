"""
STUDENT EXERCISE — connect to a DIFFERENT public MCP server.

Goal:
  Prove that our MCP client code is not tied to GitMCP. The MCP protocol
  is a standard, so the same three calls — connect, list_tools, call_tool
  — should work against any compliant server.

Rules:
  1. Do NOT use gitmcp.io (we already saw that one in main.py).
  2. Pick any other public MCP server. Suggested starting points:
       • DeepWiki   https://mcp.deepwiki.com/mcp
       • Context7   https://mcp.context7.com/mcp
       • Or find one yourself — search "public mcp servers".
  3. If a server requires an API key, OAuth, or login for basic use,
     pick a different one for today. (Handling auth is a separate topic.)

What to do (fill in the TODOs):
  1. Replace MCP_URL with the server you picked.
  2. list_tools() and print every tool name + its parameter names.
  3. Pick ONE tool from that list, look at its input_schema, and
     call it with the arguments it expects.
  4. Print the text from the result.

Run:
  python my_mcp_template.py
"""

import asyncio

from mcp import Client


# TODO 1 — replace with the MCP server you found.
MCP_URL = "https://REPLACE_ME/mcp"


async def main() -> None:
    print(f"connecting to: {MCP_URL}")

    async with Client(MCP_URL) as client:

        # TODO 2 — discover the tools this server offers.
        # Hint: same as main.py's Step 2.
        # listing = await client.list_tools()
        # for tool in listing.tools:
        #     params = list((tool.input_schema or {}).get("properties", {}).keys())
        #     print(...)
        ...

        # TODO 3 — call ONE tool.
        # Look at the list you printed above. Pick a tool. Look at its
        # input_schema to know what arguments it requires. Then:
        # result = await client.call_tool("<tool name>", { ... })
        ...

        # TODO 4 — pull the text out and print it.
        # Hint: same as main.py:
        # text = result.content[0].text if result.content else ""
        # print(text[:800])
        ...


if __name__ == "__main__":
    asyncio.run(main())
