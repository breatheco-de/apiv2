"""
Requests mock
"""

import os, json

HOST = os.environ.get("OLD_BREATHECODE_API")

with open(f"{os.getcwd()}/breathecode/admissions/fixtures/legacy_teachers.json", "r") as file:
    legacy_teachers = json.load(file)

with open(f"{os.getcwd()}/breathecode/admissions/fixtures/legacy_students.json", "r") as file:
    legacy_students = json.load(file)


class ResponseMock:
    """Simutate Response to be used by mocks"""

    status_code = None
    data = None
    content = None

    def __init__(self, status_code=200, data=""):
        self.status_code = status_code

        if isinstance(data, str):
            self.content = data
        else:
            self.data = data

    def json(self) -> dict:
        """Convert Response to JSON"""
        return self.data


def get_mock(url: str, stream=False, timeout=30):
    """Requests get mock"""
    if url == f"{HOST}/students/" or url == f"{HOST}/students":
        return ResponseMock(data=legacy_students, status_code=200)
    elif url == f"{HOST}/teachers/" or url == f"{HOST}/teachers":
        return ResponseMock(data=legacy_teachers, status_code=200)
    return ResponseMock(data="error", status_code=404)
