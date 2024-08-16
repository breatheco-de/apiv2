from logging import Logger
from typing import Generator
from unittest.mock import MagicMock, call

import pytest

from breathecode.media import settings
from breathecode.payments import tasks
from capyc.rest_framework import pytest as capy


@pytest.fixture(autouse=True)
def url(db, monkeypatch: pytest.MonkeyPatch, fake: capy.Fake) -> Generator:
    url = fake.url()
    monkeypatch.setattr("logging.Logger.warning", MagicMock())
    monkeypatch.setattr("logging.Logger.error", MagicMock())
    monkeypatch.setattr("breathecode.media.settings.transfer", MagicMock(return_value=url))
    monkeypatch.setenv("PROOF_OF_PAYMENT_BUCKET", "my-bucket")
    yield url


def test_no_file(database: capy.Database):
    tasks.set_proof_of_payment_confirmation_url.delay(1, 1)

    assert database.list_of("payments.ProofOfPayment") == []

    assert Logger.warning.call_args_list == [call("File with id 1 not found or is not transferring")]
    assert Logger.error.call_args_list == [call("File with id 1 not found or is not transferring", exc_info=True)]
    assert settings.transfer.call_args_list == []


def test_no_proof(database: capy.Database):
    database.create(file={"status": "TRANSFERRING"})
    tasks.set_proof_of_payment_confirmation_url.delay(1, 1)

    assert database.list_of("payments.ProofOfPayment") == []

    assert Logger.warning.call_args_list == [call("Proof of Payment with id 1 not found")]
    assert Logger.error.call_args_list == [call("Proof of Payment with id 1 not found", exc_info=True)]
    assert settings.transfer.call_args_list == []


def test_transferred(database: capy.Database, format: capy.Format, url: str):
    model = database.create(
        file={"status": "TRANSFERRING"},
        proof_of_payment=1,
    )
    tasks.set_proof_of_payment_confirmation_url.delay(1, 1)

    assert database.list_of("payments.ProofOfPayment") == [
        {
            **format.to_obj_repr(model.proof_of_payment),
            "confirmation_image_url": url,
            "status": "DONE",
        },
    ]

    assert Logger.warning.call_args_list == []
    assert Logger.error.call_args_list == []
    assert settings.transfer.call_args_list == [call(model.file, "my-bucket")]
