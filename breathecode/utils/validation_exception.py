from rest_framework.exceptions import APIException

class ValidationException(APIException):
    status_code = 400
    default_detail = 'There is an error in your request'
    default_code = 'client_error'

    def __init__(self, details, code=400):
        self.status_code = code
        self.default_detail = details
        super().__init__(details)
