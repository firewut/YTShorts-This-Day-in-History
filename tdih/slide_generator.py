from typing import List

from tdih.models import Event, Slide


class SlideGenerator:
    @classmethod
    def generate_slides(self, event: Event) -> List[Slide]:
        if not event.transcription:
            raise ValueError("Valid transcription is required")

        slides = []

        for idx, segment in enumerate(event.transcription.segments):
            slide = Slide(
                duration=segment["end"] - segment["start"],
                text=segment["text"],
                background_image=event.images_paths[idx % len(event.images_paths)],
            )
            slides.append(slide)

        return slides
