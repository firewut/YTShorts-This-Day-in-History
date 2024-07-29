import datetime
import pathlib
import uuid
from abc import ABC

from tdih.ai_services import AIService, IAIService, OpenAIService
from tdih.config import Settings, load_settings


def test_ai_services_interfaces():
    assert issubclass(IAIService, ABC)
    assert issubclass(OpenAIService, IAIService)


def test_ai_service_openai_init():
    api_key = str(uuid.uuid4())
    ai_service = AIService(OpenAIService(api_key=api_key))
    assert isinstance(ai_service.ai_service, OpenAIService)

    assert ai_service.ai_service.api_key == api_key
