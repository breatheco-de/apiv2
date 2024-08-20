"""
Test /answer
"""

import json as json_utils
import tempfile
from io import BytesIO
from typing import Callable
from unittest.mock import AsyncMock, MagicMock, PropertyMock, call

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.urls.base import reverse_lazy
from rest_framework import status

from breathecode.media.signals import schedule_deletion
from breathecode.media.tasks import process_file
from breathecode.services.google_cloud import File, Storage
from capyc.rest_framework import pytest as capy


@pytest.fixture
def file(fake: capy.Fake):
    files = []

    def wrapper():
        file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        text = fake.text()
        file.write(text.encode("utf-8"))
        # file.close()
        files.append(file)
        return file

    yield wrapper

    for file in files:
        file.close()


@pytest.fixture
def get_chunk(fake: capy.Fake):
    def wrapper(size):
        with open("breathecode/static/img/avatar-20.png", "rb") as f:
            chunk = f.read(size)
            file = SimpleUploadedFile(
                f"chunk.png",
                chunk,
                content_type="image/png",
            )
            return file

    yield wrapper


def mock_download(x: BytesIO) -> None:
    x.write(b"my_line\n")


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.__init__", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.client", PropertyMock(), raising=False)
    monkeypatch.setattr("breathecode.services.google_cloud.File.download", MagicMock(side_effect=mock_download))
    monkeypatch.setattr("breathecode.services.google_cloud.File.upload", MagicMock())
    monkeypatch.setattr("breathecode.media.signals.schedule_deletion.adelay", AsyncMock())
    monkeypatch.setattr("breathecode.media.tasks.process_file.delay", AsyncMock())


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_no_auth(aclient: capy.AsyncClient):
    url = reverse_lazy("v2:media:me_chunk_upload")

    response = await aclient.put(url)

    json = response.json()
    expected = {
        "detail": "Authentication credentials were not provided.",
        "status_code": 401,
    }

    assert json == expected
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_no_pemission(aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("v2:media:me_chunk_upload")
    model = await database.acreate(user=1, token={"token_type": "login", "key": fake.slug()})

    response = await aclient.put(url, headers={"Authorization": f"Token {model.token.key}"})

    json = response.json()
    expected = {
        "detail": "without-permission",
        "status_code": 403,
    }

    assert json == expected
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_op_type_not_provided(aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("v2:media:me_chunk_upload")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
        permission={"codename": "upload_media"},
    )

    response = await aclient.put(url, headers={"Authorization": f"Token {model.token.key}"})

    json = response.json()
    expected = {
        "detail": "unsupported-operation-type",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert await database.alist_of("media.Chunk") == []
    assert await database.alist_of("media.File") == []

    assert Storage.__init__.call_args_list == []
    assert File.upload.call_args_list == []

    assert process_file.delay.call_args_list == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("op_type", ["media", "proof-of-payment"])
async def test_no_total_chunks(aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake, op_type: str):
    url = reverse_lazy("v2:media:me_chunk_upload")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
        permission={"codename": "upload_media"},
    )

    data = {"operation_type": op_type}

    response = await aclient.put(url, data, headers={"Authorization": f"Token {model.token.key}"}, format="multipart")

    json = response.json()
    expected = {
        "detail": "invalid-total-chunks",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert await database.alist_of("media.Chunk") == []
    assert await database.alist_of("media.File") == []

    assert Storage.__init__.call_args_list == []
    assert File.upload.call_args_list == []

    assert process_file.delay.call_args_list == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("op_type", ["media", "proof-of-payment"])
async def test_no_filename(aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake, op_type: str):
    url = reverse_lazy("v2:media:me_chunk_upload")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
        permission={"codename": "upload_media"},
    )

    data = {"operation_type": op_type, "total_chunks": 3}

    response = await aclient.put(url, data, headers={"Authorization": f"Token {model.token.key}"}, format="multipart")

    json = response.json()
    expected = {
        "detail": "filename-required",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert await database.alist_of("media.Chunk") == []
    assert await database.alist_of("media.File") == []

    assert Storage.__init__.call_args_list == []
    assert File.upload.call_args_list == []

    assert process_file.delay.call_args_list == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("op_type", ["media", "proof-of-payment"])
async def test_no_mime(aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake, op_type: str):
    url = reverse_lazy("v2:media:me_chunk_upload")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
        permission={"codename": "upload_media"},
    )

    data = {"operation_type": op_type, "total_chunks": 3, "filename": "a.txt"}

    response = await aclient.put(url, data, headers={"Authorization": f"Token {model.token.key}"}, format="multipart")

    json = response.json()
    expected = {
        "detail": "mime-required",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert await database.alist_of("media.Chunk") == []
    assert await database.alist_of("media.File") == []

    assert Storage.__init__.call_args_list == []
    assert File.upload.call_args_list == []

    assert process_file.delay.call_args_list == []


class TestNoSchema:
    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize("op_type", ["proof-of-payment"])
    async def test_no_chunks(self, aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake, op_type: str):
        url = reverse_lazy("v2:media:me_chunk_upload")
        model = await database.acreate(
            user=1,
            token={"token_type": "login", "key": fake.slug()},
            permission={"codename": "upload_media"},
        )

        data = {"operation_type": op_type, "total_chunks": 3, "filename": "a.txt", "mime": "text/plain"}

        response = await aclient.put(
            url, data, headers={"Authorization": f"Token {model.token.key}"}, format="multipart"
        )

        json = response.json()
        expected = {
            "detail": "some-chunks-not-found",
            "status_code": 400,
        }

        assert json == expected
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert await database.alist_of("media.Chunk") == []
        assert await database.alist_of("media.File") == []

        assert Storage.__init__.call_args_list == []
        assert File.upload.call_args_list == []

        assert process_file.delay.call_args_list == []

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize("op_type", ["proof-of-payment"])
    async def test_upload_file__schedule_deletions(
        self, aclient: capy.AsyncClient, database: capy.Database, format: capy.Format, fake: capy.Fake, op_type: str
    ):
        url = reverse_lazy("v2:media:me_chunk_upload")
        filename = fake.slug() + ".txt"
        mime = "text/plain"
        chunks = [
            {
                "name": filename,
                "mime": mime,
                "operation_type": op_type,
                "total_chunks": 3,
                "chunk_index": index,
            }
            for index in range(3)
        ]
        model = await database.acreate(
            user=1,
            token={"token_type": "login", "key": fake.slug()},
            permission={"codename": "upload_media"},
            chunk=chunks,
        )

        data = {"operation_type": op_type, "total_chunks": 3, "filename": filename, "mime": "text/plain"}

        response = await aclient.put(
            url, data, headers={"Authorization": f"Token {model.token.key}"}, format="multipart"
        )

        json = response.json()
        expected = {
            "id": 1,
            "academy": None,
            "mime": "text/plain",
            "name": "a291e39ac495b2effd38d508417cd731",
            "operation_type": op_type,
            "user": 1,
            "status": "CREATED",
        }

        assert json == expected
        assert response.status_code == status.HTTP_201_CREATED
        assert await database.alist_of("media.Chunk") == [format.to_obj_repr(chunk) for chunk in model.chunk]
        assert await database.alist_of("media.File") == [
            {
                "academy_id": None,
                "bucket": "upload-bucket",
                "hash": "a291e39ac495b2effd38d508417cd731",
                "id": 1,
                "meta": None,
                "mime": "text/plain",
                "name": filename,
                "operation_type": op_type,
                "size": 24,
                "status": "CREATED",
                "user_id": 1,
                "status_message": None,
            },
        ]

        assert Storage.__init__.call_args_list == [call()]
        assert len(File.download.call_args_list) == 3

        for n in range(3):
            args, kwargs = File.download.call_args_list[0]
            assert len(args) == 1
            assert isinstance(args[0], BytesIO)
            assert kwargs == {}

        assert len(File.upload.call_args_list) == 1

        args, kwargs = File.upload.call_args_list[0]

        assert len(args) == 1
        assert isinstance(args[0], BytesIO)
        file: BytesIO = args[0]
        assert file.getvalue() == b"my_line\nmy_line\nmy_line\n"

        assert kwargs == {"content_type": "text/plain"}

        assert schedule_deletion.adelay.call_args_list == [
            call(instance=chunk, sender=chunk.__class__) for chunk in model.chunk
        ]

        assert process_file.delay.call_args_list == []


class TestMediaSchema:
    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize("op_type", ["media"])
    async def test_no_meta_keys(
        self, aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake, op_type: str
    ):
        url = reverse_lazy("v2:media:me_chunk_upload")
        model = await database.acreate(
            user=1,
            token={"token_type": "login", "key": fake.slug()},
            permission={"codename": "upload_media"},
        )

        data = {"operation_type": op_type, "total_chunks": 3, "filename": "a.txt", "mime": "text/plain"}

        response = await aclient.put(
            url, data, headers={"Authorization": f"Token {model.token.key}"}, format="multipart"
        )

        json = response.json()
        expected = {
            "detail": "missing-required-meta-key",
            "status_code": 400,
        }

        assert json == expected
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert await database.alist_of("media.Chunk") == []
        assert await database.alist_of("media.File") == []

        assert Storage.__init__.call_args_list == []
        assert File.upload.call_args_list == []

        assert process_file.delay.call_args_list == []

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize("op_type", ["media"])
    async def test_bad_meta_keys(
        self, aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake, op_type: str
    ):
        url = reverse_lazy("v2:media:me_chunk_upload")
        model = await database.acreate(
            user=1,
            token={"token_type": "login", "key": fake.slug()},
            permission={"codename": "upload_media"},
        )

        data = {
            "operation_type": op_type,
            "total_chunks": 3,
            "filename": "a.txt",
            "mime": "text/plain",
            "meta": json_utils.dumps(
                {
                    "x": "y",
                    "slug": 1,
                    "name": 1,
                    "categories": 7,
                    "academy": "a",
                }
            ),
        }

        response = await aclient.put(
            url, data, headers={"Authorization": f"Token {model.token.key}"}, format="multipart"
        )

        json = response.json()
        expected = {
            "detail": "invalid-meta-value-type",
            "status_code": 400,
        }

        assert json == expected
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert await database.alist_of("media.Chunk") == []
        assert await database.alist_of("media.File") == []

        assert Storage.__init__.call_args_list == []
        assert File.upload.call_args_list == []

        assert process_file.delay.call_args_list == []

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize("op_type", ["media"])
    async def test_no_chunks(self, aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake, op_type: str):
        url = reverse_lazy("v2:media:me_chunk_upload")
        model = await database.acreate(
            user=1,
            token={"token_type": "login", "key": fake.slug()},
            permission={"codename": "upload_media"},
        )

        data = {
            "operation_type": op_type,
            "total_chunks": 3,
            "filename": "a.txt",
            "mime": "text/plain",
            "meta": json_utils.dumps(
                {
                    "x": "y",
                    "slug": fake.slug(),
                    "name": fake.name(),
                    "categories": [fake.slug()],
                    "academy": 1,
                }
            ),
        }

        response = await aclient.put(
            url, data, headers={"Authorization": f"Token {model.token.key}"}, format="multipart"
        )

        json = response.json()
        expected = {
            "detail": "some-chunks-not-found",
            "status_code": 400,
        }

        assert json == expected
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert await database.alist_of("media.Chunk") == []
        assert await database.alist_of("media.File") == []

        assert Storage.__init__.call_args_list == []
        assert File.upload.call_args_list == []

        assert process_file.delay.call_args_list == []

    @pytest.mark.asyncio
    @pytest.mark.django_db(reset_sequences=True)
    @pytest.mark.parametrize("op_type", ["media"])
    async def test_upload_file__schedule_deletions(
        self, aclient: capy.AsyncClient, database: capy.Database, format: capy.Format, fake: capy.Fake, op_type: str
    ):
        url = reverse_lazy("v2:media:me_chunk_upload")
        filename = fake.slug() + ".txt"
        mime = "text/plain"
        chunks = [
            {
                "name": filename,
                "mime": mime,
                "operation_type": op_type,
                "total_chunks": 3,
                "chunk_index": index,
            }
            for index in range(3)
        ]
        model = await database.acreate(
            user=1,
            token={"token_type": "login", "key": fake.slug()},
            permission={"codename": "upload_media"},
            chunk=chunks,
        )

        data = {
            "operation_type": op_type,
            "total_chunks": 3,
            "filename": filename,
            "mime": "text/plain",
            "meta": json_utils.dumps(
                {
                    "x": "y",
                    "slug": fake.slug(),
                    "name": fake.name(),
                    "categories": [fake.slug()],
                    "academy": 1,
                }
            ),
        }

        response = await aclient.put(
            url, data, headers={"Authorization": f"Token {model.token.key}"}, format="multipart"
        )

        json = response.json()
        expected = {
            "id": 1,
            "academy": None,
            "mime": "text/plain",
            "name": "a291e39ac495b2effd38d508417cd731",
            "operation_type": op_type,
            "user": 1,
            "status": "TRANSFERRING",
        }

        assert json == expected
        assert response.status_code == status.HTTP_201_CREATED
        assert await database.alist_of("media.Chunk") == [format.to_obj_repr(chunk) for chunk in model.chunk]
        assert await database.alist_of("media.File") == [
            {
                "academy_id": None,
                "bucket": "upload-bucket",
                "hash": "a291e39ac495b2effd38d508417cd731",
                "id": 1,
                "meta": None,
                "mime": "text/plain",
                "name": filename,
                "operation_type": op_type,
                "size": 24,
                "status": "TRANSFERRING",
                "user_id": 1,
                "status_message": None,
            },
        ]

        assert Storage.__init__.call_args_list == [call()]
        assert len(File.download.call_args_list) == 3

        for n in range(3):
            args, kwargs = File.download.call_args_list[0]
            assert len(args) == 1
            assert isinstance(args[0], BytesIO)
            assert kwargs == {}

        assert len(File.upload.call_args_list) == 1

        args, kwargs = File.upload.call_args_list[0]

        assert len(args) == 1
        assert isinstance(args[0], BytesIO)
        file: BytesIO = args[0]
        assert file.getvalue() == b"my_line\nmy_line\nmy_line\n"

        assert kwargs == {"content_type": "text/plain"}

        assert schedule_deletion.adelay.call_args_list == [
            call(instance=chunk, sender=chunk.__class__) for chunk in model.chunk
        ]

        assert process_file.delay.call_args_list == [call(1)]
