from typing import Optional

from breathecode.utils.api_view_extensions.extension_base import ExtensionBase

__all__ = ["LanguageExtension"]


class LanguageExtension(ExtensionBase):

    def __init__(self, **kwargs) -> None: ...

    def get(self) -> str | None:
        return self._request.META.get("HTTP_ACCEPT_LANGUAGE")

    def _can_modify_queryset(self) -> bool:
        return False

    def _can_modify_response(self) -> bool:
        return False

    def _instance_name(self) -> Optional[str]:
        return "language"
