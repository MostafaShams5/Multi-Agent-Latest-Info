import asyncio
from typing import Literal, Optional
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

# Tool Imports
from tools.search import perform_web_search
from tools.weather import fetch_weather
from tools.telegram import send_telegram_message
from tools.gmail import send_gmail_report
from tools.knowledge_base import query_internal_documents

from agents.researcher import researcher_action
from agents.reporter import format_and_email
# Infrastructure Imports
from infrastructure.qdrant_store import get_memory, save_memory
from infrastructure.semantic_cache import check_cache, save_to_cache
from infrastructure.logger import logger

# Add to imports in agents/supervisor.py
from tools.media import search_tv_shows, search_itunes_media
from tools.sports import get_recent_football_matches
from tools.science import check_recent_earthquakes, locate_iss

import re

from tools.news import get_currents_news, search_hacker_news, search_dev_articles
from tools.finance import convert_currency, get_live_crypto_price



# ==========================================
class RoutingDecision(BaseModel):
    category: Literal["small_talk", "simple_tool", "complex_task"]
    direct_response: Optional[str] = None
    email_target: Optional[str] = None

triage_agent = Agent(
    'groq:qwen/qwen3-32b',
    output_type=RoutingDecision,
    retries=3,  # <--- FIX 1: Give the model 3 automatic attempts to fix its JSON formatting
    system_prompt=(
        "You are the frontline system gateway. Analyze the user's message and the conversation history.\n"
        "1. If it's a greeting, casual chat, or pleasantry, set category to 'small_talk' and provide a friendly 'direct_response'.\n"
        "2. If the user wants a quick fact, web search, internal document search, weather, sports scores, earthquake data, media/TV ratings, music/songs, official breaking news, Arabic news, local Egyptian news, Dev.to articles, Hacker News discussions, currency conversion, or crypto prices, set category to 'simple_tool'.\n"
        "3. If the user asks for deep research, multiple complex tasks, or explicitly asks to be emailed a report, set category to 'complex_task'. Look closely at the history to extract their email into 'email_target' if they previously provided it.\n\n"
        "CRITICAL FORMATTING RULES:\n"
        "- You MUST return ONLY pure, raw valid JSON.\n"
        "- DO NOT wrap your response in <function> tags, HTML, or markdown code blocks.\n"
        "- DO NOT hallucinate or call external tools (e.g., never output <function=brave_search>)."
    )
)



supervisor = Agent(
    'groq:llama-3.3-70b-versatile',
    retries=3,
    system_prompt=(
        "You are an expert AI orchestrator. You have access to tools to assist the user.\n"
        "INSTRUCTIONS:\n"
        "- When you need information, you MUST use the provided tools.\n"
        "- Do NOT write out <function> tags or XML in your response. Simply invoke the tool function directly.\n"
        "- If you need to search for a football match, use 'lookup_global_football'.\n"
        "- If you need music info, use the music tools."
    )
)
@supervisor.tool
async def lookup_tv_show(ctx: RunContext[int], query: str) -> str:
    """Searches for summaries and ratings of TV shows."""
    return await search_tv_shows(query)

@supervisor.tool
async def lookup_football_scores(ctx: RunContext[int], league: str, year: str) -> str:
    """Gets recent match scores for European football leagues (e.g., 'bl1' for Bundesliga, 'pl' for Premier League)."""
    return await get_recent_football_matches(league, year)

@supervisor.tool
async def check_global_earthquakes(ctx: RunContext[int]) -> str:
    """Checks for recent major earthquakes worldwide."""
    return await check_recent_earthquakes()

@supervisor.tool
async def check_current_weather(ctx: RunContext[int], location: str) -> str:
    """Gets the real-time weather for a specific city."""
    return await fetch_weather(location)

@supervisor.tool
async def search_live_web(ctx: RunContext[int], query: str) -> str:
    """Searches the public internet for news or facts."""
    return await perform_web_search(query)

@supervisor.tool
async def search_internal_documents(ctx: RunContext[int], query: str) -> str:
    """Searches the private RAG database for internal files and documents."""
    return await query_internal_documents(query)


#@supervisor.tool
#async def lookup_global_football(ctx: RunContext[int], date_yyyy_mm_dd: str = None, team_name: str = None) -> str:
#    """
#    Searches global football (soccer) fixtures.
#    - date_yyyy_mm_dd: The date to search (e.g., '2026-05-24'). Leave None for today.
#    - team_name: CRITICAL - Always provide a team name (e.g., 'Flamengo', 'Liverpool') if the user asks for a specific team, to avoid pulling hundreds of unrelated matches.
#    """
#    return await get_football_matches(date=date_yyyy_mm_dd, team_filter=team_name)
    
    
    

@supervisor.tool
async def search_tech_discussions(ctx: RunContext[int], query: str) -> str:
    """Searches Hacker News for tech startup news, programming discussions, and community posts."""
    return await search_hacker_news(query)

@supervisor.tool
async def search_programming_tutorials(ctx: RunContext[int], query: str) -> str:
    """Searches Dev.to for in-depth software engineering articles and coding tutorials."""
    return await search_dev_articles(query)

@supervisor.tool
async def fetch_official_news(ctx: RunContext[int], topic: str = None, language: str = "en", country: str = None) -> str:
    """
    The PRIMARY, official tool for fetching breaking global and local news. 
    CRITICAL INSTRUCTIONS:
    - This is the absolute number one choice for Arabic news. If the user asks for news in Arabic or local events, you MUST set language='ar'. 
    - If the context implies local Egyptian news, set country='EG'.
    - topic: The search keyword (e.g., 'technology', 'economy'). Leave None for general top news.
    - language: Defaults to 'en'. Use 'ar' for Arabic.
    - country: 2-letter ISO code (e.g., 'EG', 'US', 'SA').
    """
    return await get_currents_news(topic, language, country)
    

@supervisor.tool
async def calculate_currency_exchange(ctx: RunContext[int], amount: float, from_currency: str, to_currency: str) -> str:
    """
    Converts fiat money and cryptocurrencies.
    CRITICAL: You MUST convert the user's spoken currency into standard 3-letter codes before calling this.
    Example: 'Egyptian pounds' -> 'EGP', 'American dollars' -> 'USD', 'Bitcoin' -> 'BTC'.
    """
    return await convert_currency(amount, from_currency, to_currency)

@supervisor.tool
async def check_crypto_trading_pair(ctx: RunContext[int], symbol: str) -> str:
    """
    Gets the exact, real-time price of a crypto trading pair from Binance.
    CRITICAL: You MUST format the symbol by combining the target and base crypto/fiat.
    Example: If user asks for 'Bitcoin price in USDT', pass 'BTCUSDT'. For 'Ethereum in Euros', pass 'ETHEUR'.
    """
    return await get_live_crypto_price(symbol)


async def background_complex_workflow(chat_id: int, task_description: str, email: str):
    """A multi-model pipeline running non-blocking in the background."""
    logger.info(f"🚀 [Worker] Starting multi-model pipeline for {chat_id}")
    
    # 1. Qwen 3 32B extracts the heavy data (Synthesis Phase)
    raw_report = await researcher_action(task_description)
    
    # 2. Gemma 2 9B formats it beautifully and sends it via Gmail (Reporting Phase)
    success = await format_and_email(raw_data=raw_report, email=email, topic=task_description)
    
    if success:
        await send_telegram_message(chat_id, "✅ Your research was analyzed by Qwen and beautifully formatted by Gemma! Check your inbox.")
    else:
        await send_telegram_message(chat_id, "⚠️ The research completed, but I encountered an error during email dispatch.")



# ... [Scroll down to the message processor] ...

async def process_telegram_message(user_text: str, chat_id: int) -> str:
    cached_reply = await check_cache(user_text)
    if cached_reply:
        return cached_reply

    chat_history = await get_memory(chat_id)
    chat_history.append({"role": "user", "content": user_text})
    
    history_text = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history[-6:]])
    triage_prompt = f"History:\n{history_text}\n\nCurrent User Message: {user_text}"

    try:
        # 🛡️ THE TRIAGE FALLBACK LOOP
        triage_models = [
            'groq:qwen/qwen3-32b',                  # Primary: High accuracy JSON
            'groq:llama-3.3-70b-versatile',         # Fallback 1: High reliability
            'groq:moonshotai/kimi-k2-instruct-0905' # Fallback 2: Kimi
        ]
        
        decision = None
        for model_id in triage_models:
            try:
                # Dynamically inject the model ID to override the Agent's default
                triage = await triage_agent.run(triage_prompt, model=model_id)
                decision = triage.output
                logger.info(f"⚡ Triage successful using {model_id}")
                break # Success! Break out of the fallback loop.
            except Exception as e:
                logger.warning(f"⚠️ Triage failed with {model_id}: {e}. Trying fallback...")
                
        # If all models in the array failed
        if not decision:
            return "System diagnostic: All routing models are currently offline or rate-limited."
            
        final_reply = ""

        # PATH 1: Small Talk (Handled instantly by 8B)
        if decision.category == "small_talk":
            logger.info("⚡ Handled by 8B Triage")
            final_reply = decision.direct_response

        # PATH 2: Complex Task -> Offload to Background Worker
        elif decision.category == "complex_task":
            logger.info("⚙️ Offloading to Background Worker")
            if decision.email_target:
                final_reply = f"I've identified this as a complex request. I am dispatching a background agent to work on it now. The final report will be sent to {decision.email_target}."
                # Dispatch non-blocking background task
                asyncio.create_task(background_complex_workflow(chat_id, user_text, decision.email_target))
            else:
                final_reply = "I need an email address to send the results of this complex task. Please provide one so I can begin."

        # PATH 3: Simple Tool Use -> Send to 70B Supervisor
        elif decision.category == "simple_tool":
            logger.info("🧠 Escalating to 70B Supervisor")
            result = await supervisor.run(triage_prompt, deps=chat_id)
            final_reply = re.sub(r'<function=.*?>.*?</function>', '', result.output, flags=re.DOTALL)

        # D. Save State & Cache
        chat_history.append({"role": "assistant", "content": final_reply})
        await save_memory(chat_id, chat_history[-10:])
        
        # Only cache direct factual/tool answers to avoid caching conversational filler
        if decision.category == "simple_tool":
            await save_to_cache(user_text, final_reply)
        
        return final_reply

    except Exception as e:
        logger.error("Routing Error", exc_info=True)
        return "System diagnostic failed. Re-routing offline."
