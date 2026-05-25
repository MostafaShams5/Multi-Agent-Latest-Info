import os
import sentry_sdk
import logfire
from fastapi import FastAPI, Request, Header, HTTPException
from contextlib import asynccontextmanager

from config import TELEGRAM_SECRET_TOKEN, SENTRY_DSN
from infrastructure.logger import logger
from infrastructure.redis_queue import scheduler
from infrastructure.qdrant_store import init_qdrant
from infrastructure.semantic_cache import init_cache
from agents.supervisor import process_telegram_message
from tools.telegram import send_telegram_message, handle_callback
import redis.asyncio as redis
from config import REDIS_HOST, REDIS_PORT

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)
# 1. Initialize Sentry (Catches 500 errors and crashes)
if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=1.0)

# 2. Initialize Logfire (Traces every Pydantic-AI agent step automatically)
logfire.configure(send_to_logfire='if-token-present')

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Booting AI Infrastructure...")
    await init_qdrant()
    await init_cache() 
    scheduler.start()
    logger.info("⚡ Redis Background queues restored.")
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
# Instrument FastAPI to track web requests
logfire.instrument_fastapi(app)

@app.post("/webhook")
async def telegram_webhook(
    request: Request, 
    x_telegram_bot_api_secret_token: str = Header(None) # Security Header
):
    # 3. Security Check: Block unauthorized access to your LLM API
    if TELEGRAM_SECRET_TOKEN and x_telegram_bot_api_secret_token != TELEGRAM_SECRET_TOKEN:
        logger.warning("🚨 Unauthorized webhook access attempt blocked.")
        raise HTTPException(status_code=401, detail="Unauthorized")

    data = await request.json()
    
    # Route Buttons
    if "callback_query" in data:
        await handle_callback(data["callback_query"])
        return {"status": "ok"}

    # Route Text Messages
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]
        
        # 🛡️ THE RATE LIMITER (Limit: 5 requests per minute per user)
        rate_key = f"rate_limit:{chat_id}"
        request_count = await redis_client.incr(rate_key)
        
        # If it's their first message in the window, set the expiration to 60 seconds
        if request_count == 1:
            await redis_client.expire(rate_key, 60)
            
        # If they exceed 5 messages, block them
        if request_count > 5:
            logger.warning(f"🛑 Rate limit exceeded for {chat_id}")
            # Only warn them on the 6th message to avoid spamming them back
            if request_count == 6:
                await send_telegram_message(chat_id, "⚠️ You are sending messages too quickly. Please wait 60 seconds.")
            return {"status": "rate_limited"}
        
        # The Supervisor handles everything
        reply_text = await process_telegram_message(user_text, chat_id)
        await send_telegram_message(chat_id, reply_text, show_buttons=True)

    return {"status": "ok"}
