import os
import requests
from dotenv import load_dotenv

def get_headers():
    """Generates auth headers."""
    load_dotenv()
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    if not bot_token:
        raise ValueError("SLACK_BOT_TOKEN not found in .env file.")
    return {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

def list_channels() -> list:
    """Fetches public channels."""
    url = "https://slack.com/api/conversations.list"
    params = {"exclude_archived": True, "types": "public_channel"}
    response = requests.get(url, headers=get_headers(), params=params)
    response.raise_for_status()
    return response.json().get("channels", [])

def get_history(channel_id: str, limit: int = 10) -> list:
    """Fetches recent channel history."""
    url = "https://slack.com/api/conversations.history"
    params = {"channel": channel_id, "limit": limit}
    response = requests.get(url, headers=get_headers(), params=params)
    response.raise_for_status()
    return response.json().get("messages", [])

def send_message(channel_id: str, text: str) -> dict:
    """Posts a message to a channel."""
    url = "https://slack.com/api/chat.postMessage"
    headers = get_headers()
    headers["Content-Type"] = "application/json; charset=utf-8"
    payload = {"channel": channel_id, "text": text}
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    
    if not data.get("ok"):
        raise ValueError(f"Slack API Rejected: {data.get('error')}")
    return data

# --- Terminal Execution Interface ---
if __name__ == "__main__":
    print("--- Available Channels ---")
    channels = list_channels()
    if not channels:
        print("No channels found.")
        exit()

    for idx, c in enumerate(channels):
        print(f"[{idx}] #{c['name']} (ID: {c['id']})")

    try:
        # 1. Select Channel
        ch_idx = int(input("\nEnter channel number: ").strip())
        target_id = channels[ch_idx]['id']
        target_name = channels[ch_idx]['name']

        # 2. Choose Action
        action = input(f"Selected #{target_name}. [1] Read History or [2] Send Message? ").strip()

        if action == '1':
            print(f"\n--- Latest Messages in #{target_name} ---")
            msgs = get_history(target_id)
            for m in msgs:
                text = m.get('text') or f"[{m.get('subtype', 'system message')}]"
                print(f"- {text}")
                
        elif action == '2':
            msg_text = input(f"Type message to #{target_name}: ")
            if msg_text.strip():
                print("Sending...")
                send_message(target_id, msg_text)
                print("Message delivered.")
            else:
                print("Empty message. Aborted.")
        else:
            print("Invalid selection.")

    except (ValueError, IndexError):
        print("Invalid input. Run the script again.")
    except KeyboardInterrupt:
        print("\nProcess terminated.")