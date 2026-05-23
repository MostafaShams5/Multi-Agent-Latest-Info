import httpx
from config import TELEGRAM_API_URL
from infrastructure.redis_queue import scheduler
from infrastructure.qdrant_store import qdrant, MEMORY_COLLECTION
from infrastructure.logger import logger

async def send_telegram_message(chat_id: int, text: str, show_buttons: bool = False):
    payload = {"chat_id": chat_id, "text": text}
    
    if show_buttons:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [{"text": "📊 Request Automated Report", "callback_data": "btn_request"}],
                [{"text": "🛑 Unsubscribe & Clear Data", "callback_data": "btn_unsubscribe"}]
            ]
        }

    async with httpx.AsyncClient() as client:
        await client.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

async def handle_callback(callback_query: dict):
    callback_data = callback_query["data"]
    chat_id = callback_query["message"]["chat"]["id"]
    
    if callback_data == "btn_unsubscribe":
        # 1. Kill background jobs
        job_id = f"weather_report_{chat_id}"
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        # 2. Wipe memory from Vector DB
        qdrant.delete(collection_name=MEMORY_COLLECTION, points_selector=[chat_id])
        await send_telegram_message(chat_id, "🛑 You are unsubscribed. All personal memory has been wiped.")
        
    elif callback_data == "btn_request":
        await send_telegram_message(chat_id, "What would you like to monitor? \n*(e.g., 'Report weather in Tokyo every 30 mins')*")

    # Acknowledge the button click to Telegram
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API_URL}/answerCallbackQuery", 
            json={"callback_query_id": callback_query["id"]}
        )
