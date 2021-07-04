import os
from rest_framework.exceptions import APIException

IS_TEST_ENV = os.getenv('ENV') == 'test'


class ValidationException(APIException):
    status_code = 400
    default_detail = 'There is an error in your request'
    default_code = 'client_error'
    slug = None

    def __init__(self, details, code=400, slug=None):
        self.status_code = code
        self.default_detail = details
        self.slug = slug

        if IS_TEST_ENV and slug:
            super().__init__(slug)
        else:
            super().__init__(details)
