import inspect

from django.core.handlers.wsgi import WSGIRequest

import breathecode.utils.api_view_extensions.extensions as extensions

from .api_view_extension_handlers import APIViewExtensionHandlers

__all__ = ["APIViewExtensions"]

EXTENSIONS = [getattr(extensions, x) for x in dir(extensions) if inspect.isclass(getattr(extensions, x))]
LIMIT_QUERY_PARAM = "limit"
OFFSET_QUERY_PARAM = "offset"


class APIViewExtensions:
    """Django rest's view extensions."""

    _valid_extensions: list
    _kwargs: dict

    # autodetect the extension compatible with the arguments.
    def __init__(self, **kwargs) -> APIViewExtensionHandlers:

        self._valid_extensions = set()
        self._kwargs = kwargs

        for extension in EXTENSIONS:
            requirements = self._requirements(extension)
            num_requirements_found = 0

            for requirement in requirements:
                if requirement in kwargs:
                    num_requirements_found += 1

            if num_requirements_found == len(requirements):
                self._valid_extensions.add(extension)

    def __call__(self, request: WSGIRequest):
        """Get handler."""

        self.request = request
        return APIViewExtensionHandlers(request, self._valid_extensions, **self._kwargs)

    def _requirements(self, extension):
        """Get requirements of the extension."""

        return [
            x
            for x in dict(inspect.signature(extension.__init__).parameters)
            if x != "self" and x != "args" and x != "kwargs" and x != "request"
        ]
