from email import header
import json
import random
from wsgiref import headers
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from breathecode.authenticate.models import ProfileAcademy
import breathecode.utils.decorators as decorators
from rest_framework.permissions import AllowAny
from rest_framework import status

from breathecode.utils.exceptions import MalformedLanguageCode
from ..mixins import UtilsTestCase
from ...i18n import translation


def randomLang(self, force_complete=True):
    code = "en"

    # avoid choices english
    while code == "en":
        code = self.bc.random.string(lower=True, size=2)

    if force_complete or random.randint(0, 1):
        code += f"-{self.bc.random.string(upper=True, size=2)}"

    return code


def langWithRandomCountry(self, code):
    return f"{code}-{self.bc.random.string(upper=True, size=2)}"


def getLangParam(code: str):
    return code.lower().replace("-", "_")


def randomBool():
    return bool(random.randint(0, 1))


class TranslationTestSuite(UtilsTestCase):
    """
    🔽🔽🔽 Function get id
    """

    def test_Given_RandomLang_When_EnglishTranstalionIsNotGiven_Expect_Exception(self):
        code = randomLang(self, randomBool())
        with self.assertRaisesMessage(MalformedLanguageCode, "The english translation is mandatory"):
            translation(code)

    def test_Given_RandomLang_When_GeneralEnglishTranstalionAndUsaEnglishIsNotGiven_Expect_Exception(self):
        code = randomLang(self, randomBool())
        with self.assertRaisesMessage(MalformedLanguageCode, "The english translation is mandatory"):
            translation(code, en_au="Hello")

    def test_Given_RandomLang_When_LangCodeUppercase_Expect_Exception(self):
        code = randomLang(self, randomBool())
        with self.assertRaisesMessage(MalformedLanguageCode, "Lang code is not lowercase"):
            translation(code, EN_au="Hello")

    def test_Given_RandomLang_When_CountryCodeUppercase_Expect_Exception(self):
        code = randomLang(self, randomBool())
        with self.assertRaisesMessage(MalformedLanguageCode, "Country code is not lowercase"):
            translation(code, en_AU="Hello")

    def test_Given_RandomLang_When_SpanishTranslationIsNotGiven_Expect_GetEnglishTranslation(self):
        code = randomLang(self, randomBool())

        cases = ["en", "en_us"]
        for case in cases:
            kwargs = {case: "Hello"}
            string = translation(code, **kwargs)
            self.assertEqual(string, "Hello")

    def test_Given_None_When_EnglishTranslationIsGiven_Expect_GetEnglishTranslation(self):
        string = translation(None, en="Hello")
        self.assertEqual(string, "Hello")

    def test_Given_LangEs_When_SpanishTranslationIsGiven_Expect_GetGenericSpanishTranslation(self):
        code = langWithRandomCountry(self, "es")
        param = getLangParam(code)
        kwargs = {
            "en": "Hello",
            "es": "Hola",
            param: "Qué onda tío",
        }
        string = translation("es", **kwargs)
        self.assertEqual(string, "Hola")

    def test_Given_LangEsWithCountry_When_SpanishTranslationIsGiven_Expect_GetGenericSpanishTranslation(self):
        code = langWithRandomCountry(self, "es")
        kwargs = {
            "en": "Hello",
            "es": "Hola",
        }
        string = translation(code, **kwargs)
        self.assertEqual(string, "Hola")

    def test_Given_LangEsWithCountry_When_SpanishWithCountryTranslationIsGiven_Expect_GetSpanishTranslationOfThatCountry(
        self,
    ):
        code = langWithRandomCountry(self, "es")
        param = getLangParam(code)
        kwargs = {
            "en": "Hello",
            "es": "Hola",
            param: "Qué onda tío",
        }
        string = translation(code, **kwargs)
        self.assertEqual(string, "Qué onda tío")
