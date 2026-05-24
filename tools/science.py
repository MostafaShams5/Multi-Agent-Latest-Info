import httpx
from infrastructure.logger import logger
from datetime import datetime, timedelta

async def check_recent_earthquakes(min_magnitude: float = 5.0) -> str:
    """Checks the USGS catalog for recent major earthquakes in the last 24 hours."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    url = (f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
           f"&starttime={start_time.strftime('%Y-%m-%d')}"
           f"&endtime={end_time.strftime('%Y-%m-%d')}"
           f"&minmagnitude={min_magnitude}")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            
            events = data.get('features', [])
            if not events:
                return f"No earthquakes above {min_magnitude} magnitude in the last 24 hours."
                
            results = [f"- Mag {e['properties']['mag']}: {e['properties']['place']}" for e in events[:5]]
            return "Recent major earthquakes:\n" + "\n".join(results)
        except Exception as e:
            logger.error(f"USGS API Error: {e}")
            return "Earthquake monitoring offline."

async def locate_iss() -> str:
    """Finds the current latitude and longitude of the International Space Station."""
    url = "http://api.open-notify.org/iss-now.json"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            
            pos = data['iss_position']
            return f"The ISS is currently located at Latitude {pos['latitude']}, Longitude {pos['longitude']}."
        except Exception as e:
            logger.error(f"ISS API Error: {e}")
            return "Could not locate the ISS."
