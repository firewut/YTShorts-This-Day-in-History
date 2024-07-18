import typing as t
from abc import ABC, abstractmethod

import openai


# Define an interface for AI services
class IAIService(ABC):
    @abstractmethod
    def get_completion(self, messages: list[dict[str, t.Any]], model: str) -> t.Any:
        pass


# Implement the interface with OpenAI
class OpenAIService(IAIService):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)

    def get_completion(
        self, messages: list[dict[str, t.Any]], model: str = "gpt-3.5-turbo"
    ) -> openai.ChatCompletion:
        return self.client.chat.completions.create(
            model=model, messages=messages, timeout=60
        )


# AIServiceInterface now depends on the abstraction rather than a concrete implementation
class AIServiceInterface:
    def __init__(self, ai_service: IAIService) -> None:
        self.ai_service = ai_service

    def get_completion(
        self, messages: list[dict[str, t.Any]], model: str = "gpt-3.5-turbo"
    ) -> t.Any:
        return self.ai_service.get_completion(messages=messages, model=model)
