import time
from anthropic import AsyncAnthropic

from .base import BaseLLMProvider, ChatMessage, GenerationResult


class AnthropicProvider(BaseLLMProvider):

    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-latest"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(self, messages, **kwargs):

        start = time.perf_counter()

        system_prompt = ""

        chat_messages = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = str(msg.content)
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        response = await self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=chat_messages,
            max_tokens=1024,
            **kwargs
        )

        latency = (time.perf_counter() - start) * 1000

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return GenerationResult(
            content=response.content[0].text,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            cost_usd=0.0,
            finish_reason=response.stop_reason,
        )

    async def stream(self, messages, **kwargs):
        response = await self.complete(messages, **kwargs)
        yield response.content

    async def embed(self, texts):
        raise NotImplementedError(
            "Anthropic does not provide embeddings."
        )

    @property
    def cost_per_input_token(self):
        return 0.0

    @property
    def cost_per_output_token(self):
        return 0.0

    @property
    def context_window(self):
        return 200000