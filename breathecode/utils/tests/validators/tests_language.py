import pytest

from breathecode.utils.validators.language import (
    language_codes_for_lookup,
    languages_equivalent,
)


class TestLanguagesEquivalent:
    """languages_equivalent(lang_a, lang_b) treats us and en as the same."""

    def test_us_and_en_equivalent(self):
        assert languages_equivalent("us", "en") is True
        assert languages_equivalent("en", "us") is True

    def test_same_code_equivalent(self):
        assert languages_equivalent("en", "en") is True
        assert languages_equivalent("us", "us") is True
        assert languages_equivalent("es", "es") is True

    def test_different_languages_not_equivalent(self):
        assert languages_equivalent("es", "en") is False
        assert languages_equivalent("es", "us") is False
        assert languages_equivalent("pt", "en") is False

    def test_case_insensitive(self):
        assert languages_equivalent("US", "en") is True
        assert languages_equivalent("En", "us") is True
        assert languages_equivalent("ES", "es") is True

    def test_none_and_empty(self):
        assert languages_equivalent(None, None) is True
        assert languages_equivalent("", "") is True
        assert languages_equivalent(None, "") is True
        assert languages_equivalent("en", None) is False
        assert languages_equivalent("", "en") is False


class TestLanguageCodesForLookup:
    """language_codes_for_lookup(lang) returns list for filter(lang__in=...)."""

    def test_us_returns_both(self):
        assert language_codes_for_lookup("us") == ["us", "en"]

    def test_en_returns_both(self):
        assert language_codes_for_lookup("en") == ["us", "en"]

    def test_other_lang_returns_single_normalized(self):
        assert language_codes_for_lookup("es") == ["es"]
        assert language_codes_for_lookup("pt") == ["pt"]

    def test_none_or_empty_returns_empty_list(self):
        assert language_codes_for_lookup(None) == []
        assert language_codes_for_lookup("") == []
        assert language_codes_for_lookup("   ") == []

    def test_case_insensitive(self):
        assert language_codes_for_lookup("US") == ["us", "en"]
        assert language_codes_for_lookup("EN") == ["us", "en"]
        assert language_codes_for_lookup("ES") == ["es"]
