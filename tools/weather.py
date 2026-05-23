import httpx
from config import WEATHER_API_KEY
from infrastructure.logger import logger

async def fetch_weather(location: str) -> str:
    if not WEATHER_API_KEY: 
        return "Missing Weather API Key."
    
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={location}&aqi=no"
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            return f"Weather in {data['location']['name']}: {data['current']['temp_c']}°C, {data['current']['condition']['text']}."
        except Exception as e:
            logger.error(f"Weather API Error: {e}")
            return f"Could not fetch weather for {location}."
