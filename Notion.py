import os
import requests
from dotenv import load_dotenv

def get_notion_headers():
    """Generates the required headers for Notion's API."""
    load_dotenv()
    notion_token = os.getenv("NOTION_API_KEY")
    if not notion_token:
        raise ValueError("NOTION_API_KEY not found in .env file.")
    return {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28" # Notion requires a hardcoded API version
    }

def list_databases() -> str:
    """
    Searches for all Notion databases that the AI has been granted access to.
    Use this FIRST to find the correct 'database_id' when the user asks to read or add to a database.
    """
    url = "https://api.notion.com/v1/search"
    payload = {"filter": {"value": "database", "property": "object"}}
    
    response = requests.post(url, headers=get_notion_headers(), json=payload)
    response.raise_for_status()
    
    results = response.json().get("results", [])
    if not results:
        return "No databases found. The user must share a database with the integration in the Notion UI."
        
    db_list = []
    for db in results:
        # Extract plain text name of the database
        title_objs = db.get("title", [])
        name = title_objs[0].get("plain_text", "Untitled") if title_objs else "Untitled"
        db_list.append(f"Name: {name} | ID: {db['id']}")
        
    return "\n".join(db_list)

def read_database(database_id: str, limit: int = 5) -> str:
    """
    Reads the most recent entries from a specific Notion database.
    You MUST provide the exact 'database_id', NOT the database name.
    """
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {"page_size": limit}
    
    response = requests.post(url, headers=get_notion_headers(), json=payload)
    response.raise_for_status()
    
    pages = response.json().get("results", [])
    output = []
    
    for page in pages:
        # Notion's JSON is deeply nested. This extracts the page title.
        props = page.get("properties", {})
        for prop_name, prop_data in props.items():
            if prop_data.get("type") == "title":
                title_arr = prop_data.get("title", [])
                title_text = title_arr[0].get("plain_text", "Empty") if title_arr else "Empty"
                output.append(f"- {title_text}")
                
    return "\n".join(output) if output else "Database is empty."

def add_database_entry(database_id: str, title: str) -> str:
    """
    Creates a new page/entry in a specific Notion database.
    You MUST provide the exact 'database_id' and the 'title' for the new entry.
    """
    url = "https://api.notion.com/v1/pages"
    
    # Notion requires strict JSON schema to construct a page
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "title": [ # Note: This assumes the primary column is using the default type 'title'
                {
                    "text": {
                        "content": title
                    }
                }
            ]
        }
    }
    
    response = requests.post(url, headers=get_notion_headers(), json=payload)
    if response.status_code == 400:
         return f"Failed: {response.json().get('message')}. Ensure the database has a default 'Name' or 'title' property."
    response.raise_for_status()
    
    return "Entry successfully added to Notion."

def create_database(parent_page_id: str, title: str) -> str:
    """
    Creates a brand new Notion database inside an existing Notion page.
    You MUST provide the exact 'parent_page_id' where the database will live, and the 'title' for the new database.
    """
    url = "https://api.notion.com/v1/databases"
    
    # Notion requires strict JSON to define the parent and the columns (properties)
    payload = {
        "parent": {
            "type": "page_id",
            "page_id": parent_page_id
        },
        "title": [
            {
                "type": "text",
                "text": {
                    "content": title
                }
            }
        ],
        "properties": {
            # Every Notion database requires at least one 'title' property. 
            # We will name the default column "Name".
            "Name": {
                "title": {}
            },
            # We will also generate a default text column called "Description"
            "Description": {
                "rich_text": {}
            }
        }
    }
    
    response = requests.post(url, headers=get_notion_headers(), json=payload)
    
    if response.status_code != 200:
        return f"Failed to create database. Error: {response.json().get('message')}"
        
    return f"Success! Database '{title}' has been created."

def append_todo_blocks(page_id: str, tasks: str) -> str:
    """
    Appends a checklist (to-do list) to an existing Notion page.
    You MUST provide the exact 'page_id' where the list will live.
    You MUST provide 'tasks' as a comma-separated string (e.g., "Buy milk, Code script, Sleep").
    """
    # In Notion, appending to a page means adding "children" to a "block" (a page is just a big block)
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    
    # Clean up the string provided by the LLM into a Python list
    task_list = [task.strip() for task in tasks.split(",") if task.strip()]
    
    # Construct the strict JSON schema required for Notion to-do blocks
    children = []
    for task in task_list:
        children.append({
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {"content": task}
                    }
                ],
                "checked": False # Defaults the box to unchecked
            }
        })
        
    payload = {"children": children}
    
    # The append endpoint specifically requires a PATCH request, not a POST
    response = requests.patch(url, headers=get_notion_headers(), json=payload)
    
    if response.status_code != 200:
        return f"Failed to add to-do list. Error: {response.json().get('message')}"
        
    return f"Successfully added {len(task_list)} tasks as a checklist to the page."

def search_notion_pages(query: str) -> str:
    """
    Searches Notion for a specific page by its title to extract its page_id.
    Use this FIRST when the user asks to create a database inside a page by name instead of ID.
    """
    url = "https://api.notion.com/v1/search"
    payload = {
        "query": query,
        "filter": {"value": "page", "property": "object"}
    }
    
    response = requests.post(url, headers=get_notion_headers(), json=payload)
    if response.status_code != 200:
        return f"Search failed. Error: {response.json().get('message')}"
    
    results = response.json().get("results", [])
    if not results:
        return f"Could not find any pages matching '{query}'. Remind the user they must add the AI connection to the page first."
        
    output = []
    for page in results[:5]: # Limit to top 5 hits
        # The URL natively contains the page title, allowing the LLM to verify it found the right one
        output.append(f"Page URL (contains title): {page.get('url')} | EXACT PAGE ID: {page['id']}")
        
    return "\n".join(output)
