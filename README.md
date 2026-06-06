# OmniOrchestrator: Workspace Automation Agent

The **OmniOrchestrator** is an autonomous workspace administration agent powered by large language models (using a dual-cascade setup with Google Gemini and Groq). It connects across Slack, Discord, Jira, Airtable, and Notion, dynamically mapping conversational intent into strict, structured API tool calls to perform cross-platform operations.

## Architecture & Features

The workspace capabilities are split across targeted integration files, coordinated by the central agent orchestrator:

*   **`agent.py`** (The Core Orchestrator)
    *   Implements a resilient dual-cascade engine, attempting execution via Google models (Gemini) first, and falling back to a Groq cascade (Llama/Qwen) on failure.
    *   Dynamically compiles Python tools into JSON schema for LLM consumption.
    *   Maintains a stateful, in-memory session history for interactive terminal execution.
*   **`Slack.py`**
    *   `list_channels`: Fetches all public workspace channels.
    *   `get_history`: Reads recent message history from specific channels.
    *   `send_message`: Posts text messages to channels.
*   **`Notion.py`**
    *   `list_databases`: Locates all Notion databases shared with the integration.
    *   `search_notion_pages`: Finds exact page IDs by searching titles.
    *   `read_database`: Extracts recent entries from specific databases.
    *   `add_database_entry`: Adds new rows/pages into existing databases.
    *   `create_database`: Generates brand new databases inside parent pages.
    *   `append_todo_blocks`: Attaches interactive checklist blocks to existing pages.
*   **`airtable_tools.py`**
    *   `sync_inventory_levels`: Patches existing records to update specific column fields (e.g., retail stock updates).
    *   `generate_supply_report`: Fetches rows from bases, optionally filtered by strict Airtable formulas.
*   **`discord_tools.py`**
    *   `broadcast_server_announcement`: Pushes messages to specific Discord server channels.
    *   `get_recent_messages`: Pulls historical message data from channels.
*   **`jira_tools.py`**
    *   `create_bug_ticket`: Automatically creates standard "Bug" issue types within a specific Jira project.
    *   `summarize_sprint_blockers`: Executes custom Jira Query Language (JQL) searches to retrieve blocker tickets.

## Prerequisites

*   **Python 3.10+** (For local development)
*   **Docker** (For containerized deployment)

## Environment Variables

The agent orchestrator and its tools require several API keys and tokens. Create a `.env` file in the root directory based on this template:

```env
# .env.example

# LLM Providers
GEMINI_API_KEY=your_google_gemini_api_key
GROQ_API_KEY=your_groq_api_key

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token

# Notion Integration
NOTION_API_KEY=secret_your_notion_internal_integration_token

# Airtable Integration
AIRTABLE_PAT=pat_your_airtable_personal_access_token

# Discord Integration
DISCORD_BOT_TOKEN=your_discord_bot_token

# Jira Integration
JIRA_EMAIL=your_jira_account_email@domain.com
JIRA_API_TOKEN=your_jira_api_token
```

## Installation & Setup

### Local Python Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the interactive orchestrator:
   ```bash
   python agent.py
   ```

### Docker Deployment

1. Build the lightweight container image:
   ```bash
   docker build -t slack-automation-agent .
   ```
2. Run the container in detached mode, passing in your local `.env` variables:
   ```bash
   docker run -d --name slack-agent --env-file .env slack-automation-agent
   ```
3. Monitor the agent's initialization and activity logs:
   ```bash
   docker logs -f slack-agent
   ```

## File Structure

```text
.
├── .dockerignore
├── .env
├── .git/
├── .gitignore
├── Airtable.py
├── Atlassian.py
├── Discord.py
├── Dockerfile
├── Notion.py
├── README.md
├── Slack.py
├── __pycache__/
├── agent.py
├── airtable_tools.py
├── discord_tools.py
├── jira_tools.py
├── requirements.txt
└── test.py
```