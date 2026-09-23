"""
Theory 11 — Give the MCP tools to an LLM and let it choose.

Flow:
    User question
        ↓
    LLM (Groq)          ── sees the MCP tool list, picks one to call
        ↓
    Our Python app      ── executes the chosen tool via the MCP client
        ↓
    MCP Client
        ↓
    GitMCP server       ── does the real work
        ↓
    Tool result flows back to the LLM, which writes a final answer.
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv
from groq import Groq
from mcp import Client

# Load GROQ_API_KEY, GROQ_MODEL, GITHUB_REPO from .env. Nothing here is
# hard-coded — students set values once in .env and never touch the code.
load_dotenv()

# Same public MCP server as main.py. Change the repo in .env.
REPO = os.environ.get("GITHUB_REPO", "langchain-ai/langgraph")
MCP_URL = f"https://gitmcp.io/{REPO}"

# Any Groq-hosted model that supports tool calling works here.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

# Safety cap: even if the model gets stuck in a tool-call loop, we stop
# after MAX_TURNS iterations rather than burning API credits forever.
MAX_TURNS = 6


async def run_agent(user_question: str) -> str:
    # Fail fast with a friendly hint if the key is missing. Beats a
    # confusing 401 traceback three lines later.
    if not os.environ.get("GROQ_API_KEY"):
        sys.exit(
            "Missing GROQ_API_KEY. Get a free key at https://console.groq.com/keys\n"
            "Then run:  export GROQ_API_KEY=gsk_...   (or put it in a .env file)"
        )

    llm = Groq()  # picks up GROQ_API_KEY from the environment

    async with Client(MCP_URL) as mcp:

        # Discover the tools the third-party server offers. We do this on
        # every run because the server, not our code, is the source of
        # truth for what tools exist.
        mcp_tools = (await mcp.list_tools()).tools

        # We deliberately hide `fetch_generic_url_content` from the LLM.
        # When it's exposed, the model tends to guess URLs that don't
        # exist, wastes turns on failed fetches, and derails the demo.
        # The two `search_*` tools already return real documentation
        # content, so we lose nothing.
        #
        # Teaching point: WE, the client, decide which tools the LLM ever
        # sees. That is a real security and UX lever, not just a fix.
        mcp_tools = [t for t in mcp_tools if t.name != "fetch_generic_url_content"]

        # Convert each MCP tool into the shape Groq's chat API expects.
        # MCP's `input_schema` IS a JSON Schema, and Groq's
        # `function.parameters` also expects a JSON Schema — so this is
        # almost a straight copy.
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

        # Seed the conversation. The system prompt is where we teach the
        # model how to behave: use tools sparingly, don't retry failed
        # calls, keep answers short.
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

        # The agent loop. Each turn: ask the LLM. If it returns text, we're
        # done. If it returns tool_calls, we execute each one via the MCP
        # client, append the results, and loop.
        for _ in range(MAX_TURNS):
            response = llm.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=groq_tools,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            # Groq requires the assistant turn (with its tool_calls) to be
            # in history BEFORE we append the matching role="tool" results.
            messages.append(msg.model_dump(exclude_none=True))

            tool_calls = msg.tool_calls or []
            if not tool_calls:
                # No tools requested — the model produced a plain answer.
                return msg.content or ""

            # KEY POINT: the LLM only *proposes* tool calls. This loop is
            # where our code actually executes them via the MCP client.
            # That separation is the security boundary of an agent.
            for tc in tool_calls:
                name = tc.function.name
                # Groq gives `arguments` back as a JSON *string*, not a dict.
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

                # Feed the tool result back. `tool_call_id` must match the
                # assistant's request so Groq can pair them up. Content
                # must be a string; we clip huge outputs to keep the
                # context window under control.
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": name,
                    "content": text[:8000],
                })

        return "(agent stopped: reached MAX_TURNS without a final answer)"


if __name__ == "__main__":
    # Everything after the script name is treated as the question. If
    # nothing was passed, fall back to a default LangGraph question.
    question = (
        " ".join(sys.argv[1:])
        or "What is a StateGraph in LangGraph and how do you build one?"
    )
    print(f"USER: {question}\n")
    answer = asyncio.run(run_agent(question))
    print(f"\nANSWER: {answer}")
