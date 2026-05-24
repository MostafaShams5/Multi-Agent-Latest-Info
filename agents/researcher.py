import torch
from pydantic_ai import Agent
from tools.search import perform_web_search
from llmlingua import PromptCompressor
from infrastructure.logger import logger

# 1. Dynamic Device Mapping: Uses GPU on AWS G5, falls back to CPU locally
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

compressor = PromptCompressor(
    model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank", 
    use_llmlingua2=True,
    device_map=DEVICE
)

research_agent = Agent(
    'groq:llama-3.1-8b-instant',
    system_prompt="You are an expert analyst. Write clean, professional email reports. Use markdown headings."
)

# Set a threshold: Only compress if the text is massive
COMPRESSION_THRESHOLD_CHARS = 3000

async def researcher_agent(topic: str) -> str:
    logger.info(f"🕵️‍♂️ [Worker Agent] Investigating: '{topic}'")
    
    raw_data = await perform_web_search(query=f"Latest news and facts about {topic}")
    
    # 2. Smart Bypass: Skip LLMLingua if the payload is small
    if len(raw_data) < COMPRESSION_THRESHOLD_CHARS:
        logger.info("⚡ Data payload is small. Bypassing LLMLingua compression.")
        processed_data = raw_data
    else:
        logger.info(f"🗜️ Compressing {len(raw_data)} chars on {DEVICE.upper()}...")
        compressed = compressor.compress_prompt(
            context=[raw_data],
            instruction="Extract key facts.",
            rate=0.5, 
            force_tokens=['\n', '.']
        )
        processed_data = compressed['compressed_prompt']
    
    synthesis_prompt = f"Topic: '{topic}'.\nRaw Data:\n{processed_data}"
    
    try:
        result = await research_agent.run(synthesis_prompt)
        return result.output
    except Exception as e:
        logger.error(f"Worker Agent Failed: {e}")
        return f"Research failed for '{topic}'."
