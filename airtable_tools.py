import os
import requests
from dotenv import load_dotenv

def get_airtable_headers() -> dict:
    """
    Builds the authorization headers for Airtable API requests.
    Loads the 'AIRTABLE_PAT' environment variable.
    
    Returns:
        dict: Headers containing the Bearer token and Content-Type.
    """
    load_dotenv()
    pat = os.getenv("AIRTABLE_PAT")
    if not pat:
        raise ValueError("AIRTABLE_PAT not found in environment variables.")
    return {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }

def sync_inventory_levels(base_id: str, table_name: str, record_id: str, fields: dict) -> dict:
    """
    Updates specific fields for an existing record in an Airtable base.
    
    Args:
        base_id (str): The exact Airtable Base ID (starts with 'app').
        table_name (str): The exact name of the table or its ID (starts with 'tbl').
        record_id (str): The specific Record ID to update (starts with 'rec').
        fields (dict): A dictionary mapping column names to their new values.
        
    Returns:
        dict: The updated record data returned by Airtable, or an error dictionary.
    """
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}/{record_id}"
    payload = {"fields": fields}
    
    response = requests.patch(url, headers=get_airtable_headers(), json=payload)
    return response.json()

def generate_supply_report(base_id: str, table_name: str, filter_by_formula: str = None) -> list:
    """
    Fetches rows from a specific Airtable base, optionally filtered by an Airtable formula.
    
    Args:
        base_id (str): The exact Airtable Base ID (starts with 'app').
        table_name (str): The exact name of the table or its ID (starts with 'tbl').
        filter_by_formula (str, optional): A valid Airtable formula string to filter results (e.g. "{Status} = 'Pending'").
        
    Returns:
        list: A list of dictionaries representing the fetched records.
    """
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
    params = {}
    if filter_by_formula:
        params["filterByFormula"] = filter_by_formula
        
    response = requests.get(url, headers=get_airtable_headers(), params=params)
    if response.status_code != 200:
        return [response.json()]
        
    return response.json().get("records", [])
