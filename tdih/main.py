import argparse
import logging
import threading
import uuid

from moviepy.editor import CompositeVideoClip, concatenate_videoclips  # type: ignore

from tdih.ai_services import AIService, OpenAIService
from tdih.config import load_settings
from tdih.models import Event
from tdih.services import (
    DescriptionService,
    IDescriptionService,
    IImageRequestService,
    ImageRequestService,
    ITagsRequestService,
    ITextRequestService,
    ITitleRequestService,
    ITranscriptionRequestService,
    ITTSRequestService,
    TagsRequestService,
    TextRequestService,
    TitleRequestService,
    TranscriptionRequestService,
    TTSRequestService,
)
from tdih.slide_generator import SlideGenerator
from tdih.storage import IEventsFileStorage, LocalEventsFileStorage
from tdih.templates import YOUTUBE_VIDEO_DESCRIPTION_SUFFIX, YOUTUBE_VIDEO_TITLE_PREFIX
from tdih.video import create_video
from tdih.youtube_uploader import (
    YouTubeAuthenticator,
    YouTubeUploadService,
    YouTubeVideo,
    YouTubeVideoUploader,
)

logging.basicConfig(level=logging.INFO)


settings = load_settings()


def execute() -> None:
    logging.info(f"Generating content for {settings.today_str}")

    generate_events()
    generate_videos()
    upload_videos_to_youtube()

    logging.info(f"Content generated for {settings.today_str}")


def generate_videos() -> None:
    parser = argparse.ArgumentParser(description="Generate video shorts from events")
    parser.add_argument(
        "date",
        type=str,
        help="date to generate video shorts for",
        default=settings.today_str,
        nargs="?",
    )

    args = parser.parse_args()
    date = args.date
    if not date:
        date = settings.today_str

    local_file_storage: IEventsFileStorage = LocalEventsFileStorage(
        events_path=settings.events_path
    )
    slide_generator = SlideGenerator()

    events = local_file_storage.load_events(date)
    for event in events:
        slides = slide_generator.generate_slides(event)

        clips: CompositeVideoClip = []
        for slide in slides:
            clips.append(create_video(slide))

        # Concatenate text clips into a single video
        final_clip = concatenate_videoclips(clips, method="compose")

        event.video_file_path = local_file_storage.get_event_video_path(date, event.id)

        # Write the final video to a file with optimized settings
        final_clip.write_videofile(
            str(event.video_file_path),
            codec="libx264",
            fps=settings.video_fps,
            threads=threading.active_count(),
            preset="ultrafast",
            audio=str(event.tts_file_path),
        )

        # Close all text clips to release resources
        for clip in clips:
            clip.close()
        final_clip.close()

        local_file_storage.dump_event(event)


def upload_videos_to_youtube() -> None:
    parser = argparse.ArgumentParser(description="Upload video shorts from events")
    parser.add_argument(
        "date",
        type=str,
        help="date to upload video shorts for",
        default=settings.today_str,
        nargs="?",
    )

    args = parser.parse_args()
    date = args.date
    if not date:
        date = settings.today_str

    local_file_storage: IEventsFileStorage = LocalEventsFileStorage(
        events_path=settings.events_path
    )

    authenticator = YouTubeAuthenticator(settings)
    uploader = YouTubeVideoUploader(authenticator)
    upload_service = YouTubeUploadService(uploader, settings)

    events = local_file_storage.load_events(date)
    for event in events:
        if not event.video_file_path or not event.video_file_path.exists():
            continue

        tags = event.tags or []
        tags.extend(settings.default_video_tags)

        title_tags = ""
        if tags:
            tags = [
                tag.lower().replace(" ", "") for tag in tags
            ]  # Convert each tag to lowercase
            title_tags = " #".join(tags)

        video_data = YouTubeVideo(
            video_file_path=event.video_file_path,
            title=f"{YOUTUBE_VIDEO_TITLE_PREFIX} {event.title} {title_tags}",
            description=f"{event.description} {YOUTUBE_VIDEO_DESCRIPTION_SUFFIX}",
            tags=tags,
            category_id=settings.youtube_video_category,
            made_for_kids=settings.youtube_made_for_kids,
        )
        print(">>>", video_data.model_dump())
        # upload_service.upload(video_data)


def generate_events() -> None:
    parser = argparse.ArgumentParser(description="Approve events")
    parser.add_argument(
        "approve",
        type=bool,
        help="Approve events manually",
        default=True,
        nargs="?",
    )

    args = parser.parse_args()
    approve: bool = args.approve

    # Initialise AI
    ai_service: AIService = AIService(OpenAIService(api_key=settings.api_key))
    local_file_storage: IEventsFileStorage = LocalEventsFileStorage(
        events_path=settings.events_path
    )
    text_service: ITextRequestService = TextRequestService()
    title_service: ITitleRequestService = TitleRequestService()
    description_service: IDescriptionService = DescriptionService()
    tags_service: ITagsRequestService = TagsRequestService()
    tts_service: ITTSRequestService = TTSRequestService()
    transcription_service: ITranscriptionRequestService = TranscriptionRequestService()
    image_generation_service: IImageRequestService = ImageRequestService()

    # These are the events that have already been generated. This is to avoid duplicates
    today_texts: list[str] = []

    for i in range(settings.num_events):
        # Text Content
        text = text_service.get_completion(ai_service, settings, today_texts)
        today_texts.append(text)
        # Approve this event ?
        if approve:
            print(f"Text: {text}")
            is_approved = input(f"Approve? (y/n) [{i+1}/{settings.num_events}]: ")
            if is_approved.lower() != "y":
                continue

        event = Event(
            id=uuid.uuid4(),
            date=settings.today,
        )
        event.text_file_path = local_file_storage.save_event_text(
            settings.today_str, event.id, text
        )
        event.text = text

        # Get Title
        event.title = title_service.get_title(ai_service, text)

        # Get Description
        event.description = description_service.get_description(
            ai_service, text, exclude_words=event.title.split(" ")
        )

        # Get Tags
        event.tags = tags_service.get_tags(ai_service, text, exclude_tags=[])

        # Get TTS
        tts_buffer = tts_service.get_tts(
            ai_service, event.text, settings.tts_voice_strategy.pick_random_voice()
        )
        event.tts_file_path = local_file_storage.save_event_tts(
            settings.today_str, event.id, tts_buffer
        )

        # Get TTS Transcription
        transcription = transcription_service.get_transcription(ai_service, tts_buffer)
        event.transcription = transcription
        event.tts_duration = transcription.duration  # type: ignore
        event.transcription_file_path = local_file_storage.save_event_transcription(
            settings.today_str, event.id, transcription
        )

        # Get Images
        images_buffers = image_generation_service.multiple_from_transcription(
            ai_service, settings, text, transcription
        )
        images_paths = local_file_storage.save_event_images(
            settings.today_str, event.id, images_buffers
        )
        event.images_paths = images_paths

        local_file_storage.dump_event(event)


def generate_event_from_text() -> None:
    parser = argparse.ArgumentParser(description="Generate event from given text")
    parser.add_argument("text", type=str, help="Text to be used for event generation")

    args = parser.parse_args()
    text = args.text

    # Initialise AI
    ai_service: AIService = AIService(OpenAIService(api_key=settings.api_key))
    local_file_storage: IEventsFileStorage = LocalEventsFileStorage(
        events_path=settings.events_path
    )
    tts_service: ITTSRequestService = TTSRequestService()
    transcription_service: ITranscriptionRequestService = TranscriptionRequestService()
    image_generation_service: IImageRequestService = ImageRequestService()

    event = Event(id=uuid.uuid4(), date=settings.today)
    event.text = text

    if not event.text:
        raise ValueError("Text is empty")

    # Get TTS
    tts_buffer = tts_service.get_tts(
        ai_service, event.text, settings.tts_voice_strategy.pick_random_voice()
    )
    event.tts_file_path = local_file_storage.save_event_tts(
        settings.today_str, event.id, tts_buffer
    )

    # Get TTS Transcription
    transcription = transcription_service.get_transcription(ai_service, tts_buffer)
    event.transcription = transcription
    event.tts_duration = transcription.duration  # type: ignore
    event.transcription_file_path = local_file_storage.save_event_transcription(
        settings.today_str, event.id, transcription
    )

    # Get Images
    images_buffers = image_generation_service.multiple_from_transcription(
        ai_service, settings, text, transcription
    )
    images_paths = local_file_storage.save_event_images(
        settings.today_str, event.id, images_buffers
    )
    event.images_paths = images_paths

    local_file_storage.dump_event(event)
