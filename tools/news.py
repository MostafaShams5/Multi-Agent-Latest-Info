import httpx
import re
from infrastructure.logger import logger
from config import NEWS_API_KEY


async def search_hacker_news(query: str, limit: int = 3) -> str:
    """Searches Hacker News via Algolia for tech discussions and startup news."""
    url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&hitsPerPage={limit}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            
            hits = data.get("hits", [])
            if not hits:
                return f"No Hacker News stories found for '{query}'."
                
            results = []
            for hit in hits:
                title = hit.get("title", "No Title")
                points = hit.get("points", 0)
                author = hit.get("author", "Unknown")
                link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                
                results.append(f"- {title} ({points} pts by {author})\n  Link: {link}")
                
            return f"Hacker News top results for '{query}':\n" + "\n\n".join(results)
            
        except Exception as e:
            logger.error(f"Hacker News API Error: {e}")
            return "Hacker News search currently offline."

async def search_dev_articles(query: str, limit: int = 3) -> str:
    """Searches Dev.to for software engineering articles and tutorials."""
    # Using 'search' instead of 'tag' makes it more flexible for the LLM
    url = f"https://dev.to/api/articles?search={query}&per_page={limit}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            res.raise_for_status()
            articles = res.json()
            
            if not articles:
                return f"No Dev.to articles found for '{query}'."
                
            results = []
            for art in articles:
                title = art.get("title", "Untitled")
                author = art.get("user", {}).get("name", "Unknown")
                read_time = art.get("reading_time_minutes", 0)
                link = art.get("url", "")
                
                results.append(f"- {title} by {author} ({read_time} min read)\n  Link: {link}")
                
            return f"Dev.to articles for '{query}':\n" + "\n\n".join(results)
            
        except Exception as e:
            logger.error(f"Dev.to API Error: {e}")
            return "Dev.to article feed currently offline."

async def get_currents_news(topic: str = None, language: str = "en", country: str = None) -> str:
    """Fetches real-time or historical news from the Currents API. Optimized for global and Arabic news."""
    if not NEWS_API_KEY:
        return "System Alert: Missing NEWS_API_KEY."

    # Use /search if there's a specific topic, otherwise fallback to /latest-news
    endpoint = "search" if topic else "latest-news"
    url = f"https://api.currentsapi.services/v1/{endpoint}"
    
    # Build parameters dynamically
    params = {"language": language}
    if topic:
        params["keywords"] = topic
    if country:
        params["country"] = country
        
    headers = {"Authorization": NEWS_API_KEY}
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            
            articles = data.get("news", [])
            if not articles:
                return f"No news found matching Topic: '{topic}', Language: '{language}', Country: '{country}'."
                
            results = []
            # Extract top 5 articles to protect the LLM context window limits
            for art in articles[:5]:
                title = art.get("title", "Untitled")
                
                # Truncate the description to keep it clean
                desc = art.get("description", "")
                if desc:
                    desc = desc[:150] + "..." if len(desc) > 150 else desc
                else:
                    desc = "No summary available."
                    
                source = art.get("author", "Unknown Source")
                link = art.get("url", "No Link")
                
                results.append(f"- {title} (Source: {source})\n  Summary: {desc}\n  Link: {link}")
                
            header = f"Top News Results for '{topic}'" if topic else "Latest Breaking News"
            return f"{header} | Language: {language.upper()}:\n" + "\n\n".join(results)
            
        except Exception as e:
            logger.error(f"Currents API Error: {e}")
            return "Official news feed is currently offline."
