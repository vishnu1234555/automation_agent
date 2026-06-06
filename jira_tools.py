import os
import requests
import json
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

def get_jira_auth():
    """
    Builds the basic authentication object for Jira API requests.
    Loads 'JIRA_EMAIL' and 'JIRA_API_TOKEN' environment variables.
    
    Returns:
        HTTPBasicAuth: The authentication object required by the requests library.
    """
    load_dotenv()
    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")
    if not email or not token:
        raise ValueError("JIRA_EMAIL or JIRA_API_TOKEN missing from environment variables.")
    return HTTPBasicAuth(email, token)

def create_bug_ticket(domain: str, project_key: str, summary: str, description: str) -> dict:
    """
    Creates a standard 'Bug' issue type ticket in a specific Jira project.
    
    Args:
        domain (str): The Jira cloud domain (e.g., 'your-domain.atlassian.net').
        project_key (str): The exact Jira project key (e.g., 'PROJ').
        summary (str): The title or brief summary of the bug.
        description (str): Detailed explanation of the bug.
        
    Returns:
        dict: The response from the Jira API containing the new issue key and link.
    """
    url = f"https://{domain}/rest/api/3/issue"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }
                ]
            },
            "issuetype": {"name": "Bug"}
        }
    }
    
    response = requests.post(url, headers=headers, auth=get_jira_auth(), json=payload)
    return response.json()

def summarize_sprint_blockers(domain: str, jql_query: str) -> list:
    """
    Executes a search for Jira issues using a specific JQL string to identify blockers.
    
    Args:
        domain (str): The Jira cloud domain (e.g., 'your-domain.atlassian.net').
        jql_query (str): A valid Jira Query Language string (e.g., "project = PROJ AND status = Blocked").
        
    Returns:
        list: A list of dictionaries representing the blocked Jira issues.
    """
    url = f"https://{domain}/rest/api/3/search"
    headers = {"Accept": "application/json"}
    params = {
        "jql": jql_query,
        "fields": "summary,status,assignee,priority",
        "maxResults": 50
    }
    
    response = requests.get(url, headers=headers, auth=get_jira_auth(), params=params)
    if response.status_code != 200:
        return [response.json()]
        
    return response.json().get("issues", [])
