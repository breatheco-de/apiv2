# import os
# import urllib.parse
# from datetime import timedelta

# from asgiref.sync import async_to_sync

# from django.core.cache import cache
from django.core.management.base import BaseCommand

# from breathecode.authenticate.models import AcademyAuthSettings, CredentialsGoogle
from breathecode.mentorship import tasks
from breathecode.mentorship.models import MentorProfile  # , MentorshipSession

# from breathecode.services.google_apps.google_apps import GoogleApps
# from breathecode.services.google_meet.google_meet import GoogleMeet

# from django.db.models import Q
# from django.utils import timezone
# from google.apps import meet_v2
# from google.apps.meet_v2.types import Space, SpaceConfig


class Command(BaseCommand):
    help = "Delete duplicate cohort users imported from old breathecode"

    def handle(self, *args, **options):
        self.check_mentorship_profiles()
        # self.aaaaa()

    def check_mentorship_profiles(self):
        self.stdout.write(self.style.SUCCESS("Checking mentorship profiles"))
        mentor_profiles = MentorProfile.objects.filter(status__in=["ACTIVE", "UNLISTED"]).only("id")

        for mentor_profile in mentor_profiles:
            tasks.check_mentorship_profile.delay(mentor_profile.id)

        self.stdout.write(self.style.SUCCESS(f"Scheduled {len(mentor_profiles)} mentorship profiles"))

    # @async_to_sync
    # async def aaaaa(self):

    #     c = GoogleApps(id_token, refresh1)
    #     print(await c.get_user_info())
    #     # return
    #     client = GoogleMeet(token, refresh2)

    #     # sessions = MentorshipSession.objects.filter(
    #     #     Q(online_meeting_url__startswith="https://meet.google.com/"),
    #     #     service__video_provider="GOOGLE_MEET",
    #     #     meta__isnull=False,
    #     #     mentor__isnull=False,
    #     #     mentor__academy__isnull=False,
    #     #     status__in=["STARTED", "PENDING"],
    #     #     started_at__isnull=False,
    #     #     ends_at__lte=timezone.now(),
    #     # )

    #     sessions = [MentorshipSession(online_meeting_url="https://meet.google.com/ydm-qixs-aya")]

    #     # async for session in sessions:
    #     for session in sessions:
    #         # settings = AcademyAuthSettings.objects.filter(
    #         #     academy_id=session.mentor.academy.id, google_cloud_owner__isnull=False
    #         # ).first()
    #         # if not settings:
    #         #     self.stderr.write(
    #         #         self.style.ERROR(f"Academy {session.mentor.academy.id} has no google cloud owner, skipped")
    #         #     )
    #         #     continue

    #         # credentials = CredentialsGoogle.objects.filter(user=settings.google_cloud_owner).first()
    #         # if not credentials:
    #         #     self.stderr.write(
    #         #         self.style.ERROR(f"Academy {session.mentor.academy.id} has no google cloud credentials, skipped")
    #         #     )
    #         #     continue

    #         # client = GoogleMeet(credentials.token, credentials.refresh_token)

    #         # meeting_code: str = session.meta.get("meeting_code")
    #         # conference_record: str = session.meta.get("conference_record")

    #         # pylance error
    #         if session.online_meeting_url is None:
    #             continue

    #         meeting_code = session.online_meeting_url.split("/")[-1].split("?")[0]

    #         # if not meeting_code or not conference_record:
    #         #     continue

    #         # instances of a meeting, maybe differents meetings within the same space?
    #         time_expended = {}
    #         resources = {
    #             "transcripts": [],
    #             "recordings": [],
    #             "members": [],
    #         }
    #         phone_time = {}
    #         is_conference_ongoing = False
    #         conference_records = await client.alist_conference_records(filter=f'space.meeting_code="{meeting_code}"')
    #         async for record in conference_records:
    #             if not record.end_time:
    #                 is_conference_ongoing = True
    #                 break

    #             participants = await client.alist_participants(parent=record.name)
    #             async for participant in participants:
    #                 if participant.signedin_user.user and participant.signedin_user.user not in time_expended:
    #                     time_expended[participant.signedin_user.user] = {
    #                         "time_expended": timedelta(0),
    #                         "display_name": participant.signedin_user.display_name,
    #                     }

    #                 if participant.phone_user.display_name and participant.phone_user.display_name not in time_expended:
    #                     phone_time[participant.phone_user.display_name] = {
    #                         "time_expended": timedelta(0),
    #                         "display_name": participant.phone_user.display_name,
    #                     }

    #                 time = timedelta(0)

    #                 # each time that the participant join to the meeting
    #                 participant_sessions = await client.alist_participant_sessions(parent=participant.name)
    #                 async for participant_session in participant_sessions:
    #                     time += participant_session.end_time - participant_session.start_time

    #                 if participant.signedin_user.user:
    #                     time_expended[participant.signedin_user.user]["time_expended"] += time

    #                 elif participant.phone_user.display_name:
    #                     phone_time[participant.phone_user.display_name]["time_expended"] += time

    #             recordings = await client.alist_recordings(parent=record.name)

    #             async for recording in recordings:
    #                 resources["recordings"].append(
    #                     {
    #                         "file": recording.drive_destination.file,
    #                         "export_uri": recording.drive_destination.export_uri,
    #                         "start_time": recording.start_time,
    #                         "end_time": recording.end_time,
    #                     }
    #                 )

    #             transcripts = await client.alist_transcripts(parent=record.name)
    #             async for transcript in transcripts:
    #                 resources["transcripts"].append(
    #                     {
    #                         "export_uri": transcript.docs_destination.export_uri,
    #                         "document": transcript.docs_destination.document,
    #                         "start_time": transcript.start_time,
    #                         "end_time": transcript.end_time,
    #                     }
    #                 )

    #         if is_conference_ongoing:
    #             continue

    #         # kick everyone out of the meeting
    #         # try:
    #         #     await client.aend_active_conference(name=record.space)
    #         # except Exception as e:
    #         #     # this always emit an exception

    #         # remove the access to them
    #         # s = Space(
    #         #     name=record.space,
    #         #     config=SpaceConfig(access_type=SpaceConfig.AccessType.RESTRICTED),
    #         # )
    #         # space = client.update_space(space=s)

    #         # mentor = None
    #         # for key, value in time_expended.items():
    #         #     if value["display_name"] == session.mentor.name:
    #         #         mentor = key

    #         #     elif value["display_name"] in [
    #         #         session.mentor.user.first_name + " " + session.mentor.user.last_name,
    #         #         session.mentor.user.last_name + " " + session.mentor.user.first_name,
    #         #         session.mentor.user.first_name,
    #         #         session.mentor.user.last_name,
    #         #     ]:
    #         #         mentor = key

    #         # if not mentor and time_expended:
    #         #     mentor = max(time_expended, key=lambda k: time_expended[k]["time_expended"])

    #         # if mentor:
    #         #     mentor = time_expended[mentor]
    #         #     del time_expended[mentor]

    #         # mentee = max(time_expended, key=lambda k: time_expended[k]["time_expended"]) if time_expended else None
    #         # if mentee:
    #         #     mentee = time_expended[mentee]
    #         #     del time_expended[mentee]

    #         # session.mentor_joined_at
    #         # session.mentor_left_at = session.mentor_joined_at + mentor["time_expended"]
    #         # session.mentee_left_at = session.started_at + mentee["time_expended"]
    #         prev_meta = session.meta or {}
    #         session.meta = {**prev_meta, **resources}
    #         print("session.meta")
    #         print(session.meta)
    #         print("time_expended")
    #         print(time_expended)
    #         print("phone_time")
    #         print(phone_time)

    #         # await session.asave()
