import logging
import threading
import uuid

from moviepy.editor import CompositeVideoClip, concatenate_videoclips

from tdih.ai_services import AIServiceInterface, OpenAIService
from tdih.config import load_settings
from tdih.models import Event
from tdih.services import (
    IImageRequestService,
    ImageRequestService,
    ITextRequestService,
    ITranscriptionRequestService,
    ITTSRequestService,
    TextRequestService,
    TranscriptionRequestService,
    TTSRequestService,
)
from tdih.storage import IEventsFileStorage, LocalEventsFileStorage
from tdih.video import create_video

logging.basicConfig(level=logging.INFO)


settings = load_settings()


def execute() -> None:
    logging.info(f"Generating content for {settings.today_str}")

    generate_events()
    generate_shorts_from_events()

    logging.info(f"Content generated for {settings.today_str}")


def generate_shorts_from_events(date: str | None = None) -> None:
    if not date:
        date = settings.today_str

    # Load all events for the given date
    events = Event.load_all(settings.events_path, date_str=date)

    for event in events:
        slides = event.generate_slides()

        clips: CompositeVideoClip = []
        for slide in slides:
            clips.append(create_video(slide))

        # Concatenate text clips into a single video
        final_clip = concatenate_videoclips(clips, method="compose")

        # Write the final video to a file with optimized settings
        final_clip.write_videofile(
            event.video_file_path,
            codec="libx264",
            fps=settings.video_fps,
            threads=threading.active_count(),
            preset="ultrafast",
            audio=event.speech_file_path,
        )

        # Close all text clips to release resources
        for clip in clips:
            clip.close()
        final_clip.close()


def generate_events() -> None:
    # Initialise AI
    ai_service: AIServiceInterface = OpenAIService(api_key=settings.api_key)
    local_file_storage: IEventsFileStorage = LocalEventsFileStorage(
        events_path=settings.events_path
    )
    text_service: ITextRequestService = TextRequestService()
    tts_service: ITTSRequestService = TTSRequestService()
    transcription_service: ITranscriptionRequestService = TranscriptionRequestService()
    image_generation_service: IImageRequestService = ImageRequestService()

    # Prepare Events
    events: list[Event] = []

    for _ in range(settings.num_events):
        events.append(Event(id=uuid.uuid4(), date=settings.today))

    # These are the events that have already been generated. This is to avoid duplicates
    today_texts = []

    for event in events:
        # Text Content
        text = text_service.get_completion(ai_service, settings, today_texts)
        event.text_file_path = local_file_storage.save_event_text(
            settings.today_str, event.id, text
        )
        today_texts.append(text)
        event.text = text

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
        event.tts_duration = transcription.duration
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
