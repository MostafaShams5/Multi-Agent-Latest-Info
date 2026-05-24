import httpx
from config import WEATHER_API_KEY
from infrastructure.logger import logger

async def fetch_weather(location: str) -> str:
    """Gets real-time weather and the local time for a specific city."""
    if not WEATHER_API_KEY: 
        return "Missing Weather API Key."
    
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={location}&aqi=no"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            
            # WeatherAPI natively provides the time-zone adjusted local date and time!
            local_time = data['location']['localtime']
            city = data['location']['name']
            country = data['location']['country']
            
            temp = data['current']['temp_c']
            condition = data['current']['condition']['text']
            
            return f"Weather in {city}, {country} as of {local_time} (Local Time): {temp}°C, {condition}."
            
        except Exception as e:
            logger.error(f"Weather API Error: {e}")
            return f"Could not fetch weather for {location}."
