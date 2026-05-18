"""
Tests for standardize_person_name.
"""

from breathecode.marketing.utils.person_name import standardize_person_name


class TestStandardizePersonName:
    def test_mathematical_script_to_ascii(self):
        assert standardize_person_name("𝓜𝓪𝓻𝓲𝓪") == "maria"

    def test_plain_name(self):
        assert standardize_person_name("Maria") == "maria"

    def test_accented_name(self):
        assert standardize_person_name("José") == "josé"

    def test_collapses_whitespace(self):
        assert standardize_person_name("  Maria   Gómez  ") == "maria gómez"

    def test_none_and_empty(self):
        assert standardize_person_name(None) == ""
        assert standardize_person_name("") == ""

    def test_hyphenated_name(self):
        assert standardize_person_name("Mary-Jane") == "mary-jane"

    def test_digits_and_symbols_are_kept_not_rejected(self):
        assert standardize_person_name("Brandon1!") == "brandon1!"
