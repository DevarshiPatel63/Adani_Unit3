# Adani — Agentic AI Engineering (Unit III)

Classroom labs for **Unit III** of the Agentic AI Engineering course.

Each theory session ships as its own self-contained folder with runnable
Python code, a README that walks through the lesson step by step, and a
small student exercise at the end.

## Contents

| Folder | Session | What students learn |
|---|---|---|
| [theory-11-mcp-consumer/](theory-11-mcp-consumer/) | Theory 11 — MCP | Consume a real third-party MCP server (GitMCP). Discover tools with `list_tools()`, call them with `call_tool()`, then hand the tool list to a Groq LLM and let it choose. |
| [theory-12-a2a/](theory-12-a2a/) | Theory 12 — A2A | Two agents talking to each other over the Agent-to-Agent protocol. One process runs a "research specialist" agent; another runs the "main agent" that discovers the specialist's Agent Card and delegates work to it. |

## The mental model this unit builds

```
             USER
               │
               ▼
          MAIN AGENT
          /         \
      (MCP)        (A2A)
        │             │
        ▼             ▼
      TOOLS       OTHER AGENTS
```

- **MCP** = agent → **tool**. Discover and invoke capabilities.
- **A2A** = agent → **agent**. Discover and collaborate with other agents.

They coexist. An A2A specialist can itself use MCP tools internally, and
a main agent can mix both.

## Running any of the labs

Each folder is a stand-alone project with its own `requirements.txt`,
`.env.example`, and README. General flow:

```bash
cd <theory-folder>
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                  # then fill in real values
python main.py                        # or whichever entry point that lab uses
```

Groq is the LLM provider for both labs. Get a free key at
<https://console.groq.com/keys> and put it in `.env`.

## Course context

This is Unit III of a longer Agentic AI Engineering programme. Earlier
units cover LLMs, prompting, workflows vs agents, and basic MCP concepts.
Later sessions in this unit extend today's foundations into multi-agent
orchestration, trust boundaries, and a final agentic project.

## Prerequisites

- Python 3.11+
- Node.js (only for the optional MCP Inspector in Theory 11)
- A free Groq API key
- A terminal and VS Code (or any editor)

No paid services required.

## Repository layout

```
.
├── README.md                    ← this file
├── .gitignore
├── theory-11-mcp-consumer/      ← Theory 11 lab
└── theory-12-a2a/               ← Theory 12 lab
```
