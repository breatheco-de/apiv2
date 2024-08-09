import hashlib
import os
from copy import copy
from io import BytesIO
from typing import Any, Awaitable, Callable, Optional, Tuple, TypedDict, overload

from adrf.requests import AsyncRequest
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.admissions.models import Academy
from breathecode.authenticate.actions import aget_user_language
from breathecode.media.models import Chunk, File
from breathecode.media.signals import schedule_deletion
from breathecode.services.google_cloud.storage import Storage
from breathecode.utils.i18n import translation
from capyc.rest_framework.exceptions import ValidationException

__all__ = ["UploadMixin", "ChunkedUploadMixin", "ChunkUploadMixin", "media_settings"]


class MediaSettings(TypedDict):
    chunk_size: int
    max_chunks: int
    is_quota_exceeded: Callable[[AsyncRequest, Optional[int]], Awaitable[bool]]
    is_authorized: Callable[[AsyncRequest, Optional[int]], Awaitable[bool]]
    is_mime_supported: Callable[[InMemoryUploadedFile | TemporaryUploadedFile, Optional[int]], Awaitable[bool]]
    validate_meta = Callable[[Any], None]


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
]


async def allow_any(request: AsyncRequest, academy_id: Optional[int] = None) -> bool:
    return True


async def no_quota_limit(request: AsyncRequest, academy_id: Optional[int] = None) -> bool:
    return False


async def media_is_mime_supported(
    file: InMemoryUploadedFile | TemporaryUploadedFile, academy_id: Optional[int] = None
) -> bool:
    return file.content_type in MEDIA_MIME_ALLOWED


async def no_validate_meta(meta: Any) -> None: ...


async def schedule_media(meta: Any) -> None: ...


MB = 1024 * 1024
CHUNK_SIZE = 1 * MB


MEDIA_SETTINGS: dict[str, MediaSettings] = {
    "media": {
        "chunk_size": CHUNK_SIZE,
        "max_chunks": None,
        "is_quota_exceeded": no_quota_limit,
        "is_authorized": allow_any,
        "is_mime_supported": media_is_mime_supported,
        "validate_meta": no_validate_meta,
        "scheduler": schedule_media,
    },
    "proof-of-payment": {
        "chunk_size": CHUNK_SIZE,
        "max_chunks": None,
        "is_quota_exceeded": no_quota_limit,
        "is_authorized": allow_any,
        "is_mime_supported": media_is_mime_supported,
        "validate_meta": no_validate_meta,
        "scheduler": schedule_media,
    },
    "profile-pictures": {
        "chunk_size": CHUNK_SIZE,
        "max_chunks": 25,  # because currently it accepts 4K photos
        "is_quota_exceeded": no_quota_limit,  # change it in a future
        "is_authorized": allow_any,
        "is_mime_supported": media_is_mime_supported,
        "validate_meta": no_validate_meta,
        "scheduler": schedule_media,
    },
}
MEDIA_OPERATION_TYPES = tuple(", ".join(MEDIA_SETTINGS.keys()))


@overload
def media_settings() -> Tuple[str, ...]: ...


@overload
def media_settings(operation_type: str) -> MediaSettings | None: ...


def media_settings(operation_type: Optional[str] = None) -> MediaSettings | Tuple[str, ...] | None:
    if operation_type is None:
        return tuple(MEDIA_SETTINGS.keys())

    return copy(MEDIA_SETTINGS.get(operation_type))


class UploadMixin(APIView):
    async def upload(self, academy_id: Optional[int] = None):
        request = self.request
        lang = await aget_user_language(request)
        self.lang = lang

        t = request.data.get("operation_type")
        if t not in MEDIA_SETTINGS:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Unsupported media type operation {t}, choose some of {MEDIA_OPERATION_TYPES}",
                    es=f"Tipo de operación de tipo de media no válido {t}, seleccione alguno de {MEDIA_OPERATION_TYPES}",
                    slug="unsupported-media-type",
                ),
                code=400,
            )

        if MEDIA_SETTINGS[t]["is_authorized"](request, academy_id) is False:
            raise ValidationException(
                translation(
                    lang,
                    en=f"You aren't authorized to upload any {t} operation type",
                    es=f"No está autorizado para subir ninguna operación de tipo {t}",
                    slug="unauthorized-media-upload",
                ),
                code=403,
            )

        self.total_chunks = request.data.get("total_chunks")
        if MEDIA_SETTINGS[t]["max_chunks"] < self.total_chunks:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Total chunks exceeded, maximum allowed is {MEDIA_SETTINGS[t]['max_chunks']}",
                    es=f"El número total de trozos supera el límite permitido, el máximo es {MEDIA_SETTINGS[t]['max_chunks']}",
                    slug="total-chunks-exceeded",
                ),
                code=400,
            )

        self.op_type = t


class ChunkedUploadMixin(UploadMixin):
    async def upload(self, academy_id: Optional[int] = None):
        super().upload(academy_id)
        request = self.request
        lang = self.lang

        if MEDIA_SETTINGS[self.op_type]["is_quota_exceeded"](request, academy_id):
            raise ValidationException(
                translation(
                    lang,
                    en="Your current quota is exceeded, please contact support",
                    es="Su cuota actual excede, contacte con soporte",
                    slug="quota-exceeded",
                ),
                code=400,
            )

        # self.instance = File.objects.filter()

        chunk = request.FILES.get("chunk")
        if chunk is None:
            raise ValidationException(
                translation(
                    lang,
                    en="No chunk provided",
                    es="No se proporcionó chunk",
                    slug="no-chunk-provided",
                ),
                code=400,
            )
        if await MEDIA_SETTINGS[self.op_type]["is_mime_supported"](chunk, academy_id) is False:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Unsupported mime type {chunk.content_type}, choose some of {MEDIA_MIME_ALLOWED}",
                    es=f"Tipo MIME no válido {chunk.content_type}, seleccione alguno de {MEDIA_MIME_ALLOWED}",
                    slug="unsupported-mime-type",
                ),
                code=400,
            )

        if MEDIA_SETTINGS[self.op_type]["chunk_size"] != chunk.size:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Chunk size doesn't match the expected {MEDIA_SETTINGS[self.op_type]['chunk_size']}",
                    es=f"El tamaño del chunk no coincide con el esperado {MEDIA_SETTINGS[self.op_type]['chunk_size']}",
                    slug="chunk-size-does-not-match",
                ),
                code=400,
            )

        chunk_index = request.data.get("chunk_index")
        if isinstance(chunk_index, int) is False:
            raise ValidationException(
                translation(
                    lang,
                    en="Chunk index is not an integer",
                    es="El índice del chunk no es un número entero",
                    slug="chunk-index-not-integer",
                ),
                code=400,
            )

        file_name = request.data.get("filename")

        if academy_id:
            academy = Academy.objects.filter(id=academy_id).first()

        else:
            academy = None

        self.instance = Chunk.objects.filter(
            academy=academy,
            user=request.user,
            name=file_name,
            operation_type=self.op_type,
            mime=chunk.content_type,
            chunk_index=chunk_index,
            total_chunks=self.total_chunks,
            chunk_size=chunk.size,
        ).first()
        if self.instance:
            raise ValidationException(
                translation(
                    self.lang,
                    en="Chunk already exists",
                    es="Chunk ya existe",
                    slug="chunk-already-exists",
                ),
                code=400,
            )

        Chunk.objects.create(
            academy=academy,
            user=request.user,
            name=file_name,
            operation_type=self.op_type,
            mime=chunk.content_type,
            chunk_index=chunk_index,
            total_chunks=self.total_chunks,
            bucket=os.getenv("UPLOAD_BUCKET", "upload-bucket"),
            chunk_size=chunk.size,
        )

        return Response(
            {
                "academy": academy.slug if academy else None,
                "user": request.user.id,
                "name": file_name,
                "operation_type": self.op_type,
                "mime": chunk.content_type,
                "chunk_index": chunk_index,
                "total_chunks": self.total_chunks,
            },
            status=status.HTTP_201_CREATED,
        )


class ChunkUploadMixin(UploadMixin):
    async def upload(self, academy_id: Optional[int] = None):
        super().upload(academy_id)
        request = self.request
        # chunk = request.FILES.get("chunk")
        total_chunks = request.data.get("total_chunks")
        file_name = request.data.get("filename")
        mime = request.data.get("mime")

        # query = {}

        if academy_id:
            academy = Academy.objects.filter(id=academy_id).first()

        else:
            academy = None

        file = await File.objects.filter(
            academy=academy,
            user=request.user,
            name=file_name,
            mime=mime,
            operation_type=self.op_type,
        ).afirst()
        if file:
            raise ValidationException(
                translation(
                    self.lang,
                    en="File already exists",
                    es="Archivo ya existe",
                    slug="file-already-exists",
                ),
                code=400,
            )

        chunks = Chunk.objects.filter(
            academy=academy,
            user=request.user,
            name=file_name,
            operation_type=self.op_type,
            total_chunks=total_chunks,
            mime=mime,
        ).order_by("chunk_index")

        if (n := chunks.count()) < total_chunks:
            missing_chunks = total_chunks - n
            raise ValidationException(
                translation(
                    self.lang,
                    en=f"{missing_chunks}/{total_chunks} chunks are missing",
                    es=f"{missing_chunks}/{total_chunks} chunks están faltando",
                    slug="chunk-not-found",
                ),
                code=400,
            )
        res = BytesIO()

        storage = Storage()

        # separate it to a cloud function to avoid memory issues
        async for chunk in chunks:
            f = BytesIO()

            uploaded_chunk = storage.file(chunk.bucket, chunk.file_name)
            uploaded_chunk.download(f)

            res.write(f.getvalue())

            schedule_deletion.delay(instance=self, sender=self.__class__)

        bucket = storage.bucket(os.getenv("UPLOAD_BUCKET", "upload-bucket"))
        size = res.tell()
        res.seek(0)

        hash = hashlib.md5(res.getvalue()).hexdigest()
        res.seek(0)

        new_file = storage.file(bucket, hash)
        new_file.upload(res, content_type=mime, public=True)

        file = await File.objects.acreate(
            academy=academy,
            user=request.user,
            name=file_name,
            mime=mime,
            operation_type=self.op_type,
            size=size,
            hash=hash,
            bucket=bucket,
        )

        return Response(
            {
                "academy": academy.slug if academy else None,
                "user": request.user.id,
                "name": file.file_name,
                "operation_type": self.op_type,
                "mime": mime,
            },
            status=status.HTTP_201_CREATED,
        )
