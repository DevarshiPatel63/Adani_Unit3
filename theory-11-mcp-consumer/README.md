# theory-11-mcp-consumer

Classroom lab for **Theory 11 — Consuming a third-party MCP server**.

## What are we learning?

> We are **not** building an MCP server today.
> We are learning how an AI application can **consume** an MCP server that someone else has already built and hosted.

We use **GitMCP** — a free, public MCP server at `gitmcp.io` that turns any
public GitHub repository into a set of MCP tools. It requires **no GitHub
token, no OAuth, no API key**.

Only the (optional) LLM section needs a Groq API key.

---

## Architecture

```
Our Python app  ──▶  MCP Client  ──▶  GitMCP server  ──▶  GitHub (public data)
```

With an LLM in the loop:

```
User question
   ↓
LLM (Groq)          ── sees the list of MCP tools, decides which to call
   ↓
Our Python app      ── executes the chosen MCP tool
   ↓
MCP Client
   ↓
GitMCP server
   ↓
Tool result
   ↓
LLM                 ── writes a final natural-language answer
   ↓
User
```

---

## Installation

```bash
cd theory-11-mcp-consumer
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Then copy the env template and fill it in:

```bash
cp .env.example .env
# open .env and set GROQ_API_KEY (free at https://console.groq.com/keys)
# optionally change GITHUB_REPO to any public GitHub repo you like
```

The three variables loaded from `.env`:

| Var | Used by | Default | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | `agent.py` only | *(none — required for agent.py)* | Not needed for `main.py`. |
| `GROQ_MODEL` | `agent.py` | `openai/gpt-oss-120b` | Any Groq-hosted model with tool use. |
| `GITHUB_REPO` | both | `langchain-ai/langgraph` | `owner/name`. Any public GitHub repo. |

No API keys are hard-coded in the code. Everything comes from `.env` (or the
process environment). `.env` is git-ignored.

---

## Step 1 — Connect (in `main.py`)

```python
async with Client("https://gitmcp.io/langchain-ai/langgraph") as client:
    ...
```

`Client(url)` opens a streamable-HTTP MCP session. The `async with` block also
runs the MCP `initialize` handshake for us.

---

## Step 2 — Discover: `list_tools()`

```python
listing = await client.list_tools()
```

Read this line out loud as:

> **`list_tools()` = "What can you do?"**

The server answers with a list of tools. Each tool has a `name`,
`description`, and `input_schema` (JSON Schema). For this GitMCP endpoint you
will see four real tools:

```
- fetch_langgraph_documentation       params: []
- search_langgraph_documentation      params: ['query']
- search_langgraph_code               params: ['query', 'page']
- fetch_generic_url_content           params: ['url']
```

Note: the first three names are **templated per repo**. Point `MCP_URL` at
`https://gitmcp.io/modelcontextprotocol/python-sdk` and they become
`search_python_sdk_documentation` etc. That is why `main.py` picks the tool
by pattern (`startswith("search_") and endswith("_documentation")`) instead
of hard-coding a name — change only the `REPO` constant and the whole demo
follows.

---

## Step 3 — Call: `call_tool()`

```python
result = await client.call_tool(
    "search_langgraph_documentation",
    {"query": "state graph"},
)
```

Read this line out loud as:

> **`call_tool()` = "Please do this."**

The result comes back as content blocks; for text tools:

```python
result.content[0].text
```

Run it:

```bash
python main.py
```

You will see the tool list, then a real semantic search hit from the SDK's
docs.

---

## Step 4 — Give the tools to an LLM (in `agent.py`)

`agent.py` calls `list_tools()` and converts each tool into Groq's
function-calling shape. The mapping is nearly identical because Groq's
`function.parameters` field expects **exactly** JSON Schema — the same thing
MCP's `input_schema` already is.

```python
groq_tools = [
    {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.input_schema,
        },
    }
    for t in mcp_tools
]
```

## Step 5 — Let the LLM choose a tool

The main loop is small enough to read out loud:

1. Send `messages` + `tools=` to Groq.
2. If the model returns `tool_calls`, execute each one via the MCP client and append the results as `role: "tool"` messages.
3. Loop until the model answers with no more tool calls.

Run it:

```bash
python agent.py "What is a StateGraph in LangGraph and how do you build one?"
```

You will see `[llm → tool] ...` and `[tool → llm] ...` prints, then a final
natural-language answer. **The LLM never touched the MCP server directly.** It
only decided *what* to call. Our code did the calling.

---

## Step 6 — API vs MCP

Run `main.py` again and watch the **PART 4** section at the bottom. It fetches
the same repository two ways:

```
[API]  our code  ─────────▶  api.github.com  (direct GitHub REST API)
[MCP]  our code  ─▶ MCP ─▶  gitmcp.io       (MCP server on top of GitHub)
```

The teaching point is **not** "MCP has less code". It is:

- **API** — a direct, service-specific interface. You know the endpoint, the
  params, the response shape. Ideal for deterministic backend integrations.
- **MCP** — a standardized, *discoverable* interface. An AI application can
  ask "what can you do?" at runtime and decide which capability to invoke.
  Ideal for agent workflows.

They coexist. GitMCP itself calls the GitHub REST API behind the scenes.
**MCP does not replace APIs.**

---

## Student challenge

Pick **one** and change only a few lines:

1. **Point at another public repo.** Change `REPO` at the top of `main.py` to
   `modelcontextprotocol/python-sdk` (or any other public repo), re-run
   `main.py`, and observe how the tool names change
   (`search_python_sdk_documentation`, …). Because we pick tools by pattern,
   `main.py` should still work without any other edits — but you'll want to
   pick a more relevant `query` for Step 3.

2. **Ask a code question instead of a docs question.** In `agent.py`, change
   the default question to something the model can only answer by calling
   `search_langgraph_code` (e.g. *"Where is `add_conditional_edges` defined
   in the source?"*). Watch which tool the LLM picks.

3. **Filter which tools the LLM sees.** In `agent.py`, drop
   `fetch_generic_url_content` from `groq_tools` before sending it to Groq.
   Ask the model to fetch an arbitrary URL. Observe how its answer changes.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: mcp` | Activate the venv, then `pip install -r requirements.txt`. |
| `Missing GROQ_API_KEY` | `export GROQ_API_KEY=gsk_...` or add it to `.env`. Only `agent.py` needs this. |
| Connection error to `gitmcp.io` | Check internet / VPN / firewall. GitMCP is public — no auth required. |
| Tool not found by the model | Names are templated per repo. Change the demo repo → tool names change. Always list tools first. |
| `invalid model` from Groq | Set `GROQ_MODEL=openai/gpt-oss-120b` (or `openai/gpt-oss-20b`). |
| `RuntimeError: asyncio.run() cannot be called from a running event loop` | You're in a Jupyter cell — use `await run_agent(...)` instead, or run from the terminal. |

---

## What to remember

- `list_tools()` = **"What can you do?"**
- `call_tool()` = **"Please do this."**
- The LLM never executes tools. It only *proposes*. Our code executes.
- MCP is an **AI-facing standard**. APIs are still APIs.
