import httpx
from datetime import datetime
from config import FOOTBALL_API_KEY
from infrastructure.logger import logger

async def get_recent_football_matches(date: str = None, team_filter: str = None) -> str:
    """
    Gets global football matches for a specific date. 
    Applies a local team_filter to prevent sending 700+ daily matches to the LLM.
    """
    if not FOOTBALL_API_KEY:
        return "System Alert: Missing FOOTBALL_API_KEY."

    # Default to today's date in YYYY-MM-DD format if the LLM doesn't specify
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    url = f"https://v3.football.api-sports.io/fixtures?date={date}"
    headers = {
        "x-apisports-key": FOOTBALL_API_KEY
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.get(url, headers=headers)
            res.raise_for_status()
            data = res.json()

            fixtures = data.get("response", [])
            if not fixtures:
                return f"No matches found for {date}."

            results = []
            for item in fixtures:
                # Extract data using the exact api-sports schema
                league = item["league"]["name"]
                status = item["fixture"]["status"]["short"]  # e.g., FT (Full Time), NS (Not Started)
                home = item["teams"]["home"]["name"]
                away = item["teams"]["away"]["name"]
                
                # If a team filter is provided by the LLM, ignore matches that don't match
                if team_filter:
                    if team_filter.lower() not in home.lower() and team_filter.lower() not in away.lower():
                        continue

                # Goals can be None if the match hasn't started
                h_goals = item["goals"]["home"] if item["goals"]["home"] is not None else "-"
                a_goals = item["goals"]["away"] if item["goals"]["away"] is not None else "-"

                # Format: [Serie A] Flamengo 0 - 3 Palmeiras (FT)
                results.append(f"[{league}] {home} {h_goals} - {a_goals} {away} ({status})")

            if not results:
                return f"No matches found matching '{team_filter}' on {date}."

            # Context Window Protection: Cap at 20 matches if no filter is applied
            if len(results) > 20:
                summary = "\n".join(results[:20])
                return (
                    f"Showing 20 of {len(results)} matches for {date}:\n{summary}\n\n"
                    f"System Note to LLM: There are {len(results) - 20} more matches. "
                    f"If the user wants a specific match, use the 'team_filter' parameter."
                )

            return f"Match results for {date}:\n" + "\n".join(results)

        except Exception as e:
            logger.error(f"API-Sports Error: {e}")
            return "Global sports data feed currently offline."
