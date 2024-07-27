import os
import pathlib
import pickle
import typing as t

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from pydantic import BaseModel

from tdih.config import Settings
from tdih.uploader import IAuthenticator, IVideo, IVideoUploader


# YouTubeVideo Class
class YouTubeVideo(IVideo, BaseModel):
    video_file_path: pathlib.Path
    title: str
    description: str
    tags: list[str]
    category_id: str
    made_for_kids: bool

    def __init__(
        self,
        video_file_path: pathlib.Path,
        title: str,
        description: str,
        tags: list[str],
        category_id: str,
        made_for_kids: bool = False,
    ):
        super().__init__(
            video_file_path=video_file_path,
            title=title,
            description=description,
            tags=tags,
            category_id=category_id,
            made_for_kids=made_for_kids,
        )

    def get_video_file_path(self) -> pathlib.Path:
        return self.video_file_path

    def get_snippet(self, settings: Settings) -> dict[str, t.Any]:
        # https://developers.google.com/youtube/v3/docs/videos
        return {
            "snippet": {
                "channelTitle": settings.youtube_channel_title,
                "channelId": settings.youtube_channel_id,
                "title": self.title,
                "description": self.description,
                "tags": self.tags,
                "categoryId": self.category_id,
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": "private",
                "madeForKids": self.made_for_kids,
            },
        }


# YouTubeAuthenticator Class
class YouTubeAuthenticator(IAuthenticator):
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"

    def __init__(self, settings: Settings):
        self.client_config = {
            "installed": {
                "client_id": settings.youtube_oauth2_client_id,
                "project_id": settings.youtube_oauth2_project_id,
                "auth_uri": settings.youtube_oauth2_auth_uri,
                "token_uri": settings.youtube_oauth2_token_uri,
                "auth_provider_x509_cert_url": settings.youtube_oauth2_auth_provider_x509_cert_url,
                "client_secret": settings.youtube_oauth2_client_secret,
                "redirect_uris": settings.youtube_oauth2_redirect_uris,
            }
        }

    def authenticate(self) -> t.Any:
        credentials = None
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                credentials = pickle.load(token)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(
                    self.client_config, self.SCOPES
                )
                credentials = flow.run_local_server(port=0)
            with open("token.pickle", "wb") as token:
                pickle.dump(credentials, token)

        try:
            youtube = build(
                self.API_SERVICE_NAME, self.API_VERSION, credentials=credentials
            )
            print("Successfully authenticated with YouTube API")
            return youtube
        except HttpError as error:
            print(f"An HTTP error {error.resp.status} occurred:\n{error.content}")


# YouTubeVideoUploader Class
class YouTubeVideoUploader(IVideoUploader):
    def __init__(self, authenticator: IAuthenticator):
        self.authenticator = authenticator
        self.youtube = self.authenticator.authenticate()

    def upload_video(self, settings: Settings, video: YouTubeVideo):
        # Upload video logic using YouTube Data API
        media_body = MediaFileUpload(
            filename=video.get_video_file_path(),
            mimetype="video/mp4",
            chunksize=-1,
            resumable=True,
        )
        body = video.get_snippet(settings)
        request = self.youtube.videos().insert(
            part="snippet,status", body=body, media_body=media_body
        )

        response = None
        try:
            print("Uploading video...")
            response = request.execute()
            print(f'Video uploaded. Video ID: {response["id"]}')
        except HttpError as e:
            print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
        return response


# YouTubeUploadService Class
class YouTubeUploadService:
    def __init__(self, uploader: IVideoUploader, settings: Settings):
        self.uploader = uploader
        self.settings = settings

    def upload(self, video: YouTubeVideo):
        self.uploader.upload_video(self.settings, video)
