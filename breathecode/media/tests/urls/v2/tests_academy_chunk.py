"""
Test /answer
"""

import tempfile
from typing import Callable
from unittest.mock import MagicMock, PropertyMock, call

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.urls.base import reverse_lazy
from rest_framework import status

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


@pytest.fixture(autouse=True)
def setup(db, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.__init__", MagicMock(return_value=None))
    monkeypatch.setattr("breathecode.services.google_cloud.Storage.client", PropertyMock(), raising=False)
    monkeypatch.setattr("breathecode.services.google_cloud.File.upload", MagicMock())


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_no_auth(aclient: capy.AsyncClient):
    url = reverse_lazy("v2:media:academy_chunk")

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
    url = reverse_lazy("v2:media:academy_chunk")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
    )

    response = await aclient.put(url, headers={"Authorization": f"Token {model.token.key}", "Academy": "1"})

    json = response.json()
    expected = {
        "detail": "You (user: 1) don't have this capability: crud_file for academy 1",
        "status_code": 403,
    }

    assert json == expected
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
async def test_op_type_not_provided(aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake):
    url = reverse_lazy("v2:media:academy_chunk")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
        academy=1,
        role=1,
        profile_academy=1,
        capability={"slug": "crud_file"},
        city=1,
        country=1,
    )

    response = await aclient.put(url, headers={"Authorization": f"Token {model.token.key}", "Academy": "1"})

    json = response.json()
    expected = {
        "detail": "unsupported-operation-type",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert await database.alist_of("media.Chunk") == []

    assert Storage.__init__.call_args_list == []
    assert File.upload.call_args_list == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("op_type", ["media", "proof-of-payment"])
async def test_no_total_chunks(aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake, op_type: str):
    url = reverse_lazy("v2:media:academy_chunk")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
        academy=1,
        role=1,
        profile_academy=1,
        capability={"slug": "crud_file"},
        city=1,
        country=1,
    )

    data = {"operation_type": op_type}

    response = await aclient.put(
        url, data, headers={"Authorization": f"Token {model.token.key}", "Academy": "1"}, format="multipart"
    )

    json = response.json()
    expected = {
        "detail": "invalid-total-chunks",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert await database.alist_of("media.Chunk") == []

    assert Storage.__init__.call_args_list == []
    assert File.upload.call_args_list == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("op_type", ["media", "proof-of-payment"])
async def test_no_chunk(aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake, op_type: str):
    url = reverse_lazy("v2:media:academy_chunk")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
        academy=1,
        role=1,
        profile_academy=1,
        capability={"slug": "crud_file"},
        city=1,
        country=1,
    )

    data = {"operation_type": op_type, "total_chunks": 3}

    response = await aclient.put(
        url, data, headers={"Authorization": f"Token {model.token.key}", "Academy": "1"}, format="multipart"
    )

    json = response.json()
    expected = {
        "detail": "no-chunk-provided",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert await database.alist_of("media.Chunk") == []

    assert Storage.__init__.call_args_list == []
    assert File.upload.call_args_list == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize("op_type", ["media", "proof-of-payment"])
async def test_unsupported_mime(
    aclient: capy.AsyncClient, database: capy.Database, fake: capy.Fake, op_type: str, file: Callable
):
    url = reverse_lazy("v2:media:academy_chunk")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
        academy=1,
        role=1,
        profile_academy=1,
        capability={"slug": "crud_file"},
        city=1,
        country=1,
    )

    f = file()

    data = {"operation_type": op_type, "total_chunks": 3, "chunk": f}

    response = await aclient.put(
        url, data, headers={"Authorization": f"Token {model.token.key}", "Academy": "1"}, format="multipart"
    )

    json = response.json()
    expected = {
        "detail": "unsupported-mime-type",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert await database.alist_of("media.Chunk") == []

    assert Storage.__init__.call_args_list == []
    assert File.upload.call_args_list == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize(
    "op_type, op_props",
    [
        ("media", {"size": 1024 * 1024}),
        ("proof-of-payment", {"size": 1024 * 1024}),
    ],
)
async def test_no_chunk_index(
    aclient: capy.AsyncClient,
    database: capy.Database,
    fake: capy.Fake,
    op_type: str,
    op_props: dict,
    get_chunk: Callable,
):
    url = reverse_lazy("v2:media:academy_chunk")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
        academy=1,
        role=1,
        profile_academy=1,
        capability={"slug": "crud_file"},
        city=1,
        country=1,
    )

    f = get_chunk(op_props["size"])

    data = {"operation_type": op_type, "total_chunks": 3, "chunk": f}

    response = await aclient.put(
        url, data, headers={"Authorization": f"Token {model.token.key}", "Academy": "1"}, format="multipart"
    )

    json = response.json()
    expected = {
        "detail": "chunk-index-not-integer",
        "status_code": 400,
    }

    assert json == expected
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert await database.alist_of("media.Chunk") == []

    assert Storage.__init__.call_args_list == []
    assert File.upload.call_args_list == []


@pytest.mark.asyncio
@pytest.mark.django_db(reset_sequences=True)
@pytest.mark.parametrize(
    "op_type, op_props",
    [
        ("media", {"size": 1024 * 1024}),
        ("proof-of-payment", {"size": 1024 * 1024}),
    ],
)
async def test_chunk_uploaded(
    aclient: capy.AsyncClient,
    database: capy.Database,
    fake: capy.Fake,
    op_type: str,
    op_props: dict,
    get_chunk: Callable,
):
    url = reverse_lazy("v2:media:academy_chunk")
    model = await database.acreate(
        user=1,
        token={"token_type": "login", "key": fake.slug()},
        academy=1,
        role=1,
        profile_academy=1,
        capability={"slug": "crud_file"},
        city=1,
        country=1,
    )

    f = get_chunk(op_props["size"])

    data = {"operation_type": op_type, "total_chunks": 3, "chunk": f, "chunk_index": 0}

    response = await aclient.put(
        url, data, headers={"Authorization": f"Token {model.token.key}", "Academy": "1"}, format="multipart"
    )

    json = response.json()
    expected = {
        "academy": model.academy.slug,
        "chunk_index": 0,
        "mime": "image/png",
        "name": "chunk.png",
        "operation_type": op_type,
        "total_chunks": 3,
        "user": 1,
    }

    assert json == expected
    assert response.status_code == status.HTTP_201_CREATED
    assert await database.alist_of("media.Chunk") == [
        {
            "academy_id": model.academy.id,
            "bucket": "upload-bucket",
            "chunk_index": 0,
            "chunk_size": 9712,
            "id": 1,
            "mime": "image/png",
            "name": "chunk.png",
            "operation_type": op_type,
            "total_chunks": 3,
            "user_id": 1,
        },
    ]

    assert Storage.__init__.call_args_list == [call()]
    assert len(File.upload.call_args_list) == 1

    args, kwargs = File.upload.call_args_list[0]

    assert len(args) == 1
    assert isinstance(args[0], InMemoryUploadedFile)
    file: InMemoryUploadedFile = args[0]
    assert file.name == "chunk.png"
    assert file.size == 9712
    assert file.content_type == "image/png"

    assert kwargs == {"content_type": "image/png"}
