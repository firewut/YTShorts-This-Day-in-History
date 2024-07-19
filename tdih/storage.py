import datetime
import io
import json
import os
import pathlib
import typing as t
import uuid
from abc import ABC, abstractmethod

from openai.types.audio.transcription import Transcription
from pydantic import BaseModel


class IEventsFileStorage(ABC):
    @abstractmethod
    def __init__(self, events_path: pathlib.Path) -> None: ...

    @abstractmethod
    def load_events(self, date_str: str) -> list[t.Any]:
        """Load events from the directory."""
        ...

    @abstractmethod
    def dump_event(self, event: t.Any) -> None:
        """Dump the event to a file."""
        ...

    def get_event_path(self, date_str: str, event_id: uuid.UUID) -> pathlib.Path:
        """Retrieve the path to the event's directory."""
        ...

    def save_event_text(self, event_id: uuid.UUID, text: str) -> pathlib.Path:
        """Save the event's text and return the path to the text file."""
        ...

    def get_event_text_path(self, date_str: str, event_id: uuid.UUID) -> pathlib.Path:
        """Retrieve the path to the event's text file."""
        ...

    def save_event_tts(
        self, date_str: str, event_id: uuid.UUID, tts: io.BytesIO | None
    ) -> pathlib.Path:
        """Save the event's TTS and return the path to the TTS file."""
        ...

    def get_event_tts_path(self, date_str: str, event_id: uuid.UUID) -> pathlib.Path:
        """Retrieve the path to the event's TTS file."""
        ...

    def save_event_transcription(
        self, date_str: str, event_id: uuid.UUID, transcription: Transcription
    ) -> pathlib.Path:
        """Save the event's transcription and return the path to the transcription file."""
        ...

    def get_event_transcription_path(
        self, date_str: str, event_id: uuid.UUID
    ) -> pathlib.Path:
        """Retrieve the path to the event's transcription file."""
        ...

    def save_event_images(
        self, date_str: str, event_id: uuid.UUID, images: list[io.BytesIO]
    ) -> list[pathlib.Path]:
        """Save the event's images and return the paths to the image files."""
        ...

    def get_event_images_path(
        self, date_str: str, event_id: uuid.UUID, image_id: int
    ) -> pathlib.Path:
        """Retrieve the path to the event's images directory."""
        ...


class LocalEventsFileStorage(IEventsFileStorage):
    root_path: pathlib.Path  # Path to the root directory of the project
    events_path: pathlib.Path  # Path to the directory where events are stored

    def __init__(self, events_path: pathlib.Path) -> None:
        self.events_path = events_path
        self.root_path = pathlib.Path(__file__).parent.parent

    def dump_event(self, event: BaseModel) -> None:
        event_path = self.get_event_path(date_str=str(event.date), event_id=event.id)
        with open(event_path / f"event.json", "w") as f:
            f.write(event.model_dump_json(indent=4))

    def load_events(self, date_str: str) -> list[t.Any]:
        events = []

        for event_file in self.events_path.glob(f"*/event_{date_str}.json"):
            with open(event_file, "r") as f:
                event_dict = json.load(f)
                event_dict["date"] = datetime.datetime.strptime(
                    event_dict["date"], "%Y-%m-%d"
                ).date()
                event_dict["id"] = uuid.UUID(event_dict["id"])
                event_dict["transcription"] = Transcription.model_validate_json(
                    event_dict["transcription"]
                )
                events.append(t.Any(**event_dict))

        return events

    def get_event_path(self, date_str: str, event_id: uuid.UUID) -> pathlib.Path:
        """Retrieve the path to the event's directory."""
        return (self.events_path / date_str / str(event_id)).relative_to(self.root_path)

    def save_event_text(
        self, date_str: str, event_id: uuid.UUID, text: str
    ) -> pathlib.Path:
        """Save the event's text and return the path to the text file."""
        filename = self.get_event_text_path(date_str, event_id)
        os.makedirs(pathlib.Path(filename).parent, exist_ok=True)

        with open(filename, "w") as f:
            f.write(text)

        return filename

    def get_event_text_path(self, date_str: str, event_id: uuid.UUID) -> pathlib.Path:
        """Retrieve the path to the event's text file."""
        return self.get_event_path(date_str, event_id) / f"text.txt"

    def save_event_tts(
        self, date_str: str, event_id: uuid.UUID, tts: io.BytesIO | None
    ) -> pathlib.Path:
        """Save the event's TTS and return the path to the TTS file."""
        if not tts:
            raise ValueError("TTS is empty")

        filename = self.get_event_tts_path(date_str, event_id)
        os.makedirs(pathlib.Path(filename).parent, exist_ok=True)

        tts.seek(0)
        with open(filename, "wb") as f:
            f.write(tts.read())

        return filename

    def get_event_tts_path(self, date_str: str, event_id: uuid.UUID) -> pathlib.Path:
        """Retrieve the path to the event's TTS file."""
        return self.get_event_path(date_str, event_id) / f"tts.mp3"

    def save_event_transcription(
        self, date_str: str, event_id: uuid.UUID, transcription: Transcription
    ) -> pathlib.Path:
        """Save the event's transcription and return the path to the transcription file."""
        filename = self.get_event_transcription_path(date_str, event_id)
        os.makedirs(pathlib.Path(filename).parent, exist_ok=True)

        with open(filename, "w") as f:
            f.write(transcription.model_dump_json())

        return filename

    def get_event_transcription_path(
        self, date_str: str, event_id: uuid.UUID
    ) -> pathlib.Path:
        """Retrieve the path to the event's transcription file."""
        return self.get_event_path(date_str, event_id) / f"transcription.json"

    def save_event_images(
        self, date_str: str, event_id: uuid.UUID, images: list[io.BytesIO]
    ) -> list[pathlib.Path]:
        """Save the event's images and return the paths to the image files."""
        images_paths = []

        for image_buffer in images:
            filename = self.get_event_images_path(date_str, event_id, image_buffer.name)
            os.makedirs(pathlib.Path(filename).parent, exist_ok=True)

            image_buffer.seek(0)
            with open(filename, "wb") as f:
                f.write(image_buffer.read())

            images_paths.append(filename)

        return images_paths

    def get_event_images_path(
        self, date_str: str, event_id: uuid.UUID, image_name: str
    ) -> pathlib.Path:
        """Retrieve the path to the event's images directory."""
        return self.get_event_path(date_str, event_id) / f"images/{image_name}"


"""(self.event_path / filename).relative_to(
            settings.root_path
        )
"""
