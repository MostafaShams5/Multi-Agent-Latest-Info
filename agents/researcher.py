import torch
from pydantic_ai import Agent
from tools.search import perform_web_search
from llmlingua import PromptCompressor
from infrastructure.logger import logger

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
compressor = PromptCompressor(
    model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank", 
    use_llmlingua2=True,
    device_map=DEVICE
)

# Qwen 3 32B handles the deep analytical extraction
research_agent = Agent(
    'groq:qwen/qwen3-32b', 
    system_prompt=(
        "You are a backend data extractor and web researcher. "
        "Analyze the provided web search context and extract all the critical, factual data. "
        "Focus purely on depth and accuracy. Do not worry about making it pretty or formatting it as an email—your raw output will be passed to a dedicated writing model."
    )
)

COMPRESSION_THRESHOLD_CHARS = 3000

async def researcher_action(topic: str) -> str:
    logger.info(f"🕵️‍♂️ [Researcher] Qwen-32B investigating: '{topic}'")
    
    raw_data = await perform_web_search(query=f"Latest news and facts about {topic}")
    
    if len(raw_data) < COMPRESSION_THRESHOLD_CHARS:
        processed_data = raw_data
    else:
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
        logger.error(f"Researcher Failed: {e}")
        return f"Extraction failed for '{topic}'."
