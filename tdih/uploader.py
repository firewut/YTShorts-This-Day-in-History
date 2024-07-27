import pathlib
import typing as t
from abc import ABC, abstractmethod

from tdih.config import Settings


# IAuthenticator Interface
class IAuthenticator(ABC):
    @abstractmethod
    def authenticate(self):
        pass


class IVideo(ABC):
    @abstractmethod
    def get_snippet(self) -> dict[str, t.Any]:
        pass

    @abstractmethod
    def get_video_file_path(self) -> pathlib.Path:
        pass


# IVideoUploader Interface
class IVideoUploader(ABC):
    @abstractmethod
    def upload_video(self, settings: Settings, video: IVideo):
        pass
