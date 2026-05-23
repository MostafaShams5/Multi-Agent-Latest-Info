from litellm import acompletion
from tools.search import perform_web_search
from infrastructure.logger import logger

async def researcher_agent(topic: str) -> str:
    """A dedicated fast-agent that researches a topic and writes a report."""
    logger.info(f"🕵️‍♂️ [Researcher Agent] Investigating: '{topic}'")
    
    search_prompt = f"You are a researcher. Generate a single, highly effective search query to find the latest information about: {topic}. Output ONLY the search query."
    
    try:
        query_response = await acompletion(
            model="groq/llama-3.1-8b-instant", 
            messages=[{"role": "user", "content": search_prompt}]
        )
        search_query = query_response.choices[0].message.content.strip()
        
        raw_data = await perform_web_search(query=search_query)
        
        synthesis_prompt = f"""
        You are an expert analyst. Write a clean, professional email report on the topic: '{topic}'.
        Use this raw data: {raw_data}
        Format with headings and bullet points.
        """
        
        report_response = await acompletion(
            model="groq/llama-3.1-8b-instant",
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.3
        )
        
        return report_response.choices[0].message.content

    except Exception as e:
        logger.error(f"Worker Agent Failed: {e}")
        return f"Research failed for '{topic}'."
