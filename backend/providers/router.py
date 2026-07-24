import json

from dataclasses import dataclass


@dataclass
class RoutingCriteria:
    task_type: str
    max_cost_per_call: float | None = None
    require_vision: bool = False
    require_long_context: bool = False
    latency_budget_ms: int | None = None
    prefer_fine_tuned: bool = False


class ModelRouter:

    def __init__(self, redis_client):
        self.redis = redis_client

    async def get_models(self):
        data = await self.redis.get("router:models")

        if not data:
            return []

        return json.loads(data)

    async def route(self, criteria: RoutingCriteria):

        models = await self.get_models()

        # Vision models
        if criteria.require_vision:
            models = [
                m for m in models
                if m.get("vision", False)
            ]

        # Long context models (>100k)
        if criteria.require_long_context:
            models = [
                m for m in models
                if m.get("context_window", 0) > 100000
            ]

        # Evaluation should never use fine-tuned models
        if criteria.task_type == "evaluation":
            models = [
                m for m in models
                if not m.get("fine_tuned", False)
            ]

        # Prefer fine-tuned model for the requested task
        elif criteria.prefer_fine_tuned:
            fine_tuned = [
                m for m in models
                if m.get("fine_tuned", False)
                and m.get("task_type") == criteria.task_type
            ]

            if fine_tuned:
                models = fine_tuned

        # Cost filter
        if criteria.max_cost_per_call is not None:
            models = [
                m for m in models
                if m.get("estimated_cost", 0)
                <= criteria.max_cost_per_call
            ]

        # Latency filter
        if criteria.latency_budget_ms is not None:
            models = [
                m for m in models
                if m.get("latency_ms", 0)
                <= criteria.latency_budget_ms
            ]

        if not models:
            raise ValueError("No suitable model found.")

        # Default: choose the cheapest
        models.sort(key=lambda m: m.get("estimated_cost", float("inf")))

        return models[0]