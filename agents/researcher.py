from pydantic_ai import Agent
from tools.search import perform_web_search
from llmlingua import PromptCompressor
from infrastructure.logger import logger
import os


compressor = PromptCompressor(
    model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank", 
    use_llmlingua2=True,
    device_map="cpu"  # <--- ADD THIS LINE TO FORCE CPU MODE
)

research_agent = Agent(
    'groq:llama-3.1-8b-instant',
    system_prompt="You are an expert analyst. Write clean, professional email reports. Use markdown headings."
)

async def researcher_agent(topic: str) -> str:
    logger.info(f"🕵️‍♂️ [Worker Agent] Investigating: '{topic}'")
    
    # 1. Gather Raw Data
    search_query = f"Latest news and facts about {topic}"
    raw_data = await perform_web_search(query=search_query)
    
    # 2. Token Compression (LLMLingua)
    # Reduces massive context windows while retaining semantic meaning
    logger.info("🗜️ Compressing web data tokens...")
    compressed_data = compressor.compress_prompt(
        context=[raw_data],
        instruction="Extract key facts.",
        rate=0.5, # Compress by 50%
        force_tokens=['\n', '.']
    )
    
    # 3. Synthesize via Pydantic AI
    synthesis_prompt = f"Topic: '{topic}'.\nRaw Data:\n{compressed_data['compressed_prompt']}"
    
    try:
        # Pydantic AI automatically handles the Groq HTTP connection
        result = await research_agent.run(synthesis_prompt)
        return result.output
    except Exception as e:
        logger.error(f"Worker Agent Failed: {e}")
        return f"Research failed for '{topic}'."
