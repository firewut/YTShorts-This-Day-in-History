import io
import logging
import tempfile
import typing as t
import uuid
from abc import ABC, abstractmethod

import openai
import requests
from openai.types.audio.transcription import Transcription

logging.basicConfig(level=logging.INFO)


# Define an interface for AI services
class IAIService(ABC):
    @abstractmethod
    def get_default_completion_model(self) -> str:
        """Get the default completion model for the AI service."""
        ...

    @abstractmethod
    def get_default_tts_model(self) -> str:
        """Get the default TTS model for the AI service."""
        ...

    @abstractmethod
    def get_default_transcription_model(self) -> str:
        """Get the default transcription model."""
        ...

    @abstractmethod
    def get_default_image_model(self) -> str:
        """Get the default image model for the AI service."""
        ...

    @abstractmethod
    def get_completion(
        self, messages: list[dict[str, t.Any]], model: str | None
    ) -> t.Any:
        """Get completion from the AI service."""
        ...

    @abstractmethod
    def get_tts(self, text: str, voice: str) -> io.BytesIO | None:
        """Get TTS from the AI service."""
        ...

    @abstractmethod
    def get_transcription(self, tts_buffer: io.BytesIO) -> Transcription:
        """Get TTS transcription from the AI service using the TTS file path."""
        ...

    @abstractmethod
    def get_image(self, text: str, settings: t.Any) -> io.BytesIO:
        """Get image from the AI service."""
        ...


# Implement the interface with OpenAI
class OpenAIService(IAIService):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.client = openai.OpenAI(api_key=api_key)

    def get_default_completion_model(self) -> str:
        """Get the default completion model."""
        return "gpt-4o"

    def get_default_tts_model(self) -> str:
        """Get the default TTS model."""
        return "tts-1"

    def get_default_transcription_model(self) -> str:
        """Get the default transcription model."""
        return "whisper-1"

    def get_default_image_model(self) -> str:
        """Get the default image model."""
        return "dall-e-3"

    def get_completion(
        self, messages: list[dict[str, t.Any]], model: str | None = None
    ) -> openai.types.chat.ChatCompletion:
        """Get completion from OpenAI."""

        if not model:
            model = self.get_default_completion_model()

        return self.client.chat.completions.create(
            model=model, messages=messages, timeout=60  # type: ignore
        )

    def get_tts(self, text: str, voice: str) -> io.BytesIO | None:
        """Get TTS from OpenAI."""

        tts_buffer = io.BytesIO()
        with self.client.audio.speech.with_streaming_response.create(
            model=self.get_default_tts_model(),
            voice=voice,  # type: ignore
            input=text,
            response_format="mp3",
            timeout=60,
        ) as response:
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile() as temp_file:
                    response.stream_to_file(temp_file.name)
                    temp_file.seek(0)
                    tts_buffer = io.BytesIO(temp_file.read())
                    tts_buffer.name = f"{temp_file}.mp3"
                return tts_buffer

        return None

    def get_transcription(self, tts_buffer: io.BytesIO) -> Transcription:
        """Get TTS transcription from OpenAI service using the TTS file path."""
        tts_buffer.seek(0)
        if not tts_buffer.name:
            tts_buffer.name = f"{uuid.uuid4()}.mp3"

        return self.client.audio.transcriptions.create(
            file=tts_buffer,
            model=self.get_default_transcription_model(),
            language="en",
            response_format="verbose_json",
            timeout=60,
        )

    def get_image(self, text: str, settings: t.Any) -> io.BytesIO:
        """Get image from OpenAI."""
        response = self.client.images.generate(
            model=self.get_default_image_model(),
            prompt=text,
            size=f"{settings.dalle_image_width}x{settings.dalle_image_height}",  # type: ignore
            quality="hd",
            n=1,
            timeout=60,
        )
        image_buffer = io.BytesIO()

        try:
            for j, image in enumerate(response.data):
                if not image.url:
                    raise ValueError("Image URL not found in the response.")

                content = requests.get(image.url).content
                image_buffer = io.BytesIO(content)
                image_buffer.name = f"image_{j}.png"
        except Exception as e:
            logging.error(e)

        return image_buffer


# AIService now depends on the abstraction rather than a concrete implementation
class AIService:
    def __init__(self, ai_service: IAIService) -> None:
        self.ai_service = ai_service

    def get_completion(
        self, messages: list[dict[str, t.Any]], model: str | None = None
    ) -> t.Any:
        return self.ai_service.get_completion(messages=messages, model=model)

    def get_tts(self, text: str, voice: str) -> io.BytesIO | None:
        return self.ai_service.get_tts(text, voice)

    def get_transcription(self, tts_buffer: io.BytesIO) -> Transcription:
        return self.ai_service.get_transcription(tts_buffer)

    def get_image(self, text: str, settings: t.Any) -> io.BytesIO:
        return self.ai_service.get_image(text, settings)
