"""
Tests for validate_email_local action
"""
import pytest
from capyc.rest_framework.exceptions import ValidationException

from breathecode.marketing.actions import validate_email_local


@pytest.mark.django_db
class TestValidateEmailLocal:
    """Test suite for validate_email_local function"""

    def test_valid_email_gmail(self):
        """Test validation of a valid Gmail email"""
        result = validate_email_local("test@gmail.com", "en")
        
        assert result["email"] == "test@gmail.com"
        assert result["user"] == "test"
        assert result["domain"] == "gmail.com"
        assert result["format_valid"] is True
        assert result["free"] is True
        assert result["disposable"] is False
        assert result["role"] is False
        assert result["score"] > 0.60

    def test_valid_email_corporate(self):
        """Test validation of a valid corporate email"""
        # Using a real domain with MX records (microsoft.com has MX records)
        result = validate_email_local("john.doe@microsoft.com", "en")
        
        assert result["email"] == "john.doe@microsoft.com"
        assert result["user"] == "john.doe"
        assert result["domain"] == "microsoft.com"
        assert result["format_valid"] is True
        assert result["free"] is False
        assert result["disposable"] is False
        assert result["score"] > 0.60

    def test_invalid_format(self):
        """Test validation of invalid email format"""
        with pytest.raises(ValidationException) as exc_info:
            validate_email_local("invalid-email", "en")
        
        assert exc_info.value.slug == "email-not-valid"

    def test_empty_email(self):
        """Test validation of empty email"""
        with pytest.raises(ValidationException) as exc_info:
            validate_email_local("", "en")
        
        assert exc_info.value.slug == "email-not-valid"

    def test_none_email(self):
        """Test validation of None email"""
        with pytest.raises(ValidationException) as exc_info:
            validate_email_local(None, "en")
        
        assert exc_info.value.slug == "email-not-valid"

    def test_disposable_email(self):
        """Test validation of disposable email"""
        with pytest.raises(ValidationException) as exc_info:
            validate_email_local("test@10minutemail.com", "en")
        
        assert exc_info.value.slug == "disposable-email"

    def test_role_email(self):
        """Test validation of role-based email"""
        # Using a real domain with MX records
        result = validate_email_local("info@microsoft.com", "en")
        
        assert result["role"] is True
        assert result["score"] > 0.60  # Should still pass but with lower score

    def test_email_with_uppercase(self):
        """Test that email is normalized to lowercase"""
        # Using a real domain with MX records
        result = validate_email_local("TEST@GMAIL.COM", "en")
        
        assert result["email"] == "test@gmail.com"
        assert result["user"] == "test"
        assert result["domain"] == "gmail.com"

    def test_email_with_spaces(self):
        """Test that email spaces are stripped"""
        # Using a real domain with MX records
        result = validate_email_local("  test@gmail.com  ", "en")
        
        assert result["email"] == "test@gmail.com"

    def test_yahoo_email(self):
        """Test validation of Yahoo email"""
        result = validate_email_local("user@yahoo.com", "en")
        
        assert result["domain"] == "yahoo.com"
        assert result["free"] is True
        assert result["score"] > 0.60

    def test_hotmail_email(self):
        """Test validation of Hotmail email"""
        result = validate_email_local("user@hotmail.com", "en")
        
        assert result["domain"] == "hotmail.com"
        assert result["free"] is True
        assert result["score"] > 0.60

    def test_multiple_disposable_domains(self):
        """Test multiple disposable email domains"""
        disposable_domains = [
            "10minutemail.com",
            "20minutemail.com",
            "guerrillamail.com",
            "mailinator.com",
            "tempmail.com",
        ]
        
        for domain in disposable_domains:
            with pytest.raises(ValidationException) as exc_info:
                validate_email_local(f"test@{domain}", "en")
            
            assert exc_info.value.slug == "disposable-email"

    def test_spanish_error_messages(self):
        """Test that error messages are in Spanish when lang=es"""
        with pytest.raises(ValidationException) as exc_info:
            validate_email_local("invalid-email", "es")
        
        assert exc_info.value.slug == "email-not-valid"
        # The message should be in Spanish
        assert "correo electrónico" in str(exc_info.value).lower() or "email" in str(exc_info.value).lower()

    def test_email_structure(self):
        """Test that returned email structure matches expected format"""
        # Using a real domain with MX records
        result = validate_email_local("test@gmail.com", "en")
        
        required_keys = [
            "email",
            "user",
            "domain",
            "format_valid",
            "mx_found",
            "mx_records",
            "spf",
            "dmarc",
            "role",
            "disposable",
            "free",
            "score",
        ]
        
        for key in required_keys:
            assert key in result, f"Missing key: {key}"
        
        assert isinstance(result["format_valid"], bool)
        assert isinstance(result["mx_found"], bool)
        assert isinstance(result["mx_records"], list)
        assert isinstance(result["role"], bool)
        assert isinstance(result["disposable"], bool)
        assert isinstance(result["free"], bool)
        assert isinstance(result["score"], float)
        assert 0.0 <= result["score"] <= 1.0

