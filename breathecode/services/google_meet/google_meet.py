from typing import Optional, TypedDict, Unpack

import google.apps.meet_v2.services.conference_records_service.pagers as pagers
from asgiref.sync import async_to_sync
from google.apps import meet_v2
from google.apps.meet_v2.types import Space
from google.protobuf.field_mask_pb2 import FieldMask

__all__ = ["GoogleMeet"]


class CreateSpaceRequest(TypedDict):
    space: Space


class EndActiveConferenceRequest(TypedDict):
    name: str


class GetConferenceRecordRequest(TypedDict):
    name: str


class GetParticipantRequest(TypedDict):
    name: str


class GetParticipantSessionRequest(TypedDict):
    name: str


class GetRecordingRequest(TypedDict):
    name: str


class GetSpaceRequest(TypedDict):
    name: str


class UpdateSpaceRequest(TypedDict):
    space: Space
    update_mask: FieldMask


class GetTranscriptRequest(TypedDict):
    name: str


class ListConferenceRecordsRequest(TypedDict):
    page_size: int
    page_token: str
    filter: str  # in EBNF format, space.meeting_code, space.name, start_time and end_time


class ListRecordingsRequest(TypedDict):
    parent: str
    page_size: int
    page_token: str


class ListParticipantSessionsRequest(TypedDict):
    parent: str
    page_size: int
    page_token: str
    filter: str  # in EBNF format, start_time and end_time


class ListTranscriptsRequest(TypedDict):
    parent: str
    page_size: int
    page_token: str


class ListParticipantsRequest(TypedDict):
    parent: str
    page_size: int
    page_token: str
    filter: str  # in EBNF format, start_time and end_time


class GoogleMeet:
    _spaces_service_client: Optional[meet_v2.SpacesServiceAsyncClient]
    _conference_records_service_client: Optional[meet_v2.ConferenceRecordsServiceAsyncClient]

    def __init__(self):
        from breathecode.setup import resolve_gcloud_credentials

        resolve_gcloud_credentials()

        self._spaces_service_client = None
        self._conference_records_service_client = None

    async def spaces_service_client(self):
        if self._spaces_service_client is None:
            self._spaces_service_client = meet_v2.SpacesServiceAsyncClient()

        return self._spaces_service_client

    async def conference_records_service_client(self):
        if self._conference_records_service_client is None:
            self._conference_records_service_client = meet_v2.ConferenceRecordsServiceAsyncClient()

        return self._conference_records_service_client

    async def acreate_space(self, **kwargs: Unpack[CreateSpaceRequest]) -> meet_v2.Space:

        # Create a client
        client = await self.spaces_service_client()

        # Initialize request argument(s)
        request = meet_v2.CreateSpaceRequest(**kwargs)

        # Make the request
        return await client.create_space(request=request)

    @async_to_sync
    async def create_space(self, **kwargs: Unpack[CreateSpaceRequest]) -> meet_v2.Space:
        return await self.acreate_space(**kwargs)

    async def aget_space(self, **kwargs: Unpack[GetSpaceRequest]) -> meet_v2.Space:

        # Create a client
        client = await self.spaces_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetSpaceRequest(**kwargs)

        # Make the request
        response = await client.get_space(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def get_space(self, **kwargs: Unpack[GetSpaceRequest]) -> meet_v2.Space:
        return await self.aget_space(**kwargs)

    async def aupdate_space(self, **kwargs: Unpack[UpdateSpaceRequest]) -> meet_v2.Space:
        # Create a client
        client = await self.spaces_service_client()

        # Initialize request argument(s)
        request = meet_v2.UpdateSpaceRequest(**kwargs)

        # Make the request
        response = await client.update_space(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def update_space(self, **kwargs: Unpack[UpdateSpaceRequest]) -> meet_v2.Space:
        return await self.aupdate_space(**kwargs)

    async def aend_active_conference(self, **kwargs: Unpack[EndActiveConferenceRequest]) -> None:
        # Create a client
        client = await self.spaces_service_client()

        # Initialize request argument(s)
        request = meet_v2.EndActiveConferenceRequest(**kwargs)

        # Make the request
        return await client.end_active_conference(request=request)

    @async_to_sync
    async def end_active_conference(self, **kwargs: Unpack[EndActiveConferenceRequest]) -> None:
        return await self.aend_active_conference(**kwargs)

    async def alist_participants(self, **kwargs: Unpack[ListParticipantsRequest]) -> pagers.ListParticipantsAsyncPager:
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.ListParticipantsRequest(**kwargs)

        # Make the request
        return await client.list_participants(request=request)

    async def aget_participant(self, **kwargs: Unpack[GetParticipantRequest]) -> meet_v2.Participant:
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetParticipantRequest(**kwargs)

        # Make the request
        return await client.get_participant(request=request)

    @async_to_sync
    async def get_participant(self, **kwargs: Unpack[GetParticipantRequest]) -> meet_v2.Participant:
        return await self.aget_participant(**kwargs)

    async def alist_participant_sessions(
        self, **kwargs: Unpack[ListParticipantSessionsRequest]
    ) -> pagers.ListParticipantSessionsAsyncPager:
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.ListParticipantSessionsRequest(**kwargs)

        # Make the request
        return await client.list_participant_sessions(request=request)

    async def aget_participant_session(
        self, **kwargs: Unpack[GetParticipantSessionRequest]
    ) -> meet_v2.ParticipantSession:
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetParticipantSessionRequest(**kwargs)

        # Make the request
        return await client.get_participant_session(request=request)

    @async_to_sync
    async def get_participant_session(
        self, **kwargs: Unpack[GetParticipantSessionRequest]
    ) -> meet_v2.ParticipantSession:
        return await self.aget_participant_session(**kwargs)

    async def alist_recordings(self, **kwargs: Unpack[ListRecordingsRequest]) -> pagers.ListRecordingsAsyncPager:
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.ListRecordingsRequest(**kwargs)

        # Make the request
        return await client.list_recordings(request=request)

    async def aget_recording(self, **kwargs: Unpack[GetRecordingRequest]) -> meet_v2.Recording:
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetRecordingRequest(**kwargs)

        # Make the request
        response = await client.get_recording(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def get_recording(self, **kwargs: Unpack[GetRecordingRequest]) -> meet_v2.Recording:
        return await self.aget_recording(**kwargs)

    async def alist_transcripts(self, **kwargs: Unpack[ListTranscriptsRequest]) -> pagers.ListTranscriptsAsyncPager:
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.ListTranscriptsRequest(**kwargs)

        # Make the request
        return await client.list_transcripts(request=request)

    async def aget_transcript(self, **kwargs: Unpack[GetTranscriptRequest]) -> meet_v2.Transcript:
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetTranscriptRequest(**kwargs)

        # Make the request
        response = await client.get_transcript(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def get_transcript(self, **kwargs: Unpack[GetTranscriptRequest]) -> meet_v2.Transcript:
        return await self.aget_transcript(**kwargs)

    async def alist_conference_records(
        self, **kwargs: Unpack[ListConferenceRecordsRequest]
    ) -> pagers.ListConferenceRecordsAsyncPager:
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.ListConferenceRecordsRequest(**kwargs)

        # Make the request
        return await client.list_conference_records(request=request)

    async def aget_conference_record(self, **kwargs: Unpack[GetConferenceRecordRequest]) -> meet_v2.ConferenceRecord:
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetConferenceRecordRequest(**kwargs)

        # Make the request
        return await client.get_conference_record(request=request)

    @async_to_sync
    async def get_conference_record(self, **kwargs: Unpack[GetConferenceRecordRequest]) -> meet_v2.ConferenceRecord:
        return await self.aget_conference_record(**kwargs)
