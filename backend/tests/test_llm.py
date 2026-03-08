import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.core.llm import LLMService

def test_llm_service_init():
    service = LLMService(api_key="test-key", model="claude-opus-4-5-20251101")
    assert service.model == "claude-opus-4-5-20251101"

@pytest.mark.asyncio
async def test_llm_generate_calls_api():
    with patch("app.core.llm.anthropic.AsyncAnthropic") as mock_client:
        mock_response = Mock()
        mock_response.content = [Mock(text='{"test": "response"}')]
        mock_client.return_value.messages.create = AsyncMock(return_value=mock_response)

        service = LLMService(api_key="test-key")
        result = await service.generate(
            system_prompt="You are helpful",
            user_prompt="Hello"
        )

        assert result == '{"test": "response"}'
