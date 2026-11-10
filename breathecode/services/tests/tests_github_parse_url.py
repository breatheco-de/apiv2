from breathecode.services.github import Github


def test_parse_raw_url_classic_branch():
    parsed = Github().parse_github_url(
        "https://raw.githubusercontent.com/4GeeksAcademy/ai-engineering-syllabus/main/content/projects/edutrack-data-audit-sql/edutrack.sql"
    )

    assert parsed == {
        "owner": "4GeeksAcademy",
        "repo": "ai-engineering-syllabus",
        "branch": "main",
        "path": "content/projects/edutrack-data-audit-sql/edutrack.sql",
        "url_type": "raw",
        "is_file": True,
        "is_image": False,
        "ext": "sql",
    }


def test_parse_raw_url_refs_heads():
    parsed = Github().parse_github_url(
        "https://raw.githubusercontent.com/4GeeksAcademy/ai-engineering-syllabus/refs/heads/main/content/projects/edutrack-data-audit-sql/edutrack.sql"
    )

    assert parsed["branch"] == "main"
    assert parsed["path"] == "content/projects/edutrack-data-audit-sql/edutrack.sql"
    assert parsed["url_type"] == "raw"
    assert parsed["is_file"] is True
    assert parsed["ext"] == "sql"


def test_parse_raw_url_refs_tags():
    parsed = Github().parse_github_url(
        "https://raw.githubusercontent.com/4GeeksAcademy/ai-engineering-syllabus/refs/tags/v1.2.3/content/projects/edutrack-data-audit-sql/edutrack.sql"
    )

    assert parsed["branch"] == "v1.2.3"
    assert parsed["path"] == "content/projects/edutrack-data-audit-sql/edutrack.sql"
    assert parsed["url_type"] == "raw"


def test_parse_blob_url_refs_heads():
    parsed = Github().parse_github_url(
        "https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/refs/heads/main/content/projects/edutrack-data-audit-sql/edutrack.sql"
    )

    assert parsed["branch"] == "main"
    assert parsed["path"] == "content/projects/edutrack-data-audit-sql/edutrack.sql"
    assert parsed["url_type"] == "blob"
    assert parsed["is_file"] is True


def test_parse_blob_url_classic_branch():
    parsed = Github().parse_github_url(
        "https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/edutrack-data-audit-sql/README.md"
    )

    assert parsed["branch"] == "main"
    assert parsed["path"] == "content/projects/edutrack-data-audit-sql/README.md"
    assert parsed["url_type"] == "blob"
    assert parsed["ext"] == "md"
