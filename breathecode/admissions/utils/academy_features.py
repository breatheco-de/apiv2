"""
Utility functions to check academy feature flags from backend code.
"""

from typing import Optional
from breathecode.admissions.models import Academy


def has_feature_flag(academy: Optional[Academy], feature_key: str, default: bool = True) -> bool:
    """
    Check if an academy has a specific feature flag enabled.
    
    Args:
        academy: Academy instance or None
        feature_key: Key of the feature flag (e.g., 'verify_user_invite_email', 'allow_events')
        default: Default value if academy is None or flag doesn't exist
        
    Returns:
        bool: True if feature is enabled, False otherwise
        
    Examples:
        >>> academy = Academy.objects.get(id=1)
        >>> if has_feature_flag(academy, 'verify_user_invite_email'):
        ...     # Send verification email
        ...
        >>> # Works with None academy (returns default)
        >>> has_feature_flag(None, 'allow_events', default=True)
        True
    """
    if academy is None:
        return default
    
    features = academy.get_academy_features()

    # Prefer dot-notation paths, e.g. "commerce.reseller", "events.enabled".
    path = feature_key
    if isinstance(path, str) and "." in path:
        current = features
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]

        if isinstance(current, bool):
            return current
    
    # Check in navigation dict
    if feature_key in features.get("navigation", {}):
        return features["navigation"][feature_key]
    
    # Fallback to default if flag doesn't exist
    return default


def get_feature_flag(academy: Optional[Academy], feature_key: str, default=None):
    """
    Get the value of a feature flag (useful for non-boolean flags like custom_links).
    
    Args:
        academy: Academy instance or None
        feature_key: Key of the feature flag
        default: Default value if academy is None or flag doesn't exist
        
    Returns:
        The value of the feature flag (can be bool, list, dict, etc.)
        
    Examples:
        >>> academy = Academy.objects.get(id=1)
        >>> custom_links = get_feature_flag(academy, 'custom_links', default=[])
        >>> for link in custom_links:
        ...     print(link['url'])
    """
    if academy is None:
        return default
    
    features = academy.get_academy_features()

    # Prefer dot-notation paths, e.g. "commerce.reseller", "events.enabled", "navigation.custom_links".
    path = feature_key
    if isinstance(path, str) and "." in path:
        current = features
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]

        if current is not None:
            return current
    
    # Check in navigation dict
    if feature_key in features.get("navigation", {}):
        return features["navigation"][feature_key]
    
    # Fallback to default if flag doesn't exist
    return default

