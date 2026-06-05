from breathecode.admissions.models import default_academy_features


def test_default_academy_features_include_public_portal_disabled_by_default():
    features = default_academy_features()

    assert features["public_portal"] == {
        "enabled": False,
        "lessons": {"enabled": False},
        "interactive_exercises": {"enabled": False},
        "interactive_coding_tutorials": {"enabled": False},
        "technology": {"enabled": False},
    }
