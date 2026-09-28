"""
Theory 12 — The MAIN AGENT (A2A client).

This program pretends to be the "main agent" — the one talking to the
student. Instead of doing research itself, it DELEGATES the work to a
remote specialist over the A2A protocol.

The remote specialist here is `research_agent.py`, but the main agent
does NOT import it. All it knows is:
    - a URL where an A2A agent lives
    - what the agent's card says it can do

Run in one terminal:
    python research_agent.py

Then in ANOTHER terminal:
    python main_agent.py
"""

import asyncio
import os
import uuid

import httpx
from dotenv import load_dotenv

from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types import Role, SendMessageRequest


load_dotenv()

HOST = os.environ.get("RESEARCH_AGENT_HOST", "127.0.0.1")
PORT = int(os.environ.get("RESEARCH_AGENT_PORT", "9999"))
REMOTE_URL = f"http://{HOST}:{PORT}"


async def ask_remote_agent(question: str) -> str:
    # -----------------------------------------------------------------
    # STEP 1 — DISCOVER
    #
    # Fetch the Agent Card from the well-known URL. Until this point the
    # main agent does NOT know the specialist's name or skills — it only
    # knows a URL. This is the "Who are you? What can you do?" step.
    # -----------------------------------------------------------------
    async with httpx.AsyncClient() as http:
        resolver = A2ACardResolver(httpx_client=http, base_url=REMOTE_URL)
        card = await resolver.get_agent_card()

    print(f"[discover] found agent: {card.name}")
    print(f"[discover]   description: {card.description}")
    print(f"[discover]   skills     : {[s.id for s in card.skills]}")

    # -----------------------------------------------------------------
    # STEP 2 — BUILD A CLIENT FROM THE CARD
    #
    # `create_client` reads the card's supported_interfaces and picks a
    # transport (JSON-RPC in our case). We stay in non-streaming mode
    # for classroom simplicity — the whole reply arrives in one chunk.
    # -----------------------------------------------------------------
    client = await create_client(
        agent=card,
        client_config=ClientConfig(streaming=False),
    )

    # -----------------------------------------------------------------
    # STEP 3 — SEND A MESSAGE
    #
    # We wrap the question in a Message with role=USER, then wrap that
    # in a SendMessageRequest. This is A2A's version of "please do this."
    # -----------------------------------------------------------------
    message = new_text_message(question, role=Role.ROLE_USER)
    message.message_id = uuid.uuid4().hex  # each message needs a unique id
    request = SendMessageRequest(message=message)

    print("[send    ] shipping the task to the remote agent…")

    # -----------------------------------------------------------------
    # STEP 4 — WAIT FOR THE TASK RESULT
    #
    # `send_message` is an async iterator. In non-streaming mode it
    # yields exactly one final chunk: the completed Task with any
    # artifacts the specialist produced.
    # -----------------------------------------------------------------
    briefing = ""
    async for chunk in client.send_message(request):
        # Each chunk is a StreamResponse that wraps either a Task, a
        # status update, or an artifact update. We only care about the
        # task chunks that carry finished artifacts.
        task = getattr(chunk, "task", None)
        if task is None:
            continue
        for artifact in task.artifacts:
            for part in artifact.parts:
                if part.text:
                    briefing = part.text

    await client.close()
    return briefing


def main() -> None:
    question = input("Ask a question for the research agent: ")
    print()
    briefing = asyncio.run(ask_remote_agent(question))
    print("\n=== MAIN AGENT ANSWER ===")
    print(briefing or "(remote agent returned no text)")


if __name__ == "__main__":
    main()
