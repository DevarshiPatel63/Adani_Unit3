"""
Theory 11 — Give the MCP tools to an LLM and let it choose.

Flow of this file:

    User question
        ↓
    LLM (Groq)                      ── sees the list of MCP tools
        ↓                              and decides which to call
    Our Python app                  ── executes that MCP tool via the client
        ↓
    MCP Client
        ↓
    GitMCP server
        ↓
    Tool result
        ↓
    LLM                              ── receives result, writes final answer
        ↓
    Answer to the user
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from groq import Groq
from mcp import Client

load_dotenv()  # reads GROQ_API_KEY, GROQ_MODEL, GITHUB_REPO from .env

# Same MCP server as main.py — public, no auth. Change the repo in .env.
REPO = os.environ.get("GITHUB_REPO", "langchain-ai/langgraph")
MCP_URL = f"https://gitmcp.io/{REPO}"

# Any Groq-hosted model that supports tool use.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

# Safety cap so a confused loop can't spin forever.
MAX_TURNS = 6


async def run_agent(user_question: str) -> str:
    if not os.environ.get("GROQ_API_KEY"):
        sys.exit(
            "Missing GROQ_API_KEY. Get a free key at https://console.groq.com/keys\n"
            "Then run:  export GROQ_API_KEY=gsk_...   (or put it in a .env file)"
        )

    llm = Groq()  # picks up GROQ_API_KEY from env

    async with Client(MCP_URL) as mcp:  

        # 1. DISCOVER the tools the server offers.
        mcp_tools = (await mcp.list_tools()).tools

        # Hide `fetch_generic_url_content` from the LLM. It invites the model
        # to guess URLs, which often 404, burning turns. The two search_*
        # tools already return real content. This shows a real, useful lever:
        # AS THE CLIENT, WE decide which tools the LLM ever sees.
        mcp_tools = [t for t in mcp_tools if t.name != "fetch_generic_url_content"]

        # 2. CONVERT MCP tool definitions into Groq's function-calling shape.
        #    MCP's `input_schema` IS a JSON Schema, which is exactly what
        #    Groq wants for `function.parameters`. Nearly a 1:1 copy.
        groq_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": (t.description or "")[:1024],
                    "parameters": t.input_schema or {"type": "object", "properties": {}},
                },
            }
            for t in mcp_tools
        ]

        # 3. Seed the conversation.
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. You have access to tools from a "
                    "third-party MCP server that can search documentation and code "
                    "for a specific GitHub repository. "
                    "Call at most 1–2 tools. As soon as you have enough information "
                    "to answer, stop calling tools and reply directly. "
                    "If a tool call fails, do not retry the same URL — answer with "
                    "what you already have. Be concise."
                ),
            },
            {"role": "user", "content": user_question},
        ]

        # 4. LLM ↔ tool loop.
        for _ in range(MAX_TURNS):
            response = llm.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=groq_tools,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            # Keep the assistant turn (with any tool_calls) in history.
            messages.append(msg.model_dump(exclude_none=True))

            tool_calls = msg.tool_calls or []
            if not tool_calls:
                # No tool requested → the LLM is answering directly.
                return msg.content or ""

            # 5. EXECUTE each requested tool call via the MCP client.
            for tc in tool_calls:
                name = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                print(f"[llm → tool] {name}({args})")

                result = await mcp.call_tool(name, args)
                text = (
                    result.content[0].text
                    if result.content and hasattr(result.content[0], "text")
                    else str(result.content)
                )
                preview = text[:120].replace("\n", " ")
                print(f"[tool → llm] {preview}{'…' if len(text) > 120 else ''}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": name,
                    "content": text[:8000],  # Groq needs a string; clip huge outputs.
                })

        return "(agent stopped: reached MAX_TURNS without a final answer)"


if __name__ == "__main__":
    question = (
        " ".join(sys.argv[1:])
        or "What is a StateGraph in LangGraph and how do you build one?"
    )
    print(f"USER: {question}\n")
    answer = asyncio.run(run_agent(question))
    print(f"\nANSWER: {answer}")
