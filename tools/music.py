import httpx
from infrastructure.logger import logger

async def get_artist_profile(artist_name: str) -> str:
    """Fetches artist biography, genre, and formation year from TheAudioDB."""
    url = f"https://www.theaudiodb.com/api/v1/json/2/search.php?s={artist_name}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            
            if not data or not data.get("artists"):
                return f"No artist profile found for '{artist_name}'."
                
            # Extracting using the exact JSON keys from TheAudioDB
            artist = data["artists"][0]
            name = artist.get("strArtist", "Unknown")
            formed = artist.get("intFormedYear", "Unknown")
            genre = artist.get("strGenre", "Unknown")
            # Truncate biography to keep context windows clean
            bio = artist.get("strBiography", "")[:600] 
            
            return f"Artist: {name}\nFormed: {formed}\nGenre: {genre}\nBio Summary: {bio}..."
            
        except Exception as e:
            logger.error(f"TheAudioDB API Error: {e}")
            return "Music database currently offline."

async def search_music_track(query: str) -> str:
    """Searches Deezer for track information, duration, and an MP3 preview link."""
    url = f"https://api.deezer.com/search?q={query}&limit=3"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            
            if not data or not data.get("data"):
                return f"No tracks found for '{query}'."
                
            results = []
            for track in data["data"]:
                title = track.get("title", "Unknown Track")
                artist = track.get("artist", {}).get("name", "Unknown Artist")
                
                # Convert duration from seconds to MM:SS format
                duration_sec = track.get("duration", 0)
                mins, secs = divmod(duration_sec, 60)
                duration_formatted = f"{mins}:{secs:02d}"
                
                preview = track.get("preview", "No preview available")
                
                results.append(
                    f"- {title} by {artist} ({duration_formatted})\n  Listen Preview: {preview}"
                )
                
            return f"Top search results for '{query}':\n" + "\n\n".join(results)
            
        except Exception as e:
            logger.error(f"Deezer API Error: {e}")
            return "Deezer service offline."
