import os
import requests
from dotenv import load_dotenv

def get_discord_headers():
    """Generates the required headers for Discord's API."""
    load_dotenv()
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    if not discord_token:
        raise ValueError("DISCORD_BOT_TOKEN not found in .env file.")
    return {
        "Authorization": f"Bot {discord_token}",
        "Content-Type": "application/json"
    }

def list_discord_guilds() -> str:
    """
    Retrieves the list of Discord guilds (servers) the bot is in.
    Use this FIRST to find the 'guild_id' before listing channels.
    """
    url = "https://discord.com/api/v10/users/@me/guilds"
    
    response = requests.get(url, headers=get_discord_headers())
    if response.status_code != 200:
        return f"Failed to list guilds. Error: {response.text}"
        
    guilds = response.json()
    if not guilds:
        return "The bot is not currently in any Discord servers."
        
    output = []
    for guild in guilds:
        output.append(f"Guild Name: '{guild.get('name')}' | EXACT GUILD ID: {guild.get('id')}")
        
    return "\n".join(output)

def list_discord_channels(guild_id: str) -> str:
    """
    Retrieves the list of channels in a specific Discord guild (server).
    You MUST provide the exact 'guild_id' (server ID).
    Use this to find the 'channel_id' before sending a message.
    """
    url = f"https://discord.com/api/v10/guilds/{guild_id}/channels"
    
    response = requests.get(url, headers=get_discord_headers())
    if response.status_code != 200:
        return f"Failed to list channels. Error: {response.text}"
        
    channels = response.json()
    if not channels:
        return f"No channels found in guild {guild_id}."
        
    output = []
    for channel in channels:
        # channel types: 0 = text, 2 = voice. We mostly care about text channels for messaging
        if channel.get('type') == 0:
            output.append(f"Channel Name: '#{channel.get('name')}' | EXACT CHANNEL ID: {channel.get('id')}")
            
    return "\n".join(output) if output else "No text channels found in this server."

def send_discord_message(channel_id: str, message: str) -> str:
    """
    Sends a message to a specific Discord channel.
    You MUST provide the exact 'channel_id' and the 'message' content.
    """
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    payload = {"content": message}
    
    response = requests.post(url, headers=get_discord_headers(), json=payload)
    if response.status_code == 200:
        return f"Successfully sent message to Discord channel {channel_id}."
        
    return f"Failed to send message. Error: {response.text}"
