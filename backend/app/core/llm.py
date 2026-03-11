import anthropic
from typing import AsyncIterator
from enum import Enum


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class LLMService:
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.ANTHROPIC,
        anthropic_api_key: str = None,
        openai_api_key: str = None,
        model: str = None,
    ):
        self.provider = provider

        if provider == LLMProvider.ANTHROPIC:
            self.client = anthropic.Anthropic(api_key=anthropic_api_key)
            self.async_client = anthropic.AsyncAnthropic(api_key=anthropic_api_key)
            self.model = model or "claude-opus-4-5-20251101"

        elif provider == LLMProvider.OPENAI:
            self.client = openai.OpenAI(api_key=openai_api_key)
            self.async_client = openai.AsyncOpenAI(api_key=openai_api_key)
            self.model = model or "gpt-4o"

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """Generate a response (non-streaming)."""
        if self.provider == LLMProvider.ANTHROPIC:
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text

        elif self.provider == LLMProvider.OPENAI:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content

    async def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """Generate a streaming response."""
        if self.provider == LLMProvider.ANTHROPIC:
            async with self.async_client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        elif self.provider == LLMProvider.OPENAI:
            stream = await self.async_client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                stream=True,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            async for chunk in stream:
                token = chunk.choices[0].delta.content
                if token is not None:
                    yield token

    def generate_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
    ) -> str:
        """Generate a response synchronously."""
        if self.provider == LLMProvider.ANTHROPIC:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text

        elif self.provider == LLMProvider.OPENAI:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content
