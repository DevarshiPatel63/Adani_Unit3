"""
Theory 12 — The REMOTE SPECIALIST (A2A server).

This file is a stand-alone Python program that starts an A2A server on
http://127.0.0.1:9999. Once running, ANY A2A client on the network can:

    1. Fetch its Agent Card at /.well-known/agent-card.json
    2. Send it a message asking for research
    3. Get a task result back

Internally the specialist uses Groq to actually think. The main agent
does NOT need to know that — it only sees the Agent Card and the reply.

Run in one terminal:
    python research_agent.py

Then in ANOTHER terminal:
    python main_agent.py
"""

import os

import uvicorn
from dotenv import load_dotenv
from groq import Groq
from starlette.applications import Starlette

# All the A2A SDK pieces we need. Read the imports slowly — every name
# maps to one of the 5 A2A concepts from the theory slides.
from a2a.helpers import get_message_text, new_task_from_user_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill


load_dotenv()

HOST = os.environ.get("RESEARCH_AGENT_HOST", "127.0.0.1")
PORT = int(os.environ.get("RESEARCH_AGENT_PORT", "9999"))
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = (
    "You are a research specialist. Given a topic, produce a SHORT briefing "
    "for a colleague: 3-5 bullet points, plain English, no fluff. If you "
    "genuinely don't know, say so."
)


# ---------------------------------------------------------------------
# 1. THE EXECUTOR — this is where our agent's actual "brain" lives.
#
# The A2A SDK gives us a class to subclass: AgentExecutor. When a message
# comes in from a client, the SDK calls `execute(...)` and hands us:
#   - context: what the client sent (the Message, the current Task, etc.)
#   - event_queue: our outbox — we emit results by pushing events here.
# ---------------------------------------------------------------------
class ResearchExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.llm = Groq()  # reads GROQ_API_KEY from env

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # A2A tracks each request as a "Task". If there isn't one yet
        # (first message of a new conversation), we create one and emit it
        # so the client can see it exists.
        task = context.current_task or new_task_from_user_message(context.message)
        if not context.current_task:
            await event_queue.enqueue_event(task)

        # TaskUpdater is a convenience for pushing events tied to this task.
        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )

        # Pull the plain text out of the incoming message.
        question = get_message_text(context.message) or ""

        # Actually do the work — ask Groq for a briefing.
        response = self.llm.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        briefing = response.choices[0].message.content or "(no content)"

        # Emit the ARTIFACT — the useful output of this task.
        # The A2A word for "here's the deliverable" is Artifact.
        await updater.add_artifact(
            parts=[new_text_part(text=briefing)],
            name="research-briefing",
        )

        # Mark the task done. This closes the stream on the client side.
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Required by the interface. Our tiny demo doesn't support cancel.
        pass


# ---------------------------------------------------------------------
# 2. THE AGENT CARD — the "digital business card" the client discovers.
#
# Anything a client should know about us BEFORE sending a message goes
# here: our name, what we do, what protocol/URL to reach us on, and the
# skills we offer.
# ---------------------------------------------------------------------
agent_card = AgentCard(
    name="Research Agent",
    description="A specialist that produces short research briefings.",
    version="0.1.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=False),
    supported_interfaces=[
        AgentInterface(
            protocol_binding="JSONRPC",
            url=f"http://{HOST}:{PORT}/",
            protocol_version="1.0",
        )
    ],
    skills=[
        AgentSkill(
            id="research",
            name="Research a topic",
            description="Given a topic or question, produces a 3–5 bullet briefing.",
            tags=["research", "briefing", "summary"],
            examples=[
                "What is LangGraph?",
                "Compare REST and GraphQL in two sentences each.",
            ],
            input_modes=["text/plain"],
            output_modes=["text/plain"],
        )
    ],
)


# ---------------------------------------------------------------------
# 3. WIRE IT UP AND SERVE.
#
# DefaultRequestHandler takes the executor + a place to remember tasks
# and knows how to answer A2A JSON-RPC calls. Then we mount two sets of
# routes on a Starlette app:
#   - the well-known Agent Card endpoint (so clients can discover us)
#   - the JSON-RPC endpoint (so clients can send messages)
# ---------------------------------------------------------------------
def main() -> None:
    if not os.environ.get("GROQ_API_KEY"):
        raise SystemExit(
            "Missing GROQ_API_KEY. Get a free key at https://console.groq.com/keys "
            "and put it in a .env file next to this script."
        )

    handler = DefaultRequestHandler(
        agent_executor=ResearchExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )
    routes = [
        *create_agent_card_routes(agent_card),
        *create_jsonrpc_routes(handler, "/"),
    ]
    app = Starlette(routes=routes)

    print(f"Research Agent listening on http://{HOST}:{PORT}")
    print(f"Agent Card at http://{HOST}:{PORT}/.well-known/agent-card.json")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
