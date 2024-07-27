import datetime
import os
import pathlib
import random
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ISettingsLoader(ABC):
    @abstractmethod
    def load(self, key: str, default=None):
        pass


class EnvSettingsLoader(ISettingsLoader):
    def load(self, key: str, default=None):
        return os.environ.get(key, default)


class TTSVoiceStrategy(ABC):
    @abstractmethod
    def get_voices(self) -> t.Sequence[str]:
        pass

    @abstractmethod
    def pick_random_voice(self) -> str:
        pass


class DefaultTTSVoiceStrategy(TTSVoiceStrategy):
    def get_voices(self) -> t.Sequence[str]:
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
    words_count: int = 30
    dalle_image_width: int = 1024
    dalle_image_height: int = 1024
    today: datetime.date = field(init=False)
    max_num_images_per_video: int = 5  # Dall-e limitation per minute

    default_video_tags: t.Sequence[str] = ("history", "ai", "today")

    youtube_channel_title: str = "Today in history"
    youtube_channel_id: str = "UCgiSRFK7zOCi3gP8ofAaH9A"
    youtube_oauth2_client_id: str = field(init=False)
    youtube_oauth2_project_id: str = field(init=False)
    youtube_oauth2_auth_uri: str = field(init=False)
    youtube_oauth2_token_uri: str = field(init=False)
    youtube_oauth2_auth_provider_x509_cert_url: str = field(init=False)
    youtube_oauth2_client_secret: str = field(init=False)
    youtube_oauth2_redirect_uris: list[str] = field(init=False)
    youtube_made_for_kids: bool = False
    youtube_video_category: str = "22"  # People and Blogs

    def __post_init__(self):
        self.api_key = self.settings_loader.load("OPENAI_API_KEY", None)
        if not self.api_key:
            raise ValueError("OpenAI API Key is required")

        self.events_path = pathlib.Path(__file__).parent.parent / "videos"
        os.makedirs(self.events_path, exist_ok=True)

        self.today = datetime.date.today() + datetime.timedelta(days=1)
        self.today_str: str = str(self.today)

        # Youtube secrets
        self.youtube_oauth2_client_id = self.settings_loader.load(
            "YOUTUBE_OAUTH2_CLIENT_ID", None
        )
        self.youtube_oauth2_project_id = self.settings_loader.load(
            "YOUTUBE_OAUTH2_PROJECT_ID", None
        )
        self.youtube_oauth2_auth_uri = self.settings_loader.load(
            "YOUTUBE_OAUTH2_AUTH_URI", None
        )
        self.youtube_oauth2_token_uri = self.settings_loader.load(
            "YOUTUBE_OAUTH2_TOKEN_URI", None
        )
        self.youtube_oauth2_auth_provider_x509_cert_url = self.settings_loader.load(
            "YOUTUBE_OAUTH2_AUTH_PROVIDER_X509_CERT_URL", None
        )
        self.youtube_oauth2_client_secret = self.settings_loader.load(
            "YOUTUBE_OAUTH2_CLIENT_SECRET", None
        )
        self.youtube_oauth2_redirect_uris = self.settings_loader.load(
            "YOUTUBE_OAUTH2_REDIRECT_URIS", ""
        ).split(",")


@lru_cache
def load_settings():
    settings_loader = EnvSettingsLoader()
    tts_voice_strategy = DefaultTTSVoiceStrategy()
    return Settings(
        settings_loader=settings_loader,
        tts_voice_strategy=tts_voice_strategy,
    )
