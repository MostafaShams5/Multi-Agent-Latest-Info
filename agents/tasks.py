from tools.weather import fetch_weather
from tools.telegram import send_telegram_message
from tools.gmail import send_gmail_report
from infrastructure.logger import logger

async def send_periodic_weather_report(chat_id: int, locations: list, email: str = None):
    """The background task managed by Redis."""
    logger.info(f"⏰ [Worker] Executing scheduled report for {chat_id}")
    
    reports = [await fetch_weather(loc) for loc in locations]
    combined = "\n".join(reports)
    report_text = f"📊 [Automated Report]\n\n{combined}"
    
    await send_telegram_message(chat_id, report_text, show_buttons=True)
    
    if email:
        await send_gmail_report(to_email=email, subject="Your Automated Update", content=combined)
