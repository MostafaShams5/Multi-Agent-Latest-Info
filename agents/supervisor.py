import json
import re
import asyncio
from pydantic_ai import Agent, RunContext
from tools.search import perform_web_search
from tools.weather import fetch_weather
from tools.telegram import send_telegram_message
from tools.gmail import send_gmail_report
from tools.knowledge_base import query_internal_documents
from agents.researcher import researcher_agent
from agents.tasks import send_periodic_weather_report
from infrastructure.redis_queue import scheduler
from infrastructure.qdrant_store import get_memory, save_memory
from infrastructure.logger import logger

# --- UPGRADED SUPERVISOR ---
supervisor = Agent(
    'groq:llama-3.3-70b-versatile',
    system_prompt=(
        "You are an elite, highly intelligent AI assistant. "
        "If a user wants to schedule a report, you MUST gather the locations, the email, and the time interval. "
        "CRITICAL: If the user provides an email in a follow-up message, you MUST look at the CONVERSATION HISTORY to find the city and time they requested earlier. "
        "NEVER guess or invent cities (like 'New York') if the user explicitly asked for a different city."
    )
)

@supervisor.tool
async def schedule_automated_report(ctx: RunContext[int], locations: list[str], email: str, interval_minutes: int = 60) -> str:
    """Schedules a recurring weather/status report for the user."""
    chat_id = ctx.deps
    job_id = f"weather_report_{chat_id}"

    scheduler.add_job(
        send_periodic_weather_report, 'interval', minutes=interval_minutes, 
        args=[chat_id, locations, email], id=job_id, replace_existing=True 
    )
    asyncio.create_task(send_periodic_weather_report(chat_id, locations, email))
    return f"Scheduled for {', '.join(locations)} every {interval_minutes} minutes."

@supervisor.tool
async def dispatch_deep_research(ctx: RunContext[int], topic: str, email: str) -> str:
    """Triggers the background Worker Agent to research a topic and email the results."""
    chat_id = ctx.deps
    async def background_workflow():
        report = await researcher_agent(topic)
        await send_gmail_report(to_email=email, subject=f"Research: {topic}", content=report)
        await send_telegram_message(chat_id, f"✅ Research on '{topic}' is in your inbox!")
    
    asyncio.create_task(background_workflow())
    return f"Worker Agent deployed for '{topic}'."

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


# --- THE MESSAGE ROUTER ---
async def process_telegram_message(user_text: str, chat_id: int) -> str:
    # 1. Fetch memory for context (Cache has been removed from this layer!)
    chat_history = await get_memory(chat_id)
    chat_history.append({"role": "user", "content": user_text})
    
    # 2. Clean Context Formatting
    history_text = ""
    for msg in chat_history[-6:-1]: 
        role_name = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role_name}: {msg['content']}\n"

    # 3. Bulletproof Memory Injection Prompt
    context_prompt = (
        f"--- CONVERSATION HISTORY ---\n{history_text}\n"
        f"--- CURRENT USER MESSAGE ---\nUser: {user_text}\n\n"
        f"INSTRUCTION: If the current message is just an email address, extract the requested city and time interval from the CONVERSATION HISTORY to execute the tool."
    )

    try:
        # Run the agent
        result = await supervisor.run(context_prompt, deps=chat_id)
        final_reply = result.output 
        
        # --- THE SAFETY NET: Catch Groq's XML Hallucinations ---
        if "<function" in final_reply:
            logger.warning(f"Intercepted Groq XML Hallucination: {final_reply}")
            
            if "search_live_web" in final_reply:
                query_match = re.search(r'"query":\s*"([^"]+)"', final_reply)
                if query_match:
                    query = query_match.group(1)
                    logger.info(f"Safety Net Executing Search for: {query}")
                    final_reply = await perform_web_search(query)
                else:
                    final_reply = "Let me look that up for you..."
            elif "hello" in user_text.lower() or "hi" in user_text.lower():
                final_reply = "Hello! How can I help you today?"
            else:
                final_reply = "I am processing that request right now."

        # 4. Save state
        chat_history.append({"role": "assistant", "content": final_reply})
        await save_memory(chat_id, chat_history[-10:])
        
        return final_reply

    except Exception as e:
        logger.error("Routing Error", exc_info=True)
        return "System diagnostic failed. Re-routing offline."
