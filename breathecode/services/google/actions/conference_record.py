from django.db.models import QuerySet
from task_manager.core.exceptions import AbortTask

from breathecode.authenticate.models import CredentialsGoogle
from breathecode.services.google.utils import get_client


async def conference_record(name: str, credentials: QuerySet[CredentialsGoogle]):
    from breathecode.mentorship.models import MentorshipSession

    errors = ""

    async for credential in credentials:
        try:
            client = get_client(credential)
            conference_record = await client.aget_conference_record(name=name)

            space = await client.aget_space(name=conference_record.space)
            session = await MentorshipSession.objects.filter(online_meeting_url=space.meeting_uri).afirst()
            if session is None:
                raise AbortTask(f"MentorshipSession with meeting url {space.meeting_uri} not found")

            if conference_record.end_time is None:
                session.status = "STARTED"

            elif session.mentor_joined_at is None or session.started_at is None:
                session.status = "FAILED"
                session.ended_at = conference_record.end_time

            else:
                session.status = "COMPLETED"
                session.ended_at = conference_record.end_time

            await session.asave()

            return

        except AbortTask as e:
            raise e

        except Exception as e:
            errors += f"Error with credentials {credential.id}: {e}\n"

    raise AbortTask(errors)
