from opentelemetry import trace

from .router import ModelRouter
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider


class NeuroFlowClient:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, redis_client, openai_api_key, anthropic_api_key):

        if hasattr(self, "_initialized"):
            return

        self.redis = redis_client

        self.providers = {
            "openai": OpenAIProvider(openai_api_key),
            "anthropic": AnthropicProvider(anthropic_api_key),
        }

        self.router = ModelRouter(redis_client)

        self.tracer = trace.get_tracer(__name__)

        self._initialized = True

    async def chat(self, messages, routing_criteria):

        model_config = await self.router.route(routing_criteria)

        provider = self.providers[model_config["provider"]]

        with self.tracer.start_as_current_span("provider_call") as span:

            result = await provider.complete(
                messages,
                model=model_config["model"]
            )

            span.set_attribute("model", result.model)
            span.set_attribute("input_tokens", result.input_tokens)
            span.set_attribute("output_tokens", result.output_tokens)
            span.set_attribute("cost_usd", result.cost_usd)
            span.set_attribute("latency_ms", result.latency_ms)

        await self.redis.incr(
            f"metrics:model:{result.model}:calls"
        )

        await self.redis.incrbyfloat(
            f"metrics:model:{result.model}:cost_usd",
            result.cost_usd,
        )

        return result

    async def embed(self, texts):

        provider = self.providers["openai"]

        return await provider.embed(texts)