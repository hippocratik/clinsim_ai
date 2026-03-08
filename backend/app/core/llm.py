import anthropic
from typing import AsyncIterator

class LLMService:
    def __init__(self, api_key: str, model: str = "claude-opus-4-5-20251101"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.async_client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response (non-streaming)."""
        response = await self.async_client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024
    ) -> AsyncIterator[str]:
        """Generate a streaming response."""
        async with self.async_client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def generate_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response synchronously."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        return response.content[0].text
