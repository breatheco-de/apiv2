from unittest.mock import MagicMock, call, patch

import pytest

from breathecode.authenticate.models import CredentialsGithub
from breathecode.registry.models import Asset
from breathecode.registry.utils import AssetErrorLogType, AssetException, AssetValidator


@pytest.fixture
def mock_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(AssetValidator, "error", MagicMock(side_effect=Exception("stop")))


# Prevent checks from running automatically in __init__ for method-specific tests
@patch.object(AssetValidator, "readme_url", MagicMock())
@patch.object(AssetValidator, "urls", MagicMock())
@patch.object(AssetValidator, "lang", MagicMock())
@patch.object(AssetValidator, "translations", MagicMock())
@patch.object(AssetValidator, "technologies", MagicMock())
@patch.object(AssetValidator, "description", MagicMock())
@patch.object(AssetValidator, "preview", MagicMock())
@patch.object(AssetValidator, "readme", MagicMock())
@patch.object(AssetValidator, "category", MagicMock())
@patch.object(AssetValidator, "images", MagicMock())
def mocked_validator_init(self, asset, log_errors=False):
    self.asset = asset
    self.log_errors = log_errors
    self.errors = []
    self.warns = []


def test_asset_validator_exists():
    """Test that AssetValidator can be instantiated."""
    mock_asset = MagicMock(spec=Asset)
    # Instantiation itself is the test here
    AssetValidator(mock_asset)


def test_asset_validator_warns_property_initial_state():
    """Test that AssetValidator initializes the warns property correctly."""
    mock_asset = MagicMock(spec=Asset)
    # Let __init__ run normally to check initial state
    validator = AssetValidator(mock_asset)
    assert validator.warns == ["translations", "technologies"]


def test_asset_validator_errors_property_initial_state():
    """Test that AssetValidator initializes the errors property correctly."""
    mock_asset = MagicMock(spec=Asset)
    # Let __init__ run normally to check initial state
    validator = AssetValidator(mock_asset)
    assert validator.errors == ["lang", "urls", "category", "preview", "images", "readme_url", "description"]


class TestError:
    """Tests for the AssetValidator.error method."""

    def test_error_raises_exception_when_log_errors_false(self):
        """Verify error() raises AssetException when log_errors=False."""
        mock_asset = MagicMock(spec=Asset)
        validator = AssetValidator(mock_asset, log_errors=False)

        error_slug = "test-error-slug"
        error_message = "This is a test error message."

        with pytest.raises(Exception, match=error_message):
            validator.error(error_slug, error_message)

        # Check the exception attributes

        assert mock_asset.log_error.call_count == 0

    def test_error_logs_error_when_log_errors_true(self):
        """Verify error() calls log() and adds slug to errors when log_errors=True."""
        mock_asset = MagicMock(spec=Asset)
        validator = AssetValidator(mock_asset, log_errors=True)

        error_slug = "test-log-slug"
        error_message = "This is a test log message."

        with pytest.raises(Exception, match=error_message):
            validator.error(error_slug, error_message)

        mock_asset.log_error.assert_called_once_with(error_slug, error_message)


class TestValidate:
    """Tests for the main AssetValidator.validate method."""

    def test_all_checks_are_called_successfully(self, monkeypatch: pytest.MonkeyPatch):
        """Verify that validate() returns the current errors list populated by __init__."""
        mock_asset = MagicMock(spec=Asset)
        # Let __init__ run to populate errors
        validator = AssetValidator(mock_asset)
        errors = ["x", "y"]
        warns = ["a", "b"]
        validator.errors = errors
        validator.warns = warns

        mock_x = MagicMock()
        mock_y = MagicMock()
        mock_a = MagicMock()
        mock_b = MagicMock()

        monkeypatch.setattr(AssetValidator, "errors", errors)
        monkeypatch.setattr(AssetValidator, "warns", warns)
        monkeypatch.setattr(AssetValidator, "x", mock_x, raising=False)
        monkeypatch.setattr(AssetValidator, "y", mock_y, raising=False)
        monkeypatch.setattr(AssetValidator, "a", mock_a, raising=False)
        monkeypatch.setattr(AssetValidator, "b", mock_b, raising=False)

        initial_errors = validator.errors[:]
        result = validator.validate()
        assert result == None
        # Check some expected initial errors
        mock_x.assert_called_once_with()
        mock_y.assert_called_once_with()
        mock_a.assert_called_once_with()
        mock_b.assert_called_once_with()

    @pytest.mark.parametrize("check_to_fail, is_error", [("x", True), ("y", True), ("a", False), ("b", False)])
    def test_some_check_fails(self, monkeypatch: pytest.MonkeyPatch, check_to_fail, is_error):
        """Verify that validate() returns the current errors list populated by __init__."""
        mock_asset = MagicMock(spec=Asset)
        validator = AssetValidator(mock_asset)

        errors = ["x", "y"]
        warns = ["a", "b"]

        validator.errors = errors
        validator.warns = warns

        if check_to_fail == "x":
            mock_x = MagicMock(side_effect=AssetException("x-error", severity="ERROR"))
        else:
            mock_x = MagicMock()

        if check_to_fail == "y":
            mock_y = MagicMock(side_effect=AssetException("y-error", severity="ERROR"))
        else:
            mock_y = MagicMock()

        if check_to_fail == "a":
            mock_a = MagicMock(side_effect=AssetException("a-error", severity="WARNING"))
        else:
            mock_a = MagicMock()

        if check_to_fail == "b":
            mock_b = MagicMock(side_effect=AssetException("b-error", severity="WARNING"))
        else:
            mock_b = MagicMock()

        monkeypatch.setattr(AssetValidator, "errors", errors)
        monkeypatch.setattr(AssetValidator, "warns", warns)
        monkeypatch.setattr(AssetValidator, "x", mock_x, raising=False)
        monkeypatch.setattr(AssetValidator, "y", mock_y, raising=False)
        monkeypatch.setattr(AssetValidator, "a", mock_a, raising=False)
        monkeypatch.setattr(AssetValidator, "b", mock_b, raising=False)

        with pytest.raises(AssetException, match=f"{check_to_fail}-error") as e:
            validator.validate()
            assert e.severity == "ERROR" if is_error else "WARNING"


@patch("breathecode.registry.utils.Github.__init__", MagicMock(return_value=None))  # Mock Github service
@patch.object(AssetValidator, "__init__", mocked_validator_init)
@pytest.mark.usefixtures("mock_error")
class TestReadmeUrl:
    """Tests for the AssetValidator.readme_url method (isolated from __init__ checks)."""

    def test_readme_url_valid(self, monkeypatch):
        """Test readme_url validation passes when URL is valid and owner/credentials exist."""
        mock_creds = MagicMock()
        mock_filter = MagicMock()
        mock_filter.return_value.first.return_value = mock_creds
        monkeypatch.setattr("breathecode.authenticate.models.CredentialsGithub.objects.filter", mock_filter)

        mock_file_exists = MagicMock(return_value=True)
        monkeypatch.setattr("breathecode.services.github.Github.file_exists", mock_file_exists)

        mock_asset = MagicMock(
            spec=Asset, readme_url="https://github.com/org/repo/blob/main/README.md", owner=MagicMock(id=1)
        )
        validator = AssetValidator(mock_asset)
        # Expect no exceptions and no errors added
        res = validator.readme_url()
        assert res is None
        AssetValidator.error.assert_not_called()

    def test_readme_url__with_missing_owner(self, monkeypatch):
        """Test readme_url calls AssetValidator.error when asset.owner is None."""
        mock_creds = MagicMock()
        mock_filter = MagicMock()
        mock_filter.return_value.first.return_value = mock_creds
        monkeypatch.setattr("breathecode.authenticate.models.CredentialsGithub.objects.filter", mock_filter)

        mock_asset = MagicMock(spec=Asset, readme_url=None, owner=MagicMock(id=1))
        mock_asset.owner = None

        validator = AssetValidator(mock_asset)
        with pytest.raises(Exception, match="stop"):
            validator.readme_url()

        AssetValidator.error.assert_called_once_with(
            "invalid-owner", "Asset must have an owner and the owner must have write access to the readme file"
        )

    def test_readme_url__with_missing_credentials(self, monkeypatch):
        """Test readme_url calls AssetValidator.error when Github credentials are not found."""
        mock_filter = MagicMock()
        mock_filter.return_value.first.return_value = None
        monkeypatch.setattr("breathecode.authenticate.models.CredentialsGithub.objects.filter", mock_filter)

        mock_asset = MagicMock(spec=Asset, readme_url="", owner=MagicMock(id=1))

        mock_file_exists = MagicMock(return_value=True)
        monkeypatch.setattr("breathecode.services.github.Github.file_exists", mock_file_exists)

        validator = AssetValidator(mock_asset)
        with pytest.raises(Exception, match="stop"):
            validator.readme_url()

        AssetValidator.error.assert_called_once_with(
            "invalid-owner", "Github credentials for asset owner were not found"
        )

    def test_readme_url__with_missing_credentials_and_owner_(self, monkeypatch):
        """Test readme_url raises error when file doesn't exist."""

        url = "https://github.com/org/repo/blob/main/README.md"

        mock_filter = MagicMock()
        mock_filter.return_value.first.return_value = MagicMock(spec=CredentialsGithub, token="123")
        monkeypatch.setattr("breathecode.authenticate.models.CredentialsGithub.objects.filter", mock_filter)

        mock_file_exists = MagicMock(return_value=False)
        monkeypatch.setattr("breathecode.services.github.Github.file_exists", mock_file_exists)

        mock_asset = MagicMock(spec=Asset, readme_url=url, owner=MagicMock(id=1))

        validator = AssetValidator(mock_asset)
        with pytest.raises(Exception, match="stop"):
            validator.readme_url()

        AssetValidator.error.assert_called_once_with("invalid-readme-url", "Readme URL points to a missing file")
        mock_file_exists.assert_called_once_with(mock_asset.readme_url)

    def test_readme_url_empty__passes_validation(self, monkeypatch):
        """Test that an empty readme_url passes the initial validation checks without error."""

        url = "https://github.com/org/repo/blob/main/README.md"

        mock_filter = MagicMock()
        mock_filter.return_value.first.return_value = MagicMock(spec=CredentialsGithub, token="123")
        monkeypatch.setattr("breathecode.authenticate.models.CredentialsGithub.objects.filter", mock_filter)

        mock_file_exists = MagicMock(return_value=True)
        monkeypatch.setattr("breathecode.services.github.Github.file_exists", mock_file_exists)

        mock_asset = MagicMock(spec=Asset, readme_url=url, owner=MagicMock(id=1))

        validator = AssetValidator(mock_asset)
        res = validator.readme_url()
        assert res is None

        AssetValidator.error.assert_not_called()
        mock_file_exists.assert_called_once_with(mock_asset.readme_url)


class TestUrls:
    """Tests for the AssetValidator.urls method, validating URLs extracted from README."""

    # Parametrized tests for AssetValidator.urls method
    # Parameters: (test_id, readme_return, get_urls_return, test_url_side_effect, expect_exception, expected_test_url_calls)
    urls_test_cases = [
        (
            "no_html_key",
            {"content": "no html here"},  # get_readme returns no 'html' key
            None,  # get_urls_from_html won't be called
            None,  # test_url won't be called
            False,  # No exception expected from urls() method itself
            0,  # test_url should not be called
        ),
        (
            "html_key_empty_urls",
            {"html": "<p>Some html</p>"},  # get_readme returns 'html' key
            [],  # get_urls_from_html returns empty list
            None,  # test_url won't be called
            False,  # No exception expected
            0,  # test_url should not be called
        ),
        (
            "valid_urls_in_html",
            {"html": '<a href="good.com"></a> <img src="ok.png"/>'},  # get_readme returns 'html'
            ["good.com", "ok.png"],  # get_urls_from_html returns these
            [True, True],  # Mock test_url to return True for each call (no exception)
            False,  # No exception expected
            2,  # test_url should be called twice
        ),
        (
            "invalid_url_in_html",
            {"html": '<a href="bad_url"></a>'},  # get_readme returns 'html'
            ["bad_url"],  # get_urls_from_html returns this
            Exception("Bad URL detected"),  # Mock test_url to raise an Exception
            True,  # Expect an exception to propagate from test_url
            1,  # test_url should be called once before exception
        ),
    ]

    @pytest.mark.parametrize(
        "test_id, readme_return, get_urls_return, test_url_side_effect, expect_exception, expected_test_url_calls",
        urls_test_cases,
        ids=[t[0] for t in urls_test_cases],  # Use test_id for better reporting
    )
    @patch("breathecode.registry.utils.get_urls_from_html")
    @patch("breathecode.registry.utils.test_url")
    def test_urls_validates_urls_from_readme(
        self,
        mock_test_url,
        mock_get_urls,
        test_id,  # keep this for readability in console
        readme_return,
        get_urls_return,
        test_url_side_effect,
        expect_exception,
        expected_test_url_calls,
    ):
        """Test AssetValidator.urls method validates URLs extracted from readme HTML."""
        # Arrange
        mock_asset = MagicMock(spec=Asset)
        mock_asset.get_readme.return_value = readme_return
        mock_get_urls.return_value = get_urls_return
        mock_test_url.side_effect = test_url_side_effect

        validator = AssetValidator(mock_asset)

        # Act & Assert
        if expect_exception:
            with pytest.raises(Exception) as exc_info:
                validator.urls()
            # If test_url raised exception, assert it's the expected one
            if isinstance(test_url_side_effect, Exception):
                assert str(exc_info.value) == str(test_url_side_effect)
        else:
            validator.urls()  # Should not raise exception

        mock_asset.get_readme.assert_called_once_with(parse=True)

        # Assert calls to dependencies
        if "html" in readme_return:
            mock_get_urls.assert_called_once_with(readme_return["html"])
            assert mock_test_url.call_count == expected_test_url_calls
            if expected_test_url_calls > 0:
                # Check that test_url was called with the urls returned by get_urls_from_html
                assert mock_test_url.call_args_list == [
                    call(x, allow_relative=False) for x in get_urls_return[:expected_test_url_calls]
                ]

        else:
            mock_get_urls.assert_not_called()
            mock_test_url.assert_not_called()


@patch.object(AssetValidator, "__init__", mocked_validator_init)
@pytest.mark.usefixtures("mock_error")
class TestLang:
    """Tests for the AssetValidator.lang method (isolated from __init__ checks)."""

    def test_lang_present(self):
        """Test lang() does not call error when language is present."""
        mock_asset = MagicMock(spec=Asset, lang="en")
        validator = AssetValidator(mock_asset)
        validator.lang()
        # Assert error was not called for the valid case
        AssetValidator.error.assert_not_called()

    def test_lang_missing(self):
        """Test lang() calls error with correct message when language is None."""
        mock_asset = MagicMock(spec=Asset, lang=None)
        validator = AssetValidator(mock_asset)
        # Calling lang() should trigger the mocked error
        with pytest.raises(Exception, match="stop"):
            validator.lang()
        # Assert that the original error method was called correctly before the mock intercepted
        AssetValidator.error.assert_called_once_with(
            AssetErrorLogType.INVALID_LANGUAGE, "Asset is missing a language or has an invalid language assigned"
        )

    def test_lang_empty_string(self):
        """Test lang() calls error with correct message when language is an empty string."""
        mock_asset = MagicMock(spec=Asset, lang="")
        validator = AssetValidator(mock_asset)
        # Calling lang() should trigger the mocked error
        with pytest.raises(Exception, match="stop"):
            validator.lang()
        # Assert that the original error method was called correctly before the mock intercepted
        AssetValidator.error.assert_called_once_with(
            AssetErrorLogType.INVALID_LANGUAGE, "Asset is missing a language or has an invalid language assigned"
        )


@patch.object(AssetValidator, "__init__", mocked_validator_init)
class TestTranslations:
    """Tests for the AssetValidator.translations method (isolated from __init__ checks)."""

    def test_translations_present(self):
        mock_asset = MagicMock(spec=Asset)
        mock_asset.all_translations.exists.return_value = True
        validator = AssetValidator(mock_asset)
        validator.translations()

    def test_translations_missing(self):
        mock_asset = MagicMock(spec=Asset)
        mock_asset.all_translations.exists.return_value = False
        validator = AssetValidator(mock_asset)
        with pytest.raises(Exception, match="No translations"):
            validator.translations()


@patch.object(AssetValidator, "__init__", mocked_validator_init)
class TestTechnologies:
    """Tests for the AssetValidator.technologies method (isolated from __init__ checks)."""

    def test_technologies_present_enough(self):
        """Test technologies() does not raise an exception when enough technologies are present."""
        mock_asset = MagicMock(spec=Asset)
        mock_asset.technologies.count.return_value = 2
        validator = AssetValidator(mock_asset)
        try:
            validator.technologies()
        except Exception as e:
            pytest.fail(f"technologies() raised an unexpected exception: {e}")

    # Combined test for insufficient technologies
    @pytest.mark.parametrize("tech_count", [1, 0], ids=["one_technology", "zero_technologies"])
    def test_technologies_raises_exception_when_insufficient(self, tech_count):
        """Test technologies() raises correct exception when technology count is less than 2."""
        mock_asset = MagicMock(spec=Asset)
        mock_asset.technologies.count.return_value = tech_count  # Use parametrized value
        validator = AssetValidator(mock_asset)
        # Check for the specific exception raised by the method
        with pytest.raises(Exception, match="Asset should have at least 2 technology tags"):
            validator.technologies()


@patch.object(AssetValidator, "__init__", mocked_validator_init)
class TestDifficulty:
    """Tests for the AssetValidator.difficulty method (isolated from __init__ checks)."""

    def test_difficulty_present(self):
        """Test difficulty() does not raise an exception when difficulty is present."""
        mock_asset = MagicMock(spec=Asset, difficulty="Easy")
        validator = AssetValidator(mock_asset)
        try:
            validator.difficulty()  # Base method only checks existence
        except Exception as e:
            pytest.fail(f"difficulty() raised an unexpected exception: {e}")

    # Combined test for missing or empty difficulty
    @pytest.mark.parametrize("difficulty_value", [None, ""], ids=["difficulty_none", "difficulty_empty"])
    def test_difficulty_raises_exception_when_missing_or_empty(self, difficulty_value):
        """Test difficulty() raises correct exception when difficulty is None or empty string."""
        mock_asset = MagicMock(spec=Asset, difficulty=difficulty_value)
        validator = AssetValidator(mock_asset)
        with pytest.raises(Exception, match="No difficulty"):
            validator.difficulty()


@patch.object(AssetValidator, "__init__", mocked_validator_init)
@pytest.mark.usefixtures("mock_error")
class TestDescription:
    """Tests for the AssetValidator.description method (isolated from __init__ checks)."""

    def test_description_present_long_enough(self):
        """Test description() does not call error when description is long enough."""
        # Create a description longer than 100 characters
        long_description = "a" * 101
        mock_asset = MagicMock(spec=Asset, description=long_description)
        validator = AssetValidator(mock_asset)
        validator.description()
        AssetValidator.error.assert_not_called()

    # Combine tests for invalid descriptions
    @pytest.mark.parametrize(
        "description_value, test_id",
        [("Too short", "too_short"), (None, "missing"), ("", "empty_string")],
        ids=["too_short", "missing", "empty_string"],
    )
    def test_description_invalid_raises_error(self, description_value, test_id):
        """Test description() calls error when description is missing, empty, or too short."""
        mock_asset = MagicMock(spec=Asset, description=description_value)
        validator = AssetValidator(mock_asset)
        # Catch the exception from the mock_error fixture
        with pytest.raises(Exception, match="stop"):
            validator.description()
        # Assert that the original error method was called correctly
        AssetValidator.error.assert_called_once_with(
            AssetErrorLogType.POOR_DESCRIPTION, "Description is too small or empty"
        )


@patch.object(AssetValidator, "__init__", mocked_validator_init)
# No mock_error fixture needed as the method is currently a no-op
class TestPreview:
    """Tests for the AssetValidator.preview method (isolated from __init__ checks)."""

    @pytest.mark.parametrize(
        "preview_value",
        [None, "", "https://example.com/preview.jpg", "invalid-url"],
        ids=["preview_none", "preview_empty", "preview_valid", "preview_invalid"],
    )
    def test_preview_method_currently_no_op(self, preview_value):
        """Test that preview() currently does nothing and raises no errors due to being commented out."""
        mock_asset = MagicMock(spec=Asset, preview=preview_value)
        validator = AssetValidator(mock_asset)

        try:
            validator.preview()
        except Exception as e:
            pytest.fail(f"preview() raised an unexpected exception: {e}")


@patch.object(AssetValidator, "__init__", mocked_validator_init)
@pytest.mark.usefixtures("mock_error")
class TestReadme:
    """Tests for the AssetValidator.readme method (isolated from __init__ checks)."""

    # Combined test for valid cases
    @pytest.mark.parametrize(
        "readme_value, external_value, test_id",
        [
            ("Some markdown content", False, "present_internal"),
            ("", True, "empty_external"),
        ],
        ids=["present_internal", "empty_external"],
    )
    def test_readme_valid_cases_do_not_call_error(self, readme_value, external_value, test_id):
        """Test readme() does not call error for valid readme content or empty external assets."""
        mock_asset = MagicMock(spec=Asset, readme=readme_value, external=external_value)
        validator = AssetValidator(mock_asset)
        validator.readme()
        AssetValidator.error.assert_not_called()

    @pytest.mark.parametrize(
        "readme_value, external_value, test_id",
        [
            (None, False, "readme_none_external_false"),
            (None, True, "readme_none_external_true"),  # None takes precedence
            ("", False, "readme_empty_external_false"),
        ],
        ids=["readme_none_external_false", "readme_none_external_true", "readme_empty_external_false"],
    )
    def test_readme_invalid_raises_error(self, readme_value, external_value, test_id):
        """Test readme() calls error when readme is None, or empty and not external."""
        mock_asset = MagicMock(spec=Asset, readme=readme_value, external=external_value)
        validator = AssetValidator(mock_asset)
        # Catch the exception from the mock_error fixture
        with pytest.raises(Exception, match="stop"):
            validator.readme()
        # Assert that the original error method was called correctly
        AssetValidator.error.assert_called_once_with(AssetErrorLogType.EMPTY_README, "Asset is missing a readme file")


@patch.object(AssetValidator, "__init__", mocked_validator_init)
@pytest.mark.usefixtures("mock_error")
class TestCategory:
    """Tests for the AssetValidator.category method (isolated from __init__ checks)."""

    def test_category_present(self):
        """Test category() does not call error when category is present."""
        mock_category = MagicMock()
        mock_asset = MagicMock(spec=Asset, category=mock_category)
        validator = AssetValidator(mock_asset)
        validator.category()
        AssetValidator.error.assert_not_called()

    def test_category_missing(self):
        """Test category() calls error with correct message when category is None."""
        mock_asset = MagicMock(spec=Asset, category=None)
        validator = AssetValidator(mock_asset)
        # Catch the exception from the mock_error fixture
        with pytest.raises(Exception, match="stop"):
            validator.category()
        # Assert that the original error method was called correctly
        AssetValidator.error.assert_called_once_with(AssetErrorLogType.EMPTY_CATEGORY, "Asset is missing a category")


@patch.object(AssetValidator, "__init__", mocked_validator_init)
# Remove mock_error fixture usage
class TestImages:
    """Tests for the AssetValidator.images method (isolated from __init__ checks)."""

    # Parametrized test covering different image status scenarios
    @pytest.mark.parametrize(
        "image_statuses, expected_error_calls, test_id",
        [
            ([], 0, "no_images"),  # No images
            (["OK", "OK"], 0, "all_ok"),  # All images OK
            (["OK", "ERROR"], 1, "one_error"),  # One error
            (["PENDING", "OK", "FAILED"], 2, "two_errors"),  # Two errors
            (["ERROR", "ERROR"], 2, "all_error"),  # All error
        ],
        ids=["no_images", "all_ok", "one_error", "two_errors", "all_error"],
    )
    def test_images_validation_status(self, monkeypatch, image_statuses, expected_error_calls, test_id):
        """Test images() calls error based on image download_status."""
        # Arrange: Create mock images with specified statuses
        mock_images = [MagicMock(download_status=status) for status in image_statuses]
        mock_asset = MagicMock(spec=Asset)
        # Mock the .all() manager method to return the list of mock images
        mock_asset.images.all.return_value = mock_images

        # Arrange: Mock AssetValidator.error locally WITHOUT exception side effect
        mock_error_method = MagicMock()
        monkeypatch.setattr(AssetValidator, "error", mock_error_method)

        validator = AssetValidator(mock_asset)

        # Act: Call the method (no exception expected from mock)
        validator.images()

        # Assert: Check the call count on the locally mocked error method
        assert mock_error_method.call_count == expected_error_calls

        # Assert: Check arguments if errors were expected
        if expected_error_calls > 0:
            mock_error_method.assert_any_call(
                AssetErrorLogType.INVALID_IMAGE,
                "Check the asset images, there seems to be images not properly downloaded",
            )
        else:
            # Explicitly check not called if 0 calls expected
            mock_error_method.assert_not_called()

    # Removed original test_images_present
    # Removed original test_images_missing
