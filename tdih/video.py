import typing as t
from abc import ABC, abstractmethod

from moviepy.editor import ColorClip, CompositeVideoClip, ImageClip, TextClip

from tdih.config import load_settings
from tdih.models import Slide

settings = load_settings()


# Interface for parameter extraction
class IParamsExtractor(ABC):
    @abstractmethod
    def extract_params(self, slide: Slide) -> dict[str, t.Any]:
        pass


# Concrete implementation for Slide parameter extraction
class SlideParamsExtractor(IParamsExtractor):
    def extract_params(self, slide: Slide) -> dict[str, t.Any]:
        return {
            "text": slide.text,
            "fontsize": 50,
            "text_color": slide.text_color,
            "text_method": "caption",
            "text_bg_color": (0, 0, 0),
            "duration": slide.duration,
            "background_image": slide.background_image,
        }


# Interface for clip creation
class IClipCreator(ABC):
    @abstractmethod
    def create_clip(self, params: dict[str, t.Any]) -> t.Any:
        pass


# Concrete implementation for background clip creation
class BackgroundClipCreator(IClipCreator):
    def create_clip(self, params: dict[str, t.Any]) -> ImageClip:
        return (
            ImageClip(params["background_image"])
            .resize((settings.video_width, settings.video_height))
            .set_duration(params["duration"])
        )


# Concrete implementation for text clip creation
class TextClipCreator(IClipCreator):
    def create_clip(
        self, params: dict[str, t.Any], background_clip: ImageClip
    ) -> TextClip:
        return (
            TextClip(
                txt=params["text"],
                fontsize=params["fontsize"],
                size=(0.8 * background_clip.size[0], 0),
                color=params["text_color"],
                method=params["text_method"],
            )
            .set_position("center")
            .set_duration(params["duration"])
        )


# Concrete implementation for color clip creation
class ColorClipCreator(IClipCreator):
    def create_clip(self, params: dict[str, t.Any], text_clip: TextClip) -> ColorClip:
        return (
            ColorClip(
                size=(settings.video_width, int(text_clip.size[1] * 1.4)),
                color=params.get(
                    "text_bg_color", (0, 0, 0)
                ),  # Default to black if no color is specified
                duration=params["duration"],
            )
            .set_opacity(0.8)
            .set_duration(
                text_clip.duration,
            )
            .set_position(
                "center",
            )
        )


def create_video(slide: Slide) -> CompositeVideoClip:
    params_extractor = SlideParamsExtractor()
    params = params_extractor.extract_params(slide)

    background_creator = BackgroundClipCreator()
    background_clip = background_creator.create_clip(params)

    text_creator = TextClipCreator()
    text_clip = text_creator.create_clip(params, background_clip)

    # Create a color clip as the background
    color_clip_creator = ColorClipCreator()
    color_clip = color_clip_creator.create_clip(params, text_clip)

    final_clip = CompositeVideoClip([background_clip, color_clip, text_clip])

    return final_clip
