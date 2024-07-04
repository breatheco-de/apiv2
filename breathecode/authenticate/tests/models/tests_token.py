"""
Test cases for /academy/:id/member/:id
"""

from datetime import timedelta
from time import sleep
from django.utils import timezone
from breathecode.services import datetime_to_iso_format
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase
from ...models import Token
from ...exceptions import BadArguments, TokenNotFound, InvalidTokenType


class TokenTestSuite(AuthTestCase):
    """
    🔽🔽🔽 get_or_create bad arguments
    """

    def test_get_or_create__bad_arguments(self):
        with self.assertRaises(InvalidTokenType) as _:
            Token.get_or_create(None, None)

        self.assertEqual(self.all_token_dict(), [])

    def test_get_or_create__bad_user(self):
        with self.assertRaises(InvalidTokenType) as _:
            Token.get_or_create(None, "they-killed-kenny")

        self.assertEqual(self.all_token_dict(), [])

    def test_get_or_create__bad_token_type(self):
        model = self.generate_models(user=True)

        with self.assertRaises(InvalidTokenType) as _:
            Token.get_or_create(model.user, None)

        self.assertEqual(self.all_token_dict(), [])

    """
    🔽🔽🔽 get_or_create token_type login
    """

    def test_get_or_create__token_type_login(self):
        start = timezone.now()
        model = self.generate_models(user=True)

        Token.get_or_create(model.user, token_type="login")
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        expires_at = db[0]["expires_at"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertGreater(expires_at, start)
        self.assertLess(expires_at, end + timedelta(days=1))
        self.assertGreater(expires_at, end + timedelta(days=1) - timedelta(seconds=10))
        self.assertToken(token)

        del db[0]["created"]
        del db[0]["expires_at"]
        del db[0]["key"]

        self.assertEqual(db, [{"id": 1, "token_type": "login", "user_id": 1}])

    def test_get_or_create__token_type_login__passing_hours_length(self):
        start = timezone.now()
        model = self.generate_models(user=True)

        Token.get_or_create(model.user, token_type="login", hours_length=2)
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        expires_at = db[0]["expires_at"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertGreater(expires_at, start)
        self.assertLess(expires_at, end + timedelta(hours=2))
        self.assertGreater(expires_at, end + timedelta(hours=2) - timedelta(seconds=10))
        self.assertToken(token)

        del db[0]["created"]
        del db[0]["expires_at"]
        del db[0]["key"]

        self.assertEqual(db, [{"id": 1, "token_type": "login", "user_id": 1}])

    def test_get_or_create__token_type_login__passing_expires_at(self):
        expires_at = timezone.now() + timedelta(days=7)
        start = timezone.now()
        model = self.generate_models(user=True)

        Token.get_or_create(model.user, token_type="login", expires_at=expires_at)
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)
        self.assertToken(token)

        del db[0]["created"]
        del db[0]["key"]

        self.assertEqual(
            db,
            [
                {
                    "id": 1,
                    "token_type": "login",
                    "user_id": 1,
                    "expires_at": expires_at,
                }
            ],
        )

    """
    🔽🔽🔽 get_or_create token_type one_time
    """

    def test_get_or_create__token_type_one_time(self):
        start = timezone.now()
        model = self.generate_models(user=True)

        Token.get_or_create(model.user, token_type="one_time")
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertToken(token)

        del db[0]["created"]
        del db[0]["key"]

        self.assertEqual(
            db,
            [
                {
                    "id": 1,
                    "token_type": "one_time",
                    "user_id": 1,
                    "expires_at": None,
                }
            ],
        )

    def test_get_or_create__token_type_one_time__passing_hours_length(self):
        model = self.generate_models(user=True)

        with self.assertRaises(BadArguments) as _:
            Token.get_or_create(model.user, token_type="one_time", hours_length=2)

        self.assertEqual(self.all_token_dict(), [])

    def test_get_or_create__token_type_one_time__passing_expires_at(self):
        expires_at = timezone.now() + timedelta(days=7)
        model = self.generate_models(user=True)

        with self.assertRaises(BadArguments) as _:
            Token.get_or_create(model.user, token_type="one_time", expires_at=expires_at)

        self.assertEqual(self.all_token_dict(), [])

    """
    🔽🔽🔽 get_or_create token_type permanent
    """

    def test_get_or_create__token_type_permanent(self):
        start = timezone.now()
        model = self.generate_models(user=True)

        Token.get_or_create(model.user, token_type="permanent")
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertToken(token)

        del db[0]["created"]
        del db[0]["key"]

        self.assertEqual(
            db,
            [
                {
                    "id": 1,
                    "token_type": "permanent",
                    "user_id": 1,
                    "expires_at": None,
                }
            ],
        )

    def test_get_or_create__token_type_permanent__passing_hours_length(self):
        model = self.generate_models(user=True)

        with self.assertRaises(BadArguments) as _:
            Token.get_or_create(model.user, token_type="permanent", hours_length=2)

        self.assertEqual(self.all_token_dict(), [])

    def test_get_or_create__token_type_permanent__passing_expires_at(self):
        expires_at = timezone.now() + timedelta(days=7)
        model = self.generate_models(user=True)

        with self.assertRaises(BadArguments) as _:
            Token.get_or_create(model.user, token_type="permanent", expires_at=expires_at)

        self.assertEqual(self.all_token_dict(), [])

    """
    🔽🔽🔽 get_or_create token_type temporal
    """

    def test_get_or_create__token_type_temporal(self):
        start = timezone.now()
        model = self.generate_models(user=True)

        Token.get_or_create(model.user, token_type="temporal")
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        expires_at = db[0]["expires_at"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertGreater(expires_at, start)
        self.assertLess(expires_at, end + timedelta(minutes=10))
        self.assertGreater(expires_at, end + timedelta(minutes=10) - timedelta(seconds=10))
        self.assertToken(token)

        del db[0]["created"]
        del db[0]["expires_at"]
        del db[0]["key"]

        self.assertEqual(db, [{"id": 1, "token_type": "temporal", "user_id": 1}])

    def test_get_or_create__token_type_temporal__passing_hours_length(self):
        start = timezone.now()
        model = self.generate_models(user=True)

        Token.get_or_create(model.user, token_type="temporal", hours_length=2)
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        expires_at = db[0]["expires_at"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertGreater(expires_at, start)
        self.assertLess(expires_at, end + timedelta(hours=2))
        self.assertGreater(expires_at, end + timedelta(hours=2) - timedelta(seconds=10))
        self.assertToken(token)

        del db[0]["created"]
        del db[0]["expires_at"]
        del db[0]["key"]

        self.assertEqual(db, [{"id": 1, "token_type": "temporal", "user_id": 1}])

    def test_get_or_create__token_type_temporal__passing_expires_at(self):
        expires_at = timezone.now() + timedelta(days=7)
        start = timezone.now()
        model = self.generate_models(user=True)

        Token.get_or_create(model.user, token_type="temporal", expires_at=expires_at)
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)
        self.assertToken(token)

        del db[0]["created"]
        del db[0]["key"]

        self.assertEqual(
            db,
            [
                {
                    "id": 1,
                    "token_type": "temporal",
                    "user_id": 1,
                    "expires_at": expires_at,
                }
            ],
        )

    """
    🔽🔽🔽 get_or_create hours_length and expires_at together
    """

    def test_get_or_create__token_type_login__hours_length_and_expires_at_together(self):
        model = self.generate_models(user=True)
        expires_at = timezone.now()

        with self.assertRaises(BadArguments) as _:
            Token.get_or_create(model.user, token_type="login", hours_length=2, expires_at=expires_at)

        self.assertEqual(self.all_token_dict(), [])

    def test_get_or_create__token_type_one_time__hours_length_and_expires_at_together(self):
        model = self.generate_models(user=True)
        expires_at = timezone.now()

        with self.assertRaises(BadArguments) as _:
            Token.get_or_create(model.user, token_type="one_time", hours_length=2, expires_at=expires_at)

        self.assertEqual(self.all_token_dict(), [])

    def test_get_or_create__token_type_permanent__hours_length_and_expires_at_together(self):
        model = self.generate_models(user=True)
        expires_at = timezone.now()

        with self.assertRaises(BadArguments) as _:
            Token.get_or_create(model.user, token_type="permanent", hours_length=2, expires_at=expires_at)

        self.assertEqual(self.all_token_dict(), [])

    def test_get_or_create__token_type_temporal__hours_length_and_expires_at_together(self):
        model = self.generate_models(user=True)
        expires_at = timezone.now()

        with self.assertRaises(BadArguments) as _:
            Token.get_or_create(model.user, token_type="temporal", hours_length=2, expires_at=expires_at)

        self.assertEqual(self.all_token_dict(), [])

    """
    🔽🔽🔽 get_or_create Token exists
    """

    def test_get_or_create__token_type_login__token_exists(self):
        start = timezone.now()
        expires_at = timezone.now() - timedelta(days=1, seconds=1)
        token_kwargs = {"expires_at": expires_at, "token_type": "login"}
        model = self.generate_models(user=True, token=True, token_kwargs=token_kwargs)

        Token.get_or_create(model.user, token_type="login")
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        expires_at = db[0]["expires_at"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertGreater(expires_at, start)
        self.assertLess(expires_at, end + timedelta(days=1))
        self.assertGreater(expires_at, end + timedelta(days=1) - timedelta(seconds=10))
        self.assertToken(token)

        del db[0]["created"]
        del db[0]["expires_at"]
        del db[0]["key"]

        self.assertEqual(db, [{"id": 2, "token_type": "login", "user_id": 1}])

    def test_get_or_create__token_type_temporal__token_exists(self):
        start = timezone.now()
        expires_at = timezone.now() - timedelta(days=1, seconds=1)
        token_kwargs = {"expires_at": expires_at, "token_type": "temporal"}
        model = self.generate_models(user=True, token=True, token_kwargs=token_kwargs)

        Token.get_or_create(model.user, token_type="temporal")
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        expires_at = db[0]["expires_at"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertGreater(expires_at, start)
        self.assertLess(expires_at, end + timedelta(minutes=10))
        self.assertGreater(expires_at, end + timedelta(minutes=10) - timedelta(seconds=10))
        self.assertToken(token)

        del db[0]["created"]
        del db[0]["expires_at"]
        del db[0]["key"]

        self.assertEqual(db, [{"id": 2, "token_type": "temporal", "user_id": 1}])

    def test_get_or_create__token_type_one_time__token_exists(self):
        start = timezone.now()
        expires_at = None
        token_kwargs = {"expires_at": expires_at, "token_type": "one_time"}
        model = self.generate_models(user=True, token=True, token_kwargs=token_kwargs)

        Token.get_or_create(model.user, token_type="one_time")
        end = timezone.now()

        db = self.all_token_dict()
        created = db[1]["created"]
        token = db[1]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertToken(token)

        del db[1]["created"]
        del db[1]["key"]

        self.assertEqual(
            db,
            [self.model_to_dict(model, "token"), {"id": 2, "token_type": "one_time", "user_id": 1, "expires_at": None}],
        )

    def test_get_or_create__token_type_permanent__token_exists(self):
        start = timezone.now()
        expires_at = None
        token_kwargs = {"expires_at": expires_at, "token_type": "permanent"}
        model = self.generate_models(user=True, token=True, token_kwargs=token_kwargs)

        Token.get_or_create(model.user, token_type="permanent")
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertToken(token)

        del db[0]["created"]
        del db[0]["key"]

        self.assertEqual(db, [{"id": 1, "token_type": "permanent", "user_id": 1, "expires_at": None}])

    """
    🔽🔽🔽 get_or_create two Token exists and this are expired
    """

    def test_get_or_create__token_type_login__token_exists__token_expired(self):
        start = timezone.now()
        expires_at = timezone.now() - timedelta(days=1, seconds=1)
        token_kwargs = {"expires_at": expires_at, "token_type": "login"}
        base = self.generate_models(user=True)
        models = [self.generate_models(token=True, token_kwargs=token_kwargs, models=base) for _ in range(0, 2)]

        Token.get_or_create(base.user, token_type="login")
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        expires_at = db[0]["expires_at"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertGreater(expires_at, start)
        self.assertLess(expires_at, end + timedelta(days=1))
        self.assertGreater(expires_at, end + timedelta(days=1) - timedelta(seconds=10))
        self.assertToken(token)

        del db[0]["created"]
        del db[0]["expires_at"]
        del db[0]["key"]

        self.assertEqual(db, [{"id": 3, "token_type": "login", "user_id": 1}])

    def test_get_or_create__token_type_temporal__token_exists__token_expired(self):
        start = timezone.now()
        expires_at = timezone.now() - timedelta(days=1, seconds=1)
        token_kwargs = {"expires_at": expires_at, "token_type": "temporal"}
        base = self.generate_models(user=True)
        models = [self.generate_models(token=True, token_kwargs=token_kwargs, models=base) for _ in range(0, 2)]

        Token.get_or_create(base.user, token_type="temporal")
        end = timezone.now()

        db = self.all_token_dict()
        created = db[0]["created"]
        expires_at = db[0]["expires_at"]
        token = db[0]["key"]

        self.assertGreater(created, start)
        self.assertLess(created, end)

        self.assertGreater(expires_at, start)
        self.assertLess(expires_at, end + timedelta(minutes=10))
        self.assertGreater(expires_at, end + timedelta(minutes=10) - timedelta(seconds=10))
        self.assertToken(token)

        del db[0]["created"]
        del db[0]["expires_at"]
        del db[0]["key"]

        self.assertEqual(db, [{"id": 3, "token_type": "temporal", "user_id": 1}])

    """
    🔽🔽🔽 validate_and_destroy bad arguments
    """

    def test_validate_and_destroy__bad_arguments(self):
        with self.assertRaises(TokenNotFound) as _:
            Token.validate_and_destroy(None)

        self.assertEqual(self.all_token_dict(), [])

    def test_validate_and_destroy__bad_user(self):
        with self.assertRaises(TokenNotFound) as _:
            Token.validate_and_destroy("they-killed-kenny")

        self.assertEqual(self.all_token_dict(), [])

    def test_validate_and_destroy__bad_hash(self):
        model = self.generate_models(user=True)

        with self.assertRaises(TokenNotFound) as _:
            Token.validate_and_destroy(None)

        self.assertEqual(self.all_token_dict(), [])

    """
    🔽🔽🔽 validate_and_destroy bad token_type
    """

    def test_validate_and_destroy__type_login(self):
        token_kwargs = {"token_type": "login"}
        model = self.generate_models(user=True, token=True, token_kwargs=token_kwargs)

        with self.assertRaises(TokenNotFound) as _:
            Token.validate_and_destroy(model.token.key)

        self.assertEqual(self.all_token_dict(), [self.model_to_dict(model, "token")])

    def test_validate_and_destroy__type_temporal(self):
        token_kwargs = {"token_type": "temporal"}
        model = self.generate_models(user=True, token=True, token_kwargs=token_kwargs)

        with self.assertRaises(TokenNotFound) as _:
            Token.validate_and_destroy(model.token.key)

        self.assertEqual(self.all_token_dict(), [self.model_to_dict(model, "token")])

    def test_validate_and_destroy__type_permanent(self):
        token_kwargs = {"token_type": "permanent"}
        model = self.generate_models(user=True, token=True, token_kwargs=token_kwargs)

        with self.assertRaises(TokenNotFound) as _:
            Token.validate_and_destroy(model.token.key)

        self.assertEqual(self.all_token_dict(), [self.model_to_dict(model, "token")])

    """
    🔽🔽🔽 validate_and_destroy token_type is one_time
    """

    def test_validate_and_destroy__type_one_time(self):
        token_kwargs = {"token_type": "one_time"}
        model = self.generate_models(user=True, token=True, token_kwargs=token_kwargs)
        result = Token.validate_and_destroy(model.token.key)

        self.assertEqual(result, model.user)
        self.assertEqual(self.all_token_dict(), [])

    """
    🔽🔽🔽 get_valid Token not exists
    """

    def test_validate_and_destroy__token_not_exists(self):
        result = Token.get_valid("they-killed-kenny")

        self.assertEqual(result, None)
        self.assertEqual(self.all_token_dict(), [])

    """
    🔽🔽🔽 get_valid Token not found
    """

    def test_validate_and_destroy__token_not_found(self):
        model = self.generate_models(token=True)
        result = Token.get_valid("they-killed-kenny")

        self.assertEqual(result, None)
        self.assertEqual(self.all_token_dict(), [self.model_to_dict(model, "token")])

    """
    🔽🔽🔽 get_valid Token exists
    """

    def test_validate_and_destroy__token_exists(self):
        model = self.generate_models(token=True)
        result = Token.get_valid(model.token.key)

        self.assertEqual(result, model.token)
        self.assertEqual(self.all_token_dict(), [self.model_to_dict(model, "token")])

    """
    🔽🔽🔽 delete_expired_tokens Token not exists
    """

    def test_validate_and_destroy__token_not_exists(self):
        result = Token.delete_expired_tokens()

        self.assertEqual(result, None)
        self.assertEqual(self.all_token_dict(), [])

    def test_validate_and_destroy__token_not_exists__with_arg(self):
        result = Token.delete_expired_tokens()

        self.assertEqual(result, None)
        self.assertEqual(self.all_token_dict(), [])

    """
    🔽🔽🔽 delete_expired_tokens Token exists but are expired
    """

    def test_validate_and_destroy__token_exists_but_are_expired(self):
        now = timezone.now()
        token_kwargs = {"expires_at": now - timedelta(seconds=1)}
        self.generate_models(token=True, token_kwargs=token_kwargs)
        result = Token.delete_expired_tokens()

        self.assertEqual(result, None)
        self.assertEqual(self.all_token_dict(), [])

    def test_validate_and_destroy__token_exists_but_are_expired__with_arg(self):
        now = timezone.now()
        token_kwargs = {"expires_at": now - timedelta(seconds=1)}
        self.generate_models(token=True, token_kwargs=token_kwargs)
        result = Token.delete_expired_tokens()

        self.assertEqual(result, None)
        self.assertEqual(self.all_token_dict(), [])

    """
    🔽🔽🔽 delete_expired_tokens Token exists and is valid
    """

    def test_validate_and_destroy__token_exists_and_is_valid(self):
        now = timezone.now()
        token_kwargs = {"expires_at": now + timedelta(minutes=1)}
        model = self.generate_models(token=True, token_kwargs=token_kwargs)
        result = Token.delete_expired_tokens()

        self.assertEqual(result, None)
        self.assertEqual(self.all_token_dict(), [self.model_to_dict(model, "token")])

    def test_validate_and_destroy__token_exists_and_is_valid__with_arg(self):
        now = timezone.now()
        token_kwargs = {"expires_at": now + timedelta(minutes=1)}
        model = self.generate_models(token=True, token_kwargs=token_kwargs)
        result = Token.delete_expired_tokens()

        self.assertEqual(result, None)
        self.assertEqual(self.all_token_dict(), [self.model_to_dict(model, "token")])
