import datetime
import os
import pathlib
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ISettingsLoader(ABC):
    @abstractmethod
    def load(self):
        pass


class EnvSettingsLoader(ISettingsLoader):
    def load(self, key: str, default=None):
        return os.environ.get(key, default)


class TTSVoiceStrategy(ABC):
    @abstractmethod
    def get_voices(self) -> tuple[str]:
        pass

    @abstractmethod
    def pick_random_voice(self) -> str:
        pass


class DefaultTTSVoiceStrategy(TTSVoiceStrategy):
    def get_voices(self) -> tuple[str]:
        return ("alloy", "echo", "fable", "onyx", "nova", "shimmer")

    def pick_random_voice(self) -> str:
        return random.choice(self.get_voices())


@dataclass
class Settings:
    settings_loader: ISettingsLoader
    tts_voice_strategy: TTSVoiceStrategy

    api_key: str = field(init=False)
    today_str: str = field(init=False)
    events_path: pathlib.Path = field(init=False)
    num_events: int = 2
    video_width: int = 1080
    video_height: int = 1920
    video_fps: int = 30
    read_length: int = 30  # Average read length seconds
    dalle_image_width: int = 1024
    dalle_image_height: int = 1024
    today: datetime.date = field(init=False)
    max_num_images_per_video: int = 5  # Dall-e limitation per minute

    def __post_init__(self):
        self.api_key = self.settings_loader.load("OPENAI_API_KEY", None)
        if not self.api_key:
            raise ValueError("OpenAI API Key is required")

        self.events_path = pathlib.Path(__file__).parent.parent / "videos"
        os.makedirs(self.events_path, exist_ok=True)

        self.today = datetime.date.today()
        self.today_str: str = str(self.today)


@lru_cache
def load_settings():
    settings_loader = EnvSettingsLoader()
    tts_voice_strategy = DefaultTTSVoiceStrategy()
    return Settings(
        settings_loader=settings_loader,
        tts_voice_strategy=tts_voice_strategy,
    )
