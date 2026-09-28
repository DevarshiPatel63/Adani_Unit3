# theory-12-a2a

Classroom lab for **Theory 12 — A2A Protocol**.
Agentic AI Engineering course, Unit III.

## What are we learning today?

> Last week: our agent used a **third-party tool** through MCP.
> This week: our agent talks to **another agent** through A2A.

Two things you should be able to say by the end of class:

1. **MCP = agent → tool.** Discover and use capabilities.
2. **A2A = agent → agent.** Discover and collaborate with other agents.

We are NOT building an orchestrator or multi-agent framework today. Just
the smallest honest version of one main agent delegating to one remote
specialist.

---

## Architecture

```
Terminal A                            Terminal B
┌───────────────────┐    A2A over    ┌──────────────────────┐
│                   │ ─── HTTP  ───▶ │                      │
│   main_agent.py   │                │   research_agent.py  │
│                   │ ◀── JSON-RPC ─ │  (A2A server + Groq) │
│  (A2A client)     │                │  http://127.0.0.1:9999│
└───────────────────┘                └──────────┬───────────┘
                                                │
                                                ▼
                                              Groq LLM
```

The main agent does **not** import the specialist — it only knows a URL.
It discovers the Agent Card, sends a message, gets a Task back.

---

## Prerequisites

- Python 3.11+
- A Groq API key (free at <https://console.groq.com/keys>) — **only the
  specialist needs it**, not the main agent.

---

## Setup (5 minutes)

```bash
cd theory-12-a2a
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# open .env and paste your GROQ_API_KEY
```

The three env vars in `.env`:

| Var | Used by | Default |
|---|---|---|
| `GROQ_API_KEY` | `research_agent.py` only | *(required)* |
| `GROQ_MODEL` | `research_agent.py` | `openai/gpt-oss-120b` |
| `RESEARCH_AGENT_HOST` / `PORT` | both files | `127.0.0.1` / `9999` |

---

## The 75-minute story

### Part 1 — Why (Slides 1–4, ~15 min)

Talk. No code. Land these three ideas:

1. One agent can do everything, but in a real system you want
   **specialists**.
2. If specialists are built by different teams, in different languages,
   with different frameworks — how do they talk?
3. **A2A** is that "how." An open protocol for one agent to discover
   and call another.

Pause on the sentence: **"MCP connects an agent to *capabilities*. A2A
connects an agent to another *agent*."**

### Part 2 — Demo 1: in-process delegation (~10 min)

```bash
python demo1_delegation.py
```

Two Python functions, one file. `main_agent` calls `research_agent`. No
network, no protocol, no Agent Card. This is **not A2A** — it's just the
*idea* of delegation.

Ask the class: *"why is this NOT A2A?"* Answer:

> Because both functions are inside the same Python process. There is
> no server, no card, no network. If the research agent lived on a
> different computer, we couldn't do this at all.

That's the pain A2A solves.

### Part 3 — The five A2A pieces (Slides 6–7, ~10 min)

Introduce, in order:

1. **Agent Card** — the "digital business card."
2. **Message** — one turn in the conversation.
3. **Task** — the work being tracked.
4. **Artifact** — the useful output produced.
5. **Client + Server** — who's asking, who's providing.

You'll see all five appear literally by name in `research_agent.py` and
`main_agent.py`.

### Part 4 — Demo 2: real A2A (~25 min)

You need **two terminals** open side by side.

**Terminal A — start the specialist:**

```bash
source .venv/bin/activate
python research_agent.py
```

You'll see:

```
Research Agent listening on http://127.0.0.1:9999
Agent Card at http://127.0.0.1:9999/.well-known/agent-card.json
```

Show the Agent Card in a browser (open that URL). The JSON that appears
is exactly the AgentCard we built in code. That's the "who are you? what
can you do?" step happening for real.

**Terminal B — run the main agent:**

```bash
source .venv/bin/activate
python main_agent.py
```

Type a question like *"What is LangGraph and why is it useful?"* and
watch the trace:

```
[discover] found agent: Research Agent
[discover]   description: A specialist that produces short research briefings.
[discover]   skills     : ['research']
[send    ] shipping the task to the remote agent…

=== MAIN AGENT ANSWER ===
- LangGraph is a Python library …
- ...
```

Then ask the class **the payoff questions:**

- *"Which computer did the LLM call happen on?"* → the specialist's
  (Terminal A). Main agent never touched Groq.
- *"How did the main agent know what the specialist could do?"* →
  it fetched the Agent Card.
- *"If I stop the specialist and start a different one (say a Coding
  Agent) at the same URL, does main_agent.py need to change?"* → no,
  because it discovers the card at runtime.

### Part 5 — MCP vs A2A recap (Slide 10, ~5 min)

|  | MCP | A2A |
|---|---|---|
| Question it answers | *"What can my agent USE?"* | *"WHO can my agent WORK WITH?"* |
| Client/server terms | MCP client / MCP server | A2A client / A2A server |
| Discovery call | `list_tools()` | fetch Agent Card |
| Invocation | `call_tool(name, args)` | send Message → get Task |

They coexist. In the diagram at the bottom of Slide 18 the main agent
uses both. Our specialist here could itself use MCP — that's next
session's story.

### Part 6 — Student challenge (~10 min)

See below.

---

## Student challenge — turn Research Agent into a Coding Agent

Copy `research_agent.py` to `coding_agent.py` and change **only three
things**:

1. **The system prompt** — make it a coding helper instead of a research
   analyst. Example:

   ```python
   SYSTEM_PROMPT = (
       "You are a Python coding helper. Given a task, produce a short "
       "working Python snippet and a one-line explanation."
   )
   ```

2. **The Agent Card** — change `name`, `description`, and the skill:

   ```python
   name="Coding Agent",
   description="Writes small Python snippets for a given task.",
   skills=[AgentSkill(
       id="code_generation",
       name="Write Python",
       description="Given a task, produce a Python snippet.",
       tags=["python", "code"],
       examples=["Write a function that reverses a string."],
       input_modes=["text/plain"],
       output_modes=["text/plain"],
   )]
   ```

3. **The port** in `.env` (so both agents can run at once):

   ```
   RESEARCH_AGENT_PORT=9998   # main_agent will now talk to the coder
   ```

Then in Terminal A run `python coding_agent.py` and in Terminal B run
`python main_agent.py`. Ask *"Write a Python function that reverses a
string."*

Notice **you didn't touch `main_agent.py` at all.** That is the
interoperability point of A2A.

---

## What's next (Slide 18)

Once you can talk to *one* remote agent, the next question is: what if
there are ten? Who decides which one to call? Who owns the workflow?
That's the multi-agent / orchestration topic for Theory 13.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: a2a` | `pip install -r requirements.txt` |
| `Missing GROQ_API_KEY` | Put it in `.env` (only `research_agent.py` needs it). |
| `Connection refused` in Terminal B | The specialist in Terminal A isn't running yet, or crashed. Check Terminal A. |
| `Address already in use` on port 9999 | Something else is using it. Change `RESEARCH_AGENT_PORT` in `.env` to `9998` (and restart both). |
| `(remote agent returned no text)` | The specialist ran but returned no artifact — likely a Groq error. Check Terminal A. |
| macOS firewall popup | Click *Allow*. The scripts bind to `127.0.0.1` only. |

---

## The one-diagram recap to draw on the board

```
                 USER
                   │
                   ▼
              MAIN AGENT
              /         \
             /           \
         (MCP)         (A2A)
           │              │
           ▼              ▼
        TOOLS      RESEARCH AGENT
                        │
                      (MCP)
                        │
                        ▼
                     TOOLS
```

*"MCP gives my agent capabilities. A2A gives my agent collaborators."*
