import logging
import os
import sys
import io

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


class API:
    creds = None
    service = None

    token_path = "token.json"
    credentials_path = "credentials.json"
    SCOPES = ["https://www.googleapis.com/auth/drive"]

    redirect_url = None
    request_url = None

    files = None
    names = None

    link_base = "https://drive.google.com/file/d/"

    def __init__(self):
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    def init_by_file(self) -> None:
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)

            with open(self.token_path, "w") as token:
                token.write(self.creds.to_json())

        self.service = build("drive", "v3", credentials=self.creds)

    def init_by_link(self) -> tuple:
        flow = InstalledAppFlow.from_client_secrets_file(
            self.credentials_path, self.SCOPES
        )
        flow.redirect_uri = self.redirect_url

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true"
        )

        return (authorization_url, state)

    def through_the_files(self, notSupportsAllDrives = False) -> tuple:
        try:
            if not self.files:
                query = "trashed=false"
                if notSupportsAllDrives:
                    query += " and 'me' in owners"
   
                results = self.service.files().list(
                    q=query,
                    includeItemsFromAllDrives=False,
                    fields="files(name, mimeType, webViewLink, id)"
                ).execute()

                self.files = results.get("files", [])
                self.names = {file["id"]: file["name"] for file in self.files}
                self.current = 0

            if self.current + 10 <= len(self.files):
                res = self.files[self.current : self.current + 10]
                self.current += 10
            else:
                res = self.files[self.current : len(self.files)]
                self.current = len(self.files)

            return (res, self.current, len(self.files))
        
        except HttpError as err:
            print(err)

    def upload(self, name: str, mimetype: str) -> None:
        try:
            file_metadata = {
                "name": name,
                "mimeType": mimetype
            }
            media = MediaFileUpload(
                "download/" + name,
                mimetype=mimetype,
                resumable=True)

            file = (
                self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields="id"
                ).execute()
            )

            logging.info(f"File ID: {file.get('id')} -- File has been uploaded")

        except HttpError as err:
            logging.error(f"An error occured: {err}")
            file = None

        return file.get("id")
    
    def download(self, file_id: str) -> None:
        request = self.service.files().get_media(fileId=file_id)
        file = io.FileIO(f"download/{self.names[file_id]}", "wb")
        downloader = MediaIoBaseDownload(file, request)
        done = False

        while done is False:
            status, done = downloader.next_chunk()
            logging.info(f"Download {int(status.progress() * 100)}%")

    def trash(self, file_id: str) -> None:
        body = {"trashed": True}
        updated_file = self.service.files().update(fileId=file_id, body=body).execute()
        return updated_file

    def delete(self, file_id: str) -> None:
        request = self.service.files().delete(fileId=file_id)
        request.execute()


    def about(self) -> str:
        try:
            results = self.service.about().get(fields="*").execute()["user"]
            res_str = f"Имя: {results['displayName']}\nEmail: {results['emailAddress']}"
            return res_str
        except HttpError as err:
            print(err)
            return "Возникла непридвиденная ошибка."