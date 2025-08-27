import requests
import json
import os
from typing import List, Dict
from mcp.server.fastmcp import FastMCP

WEATHER_DIR = "weather"

# Get port from environment variable (Render sets this, defaults to 8001 for local dev)
PORT = int(os.environ.get("PORT", 8001))

# Initialize FastMCP server with host and port in constructor
mcp = FastMCP("weather", host="0.0.0.0", port=PORT)

@mcp.tool()
def get_current_weather(location: str) -> str:
    """
    Get current weather information for a specific location.

    Args:
        location: The city name or location to get weather for

    Returns:
        JSON string with current weather information
    """
    try:
        # Using wttr.in - a free weather API that requires no API key
        url = f"https://wttr.in/{location}?format=j1"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        weather_data = response.json()
        
        # Extract current conditions
        current = weather_data.get('current_condition', [{}])[0]
        
        weather_info = {
            'location': location,
            'temperature_c': current.get('temp_C', 'N/A'),
            'temperature_f': current.get('temp_F', 'N/A'),
            'condition': current.get('weatherDesc', [{}])[0].get('value', 'N/A'),
            'humidity': current.get('humidity', 'N/A'),
            'wind_speed_kmh': current.get('windspeedKmph', 'N/A'),
            'wind_direction': current.get('winddir16Point', 'N/A'),
            'feels_like_c': current.get('FeelsLikeC', 'N/A'),
            'feels_like_f': current.get('FeelsLikeF', 'N/A')
        }
        
        # Save weather data
        save_weather_data(location, weather_info)
        
        return json.dumps(weather_info, indent=2)
        
    except requests.RequestException as e:
        return json.dumps({'error': f'Failed to fetch weather data: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'An error occurred: {str(e)}'})


def save_weather_data(location: str, weather_data: dict):
    """Save weather data to local storage"""
    try:
        if not os.path.exists(WEATHER_DIR):
            os.makedirs(WEATHER_DIR)
        
        history_file = os.path.join(WEATHER_DIR, f"{location.lower().replace(' ', '_')}_history.json")
        
        # Load existing history or create new
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
        else:
            history = {'location': location, 'entries': []}
        
        # Add timestamp to weather data
        import datetime
        weather_data['timestamp'] = datetime.datetime.now().isoformat()
        
        # Add new entry to history
        history['entries'].append(weather_data)
        
        # Keep only last 100 entries
        history['entries'] = history['entries'][-100:]
        
        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
            
    except Exception as e:
        print(f"Failed to save weather data: {e}")

if __name__ == "__main__":
    # Run the server with SSE transport
    mcp.run(transport="sse")