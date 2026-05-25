from pydantic_ai import Agent
from tools.gmail import send_gmail_report
from infrastructure.logger import logger

# Google's Gemma 2 9B is exceptionally good at prose and markdown formatting
reporter = Agent(
    'groq:llama-3.3-70b-versatile',
    system_prompt=(
        "You are an elite technical writer and executive assistant. "
        "Your ONLY job is to take raw, messy data provided by backend research models "
        "and transform it into a beautifully formatted, brief, and highly readable email.\n"
        "RULES:\n"
        "- Don't Use Markdown (headings, bullet points, bold text) just Raw Text.\n"
        "- Completely remove any raw JSON, XML, or system logs.\n"
        "- Add a polite, professional greeting and sign-off.\n"
        "- Keep the email concise, visually appealing, and to the point."
    )
)

async def format_and_email(raw_data: str, email: str, topic: str) -> bool:
    prompt = f"Topic Requested: {topic}\n\n--- RAW DATA ---\n{raw_data}\n\nPlease draft the final email."
    
    # 🛡️ THE REPORTER FALLBACK LOOP (Protects against model decommissioning)
    fallback_models = [
        'groq:llama-3.3-70b-versatile',            # Primary: Excellent prose and structure
        'groq:moonshotai/kimi-k2-instruct-0905',   # Fallback 1: Kimi
        'groq:mixtral-8x7b-32768'                  # Fallback 2: Mixtral
    ]
    
    for model_id in fallback_models:
        try:
            logger.info(f"📝 [Reporter] Attempting formatting with: {model_id}...")
            # Dynamically override the agent's model
            result = await reporter.run(prompt, model=model_id)
            formatted_email = result.output
            
            await send_gmail_report(
                to_email=email, 
                subject=f"Agentic Report: {topic}", 
                content=formatted_email
            )
            return True
        except Exception as e:
            logger.warning(f"⚠️ Model {model_id} encountered an error: {e}. Switching to fallback...")
            
    logger.error("❌ Critical Failure: All reporter fallback models failed.")
    return False
