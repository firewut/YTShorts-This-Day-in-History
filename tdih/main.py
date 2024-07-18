import logging
import os
import threading

from moviepy.editor import CompositeVideoClip, concatenate_videoclips

from tdih.ai_services import AIServiceInterface, OpenAIService
from tdih.config import load_settings
from tdih.models import Event
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
    events = Event.load_all(settings.results_path, date_str=date)

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

    # Prepare Events
    events: list[Event] = []

    # These are the events that have already been generated. This is to avoid duplicates
    previous_events = []

    for i in range(settings.num_events):
        event_path = settings.results_path / str(i)
        os.makedirs(event_path, exist_ok=True)

        events.append(
            Event(
                date=settings.today,
                event_path=event_path,
            )
        )

    # Get responses for each event
    for event in events:
        event.request_text(ai_service, settings, previous_events)
        previous_events.append(event.text)

    # Get TTS and TTS Transcription for each event
    for event in events:
        event.request_tts(ai_service, settings)
        event.request_tts_transcription(ai_service, settings)
        event.dump()

    # Get images for each event
    for event in events:
        event.request_images(ai_service, settings)

    for event in events:
        event.video_file_path = (
            event.event_path / f"video_{settings.today_str}.mp4"
        ).relative_to(settings.root_path)

        if event.transcription:
            event.duration = event.transcription.duration

        event.dump()
