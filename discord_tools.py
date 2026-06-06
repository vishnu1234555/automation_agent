import os
import requests
from dotenv import load_dotenv

def get_discord_headers() -> dict:
    """
    Builds the authorization headers for Discord API requests.
    Loads the 'DISCORD_BOT_TOKEN' environment variable.
    
    Returns:
        dict: Headers containing the Bot token and Content-Type.
    """
    load_dotenv()
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN not found in environment variables.")
    return {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }

def broadcast_server_announcement(channel_id: str, content: str) -> dict:
    """
    Posts a message to a specific Discord channel.
    
    Args:
        channel_id (str): The exact ID of the Discord channel.
        content (str): The text message to send to the channel.
        
    Returns:
        dict: The response from the Discord API representing the sent message.
    """
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    payload = {"content": content}
    
    response = requests.post(url, headers=get_discord_headers(), json=payload)
    return response.json()

def get_recent_messages(channel_id: str, limit: int = 50) -> list:
    """
    Fetches historical channel data (recent messages) from a specific Discord channel.
    
    Args:
        channel_id (str): The exact ID of the Discord channel.
        limit (int, optional): The maximum number of messages to return (max 100, defaults to 50).
        
    Returns:
        list: A list of dictionaries representing the recent messages.
    """
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    params = {"limit": limit}
    
    response = requests.get(url, headers=get_discord_headers(), params=params)
    if response.status_code != 200:
        return [response.json()]
        
    return response.json()
