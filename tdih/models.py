import datetime
import logging
import pathlib
import uuid
from dataclasses import dataclass

from moviepy.editor import TextClip
from openai.types.audio.transcription import Transcription
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)


@dataclass
class Slide:
    duration: float
    text: str
    text_color: str = "white"
    video_clip: TextClip | None = None
    background_color: str = "black"
    background_image: pathlib.Path | None = None


class Event(BaseModel):
    id: uuid.UUID
    date: datetime.date

    # Title
    title: str | None = None

    # Description
    description: str | None = None

    # Tags
    tags: list[str] | None = None

    # Text
    text: str | None = None
    text_file_path: pathlib.Path | None = None

    # TTS
    tts_file_path: pathlib.Path | None = None
    # Transcription

    tts_duration: float = 0  # Correct duration located in Transcription
    transcription: Transcription | None = None
    transcription_file_path: pathlib.Path | None = None

    # Images
    images_paths: list[pathlib.Path] | None = None

    # Video
    video_file_path: pathlib.Path | None = None
