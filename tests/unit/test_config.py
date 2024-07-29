import datetime
import pathlib

from tdih.config import Settings, load_settings


def test_load_settings(mocker):
    mocker.patch("tdih.config.EnvSettingsLoader.load", return_value="api_key")

    settings = load_settings()
    assert issubclass(type(settings), Settings)

    assert settings.api_key == "api_key"
    assert settings.tts_voice_strategy.get_voices() == (
        "alloy",
        "echo",
        "fable",
        "onyx",
        "nova",
        "shimmer",
    )
    assert (
        settings.tts_voice_strategy.pick_random_voice()
        in settings.tts_voice_strategy.get_voices()
    )
    assert settings.num_events == 5
    assert settings.video_width == 1080
    assert settings.video_height == 1920
    assert settings.video_fps == 30
    assert settings.words_count == 30
    assert settings.dalle_image_width == 1024
    assert settings.dalle_image_height == 1024
    assert settings.today_str == str(datetime.date.today())
    assert settings.today == datetime.date.today()
    assert (
        settings.events_path == pathlib.Path(__file__).parent.parent.parent / "videos"
    )
