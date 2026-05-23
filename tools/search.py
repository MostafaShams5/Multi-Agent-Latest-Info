import httpx
from config import TAVILY_API_KEY
from infrastructure.logger import logger

async def perform_web_search(query: str) -> str:
    logger.info(f"🌍 [Tavily] Searching: '{query}'")
    if not TAVILY_API_KEY: 
        return "System Alert: Tavily API key is missing."

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "include_answer": True, 
        "max_results": 3
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            answer = data.get("answer", "")
            results = "\n".join([f"- {r['title']} ({r['url']})" for r in data.get("results", [])])
            return f"{answer}\n\nSources:\n{results}"
        except Exception as e:
            logger.error(f"Tavily Error: {e}")
            return "Search engine offline."
