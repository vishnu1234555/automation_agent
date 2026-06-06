import os
import sys
import time
import json
import asyncio
import logging
import inspect
import traceback
from typing import List, Dict, Any
from dotenv import load_dotenv

# ==========================================
# 1. ENTERPRISE CONFIGURATION & LOGGING
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("OmniOrchestrator")

load_dotenv()
google_api_key = os.getenv("GEMINI_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

if not google_api_key or not groq_api_key:
    logger.critical("FATAL: Missing GEMINI_API_KEY or GROQ_API_KEY in environment variables.")
    exit(1)

os.environ["GEMINI_API_KEY"] = google_api_key

# ==========================================
# 2. IMPORTS & TOOLS REGISTRY
# ==========================================
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from groq import AsyncGroq 

# Mock imports (Replace these with your actual local tool imports)
from Slack import list_channels, get_history, send_message
from Notion import list_databases, read_database, add_database_entry, create_database, append_todo_blocks, search_notion_pages
from airtable_tools import sync_inventory_levels, generate_supply_report
from jira_tools import create_bug_ticket, summarize_sprint_blockers
from discord_tools import broadcast_server_announcement, get_recent_messages

APP_NAME = "omni_workspace_agent"
USER_ID = "production_user_01"
SESSION_ID = "session_alpha"

TOOLS_LIST = [
    list_channels, get_history, send_message,
    list_databases, read_database, add_database_entry, create_database, append_todo_blocks, search_notion_pages,
    sync_inventory_levels, generate_supply_report,
    create_bug_ticket, summarize_sprint_blockers,
    broadcast_server_announcement, get_recent_messages
]

MASTER_INSTRUCTION = (
    "You are the Omni-Workspace Administrator with autonomous access to Slack, Notion, Airtable, Jira, and Discord.\n\n"
    "CRITICAL OPERATING RULES:\n"
    "1. AMBIGUITY: If a user asks to perform an action but does not specify the destination or target (e.g., 'send a message', 'create a ticket'), DO NOT guess. Stop and ask the user for clarification.\n"
    "2. AUTONOMY: Never ask the user for an ID if they provide a plain-text name. Chain your tools autonomously to resolve IDs.\n"
    "3. NOTION: To modify or read a page by name, you MUST execute `search_notion_pages` first to extract the exact `page_id`.\n"
    "4. SLACK: Use `list_channels`, `get_history`, and `send_message` to navigate. Never guess channel IDs; look them up.\n"
    "5. JIRA: Map engineering bugs to `create_bug_ticket`. Map sprint analysis to `summarize_sprint_blockers`.\n"
    "6. AIRTABLE: Map retail stock updates to `sync_inventory_levels`. Map base data queries to `generate_supply_report`.\n"
    "7. DISCORD: Push community updates strictly via `broadcast_server_announcement`.\n"
    "8. TOOL SYNTAX: NEVER output raw XML, HTML, or pseudo-code strings (e.g., `<function=...>`). You must rely strictly on the native JSON tool calling schema.\n"
    "9. REPORTING: Summarize actions concisely. If a tool returns an error, do not hallucinate a success—inform the user."
)

# --- CASCADE HIERARCHY ---
GOOGLE_CASCADE_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash"
]

GROQ_CASCADE_MODELS = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "qwen/qwen3-32b",
    "llama-3.1-8b-instant"
]


# ==========================================
# 3. GOOGLE ENGINE (Context-Aware + Terminal UX)
# ==========================================
class GoogleEngine:
    def __init__(self):
        self.session_service = InMemorySessionService()

    async def run(self, session_history: List[Dict[str, Any]], model_name: str) -> str:
        agent = Agent(
            name="omni_admin_agent",
            model=model_name, 
            description="Agent to read and write across the workspace ecosystem.",
            instruction=MASTER_INSTRUCTION,
            tools=TOOLS_LIST
        )
        
        # Dynamic Session ID to prevent loop crashes
        unique_timestamp = int(time.time() * 1000)
        ephemeral_session_id = f"{SESSION_ID}_{model_name}_{unique_timestamp}"
        
        await self.session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=ephemeral_session_id)
        runner = Runner(agent=agent, app_name=APP_NAME, session_service=self.session_service)
        
        context_block = "=== CONVERSATION HISTORY ===\n"
        for msg in session_history:
            if msg["role"] != "system":
                context_block += f"[{msg['role'].upper()}]: {msg['content']}\n"
        context_block += "============================\n\nPlease respond to the user's latest input based on the context above."

        content = types.Content(role='user', parts=[types.Part(text=context_block)])
        logger.info(f"[Google Engine] Initiating execution via {model_name}...")
        
        events = runner.run_async(user_id=USER_ID, session_id=ephemeral_session_id, new_message=content)
        
        # Terminal Streaming UX for Google Engine
        print(f"\nAgent (via {model_name}): ", end="", flush=True)
        final_response = ""
        async for event in events:
            if event.is_final_response():
                # ADK generally resolves final response cumulatively
                final_response = event.content.parts[0].text
                print(final_response, flush=True)
        print("\n")
                
        return final_response


# ==========================================
# 4. GROQ ENGINE (Dynamic Compiler + Parallel Execution)
# ==========================================
def compile_groq_tools(functions: List[callable]) -> tuple:
    groq_schema = []
    function_map = {}
    for func in functions:
        sig = inspect.signature(func)
        params = {"type": "object", "properties": {}, "required": []}
        
        for name, param in sig.parameters.items():
            # TYPE-AWARE COMPILATION (UPGRADE 3)
            param_type = "string" # Default
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int: param_type = "integer"
                elif param.annotation == float: param_type = "number"
                elif param.annotation == bool: param_type = "boolean"
                elif param.annotation == list or getattr(param.annotation, '__origin__', None) == list: param_type = "array"
                elif param.annotation == dict or getattr(param.annotation, '__origin__', None) == dict: param_type = "object"

            params["properties"][name] = {"type": param_type}
            
            if param.default == inspect.Parameter.empty:
                params["required"].append(name)
                
        groq_schema.append({
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": func.__doc__ or "Executes a workspace action.",
                "parameters": params
            }
        })
        function_map[func.__name__] = func
    return groq_schema, function_map


class GroqEngine:
    def __init__(self):
        self.client = AsyncGroq(api_key=groq_api_key)
        self.schema, self.func_map = compile_groq_tools(TOOLS_LIST)

    async def run(self, session_history: List[Dict[str, Any]], model_name: str) -> str:
        logger.info(f"[Groq Engine] Initiating execution via {model_name}...")
        
        working_history = session_history.copy()
        
        response = await self.client.chat.completions.create(
            model=model_name,
            messages=working_history,
            tools=self.schema,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        if message.tool_calls:
            working_history.append(message) 
            
            # PARALLEL TOOL EXECUTION (UPGRADE 2)
            async def execute_single_tool(tool_call):
                func_name = tool_call.function.name
                logger.info(f"[{model_name}] Tool executed: {func_name}")
                
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    logger.error(f"Malformed JSON for tool args: {e}")
                    return {"role": "tool", "tool_call_id": tool_call.id, "name": func_name, "content": f"Error decoding arguments: {e}"}
                
                if func_name not in self.func_map:
                    logger.error(f"Error: Tool {func_name} does not exist.")
                    return {"role": "tool", "tool_call_id": tool_call.id, "name": func_name, "content": f"Error: Tool {func_name} does not exist."}

                try:
                    func_ref = self.func_map[func_name]
                    tool_kwargs = args if args is not None else {}
                    result = await asyncio.to_thread(func_ref, **tool_kwargs)
                    return {"role": "tool", "tool_call_id": tool_call.id, "name": func_name, "content": str(result)}
                except Exception as e:
                    logger.warning(f"Tool {func_name} execution failed: {e}")
                    return {"role": "tool", "tool_call_id": tool_call.id, "name": func_name, "content": f"Execution failed: {e}\nCorrect parameters and try again."}

            # Gather and execute all tools simultaneously
            tasks = [execute_single_tool(tc) for tc in message.tool_calls]
            tool_results = await asyncio.gather(*tasks)
            working_history.extend(tool_results)
            
            # REAL-TIME STREAMING UX (UPGRADE 4)
            stream_response = await self.client.chat.completions.create(
                model=model_name,
                messages=working_history,
                stream=True
            )
            
            print(f"\nAgent (via {model_name}): ", end="", flush=True)
            final_content = ""
            async for chunk in stream_response:
                delta = chunk.choices[0].delta.content
                if delta:
                    sys.stdout.write(delta)
                    sys.stdout.flush()
                    final_content += delta
            print("\n")
            return final_content
            
        else:
            # If no tools were called, return normal response
            print(f"\nAgent (via {model_name}): {message.content}\n")
            return message.content


# ==========================================
# 5. THE STATEFUL ORCHESTRATOR
# ==========================================
async def interactive_terminal():
    google_engine = GoogleEngine()
    groq_engine = GroqEngine()
    
    session_history = [
        {"role": "system", "content": MASTER_INSTRUCTION}
    ]
    
    print("\n" + "="*60)
    print("   Omni-Workspace Production Agent (Dual-Cascade + Memory)")
    print("="*60)
    print("Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("\nInitiating graceful shutdown. Clearing session memory...")
                break
            
            session_history.append({"role": "user", "content": user_input})
            final_agent_response = None
            
            # --- THE GOOGLE CASCADE ---
            google_success = False
            for google_model in GOOGLE_CASCADE_MODELS:
                try:
                    # Note: Printing is now handled INSIDE the engine for streaming purposes
                    response = await google_engine.run(session_history, model_name=google_model)
                    final_agent_response = response
                    google_success = True
                    break 
                    
                except Exception as e:
                    error_str = str(e)
                    
                    if "403" in error_str or "PERMISSION_DENIED" in error_str:
                        logger.warning(f"Google Project Access Denied (403). Bypassing remaining Google models.")
                        break 
                    elif "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        logger.warning(f"Google API Key Rate Limit Hit. Bypassing remaining Google models.")
                        break 
                    else:
                        logger.warning(f"Google Model {google_model} failed ({error_str}). Cycling cascade...")

            # --- THE GROQ CASCADE ---
            if not google_success:
                logger.info("Initiating Groq Provider Cascade...")
                groq_success = False
                
                for groq_model in GROQ_CASCADE_MODELS:
                    try:
                        response = await groq_engine.run(session_history, model_name=groq_model)
                        final_agent_response = response
                        groq_success = True
                        break 
                        
                    except Exception as groq_err:
                        logger.error(f"Groq Model {groq_model} failed: {groq_err}")
                
                if not groq_success:
                    print("\n[SYSTEM FAILURE] All Google and Groq models failed to execute the request.\n")
            
            # --- MEMORY UPDATE ---
            if final_agent_response:
                session_history.append({"role": "assistant", "content": final_agent_response})
                    
        except KeyboardInterrupt:
            print("\n\nProcess interrupted by user. Shutting down...")
            break
        except Exception as e:
            logger.critical(f"Fatal terminal loop error: {e}")
            logger.debug(traceback.format_exc())
            break

if __name__ == "__main__":
    try:
        asyncio.run(interactive_terminal())
    except KeyboardInterrupt:
        pass