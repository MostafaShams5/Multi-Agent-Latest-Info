import httpx
from infrastructure.logger import logger

async def search_tv_shows(query: str) -> str:
    """Searches for TV show details, summaries, and ratings."""
    url = f"https://api.tvmaze.com/search/shows?q={query}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            
            if not data:
                return f"No TV shows found for '{query}'."
                
            # Extract top 3 results
            results = []
            for item in data[:3]:
                show = item['show']
                name = show.get('name', 'Unknown')
                rating = show.get('rating', {}).get('average', 'N/A')
                summary = show.get('summary', '').replace('<p>', '').replace('</p>', '').replace('<b>', '').replace('</b>', '')
                results.append(f"Title: {name} (Rating: {rating})\nSummary: {summary[:200]}...\n")
                
            return "\n".join(results)
        except Exception as e:
            logger.error(f"TVmaze API Error: {e}")
            return "TV Show database currently offline."

async def search_itunes_media(term: str, media_type: str = "movie") -> str:
    """Searches the iTunes catalog for movies, music, or podcasts."""
    url = f"https://itunes.apple.com/search?term={term}&entity={media_type}&limit=3"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            
            if data.get('resultCount', 0) == 0:
                return f"No {media_type} found for '{term}'."
                
            results = [f"- {item.get('trackName', item.get('collectionName'))} ({item.get('releaseDate', '')[:4]})" 
                       for item in data['results']]
            return "Found media:\n" + "\n".join(results)
        except Exception as e:
            logger.error(f"iTunes API Error: {e}")
            return "iTunes search offline."
