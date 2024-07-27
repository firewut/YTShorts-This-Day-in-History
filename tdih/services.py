import io
import pathlib
import typing as t
from abc import ABC, abstractmethod

from openai.types.audio.transcription import Transcription

from tdih.ai_services import AIService
from tdih.config import Settings
from tdih.templates import (
    DESCRIPTION_TEMPLATE,
    PROMPT_TEMPLATE,
    TAGS_TEMPLATE,
    TITLE_TEMPLATE,
)


class ITextRequestService(ABC):
    @abstractmethod
    def get_completion(
        self,
        ai_service: AIService,
        settings: Settings,
        existing_texts: list[str],
    ) -> str:
        """Get completion from the AI service."""
        ...


class TextRequestService(ITextRequestService):
    def get_completion(
        self,
        ai_service: AIService,
        settings: Settings,
        existing_texts: list[str],
    ) -> str:
        """Get completion from the AI service."""

        text_prompt = [
            {
                "role": "system",
                "content": PROMPT_TEMPLATE.format(
                    today=settings.today,
                    words_count=settings.words_count,
                    previous_events="\n".join(existing_texts),
                ),
            },
            {
                "role": "user",
                "content": "What happened today in history?",
            },
        ]

        response = ai_service.get_completion(text_prompt)
        return response.choices[0].message.content.strip()


class ITitleRequestService(ABC):
    @abstractmethod
    def get_title(self, ai_service: AIService, text: str) -> str:
        """Get title from the AI service."""
        ...


class TitleRequestService(ITitleRequestService):
    def get_title(self, ai_service: AIService, text: str) -> str:
        """Get title from the AI service."""
        title_prompt = [
            {
                "role": "system",
                "content": TITLE_TEMPLATE,
            },
            {
                "role": "user",
                "content": text,
            },
        ]

        response = ai_service.get_completion(title_prompt)
        return response.choices[0].message.content.strip()


class ITagsRequestService(ABC):
    @abstractmethod
    def get_tags(
        self, ai_service: AIService, text: str, exclude_tags: list[str]
    ) -> list[str]:
        """Get tags from the AI service."""
        ...


class TagsRequestService(ITagsRequestService):
    def get_tags(
        self, ai_service: AIService, text: str, exclude_tags: list[str]
    ) -> list[str]:
        """Get tags from the AI service."""
        title_prompt = [
            {
                "role": "system",
                "content": TAGS_TEMPLATE.format(
                    exclude_tags=exclude_tags,
                ),
            },
            {
                "role": "user",
                "content": text,
            },
        ]

        response = ai_service.get_completion(title_prompt)
        tags = response.choices[0].message.content
        return [tag.strip() for tag in tags.split(",")]


class IDescriptionService(ABC):
    @abstractmethod
    def get_description(
        self, ai_service: AIService, text: str, exclude_words: list[str]
    ) -> str:
        """Get description from the AI service."""
        ...


class DescriptionService(IDescriptionService):
    def get_description(
        self, ai_service: AIService, text: str, exclude_words: list[str]
    ) -> str:
        """Get description from the AI service."""
        title_prompt = [
            {
                "role": "system",
                "content": DESCRIPTION_TEMPLATE.format(
                    exclude_words=exclude_words,
                ),
            },
            {
                "role": "user",
                "content": text,
            },
        ]

        response = ai_service.get_completion(title_prompt)
        return response.choices[0].message.content.strip()


class ITTSRequestService(ABC):
    @abstractmethod
    def get_tts(
        self, ai_service: AIService, text: str, voice: str
    ) -> io.BytesIO | None:
        """Get TTS from the AI service."""
        ...


class TTSRequestService(ITTSRequestService):
    def get_tts(
        self, ai_service: AIService, text: str, voice: str
    ) -> io.BytesIO | None:
        """Get TTS from the AI service."""
        return ai_service.get_tts(text, voice)


class ITranscriptionRequestService(ABC):
    @abstractmethod
    def get_transcription(
        self,
        ai_service: AIService,
        tts_buffer: io.BytesIO | None,
    ) -> Transcription:
        """Get TTS transcription from the AI service using the TTS input."""
        pass


class TranscriptionRequestService(ITranscriptionRequestService):
    def get_transcription(
        self, ai_service: AIService, tts_buffer: io.BytesIO | None
    ) -> Transcription:
        """Get TTS transcription from the AI service using the TTS bytes."""
        if not tts_buffer:
            raise ValueError("TTS buffer is empty")

        return ai_service.get_transcription(tts_buffer)


class IImageRequestService(ABC):
    @abstractmethod
    def get_image(
        self, ai_service: AIService, settings: Settings, text: str
    ) -> io.BytesIO:
        """Generate an image using the AI service."""
        ...

    @abstractmethod
    def multiple_from_transcription(
        self,
        ai_service: AIService,
        settings: Settings,
        text: str,
        transcription: Transcription,
    ) -> list[io.BytesIO]:
        """Generate images using the AI service and text."""
        ...


class ImageRequestService(IImageRequestService):
    def get_image(
        self, ai_service: AIService, settings: Settings, text: str
    ) -> io.BytesIO:
        return ai_service.get_image(text, settings)

    def multiple_from_transcription(
        self,
        ai_service: AIService,
        settings: Settings,
        text: str,
        transcription: Transcription | None = None,
    ) -> list[io.BytesIO]:
        """Generate images using the AI service and text."""
        if not transcription:
            raise ValueError("Transcription is empty")

        images_num = len(transcription.segments)  # type: ignore
        if images_num > settings.max_num_images_per_video:
            images_num = settings.max_num_images_per_video

        images_buffers: list[io.BytesIO] = []
        for i in range(images_num):
            image_buffer = self.get_image(ai_service, settings, text)
            image_buffer.name = f"{i}_{image_buffer.name}"
            images_buffers.append(image_buffer)

        return images_buffers
