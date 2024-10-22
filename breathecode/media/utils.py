import hashlib
import json
import os
import traceback
from copy import copy
from io import BytesIO
from typing import Any, Optional, Tuple, overload

from adrf.views import APIView
from capyc.rest_framework.exceptions import ValidationException
from rest_framework import status
from rest_framework.response import Response

from breathecode.admissions.models import Academy
from breathecode.authenticate.actions import aget_user_language
from breathecode.media.models import Chunk, File
from breathecode.media.signals import schedule_deletion
from breathecode.services.google_cloud.storage import Storage
from breathecode.utils.i18n import translation

from .settings import MEDIA_MIME_ALLOWED, MEDIA_SETTINGS, MediaSettings, Schema

__all__ = ["ChunkedUploadMixin", "ChunkUploadMixin", "media_settings"]


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
                    slug="unsupported-operation-type",
                ),
                code=400,
            )

        if await MEDIA_SETTINGS[t]["is_authorized"](request, academy_id) is False:
            raise ValidationException(
                translation(
                    lang,
                    en=f"You aren't authorized to upload any {t} operation type",
                    es=f"No está autorizado para subir ninguna operación de tipo {t}",
                    slug="unauthorized-media-upload",
                ),
                code=403,
            )

        total_chunks = request.data.get("total_chunks")
        if total_chunks is None or total_chunks.isnumeric() is False or (total_chunks := float(total_chunks)) <= 0:
            raise ValidationException(
                translation(
                    lang,
                    en="total_chunks must be a positive integer",
                    es="total_chunks debe ser un número entero positivo",
                    slug="invalid-total-chunks",
                ),
                code=400,
            )

        if total_chunks.is_integer() is False:
            raise ValidationException(
                translation(
                    lang,
                    en="total_chunks must be a whole number",
                    es="total_chunks debe ser un número entero",
                    slug="invalid-total-chunks-whole-number",
                ),
                code=400,
            )

        self.total_chunks = int(total_chunks)

        if MEDIA_SETTINGS[t]["max_chunks"] and MEDIA_SETTINGS[t]["max_chunks"] < self.total_chunks:
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
        await super().upload(academy_id)
        request = self.request
        lang = self.lang

        if await MEDIA_SETTINGS[self.op_type]["is_quota_exceeded"](request, academy_id):
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
        if (await MEDIA_SETTINGS[self.op_type]["is_mime_supported"](chunk, academy_id)) is False:
            raise ValidationException(
                translation(
                    lang,
                    en=f"Unsupported mime type {chunk.content_type}, choose some of {MEDIA_MIME_ALLOWED}",
                    es=f"Tipo MIME no válido {chunk.content_type}, seleccione alguno de {MEDIA_MIME_ALLOWED}",
                    slug="unsupported-mime-type",
                ),
                code=400,
            )

        if MEDIA_SETTINGS[self.op_type]["chunk_size"] < chunk.size:
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
        if chunk_index is None or chunk_index.isnumeric() is False:
            raise ValidationException(
                translation(
                    lang,
                    en="Chunk index is not an integer",
                    es="El índice del chunk no es un número entero",
                    slug="chunk-index-not-integer",
                ),
                code=400,
            )

        chunk_index = float(chunk_index)
        if chunk_index < 0 or chunk_index > self.total_chunks:
            raise ValidationException(
                translation(
                    lang,
                    en="Chunk index out of range",
                    es="El índice del chunk está fuera de rango",
                    slug="chunk-index-out-of-range",
                ),
                code=400,
            )

        if chunk_index.is_integer() is False:
            raise ValidationException(
                translation(
                    lang,
                    en="Chunk index must be a whole number",
                    es="El índice del chunk debe ser un número entero",
                    slug="chunk-index-must-be-whole-number",
                ),
                code=400,
            )

        chunk_index = int(chunk_index)

        file_name = request.data.get("filename") or chunk.name

        if academy_id:
            academy = await Academy.objects.filter(id=academy_id).afirst()

        else:
            academy = None

        self.instance = await Chunk.objects.filter(
            academy=academy,
            user=request.user,
            name=file_name,
            operation_type=self.op_type,
            mime=chunk.content_type,
            chunk_index=chunk_index,
            total_chunks=self.total_chunks,
            chunk_size=chunk.size,
        ).afirst()
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

        bucket = os.getenv("UPLOAD_BUCKET", "upload-bucket")
        instance = await Chunk.objects.acreate(
            academy=academy,
            user=request.user,
            name=file_name,
            operation_type=self.op_type,
            mime=chunk.content_type,
            chunk_index=chunk_index,
            total_chunks=self.total_chunks,
            bucket=bucket,
            chunk_size=chunk.size,
        )

        try:
            storage = Storage()
            f = storage.file(bucket, instance.file_name)
            f.upload(chunk, content_type=chunk.content_type)

        except Exception:
            traceback.print_exc()
            await instance.adelete()
            raise ValidationException(
                translation(
                    self.lang,
                    en="Failed to upload file",
                    es="Fallo al subir el archivo",
                    slug="failed-to-upload-file",
                ),
                code=500,
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
    async def validate_meta(self, schema: Schema, meta: dict[str, Any]):
        lang = self.lang
        to_delete = []

        for key, _ in schema.items():
            if key not in meta:
                raise ValidationException(
                    translation(
                        lang,
                        en=f"Missing required meta key: {key}",
                        es=f"Falta la clave de metadatos requerida: {key}",
                        slug="missing-required-meta-key",
                    ),
                    code=400,
                )

        for key, value in meta.items():
            if key not in schema:
                to_delete.append(key)
                continue

            validator = schema[key]

            if isinstance(validator, type) is True:
                if isinstance(value, validator) is False:
                    expected_type_name = validator.__name__
                    current_type_name = type(value).__name__
                    raise ValidationException(
                        translation(
                            lang,
                            en=f"Meta value for key '{key}' must be of type {expected_type_name}, got {current_type_name}",
                            es=f'Valor de metadatos para la clave "{key}" debe ser de tipo {expected_type_name}, obtenido {current_type_name}',
                            slug="invalid-meta-value-type",
                        ),
                        code=400,
                    )

            else:
                validator(key, value)

        for key in to_delete:
            del meta[key]

    async def upload(self, academy_id: Optional[int] = None):
        from breathecode.media.tasks import process_file
        from breathecode.notify.models import Notification

        await super().upload(academy_id)
        request = self.request

        total_chunks = self.total_chunks
        file_name = request.data.get("filename")
        mime = request.data.get("mime")

        try:
            meta = json.loads(request.data.get("meta", "{}"))

        except Exception:
            raise ValidationException(
                translation(
                    self.lang,
                    en="Invalid JSON in meta field",
                    es="JSON inválido en el campo meta",
                    slug="invalid-json-in-meta-field",
                ),
                code=400,
            )

        if not file_name:
            raise ValidationException(
                translation(
                    self.lang,
                    en="filename is required",
                    es="filename es requerido",
                    slug="filename-required",
                ),
                code=400,
            )

        if not mime:
            raise ValidationException(
                translation(
                    self.lang,
                    en="mime is required",
                    es="mime es requerido",
                    slug="mime-required",
                ),
                code=400,
            )

        if isinstance(meta, dict) is False:
            raise ValidationException(
                translation(
                    self.lang,
                    en="meta must be a dictionary",
                    es="meta debe ser un diccionario",
                    slug="meta-must-be-dictionary",
                ),
                code=400,
            )

        get_schema = MEDIA_SETTINGS[self.op_type]["get_schema"]
        if get_schema:
            schema = await get_schema(meta)
            await self.validate_meta(schema, meta)

        if academy_id:
            academy = await Academy.objects.filter(id=academy_id).afirst()

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

        chunks = (
            Chunk.objects.filter(
                academy=academy,
                user=request.user,
                name=file_name,
                operation_type=self.op_type,
                total_chunks=total_chunks,
                mime=mime,
            )
            .prefetch_related("user", "academy")
            .order_by("chunk_index")
        )

        if (n := await chunks.acount()) < total_chunks:
            missing_chunks = total_chunks - n
            raise ValidationException(
                translation(
                    self.lang,
                    en=f"{missing_chunks}/{total_chunks} chunks are missing",
                    es=f"{missing_chunks}/{total_chunks} chunks están faltando",
                    slug="some-chunks-not-found",
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

            await schedule_deletion.adelay(instance=chunk, sender=chunk.__class__)

        bucket = os.getenv("UPLOAD_BUCKET", "upload-bucket")
        size = res.tell()
        res.seek(0)

        hash = hashlib.md5(res.getvalue()).hexdigest()
        res.seek(0)

        new_file = storage.file(bucket, hash)
        new_file.upload(res, content_type=mime)

        notification_id = None

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
        if MEDIA_SETTINGS[self.op_type]["process"]:
            file.status = File.Status.TRANSFERRING
            await file.asave()

            notification = await Notification.objects.acreate(
                operation_code=f"up-{self.op_type}",
                user=request.user,
                academy=academy,
                meta={"file_id": file.id},
            )
            notification_id = notification.id

            process_file.delay(file.id, notification.id)

        return Response(
            {
                "id": file.id,
                "notification": notification_id,
                "academy": academy.slug if academy else None,
                "user": request.user.id,
                "status": file.status,
                "name": file.file_name,
                "operation_type": self.op_type,
                "mime": mime,
            },
            status=status.HTTP_201_CREATED,
        )
