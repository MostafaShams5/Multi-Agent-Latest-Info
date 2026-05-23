import json
import re
import asyncio
from litellm import acompletion
from tools.search import perform_web_search
from tools.weather import fetch_weather
from tools.telegram import send_telegram_message
from tools.gmail import send_gmail_report
from agents.researcher import researcher_agent
from agents.tasks import send_periodic_weather_report
from infrastructure.redis_queue import scheduler
from infrastructure.qdrant_store import get_memory, save_memory
from infrastructure.logger import logger

async def process_telegram_message(user_text: str, chat_id: int) -> str:
    # 1. Fetch Stateless Memory
    chat_history = await get_memory(chat_id)
    chat_history.append({"role": "user", "content": user_text})
    chat_history = chat_history[-10:] # Keep last 10 messages

    is_report_request = "report" in user_text.strip().lower()

    # 2. Dynamic Tool Schema (No hardcoded times)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "setup_periodic_report",
                "description": "Schedule a recurring automated report.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "locations": {"type": "array", "items": {"type": "string"}},
                        "email": {"type": "string"},
                        "interval_minutes": {"type": "integer", "description": "Minutes between reports. Default 60."}
                    },
                    "required": ["locations", "interval_minutes"] 
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_weather",
                "description": "Get current weather for a specific location.",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "dispatch_custom_research",
                "description": "Trigger a deep research report on a topic and email it.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "email": {"type": "string"}
                    },
                    "required": ["topic", "email"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "perform_web_search",
                "description": "Search the internet for real-world information.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        }
    ]

    # 3. Upgraded Supervisor Prompt
    system_prompt = """
    You are an elite orchestration agent.
    RULES:
    1. Reply conversationally to small talk. Use the chat history for context.
    2. If a user wants a recurring report but provides no time, default to 60 minutes.
    3. If they ask for deep research to be emailed, deploy the dispatch_custom_research tool.
    4. NEVER hallucinate data. Use perform_web_search for real-time facts.
    """

    messages_for_llm = [{"role": "system", "content": system_prompt}] + chat_history

    try:
        tool_choice = {"type": "function", "function": {"name": "setup_periodic_report"}} if is_report_request else "auto"

        response = await acompletion(
            model="groq/llama-3.3-70b-versatile",
            messages=messages_for_llm,
            tools=tools,
            tool_choice=tool_choice,
            temperature=0.1
        )

        message = response.choices[0].message
        final_reply = ""

        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                
                raw_args = tool_call.function.arguments
                try: args = json.loads(raw_args)
                except: 
                    match = re.search(r'\{.*?\}', raw_args, re.DOTALL)
                    args = json.loads(match.group(0)) if match else {}

                # COMMAND: SCHEDULE REPORT
                if tool_call.function.name == "setup_periodic_report":
                    locations = args.get("locations", [])
                    email = args.get("email")
                    interval = args.get("interval_minutes", 60)
                    
                    if not locations: 
                        final_reply = "Please specify the cities for the report."
                    else:
                        job_id = f"weather_report_{chat_id}"
                        
                        # Replace existing prevents duplicates
                        scheduler.add_job(
                            send_periodic_weather_report, 
                            'interval', 
                            minutes=interval, 
                            args=[chat_id, locations, email], 
                            id=job_id,
                            replace_existing=True 
                        )
                        
                        # Fire immediately
                        asyncio.create_task(send_periodic_weather_report(chat_id, locations, email))
                        final_reply = f"✅ Scheduled for {', '.join(locations)} every {interval} minutes."

                # COMMAND: WEATHER
                elif tool_call.function.name == "fetch_weather":
                    loc = args.get("location")
                    final_reply = await fetch_weather(loc) if loc else "I need a city name."

                # COMMAND: RESEARCH DISPATCH (Agent-to-Agent)
                elif tool_call.function.name == "dispatch_custom_research":
                    topic = args.get("topic")
                    email = args.get("email")
                    
                    if not email:
                        final_reply = "I need your email address to send the research report!"
                    else:
                        async def background_research_workflow():
                            report_content = await researcher_agent(topic)
                            await send_gmail_report(to_email=email, subject=f"Research Report: {topic}", content=report_content)
                            await send_telegram_message(chat_id, f"✅ Deep research on '{topic}' complete. Check your inbox!")

                        asyncio.create_task(background_research_workflow())
                        final_reply = f"🕵️‍♂️ Researcher Agent deployed for '{topic}'. I'll notify you when it hits your inbox."

                # COMMAND: SEARCH
                elif tool_call.function.name == "perform_web_search":
                    query = args.get("query", user_text)
                    final_reply = await perform_web_search(query=query)

        else:
            final_reply = message.content or "Processed, but no response generated."

        # 4. Save state securely back to Qdrant
        chat_history.append({"role": "assistant", "content": final_reply})
        await save_memory(chat_id, chat_history)
        
        return final_reply

    except Exception as e:
        logger.error("Routing Error", exc_info=True)
        return "System diagnostic failed. Re-routing offline."
