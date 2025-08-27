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

@mcp.tool()
def get_weather_forecast(location: str, days: int = 3) -> str:
    """
    Get weather forecast for a specific location.

    Args:
        location: The city name or location to get forecast for
        days: Number of days to get forecast for (1-3)

    Returns:
        JSON string with weather forecast information
    """
    try:
        url = f"https://wttr.in/{location}?format=j1"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        weather_data = response.json()
        
        # Extract forecast data
        forecast_data = weather_data.get('weather', [])
        forecast_info = {
            'location': location,
            'forecast_days': min(days, len(forecast_data)),
            'forecast': []
        }
        
        for i, day in enumerate(forecast_data[:days]):
            day_info = {
                'date': day.get('date', 'N/A'),
                'max_temp_c': day.get('maxtempC', 'N/A'),
                'max_temp_f': day.get('maxtempF', 'N/A'),
                'min_temp_c': day.get('mintempC', 'N/A'),
                'min_temp_f': day.get('mintempF', 'N/A'),
                'condition': day.get('hourly', [{}])[0].get('weatherDesc', [{}])[0].get('value', 'N/A')
            }
            forecast_info['forecast'].append(day_info)
        
        return json.dumps(forecast_info, indent=2)
        
    except requests.RequestException as e:
        return json.dumps({'error': f'Failed to fetch forecast data: {str(e)}'})
    except Exception as e:
        return json.dumps({'error': f'An error occurred: {str(e)}'})

@mcp.tool()
def get_weather_history(location: str) -> str:
    """
    Get saved weather history for a location.

    Args:
        location: The city name or location to get history for

    Returns:
        JSON string with weather history
    """
    try:
        if not os.path.exists(WEATHER_DIR):
            return json.dumps({'error': 'No weather history available'})
        
        history_file = os.path.join(WEATHER_DIR, f"{location.lower().replace(' ', '_')}_history.json")
        
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
            return json.dumps(history, indent=2)
        else:
            return json.dumps({'error': f'No history found for {location}'})
            
    except Exception as e:
        return json.dumps({'error': f'Failed to retrieve history: {str(e)}'})

@mcp.tool()
def get_saved_locations() -> str:
    """
    Get list of locations with saved weather data.

    Returns:
        JSON string with list of saved locations
    """
    try:
        if not os.path.exists(WEATHER_DIR):
            return json.dumps({'locations': []})
        
        locations = []
        for file in os.listdir(WEATHER_DIR):
            if file.endswith('_history.json'):
                location = file.replace('_history.json', '').replace('_', ' ').title()
                locations.append(location)
        
        return json.dumps({'locations': locations}, indent=2)
        
    except Exception as e:
        return json.dumps({'error': f'Failed to retrieve locations: {str(e)}'})

@mcp.resource("locations://list")
def get_locations() -> str:
    """Get all saved weather locations"""
    return get_saved_locations()

@mcp.resource("weather://history/{location}")
def get_location_history(location: str) -> str:
    """Get weather history for a specific location"""
    return get_weather_history(location)

@mcp.prompt()
def generate_weather_prompt(location: str) -> str:
    """
    Generate a comprehensive weather report prompt for a location.

    Args:
        location: The city name or location to generate prompt for

    Returns:
        A detailed prompt for weather analysis
    """
    current_weather = get_current_weather(location)
    forecast = get_weather_forecast(location)
    
    prompt = f"""
    Please provide a comprehensive weather analysis for {location} based on the following data:

    Current Weather:
    {current_weather}

    3-Day Forecast:
    {forecast}

    Please include:
    1. Current conditions summary
    2. Temperature trends
    3. Weather outlook for the next few days
    4. Any notable weather patterns
    5. Recommendations for outdoor activities or clothing
    """
    
    return prompt

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