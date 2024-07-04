import os
import re
from typing import Any, Optional

from django.contrib.auth.models import User
from django.utils import timezone
from requests.exceptions import Timeout
from task_manager.core.exceptions import AbortTask, RetryTask
from task_manager.django.decorators import task

from breathecode.admissions.models import Academy, Cohort
from breathecode.events.models import Event
from breathecode.monitoring.actions import test_link
from breathecode.monitoring.models import CSVUpload
from breathecode.services.activecampaign import ActiveCampaign
from breathecode.utils import getLogger
from breathecode.utils.decorators import TaskPriority

from .actions import (
    bind_formentry_with_webhook,
    register_new_lead,
    save_get_geolocal,
    update_deal_custom_fields,
)
from .models import (
    AcademyAlias,
    ActiveCampaignAcademy,
    ActiveCampaignWebhook,
    Downloadable,
    FormEntry,
    ShortLink,
    Tag,
)
from .serializers import PostFormEntrySerializer

logger = getLogger(__name__)
is_test_env = os.getenv("ENV") == "test"


@task(priority=TaskPriority.MARKETING.value)
def persist_single_lead(form_data, **_: Any):
    logger.info("Starting persist_single_lead")

    entry = None
    try:
        entry = register_new_lead(form_data)
    except Timeout as e:
        if "id" in form_data:
            entry = FormEntry.objects.filter(id=form_data["id"]).first()
            if entry is not None:
                entry.storage_status_text = str(e)
                entry.storage_status = "PENDING"
                entry.save()
                raise RetryTask(f"Timeout processing lead for form_entry {str(entry.id)}")

    except Exception as e:
        if not form_data:
            return

        if "id" in form_data:
            entry = FormEntry.objects.filter(id=form_data["id"]).first()
            if entry is not None:
                entry.storage_status_text = str(e)
                entry.storage_status = "ERROR"
                entry.save()

        raise e

    if (
        entry is not None
        and entry != False
        and not is_test_env
        and ("city" not in form_data or form_data["city"] is None)
    ):
        save_get_geolocal(entry, form_data)

    return True


@task(priority=TaskPriority.MARKETING.value)
def update_link_viewcount(slug, **_: Any):
    logger.info("Starting update_link_viewcount")

    sl = ShortLink.objects.filter(slug=slug).first()
    if sl is None:
        raise RetryTask(f"ShortLink with slug {slug} not found")

    sl.hits = sl.hits + 1
    sl.lastclick_at = timezone.now()
    sl.save()

    result = test_link(url=sl.destination)
    if result["status_code"] < 200 or result["status_code"] > 299:
        sl.destination_status_text = result["status_text"]
        sl.destination_status = "ERROR"
        sl.save()

        raise Exception(result["status_text"])

    else:
        sl.destination_status = "ACTIVE"
        sl.destination_status_text = result["status_text"]
        sl.save()


@task(priority=TaskPriority.MARKETING.value)
def async_update_deal_custom_fields(formentry_id: str, **_: Any):
    logger.info("Starting to sync deal with contact")
    update_deal_custom_fields(formentry_id)
    logger.debug("async_update_deal_custom_fields: ok")


@task(priority=TaskPriority.REALTIME.value)
def async_activecampaign_webhook(webhook_id, **_: Any):
    logger.info("Starting async_activecampaign_webhook")

    webhook = ActiveCampaignWebhook.objects.filter(id=webhook_id).first()
    ac_academy = webhook.ac_academy

    bind_formentry_with_webhook(webhook)

    if ac_academy is not None:
        try:
            client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
            client.execute_action(webhook_id)
        except Exception as e:
            logger.debug("ActiveCampaign Webhook Exception")
            raise e

    else:
        message = f"ActiveCampaign Academy Profile {webhook_id} doesn't exist"

        webhook.status = "ERROR"
        webhook.status_text = message
        webhook.save()

        logger.debug(message)
        raise Exception(message)

    logger.debug("ActiveCampaign webook status: ok")


@task(priority=TaskPriority.MARKETING.value)
def add_cohort_task_to_student(user_id, cohort_id, academy_id, **_: Any):
    logger.info("Task add_cohort_task_to_student started")

    if not Academy.objects.filter(id=academy_id).exists():
        raise AbortTask(f"Academy {academy_id} not found")

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if ac_academy is None:
        raise AbortTask(f"ActiveCampaign Academy {academy_id} not found")

    user = User.objects.filter(id=user_id).first()
    if user is None:
        raise AbortTask(f"User {user_id} not found")

    cohort = Cohort.objects.filter(id=cohort_id).first()
    if cohort is None:
        raise AbortTask(f"Cohort {cohort_id} not found")

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
    tag = Tag.objects.filter(slug__iexact=cohort.slug, ac_academy__id=ac_academy.id).first()

    if tag is None:
        raise AbortTask(
            f"Cohort tag `{cohort.slug}` does not exist in the system, the tag could not be added to the student. "
            "This tag was supposed to be created by the system when creating a new cohort"
        )

    contact = client.get_contact_by_email(user.email)

    logger.info(f'Adding tag {tag.id} to acp contact {contact["id"]}')
    client.add_tag_to_contact(contact["id"], tag.acp_id)


@task(priority=TaskPriority.MARKETING.value)
def add_event_tags_to_student(event_id: int, user_id: Optional[int] = None, email: Optional[str] = None, **_: Any):
    logger.info("Task add_event_tags_to_student started")

    if not user_id and not email:
        raise AbortTask("Impossible to determine the user email")

    if user_id and email:
        raise AbortTask("You can't provide the user_id and email together")

    if not email:
        email = User.objects.filter(id=user_id).values_list("email", flat=True).first()

    if not email:
        raise AbortTask("We can't get the user email")

    event = Event.objects.filter(id=event_id).first()
    if event is None:
        raise AbortTask(f"Event {event_id} not found")

    if not event.academy:
        raise AbortTask("Impossible to determine the academy")

    academy = event.academy

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy.id).first()
    if ac_academy is None:
        raise AbortTask(f"ActiveCampaign Academy {academy.id} not found")

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
    tag_slugs = [x for x in event.tags.split(",") if x]  # prevent a tag with the slug ''
    if event.slug:
        tag_slugs.append(f"event-{event.slug}" if not event.slug.startswith("event-") else event.slug)

    tags = Tag.objects.filter(slug__in=tag_slugs, ac_academy__id=ac_academy.id)
    if not tags:
        raise AbortTask("Tags not found")

    contact = client.get_contact_by_email(email)
    for tag in tags:
        logger.info(f'Adding tag {tag.id} to acp contact {contact["id"]}')
        client.add_tag_to_contact(contact["id"], tag.acp_id)


@task(priority=TaskPriority.MARKETING.value)
def add_cohort_slug_as_acp_tag(cohort_id: int, academy_id: int, **_: Any) -> None:
    logger.info("Task add_cohort_slug_as_acp_tag started")

    if not Academy.objects.filter(id=academy_id).exists():
        raise AbortTask(f"Academy {academy_id} not found")

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if ac_academy is None:
        raise AbortTask(f"ActiveCampaign Academy {academy_id} not found")

    cohort = Cohort.objects.filter(id=cohort_id).first()
    if cohort is None:
        raise AbortTask(f"Cohort {cohort_id} not found")

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)
    tag = Tag.objects.filter(slug=cohort.slug, ac_academy__id=ac_academy.id).first()
    if tag:
        raise AbortTask(f"Tag for cohort `{cohort.slug}` already exists")

    data = client.create_tag(cohort.slug, description=f"Cohort {cohort.slug} at {ac_academy.academy.slug}")

    tag = Tag(slug=data["tag"], acp_id=data["id"], tag_type="COHORT", ac_academy=ac_academy, subscribers=0)
    tag.save()


@task(priority=TaskPriority.MARKETING.value)
def add_event_slug_as_acp_tag(event_id: int, academy_id: int, force=False, **_: Any) -> None:
    logger.info("Task add_event_slug_as_acp_tag started")

    if not Academy.objects.filter(id=academy_id).exists():
        raise AbortTask(f"Academy {academy_id} not found")

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if ac_academy is None:
        raise AbortTask(f"ActiveCampaign Academy {academy_id} not found")

    event = Event.objects.filter(id=event_id).first()
    if event is None:
        raise AbortTask(f"Event {event_id} not found")

    if not event.slug:
        raise AbortTask(f"Event {event_id} does not have slug")

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)

    if event.slug.startswith("event-"):
        new_tag_slug = event.slug
    else:
        new_tag_slug = f"event-{event.slug}"

    if (tag := Tag.objects.filter(slug=new_tag_slug, ac_academy__id=ac_academy.id).first()) and not force:
        raise AbortTask(f"Tag for event `{event.slug}` already exists")

    data = client.create_tag(new_tag_slug, description=f"Event {event.slug} at {ac_academy.academy.slug}")

    # retry create the tag in Active Campaign
    if tag:
        tag.slug = data["tag"]
        tag.acp_id = data["id"]
        tag.tag_type = "EVENT"
        tag.ac_academy = ac_academy

    else:
        tag = Tag(slug=data["tag"], acp_id=data["id"], tag_type="EVENT", ac_academy=ac_academy, subscribers=0)

    tag.save()


@task(priority=TaskPriority.MARKETING.value)
def add_downloadable_slug_as_acp_tag(downloadable_id: int, academy_id: int, **_: Any) -> None:
    logger.info("Task add_downloadable_slug_as_acp_tag started")

    if not Academy.objects.filter(id=academy_id).exists():
        raise AbortTask(f"Academy {academy_id} not found")

    ac_academy = ActiveCampaignAcademy.objects.filter(academy__id=academy_id).first()
    if ac_academy is None:
        raise AbortTask(f"ActiveCampaign Academy {academy_id} not found")

    downloadable = Downloadable.objects.filter(id=downloadable_id).first()
    if downloadable is None:
        raise AbortTask(f"Downloadable {downloadable_id} not found")

    client = ActiveCampaign(ac_academy.ac_key, ac_academy.ac_url)

    if downloadable.slug.startswith("down-"):
        new_tag_slug = downloadable.slug
    else:
        new_tag_slug = f"down-{downloadable.slug}"

    tag = Tag.objects.filter(slug=new_tag_slug, ac_academy__id=ac_academy.id).first()

    if tag:
        raise AbortTask(f"Tag for downloadable `{downloadable.slug}` already exists")

    try:
        data = client.create_tag(
            new_tag_slug, description=f"Downloadable {downloadable.slug} at {ac_academy.academy.slug}"
        )

        tag = Tag(slug=data["tag"], acp_id=data["id"], tag_type="DOWNLOADABLE", ac_academy=ac_academy, subscribers=0)
        tag.save()

    except Exception as e:
        logger.error(f"There was an error creating tag for downloadable {downloadable.slug}")
        raise e


@task(priority=TaskPriority.MARKETING.value)
def create_form_entry(csv_upload_id, **item):
    # remove the task manager parameters
    item.pop("pop", None)
    item.pop("total_pages", None)
    item.pop("attempts", None)
    item.pop("task_manager_id", None)

    logger.info("Create form entry started")

    csv_upload = CSVUpload.objects.filter(id=csv_upload_id).first()

    if not csv_upload:
        raise RetryTask("No CSVUpload found with this id")

    form_entry = FormEntry()

    error_message = ""

    if "first_name" in item:
        form_entry.first_name = item["first_name"]
    if "last_name" in item:
        form_entry.last_name = item["last_name"]
    if "email" in item:
        form_entry.email = item["email"]
    if "location" in item:
        if AcademyAlias.objects.filter(active_campaign_slug=item["location"]).exists():
            form_entry.location = item["location"]
        elif Academy.objects.filter(active_campaign_slug=item["location"]).exists():
            form_entry.location = item["location"]
        else:
            message = f'No academy exists with this academy active_campaign_slug: {item["academy"]}'
            error_message += f"{message}, "
            logger.error(message)
    if "academy" in item:
        if alias := AcademyAlias.objects.filter(slug=item["academy"]).first():
            form_entry.academy = alias.academy
        elif academy := Academy.objects.filter(slug=item["academy"]).first():
            form_entry.academy = academy
        else:
            message = f'No academy exists with this academy slug: {item["academy"]}'
            error_message += f"{message}, "
            logger.error(message)

    if not form_entry.first_name:
        message = "No first name in form entry"
        error_message += f"{message}, "
        logger.error(message)

    if form_entry.first_name and not re.findall(r"^[A-Za-zÀ-ÖØ-öø-ÿ ]+$", form_entry.first_name):
        message = "first name has incorrect characters"
        error_message += f"{message}, "
        logger.error(message)

    if not form_entry.last_name:
        message = "No last name in form entry"
        error_message += f"{message}, "
        logger.error(message)

    if form_entry.last_name and not re.findall(r"^[A-Za-zÀ-ÖØ-öø-ÿ ]+$", form_entry.last_name):
        message = "last name has incorrect characters"
        error_message += f"{message}, "
        logger.error(message)

    if not form_entry.email:
        message = "No email in form entry"
        error_message += f"{message}, "
        logger.error(message)

    email_pattern = r'(?:[a-z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&\'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])'

    if form_entry.email and not re.findall(email_pattern, form_entry.email, re.IGNORECASE):
        message = "email has incorrect format"
        error_message += f"{message}, "
        logger.error(message)

    if not form_entry.location or not form_entry.academy:
        message = "No location or academy in form entry"
        error_message += f"{message}, "
        logger.error(message)

    if error_message.endswith(", "):
        error_message = error_message[0:-2]
        error_message = f"{error_message}. "

    if error_message:
        csv_upload.log = csv_upload.log or ""
        csv_upload.log += error_message
        logger.error("Missing field in received item")
        logger.error(item)
        csv_upload.status = "ERROR"

    elif csv_upload.status != "ERROR":
        csv_upload.status = "DONE"

    csv_upload.id = csv_upload_id

    csv_upload.save()

    if not error_message:
        form_entry.save()
        serializer = PostFormEntrySerializer(form_entry, data={})
        if serializer.is_valid():
            persist_single_lead.delay(serializer.data)
        logger.info("create_form_entry successfully created")

    else:
        raise Exception(error_message)
