from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from infrastructure.logger import logger
from infrastructure.redis_queue import scheduler
from infrastructure.qdrant_store import init_qdrant
from agents.supervisor import process_telegram_message
from tools.telegram import send_telegram_message, handle_callback

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Booting AI Infrastructure...")
    
    # Init Databases
    await init_qdrant()
    
    # Start Redis Queue (Automatically restores jobs!)
    scheduler.start()
    logger.info("⚡ Redis Background queues restored.")
    
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    # Route Buttons
    if "callback_query" in data:
        await handle_callback(data["callback_query"])
        return {"status": "ok"}

    # Route Text Messages
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]
        
        # The Supervisor handles everything
        reply_text = await process_telegram_message(user_text, chat_id)
        
        # Return response to user
        await send_telegram_message(chat_id, reply_text, show_buttons=True)

    return {"status": "ok"}
