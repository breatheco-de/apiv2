from rest_framework.serializers import *  # noqa: F401 F405
from rest_framework.serializers import ModelSerializer


class ModelSerializer(ModelSerializer):
    status_fields = []

    def __init__(self, *args, **kwargs):
        has_data = "data" in kwargs

        if has_data and isinstance(kwargs["data"], list):
            kwargs["data"] = [self._format_values(x) for x in kwargs["data"]]

        elif has_data and isinstance(kwargs["data"], dict):
            kwargs["data"] = self._format_values(kwargs["data"])

        super().__init__(*args, **kwargs)

    def _format_values(self, data):
        for attr in self.status_fields:
            try:
                if data[attr] and isinstance(data[attr], str):
                    data[attr] = data[attr].upper()
            except Exception:
                ...

        return data
