import os
import requests
import json
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

def get_atlassian_auth():
    """Retrieves the Atlassian domain, email, and API token for authentication."""
    load_dotenv()
    domain = os.getenv("ATLASSIAN_DOMAIN")
    email = os.getenv("ATLASSIAN_EMAIL")
    api_token = os.getenv("ATLASSIAN_API_KEY")
    
    if not all([domain, email, api_token]):
        raise ValueError("Missing ATLASSIAN_DOMAIN, ATLASSIAN_EMAIL, or ATLASSIAN_API_KEY in .env file.")
        
    return domain, email, api_token

def search_jira_issues(jql_query: str, max_results: int = 5) -> str:
    """
    Searches for Jira issues using JQL (Jira Query Language).
    You MUST provide 'jql_query' as a valid JQL string (e.g., "project = PROJ AND status = 'In Progress'").
    """
    domain, email, api_token = get_atlassian_auth()
    url = f"https://{domain}/rest/api/3/search"
    
    auth = HTTPBasicAuth(email, api_token)
    headers = {"Accept": "application/json"}
    params = {
        "jql": jql_query,
        "maxResults": max_results,
        "fields": "summary,status,assignee"
    }
    
    response = requests.get(url, headers=headers, auth=auth, params=params)
    if response.status_code != 200:
        return f"Failed to search Jira. Error: {response.text}"
        
    issues = response.json().get("issues", [])
    if not issues:
        return f"No Jira issues found matching query: '{jql_query}'"
        
    output = []
    for issue in issues:
        key = issue.get("key")
        fields = issue.get("fields", {})
        summary = fields.get("summary", "No Summary")
        status = fields.get("status", {}).get("name", "Unknown")
        output.append(f"Issue: {key} | Status: {status} | Summary: {summary}")
        
    return "\n".join(output)

def create_jira_issue(project_key: str, summary: str, description: str, issue_type: str = "Task") -> str:
    """
    Creates a new issue in a specific Jira project.
    You MUST provide the exact 'project_key' (e.g., 'PROJ'), a 'summary' (title), and a 'description'.
    'issue_type' defaults to 'Task', but can be 'Bug', 'Story', etc. depending on the project setup.
    """
    domain, email, api_token = get_atlassian_auth()
    url = f"https://{domain}/rest/api/3/issue"
    
    auth = HTTPBasicAuth(email, api_token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Jira API v3 requires Atlassian Document Format (ADF) for descriptions
    payload = json.dumps({
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
            "issuetype": {"name": issue_type}
        }
    })
    
    response = requests.post(url, headers=headers, auth=auth, data=payload)
    if response.status_code == 201:
        created_issue = response.json()
        return f"Successfully created Jira issue: {created_issue.get('key')} at {created_issue.get('self')}"
        
    return f"Failed to create Jira issue. Error: {response.text}"

def add_jira_comment(issue_key: str, comment_text: str) -> str:
    """
    Adds a comment to an existing Jira issue.
    You MUST provide the exact 'issue_key' (e.g., 'PROJ-123') and the 'comment_text'.
    """
    domain, email, api_token = get_atlassian_auth()
    url = f"https://{domain}/rest/api/3/issue/{issue_key}/comment"
    
    auth = HTTPBasicAuth(email, api_token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # ADF format for the comment
    payload = json.dumps({
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": comment_text}]
                }
            ]
        }
    })
    
    response = requests.post(url, headers=headers, auth=auth, data=payload)
    if response.status_code == 201:
        return f"Successfully added comment to {issue_key}."
        
    return f"Failed to add comment. Error: {response.text}"
