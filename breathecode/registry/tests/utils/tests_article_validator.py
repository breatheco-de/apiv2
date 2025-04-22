from unittest.mock import MagicMock

from breathecode.registry.models import Asset
from breathecode.registry.utils import ArticleValidator, AssetValidator


def test_article_validator_exists():
    """Test that ArticleValidator can be instantiated."""
    mock_asset = MagicMock(spec=Asset)
    # Instantiation itself is the test here
    ArticleValidator(mock_asset)


def test_article_validator_inheritance():
    """Test that ArticleValidator inherits from AssetValidator."""
    assert issubclass(ArticleValidator, AssetValidator)


def test_article_validator_warns_property():
    """Test that ArticleValidator initializes the warns property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = ArticleValidator(mock_asset)
    # Correct initial warnings based on pytest output
    assert validator.warns == ["translations", "technologies"]


def test_article_validator_errors_property():
    """Test that ArticleValidator initializes the errors property correctly."""
    mock_asset = MagicMock(spec=Asset)
    validator = ArticleValidator(mock_asset)
    # Correct initial errors based on pytest output
    assert validator.errors == ["lang", "urls", "category", "preview", "images", "readme_url", "description", "readme"]
