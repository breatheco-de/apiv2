from rest_framework.schemas.openapi import AutoSchema


class GlobalSchema(AutoSchema):

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        operation["parameters"].append(
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Token",
                "schema": {"type": "string"},
            }
        )
        return operation


class MediaSchema(GlobalSchema):

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        operation["parameters"].append(
            {
                "name": "Academy",
                "in": "header",
                "required": True,
                "description": "What foo does...",
                "schema": {"type": "string"},
            }
        )
        return operation


class FileSchema(AutoSchema):

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        operation["parameters"].append(
            {
                "name": "width",
                "in": "query",
                "required": False,
                "description": "Width of image",
                "schema": {"type": "integer"},
            }
        )
        operation["parameters"].append(
            {
                "name": "height",
                "in": "query",
                "required": False,
                "description": "Height of image",
                "schema": {"type": "integer"},
            }
        )
        return operation
