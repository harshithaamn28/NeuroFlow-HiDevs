from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator


@dataclass
class ChatMessage:
    role: str          # "system", "user", "assistant"
    content: str | list


@dataclass
class GenerationResult:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    finish_reason: str


class BaseLLMProvider(ABC):

    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        **kwargs
    ) -> GenerationResult:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def embed(
        self,
        texts: list[str]
    ) -> list[list[float]]:
        pass

    @property
    @abstractmethod
    def cost_per_input_token(self) -> float:
        pass

    @property
    @abstractmethod
    def cost_per_output_token(self) -> float:
        pass

    @property
    @abstractmethod
    def context_window(self) -> int:
        pass