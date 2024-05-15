from typing import Optional

from asgiref.sync import async_to_sync
from google.apps import meet_v2


class GoogleMeet:
    _spaces_service_client: Optional[meet_v2.SpacesServiceAsyncClient]
    _conference_records_service_client: Optional[meet_v2.ConferenceRecordsServiceAsyncClient]

    def __init__(self):
        self._spaces_service_client = None
        self._conference_records_service_client = None
        pass

    async def spaces_service_client(self):
        if self._spaces_service_client is None:
            self._spaces_service_client = meet_v2.SpacesServiceAsyncClient()

        return self._spaces_service_client

    async def conference_records_service_client(self):
        if self._conference_records_service_client is None:
            self._conference_records_service_client = meet_v2.ConferenceRecordsServiceAsyncClient()

        return self._conference_records_service_client

    async def acreate_meeting(self, **kwargs):

        # Create a client
        client = await self.spaces_service_client()

        # Initialize request argument(s)
        request = meet_v2.CreateSpaceRequest()

        # Make the request
        response = await client.create_space(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def create_meeting(self):
        return await self.acreate_meeting()

    async def aget_meeting(self):

        # Create a client
        client = await self.spaces_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetSpaceRequest()

        # Make the request
        response = await client.get_space(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def get_meeting(self):
        return await self.aget_meeting()

    async def aupdate_space(self):
        # Create a client
        client = await self.spaces_service_client()

        # Initialize request argument(s)
        request = meet_v2.UpdateSpaceRequest()

        # Make the request
        response = await client.update_space(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def update_space(self):
        return await self.aupdate_space()

    async def aend_meeting(self, name: str):
        # Create a client
        client = await self.spaces_service_client()

        # Initialize request argument(s)
        request = meet_v2.EndActiveConferenceRequest(name=name)

        # Make the request
        await client.end_active_conference(request=request)

    @async_to_sync
    async def end_meeting(self, name: str):
        return await self.aend_meeting(name)

    async def alist_participants(self, parent: str):
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.ListParticipantsRequest(parent=parent)

        # Make the request
        page_result = client.list_participants(request=request)

        # Handle the response
        async for response in page_result:
            print(response)

    @async_to_sync
    async def list_participants(self, parent: str):
        return await self.alist_participants(parent)

    async def aget_participant(self, name: str):
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetParticipantRequest(name=name)

        # Make the request
        response = await client.get_participant(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def get_participant(self, name: str):
        return await self.aget_participant(name)

    async def alist_participant_sessions(self, parent: str):
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.ListParticipantSessionsRequest(parent=parent)

        # Make the request
        page_result = client.list_participant_sessions(request=request)

        # Handle the response
        async for response in page_result:
            print(response)

    @async_to_sync
    async def list_participant_sessions(self, parent: str):
        return await self.alist_participant_sessions(parent)

    async def aget_participant_session(self, name: str):
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetParticipantSessionRequest(name=name)

        # Make the request
        response = await client.get_participant_session(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def get_participant_session(self, name: str):
        return await self.aget_participant_session(name)

    async def alist_recordings(self, parent: str):
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.ListRecordingsRequest(parent=parent)

        # Make the request
        page_result = client.list_recordings(request=request)

        # Handle the response
        async for response in page_result:
            print(response)

    @async_to_sync
    async def list_recordings(self, parent: str):
        return await self.alist_recordings(parent)

    async def aget_recording(self, name: str):
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetRecordingRequest(name=name)

        # Make the request
        response = await client.get_recording(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def get_recording(self, name: str):
        return await self.aget_recording(name)

    async def alist_transcripts(self, parent: str):
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.ListTranscriptsRequest(parent=parent)

        # Make the request
        page_result = client.list_transcripts(request=request)

        # Handle the response
        async for response in page_result:
            print(response)

    @async_to_sync
    async def list_transcripts(self, parent: str):
        return await self.alist_transcripts(parent)

    async def aget_transcript(self, name: str):
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetTranscriptRequest(name=name)

        # Make the request
        response = await client.get_transcript(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def get_transcript(self, name: str):
        return await self.aget_transcript(name)

    async def alist_conference_records(self):
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.ListConferenceRecordsRequest()

        # Make the request
        page_result = client.list_conference_records(request=request)

        # Handle the response
        async for response in page_result:
            print(response)

    @async_to_sync
    async def list_conference_records(self):
        return await self.alist_conference_records()

    async def aget_conference_record(self, name: str):
        # Create a client
        client = await self.conference_records_service_client()

        # Initialize request argument(s)
        request = meet_v2.GetConferenceRecordRequest(name=name)

        # Make the request
        response = await client.get_conference_record(request=request)

        # Handle the response
        print(response)

    @async_to_sync
    async def get_conference_record(self, name: str):
        return await self.aget_conference_record(name)
