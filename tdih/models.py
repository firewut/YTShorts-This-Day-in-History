import datetime
import json
import logging
import pathlib
import random
import typing as t
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests
from moviepy.editor import TextClip
from openai.types.audio.transcription import Transcription

from tdih.ai_services import AIServiceInterface
from tdih.config import Settings
from tdih.templates import PROMPT_TEMPLATE

logging.basicConfig(level=logging.INFO)


@dataclass
class Slide:
    duration: float
    text: str
    text_color: str = "white"
    video_clip: TextClip | None = None
    background_color: str = "black"
    background_image: str | None = None


@dataclass
class Event:
    date: datetime.date
    event_path: pathlib.Path
    text: str | None = None
    duration: float = 0
    text_file_path: pathlib.Path | None = None
    transcription: Transcription | None = None
    speech_file_path: pathlib.Path | None = None
    video_file_path: pathlib.Path | None = None
    images: list[pathlib.Path] | None = None
    id: uuid.UUID = uuid.uuid4()

    def as_dict(self) -> dict[str, t.Any]:
        return {
            "date": str(self.date),
            "event_path": str(self.event_path),
            "duration": self.duration,
            "text": self.text,
            "text_file_path": str(self.text_file_path),
            "transcription": self.transcription.model_dump_json(),
            "speech_file_path": str(self.speech_file_path),
            "video_file_path": str(self.video_file_path),
            "images": [str(image) for image in self.images] if self.images else [],
            "id": str(self.id),
        }

    @classmethod
    def load_all(cls, event_path: pathlib.Path, date_str: str) -> t.Self:
        events = []

        for event_file in event_path.glob(f"*/event_{date_str}.json"):
            with open(event_file, "r") as f:
                event_dict = json.load(f)
                event_dict["date"] = datetime.datetime.strptime(
                    event_dict["date"], "%Y-%m-%d"
                ).date()
                event_dict["id"] = uuid.UUID(event_dict["id"])
                event_dict["transcription"] = Transcription.model_validate_json(
                    event_dict["transcription"]
                )
                events.append(cls(**event_dict))

        return events

    def dump(self) -> None:
        with open(self.event_path / f"event_{str(self.date)}.json", "w") as f:
            f.write(
                json.dumps(
                    self.as_dict(),
                    indent=4,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            )

    def generate_slides(self) -> list[t.Self]:
        slides = []

        if not self.transcription:
            raise ValueError("Text is not generated")

        for idx, segment in enumerate(self.transcription.segments):
            slide = Slide(
                duration=segment["end"] - segment["start"],
                text=segment["text"],
                background_image=self.images[idx % len(self.images)],
            )
            slides.append(slide)

        return slides

    def request_text(
        self,
        ai: AIServiceInterface,
        settings: Settings,
        previous_events: list[str],
    ) -> bool:
        logging.debug(f"Generating text event for {self.id}")

        text_prompt = [
            {
                "role": "system",
                "content": PROMPT_TEMPLATE.format(
                    today=settings.today,
                    read_length=settings.video_length,
                    previous_events="\n".join(previous_events),
                ),
            },
            {
                "role": "user",
                "content": "What happened today in history?",
            },
        ]

        response = ai.get_completion(text_prompt)
        self.text = response.choices[0].message.content.strip()

        filename = f"text_{settings.today_str}.txt"
        with open(self.event_path / filename, "w") as f:
            f.write(self.text)

        self.text_file_path = (self.event_path / filename).relative_to(
            settings.root_path
        )

        return True

    def request_tts(
        self, ai: AIServiceInterface, settings: Settings, voice: str | None = None
    ) -> bool:
        logging.debug(f"Generating speech event for {self.id}")
        if not self.text:
            logging.info(f"TTS won't be generated for Event {self.id}")
            return False

        filename = f"speech_{settings.today_str}.mp3"
        with open(self.event_path / filename, "wb") as f:
            pass

        self.speech_file_path = (self.event_path / filename).relative_to(
            settings.root_path
        )

        with ai.client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice=voice or settings.tts_voice_strategy.pick_random_voice(),
            input=self.text,
            timeout=60,
        ) as response:
            if response.status_code == 200:
                response.stream_to_file(self.event_path / filename)
                return True

        return False

    def request_tts_transcription(
        self,
        ai: AIServiceInterface,
        settings: Settings,
    ) -> bool:
        logging.debug(f"Generating transcription event for {self.id}")
        if not self.speech_file_path:
            logging.info(f"Transcription won't be generated for Event {self.id}")
            return False

        response = ai.client.audio.transcriptions.create(
            model="whisper-1",
            file=self.speech_file_path,
            language="en",
            response_format="verbose_json",
            timeout=60,
        )
        self.transcription = response

        return True

    def request_images(
        self,
        ai: AIServiceInterface,
        settings: Settings,
    ) -> bool:
        logging.debug(f"Generating image event for {self.id}")

        if not self.text or not self.transcription:
            return False

        images_num = len(self.transcription.segments)
        if images_num > settings.max_num_images_per_video:
            images_num = settings.max_num_images_per_video

        if self.images is None:
            self.images = []

        for i in range(images_num):
            response = ai.client.images.generate(
                model="dall-e-3",
                prompt=self.text,
                size=f"{settings.dalle_image_width}x{settings.dalle_image_height}",
                quality="hd",
                n=1,
                timeout=60,
            )
            try:
                for j, image in enumerate(response.data):
                    content = requests.get(image.url).content

                    filename = f"image_{settings.today_str}_{i}_{j}.png"
                    with open(self.event_path / filename, "wb") as f:
                        f.write(content)

                    self.images.append(
                        (self.event_path / filename).relative_to(settings.root_path)
                    )
            except Exception as e:
                logging.error(e)
                return False

        return True
