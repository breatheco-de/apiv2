import os
from io import BytesIO
from typing import Any, Awaitable, Callable, Optional, Type, TypedDict

from adrf.requests import AsyncRequest
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile

from breathecode.media.models import Chunk, File
from breathecode.services.google_cloud.storage import Storage
from capyc.rest_framework.exceptions import ValidationException

type TypeValidator = Callable[[str, Any], None]
type TypeValidatorWrapper = Callable[[Type[Any]], TypeValidator]
type Schema = dict[str, type | TypeValidatorWrapper]


class MediaSettings(TypedDict):
    chunk_size: int
    max_chunks: int
    is_quota_exceeded: Callable[[AsyncRequest, Optional[int]], Awaitable[bool]]
    is_authorized: Callable[[AsyncRequest, Optional[int]], Awaitable[bool]]
    is_mime_supported: Callable[[InMemoryUploadedFile | TemporaryUploadedFile, Optional[int]], Awaitable[bool]]
    get_schema = Optional[Callable[[AsyncRequest, Optional[int]], Awaitable[Schema]]]
    # this callback is sync because it'll be called within celery what doesn't support async operations properly
    process = Optional[Callable[[File, dict[str, Any], Optional[int]], None]]


MEDIA_MIME_ALLOWED = [
    "image/png",
    "image/svg+xml",
    "image/jpeg",
    "image/gif",
    "video/quicktime",
    "video/mp4",
    "audio/mpeg",
    "application/pdf",
    "image/jpg",
    "application/octet-stream",
    "application/x-pka",
]

PROOF_OF_PAYMENT_MIME_ALLOWED = [
    "image/png",
    "image/svg+xml",
    "image/jpeg",
    "image/gif",
    "image/jpg",
]

PROFILE_MIME_ALLOWED = [
    "image/png",
    "image/jpeg",
]


async def allow_any(request: AsyncRequest, academy_id: Optional[int] = None) -> bool:
    return True


async def no_quota_limit(request: AsyncRequest, academy_id: Optional[int] = None) -> bool:
    return False


async def media_is_mime_supported(
    file: InMemoryUploadedFile | TemporaryUploadedFile, academy_id: Optional[int] = None
) -> bool:
    return file.content_type in MEDIA_MIME_ALLOWED


async def proof_of_payment_is_mime_supported(
    file: InMemoryUploadedFile | TemporaryUploadedFile, academy_id: Optional[int] = None
) -> bool:
    return file.content_type in PROOF_OF_PAYMENT_MIME_ALLOWED


async def profile_is_mime_supported(
    file: InMemoryUploadedFile | TemporaryUploadedFile, academy_id: Optional[int] = None
) -> bool:
    return file.content_type in PROFILE_MIME_ALLOWED


async def no_schedule(meta: Any) -> bool:
    return False


async def no_schema(schema: Any) -> None:
    return []


def array(t: Type) -> Any:
    def wrapper(key, l: list[Any]) -> list[Any]:
        for index in range(len(l)):
            item = l[index]

            if not isinstance(item, t):
                raise ValidationException(
                    f"Invalid item type, expected {key}[{index}]{t.__name__}, got {key}[{index}]{type(item).__name__}"
                )

    return wrapper


async def media_schema(request: AsyncRequest, academy_id: Optional[int] = None) -> Schema:
    return {
        "slug": str,
        "name": str,
        "categories": array(str),
        "academy": int,
    }


def transfer(file: File, new_bucket: str, suffix: str = ""):
    storage = Storage()
    uploaded_file = storage.file(file.bucket, file.file_name)
    if uploaded_file.exists() is False:
        raise Exception("File does not exists")

    f = BytesIO()
    uploaded_file.download(f)

    new_file = storage.file(new_bucket, file.hash + suffix)
    new_file.upload(f, content_type=file.mime)
    url = new_file.url()
    return url


def del_temp_file(file: File | Chunk):
    storage = Storage()
    uploaded_file = storage.file(file.bucket, file.file_name)

    if uploaded_file.exists() is False:
        raise Exception("File does not exists")

    uploaded_file.delete()


def process_media(file: File) -> None:
    from .models import Category, Media

    academy_id = file.academy.id if file.academy else None
    meta = file.meta

    if Media.objects.filter(hash=file.hash, academy__id=academy_id).exists():
        del_temp_file(file)
        return

    if url := Media.objects.filter(hash=file.hash).values_list("url", flat=True).first():
        del_temp_file(file)

    if url is None:
        url = transfer(file, os.getenv("MEDIA_GALLERY_BUCKET"))

    media = Media.objects.create(
        hash=file.hash,
        slug=meta["slug"],
        name=meta["name"] or file.name,
        mime=file.mime,
        academy_id=academy_id,
        url=url,
        thumbnail=url + "-thumbnail",
    )

    categories = Category.objects.filter(slug__in=meta["categories"])
    media.categories.set(categories)


# disabled
# def process_profile(file: File, meta: dict[str, Any]) -> None:
#     url = transfer(file, os.getenv("MEDIA_GALLERY_BUCKET"))
#     storage = Storage()
#     cloud_file = storage.file(get_profile_bucket(), hash)
#     cloud_file_thumbnail = storage.file(get_profile_bucket(), f"{hash}-100x100")

#     if thumb_exists := cloud_file_thumbnail.exists():
#         cloud_file_thumbnail_url = cloud_file_thumbnail.url()


MB = 1024 * 1024
CHUNK_SIZE = 10 * MB

# keeps
MEDIA_SETTINGS: dict[str, MediaSettings] = {
    "media": {
        "chunk_size": CHUNK_SIZE,
        "max_chunks": None,
        "is_quota_exceeded": no_quota_limit,
        "is_authorized": allow_any,
        "is_mime_supported": media_is_mime_supported,
        "get_schema": media_schema,
        "process": process_media,
    },
    "proof-of-payment": {
        "chunk_size": CHUNK_SIZE,
        "max_chunks": None,
        "is_quota_exceeded": no_quota_limit,
        "is_authorized": allow_any,
        "is_mime_supported": proof_of_payment_is_mime_supported,
        "get_schema": None,
        "process": None,
    },
    # disabled
    # "profile-pictures": {
    #     "chunk_size": CHUNK_SIZE,
    #     "max_chunks": 25,  # because currently it accepts 4K photos
    #     "is_quota_exceeded": no_quota_limit,  # change it in a future
    #     "is_authorized": allow_any,
    #     "is_mime_supported": profile_is_mime_supported,
    #     "schema": no_schema,
    #     "process": process_profile,
    # },
}
