from rest_framework import HTTP_HEADER_ENCODING

__all__ = ['header_parser']


def header_parser(headers: list[tuple[bytes, bytes]], allowed=[]):
    result = {}

    if allowed:
        keys = [key[0] for key in headers if key[0].decode(HTTP_HEADER_ENCODING) in allowed]

    else:
        keys = [key[0] for key in headers]

    for header in headers:
        if header[0] in keys:
            key = header[0]
            value = header[1]

            if isinstance(key, bytes):
                key = key.decode(HTTP_HEADER_ENCODING)

            if isinstance(value, bytes):
                value = value.decode(HTTP_HEADER_ENCODING)

            result[key] = value

    return result
