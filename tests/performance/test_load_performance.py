"""Performance and load tests"""
import pytest
import asyncio
import time
from typing import List
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_webhook_requests(test_client: AsyncClient):
    """Test handling concurrent webhook requests"""
    num_concurrent = 10

    with patch("agents.supervisor.process_telegram_message", new_callable=AsyncMock) as mock_process, \
         patch("tools.telegram.send_telegram_message", new_callable=AsyncMock):
        
        mock_process.return_value = "Response"

        async def make_request(index: int):
            return await test_client.post(
                "/webhook",
                json={"update_id": index, "message": {"message_id": index, "chat": {"id": 100 + index}, "text": f"Message {index}"}},
                headers={"x-telegram-bot-api-secret-token": "test_secret_token"}
            )

        start = time.time()
        responses = await asyncio.gather(*[make_request(i) for i in range(num_concurrent)])
        duration = time.time() - start

        assert all(r.status_code == 200 for r in responses)
        assert duration < 30


@pytest.mark.asyncio
@pytest.mark.performance
async def test_response_time_distribution(test_client: AsyncClient):
    """Test response time under load"""
    num_requests = 20
    response_times: List[float] = []

    with patch("agents.supervisor.process_telegram_message", new_callable=AsyncMock) as mock_process, \
         patch("tools.telegram.send_telegram_message", new_callable=AsyncMock):
        
        mock_process.return_value = "Response"

        for i in range(num_requests):
            start = time.time()
            response = await test_client.post(
                "/webhook",
                json={"update_id": i, "message": {"chat": {"id": 200 + i}, "text": f"Message {i}"}},
                headers={"x-telegram-bot-api-secret-token": "test_secret_token"}
            )
            duration = time.time() - start
            response_times.append(duration)
            assert response.status_code == 200

        avg_time = sum(response_times) / len(response_times)
        assert avg_time < 5.0
