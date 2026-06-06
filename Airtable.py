import os
import requests
import json
from dotenv import load_dotenv

def get_airtable_headers():
    """Generates the required headers for Airtable's API."""
    load_dotenv()
    airtable_token = os.getenv("AIRTABLE_API_KEY")
    if not airtable_token:
        raise ValueError("AIRTABLE_API_KEY not found in .env file.")
    return {
        "Authorization": f"Bearer {airtable_token}",
        "Content-Type": "application/json"
    }

def read_airtable_records(base_id: str, table_id: str, max_records: int = 5) -> str:
    """
    Reads the most recent records from a specific Airtable base and table.
    You MUST provide the exact 'base_id' (starts with 'app') and 'table_id' (starts with 'tbl' or table name).
    """
    url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
    params = {"maxRecords": max_records}
    
    response = requests.get(url, headers=get_airtable_headers(), params=params)
    if response.status_code != 200:
        return f"Failed to read records. Error: {response.json().get('error', {}).get('message', 'Unknown error')}"
        
    records = response.json().get("records", [])
    if not records:
        return "The table is empty or no records were found."
        
    output = []
    for record in records:
        fields = record.get("fields", {})
        # Flatten the fields into a readable string
        field_strs = [f"{k}: {v}" for k, v in fields.items()]
        output.append(f"Record ID: {record['id']} | " + " | ".join(field_strs))
        
    return "\n".join(output)

def create_airtable_record(base_id: str, table_id: str, fields_json: str) -> str:
    """
    Creates a new record in a specific Airtable base and table.
    You MUST provide the exact 'base_id' and 'table_id'.
    You MUST provide 'fields_json' as a valid JSON string mapping column names to values (e.g., '{"Name": "John", "Status": "Todo"}').
    """
    url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
    
    try:
        fields_dict = json.loads(fields_json)
    except json.JSONDecodeError:
        return "Failed to parse fields_json. It must be a valid JSON string."
        
    payload = {
        "records": [
            {
                "fields": fields_dict
            }
        ]
    }
    
    response = requests.post(url, headers=get_airtable_headers(), json=payload)
    if response.status_code != 200:
        return f"Failed to create record. Error: {response.json().get('error', {}).get('message', 'Unknown error')}"
        
    return "Successfully created the record in Airtable."
