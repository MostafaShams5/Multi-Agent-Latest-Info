"""
Advanced Chaos, Concurrency, and Payload Testing Suite
Run with: pytest tests/test_advanced_scenarios.py -v
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

# ==========================================
# 1. END-TO-END TELEGRAM PAYLOAD FUZZING
# ==========================================

@pytest.mark.asyncio
async def test_telegram_weird_payloads(test_client: AsyncClient):
    """
    Real users send photos, stickers, and voice notes. 
    This tests that our webhook doesn't crash (500 error) when the 'text' key is missing.
    """
    payloads = [
        # Payload 1: A photo message (no text)
        {"update_id": 1, "message": {"chat": {"id": 123}, "photo": [{"file_id": "xyz"}]}},
        # Payload 2: An edited message (uses 'edited_message' instead of 'message')
        {"update_id": 2, "edited_message": {"chat": {"id": 123}, "text": "typo fix"}},
        # Payload 3: A channel post
        {"update_id": 3, "channel_post": {"chat": {"id": -100123}, "text": "hello"}},
        # Payload 4: Empty text
        {"update_id": 4, "message": {"chat": {"id": 123}, "text": ""}}
    ]

    for payload in payloads:
        response = await test_client.post(
            "/webhook", 
            json=payload,
            headers={"x-telegram-bot-api-secret-token": "test_secret_token"}
        )
        # We expect 200 OK (we gracefully ignore unhandled types), NOT a 500 Server Error
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ==========================================
# 2. CONCURRENCY & STRICT RATE LIMITING
# ==========================================

@pytest.mark.asyncio
async def test_strict_rate_limiter(test_client: AsyncClient, mock_redis_client):
    """
    Tests the Exact Boundary of your Redis Rate Limiter.
    Allowed: 5. Warning: 6th. Ignored: 7th+.
    """
    chat_id = 999
    
    # We must patch send_telegram_message so we don't actually hit the real Telegram API during tests
    with patch("main.send_telegram_message", new_callable=AsyncMock) as mock_send, \
         patch("main.process_telegram_message", new_callable=AsyncMock) as mock_process:
        
        mock_process.return_value = "Hello"
        
        # We manually simulate Redis incrementing the counter for this test
        side_effects = [1, 2, 3, 4, 5, 6, 7]
        mock_redis_client.incr = AsyncMock(side_effect=side_effects)
        # Inject our mock redis into the app
        with patch("main.redis_client", mock_redis_client):

            results = []
            # Fire 7 webhooks sequentially to test the limits
            for i in range(7):
                res = await test_client.post(
                    "/webhook",
                    json={"update_id": i, "message": {"chat": {"id": chat_id}, "text": f"Msg {i}"}},
                    headers={"x-telegram-bot-api-secret-token": "test_secret_token"}
                )
                results.append(res.json()["status"])

            # Assertions
            assert results.count("ok") == 5            # First 5 should pass normally
            assert results.count("rate_limited") == 2  # 6th and 7th should be blocked
            
            # Check if the warning message was triggered EXACTLY once (on the 6th message)
            warning_calls = [call for call in mock_send.call_args_list if "too quickly" in call.args[1]]
            assert len(warning_calls) == 1


# ==========================================
# 3. CHAOS & TIMEOUT RESILIENCE
# ==========================================

@pytest.mark.asyncio
async def test_worker_starvation_prevention(test_client: AsyncClient):
    """
    Simulates an external API (like Tavily or Sports API) hanging for 14 seconds.
    Ensures that FastAPI itself doesn't crash or timeout the webhook connection.
    """
    chat_id = 555
    
    # We mock process_telegram_message to simulate a 14-second external API hang
    async def slow_process(*args, **kwargs):
        await asyncio.sleep(14.0) 
        return "Sorry, the search took a long time."

    with patch("main.process_telegram_message", new=slow_process), \
         patch("main.send_telegram_message", new_callable=AsyncMock):
        
        try:
            # We use a 15-second timeout on our test client to ensure the server stays alive
            # and gracefully finishes the 14-second task.
            response = await test_client.post(
                "/webhook",
                json={"update_id": 1, "message": {"chat": {"id": chat_id}, "text": "Search the web"}},
                headers={"x-telegram-bot-api-secret-token": "test_secret_token"},
                timeout=15.0 
            )
            assert response.status_code == 200
        except asyncio.TimeoutError:
            pytest.fail("FastAPI failed to keep the connection alive during a 14-second background hang.")


@pytest.mark.asyncio
async def test_llm_fallback_cascade():
    """
    Simulates Groq API failure on the primary model (Qwen).
    Asserts that the system catches the error and successfully routes to the fallback model.
    """
    from agents.reporter import format_and_email
    
    # We mock the Agent.run method inside reporter.py
    with patch("agents.reporter.reporter.run", new_callable=AsyncMock) as mock_agent_run, \
         patch("agents.reporter.send_gmail_report", new_callable=AsyncMock) as mock_gmail:
        
        # Define the chaos: 
        # Attempt 1 (Primary Model): Raise an Exception (Simulate API down)
        # Attempt 2 (Fallback Model): Succeed
        class MockSuccessResult:
            output = "Formatted Email Text"

        mock_agent_run.side_effect = [
            Exception("Groq API Rate Limit Reached"), 
            MockSuccessResult()
        ]
        
        # Execute the function
        success = await format_and_email("Raw text", "test@test.com", "Topic")
        
        # Assertions
        assert success is True
        assert mock_agent_run.call_count == 2 # It should have tried exactly twice
        
        # Verify it used the primary first, then the fallback
        first_call_model = mock_agent_run.call_args_list[0].kwargs.get("model")
        second_call_model = mock_agent_run.call_args_list[1].kwargs.get("model")
        
        assert first_call_model == 'groq:llama-3.3-70b-versatile'
        assert second_call_model == 'groq:moonshotai/kimi-k2-instruct-0905'
