"""
Headers mixin
"""

__all__ = ['HeadersMixin']


class HeadersMixin():
    """Headers mixin"""
    def headers(self, **kargs: str) -> None:
        """Set headers."""
        headers = {}

        items = [
            index for index in kargs
            if kargs[index] and (isinstance(kargs[index], str) or isinstance(kargs[index], int))
        ]

        for index in items:
            headers[f'HTTP_{index.upper()}'] = str(kargs[index])

        self.client.credentials(**headers)
