# OmniOrchestrator 🛠️

A tool-calling agent over Slack, Notion, Airtable, Jira and Discord — 15 tools across
5 platforms — where the tool schemas are **generated from the Python signatures**
rather than hand-written and maintained alongside them.

Most agent codebases carry two representations of every capability: the function, and a
JSON schema block describing it to the model. They drift. A parameter gets renamed, the
schema doesn't, and the model starts calling a tool with an argument that no longer
exists — a failure that surfaces as a confusing model error rather than a `TypeError`.

Here there is one representation. Adding a capability means writing a typed function
with a docstring; the schema follows from `inspect.signature`.

---

## The schema compiler

[`tool_compiler.py`](tool_compiler.py) turns a plain function into a tool definition:

```python
def get_recent_messages(channel_id: str, limit: int = 50) -> list:
    """Pull recent messages from a channel."""
```

becomes

```jsonc
{
  "type": "function",
  "function": {
    "name": "get_recent_messages",
    "description": "Pull recent messages from a channel.",   // the docstring
    "parameters": {
      "type": "object",
      "properties": {
        "channel_id": { "type": "string"  },
        "limit":      { "type": "integer" }                  // from the annotation
      },
      "required": ["channel_id"]                             // no default ⇒ required
    }
  }
}
```

The annotation drives the type, the docstring becomes the description, and the presence
of a default decides whether a parameter is required. `self`/`cls` and `*args`/`**kwargs`
are skipped.

`Optional[X]` and `X | None` are unwrapped before mapping. That matters more than it
sounds: an equality test against `int` fails for a `Union`, so every optional numeric
parameter used to compile to `"string"` and the model was told a number was text.

The module deliberately imports nothing heavy — no `google-adk`, no HTTP clients, no
credentials — so the compiler is testable on its own:

```bash
python test_tool_compiler.py       # 12 tests, no API keys, no network
```

---

## Architecture

Two independent engines behind one conversation loop, tried in order.

| | Engine | How tools reach the model |
|---|---|---|
| 1 | **Google ADK** — Gemini 2.5 Pro → 2.5 Flash → 2.0 Flash → 1.5 Pro → 1.5 Flash | ADK introspects the Python callables itself |
| 2 | **Groq** — `openai/gpt-oss-120b` → `openai/gpt-oss-20b` | schemas from `tool_compiler.py` |

The cascade walks the Google tier first. A `403` or `429` **short-circuits the whole
tier** rather than retrying four more models against the same rejected key, and control
passes to Groq.

On the Groq path, all tool calls in a single turn are dispatched concurrently with
`asyncio.gather`, and each synchronous integration function is offloaded via
`asyncio.to_thread` so it doesn't block the event loop. The follow-up completion is
streamed token by token.

### Tools

| Platform | Tools |
|---|---|
| Slack | `list_channels`, `get_history`, `send_message` |
| Notion | `list_databases`, `search_notion_pages`, `read_database`, `add_database_entry`, `create_database`, `append_todo_blocks` |
| Airtable | `sync_inventory_levels`, `generate_supply_report` |
| Jira | `create_bug_ticket`, `summarize_sprint_blockers` |
| Discord | `broadcast_server_announcement`, `get_recent_messages` |

---

## Known limitations

Listed because they're the things that would otherwise be discovered at runtime.

- **This agent has autonomous write access.** `send_message`,
  `broadcast_server_announcement`, `create_bug_ticket`, `add_database_entry` and
  `create_database` all take effect immediately, with `tool_choice="auto"` and no
  confirmation gate. The only thing standing between an ambiguous instruction and a
  posted message is rule 1 of the system prompt, which asks the model to seek
  clarification. That is a prompt-level mitigation, not an enforced one. Point it at a
  test workspace first.

- **Memory is per-run, not persistent.** Conversation state is a Python list held in the
  process, and ADK uses `InMemorySessionService`. Exiting discards everything; there is
  no store on disk or elsewhere.

- **The Google engine rebuilds its session every turn.** It constructs a new `Agent` and
  a fresh session ID per request and replays the conversation as a text block, rather
  than using ADK's own session continuity. It works, but the framework's session service
  isn't doing the remembering — the orchestrator's own list is.

- **Discord cannot resolve a channel by name.** The system prompt tells the agent never
  to guess IDs and to look them up instead, which it can do for Slack via
  `list_channels`. Discord exposes only `broadcast_server_announcement` and
  `get_recent_messages`, both of which *take* a `channel_id` and neither of which can
  find one. You must supply the numeric ID.

- **`Airtable.py`, `Atlassian.py` and `Discord.py` are unused.** They're an earlier
  generation of the integrations, superseded by `airtable_tools.py`, `jira_tools.py` and
  `discord_tools.py`, and nothing imports them. They're kept for now because two of them
  contain capabilities the active toolset lacks — `Atlassian.add_jira_comment`,
  `Discord.list_discord_channels` — worth promoting rather than deleting.

- **Dependencies are unpinned.** `requirements.txt` names packages without versions, so
  a rebuild months from now may not resolve to the same `google-adk`.

---

## Setup

### 1. Configure

```bash
cp .env.example .env    # then fill in the values
```

Both `GEMINI_API_KEY` and `GROQ_API_KEY` are required — the agent exits at startup
without them. Platform tokens are only needed for the platforms you actually use; a
missing one surfaces as a tool-level error, not a crash.

### 2. Run locally

```bash
pip install -r requirements.txt
python agent.py
```

### 3. Or run in Docker

```bash
docker build -t omni-orchestrator .
docker run -it --env-file .env omni-orchestrator
```

**`-it` is required, not optional.** This is an interactive REPL: with `docker run -d`
there is no TTY, `input()` hits EOF immediately, and the container exits before doing
anything. If you see the stdin message in the logs, that's what happened.

---

## Layout

```text
agent.py             orchestrator, cascade logic, both engines
tool_compiler.py     signature → JSON schema (no heavy imports)
test_tool_compiler.py 12 tests, runnable without credentials
Slack.py             list_channels, get_history, send_message
Notion.py            6 database and page tools
airtable_tools.py    sync_inventory_levels, generate_supply_report
jira_tools.py        create_bug_ticket, summarize_sprint_blockers
discord_tools.py     broadcast_server_announcement, get_recent_messages
Airtable.py          unused — superseded by airtable_tools.py
Atlassian.py         unused — superseded by jira_tools.py
Discord.py           unused — superseded by discord_tools.py
test.py              one-line live smoke check against Slack
```
