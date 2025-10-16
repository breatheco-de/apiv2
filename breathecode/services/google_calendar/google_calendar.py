import os
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

__all__ = ["GoogleCalendar"]


class GoogleCalendar:
    def __init__(self, token: str, refresh_token: Optional[str] = None):
        self._credentials = self._get_credentials(token, refresh_token)
        self._service = None

    def _get_credentials(self, token: Optional[str], refresh_token: Optional[str]) -> Credentials:
        if not token:
            raise Exception("Invalid or expired credentials. Please provide a valid token.")

        creds = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_SECRET"),
        )
        creds.refresh(Request())
        return creds

    def service(self):
        if self._service is None:
            self._service = build("calendar", "v3", credentials=self._credentials)
        return self._service

    def insert_event(self, calendar_id: str, body: dict, send_updates: str = "all"):
        return self.service().events().insert(calendarId=calendar_id, body=body, sendUpdates=send_updates).execute()

    def update_event(self, calendar_id: str, event_id: str, body: dict, send_updates: str = "all"):
        return (
            self.service()
            .events()
            .update(calendarId=calendar_id, eventId=event_id, body=body, sendUpdates=send_updates)
            .execute()
        )

    def get_event(self, calendar_id: str, event_id: str):
        return self.service().events().get(calendarId=calendar_id, eventId=event_id).execute()

    def add_attendees(self, calendar_id: str, event_id: str, emails: list[str]):
        event = self.get_event(calendar_id, event_id)
        attendees = event.get("attendees", []) or []
        existing_emails = {a.get("email") for a in attendees if a.get("email")}

        to_add = [{"email": email} for email in emails if email and email not in existing_emails]

        if not to_add:
            return event

        attendees.extend(to_add)
        event["attendees"] = attendees
        return self.update_event(calendar_id, event_id, event)

    def insert_event_with_conference(self, calendar_id: str, body: dict, send_updates: str = "all"):
        import uuid

        if "conferenceData" not in body:
            body["conferenceData"] = {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }

        return (
            self.service()
            .events()
            .insert(
                calendarId=calendar_id,
                body=body,
                conferenceDataVersion=1,
                sendUpdates=send_updates,
            )
            .execute()
        )

    def add_conference(self, calendar_id: str, event_id: str, send_updates: str = "all"):
        import uuid

        body = {
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
        }

        return (
            self.service()
            .events()
            .patch(
                calendarId=calendar_id,
                eventId=event_id,
                body=body,
                conferenceDataVersion=1,
                sendUpdates=send_updates,
            )
            .execute()
        )
