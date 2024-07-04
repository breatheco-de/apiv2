import math

__all__ = ["ICallMixin"]


class ICallMixin:

    def line_limit(self, line: str):
        linebreak = "\r\n"
        max_length = 74
        max_chars_in_line_two = max_length - 1
        side = math.ceil(len(line) / 74)

        parts = []

        for index in range(0, side):
            is_first = index == 0
            offset_in_start = 0 if is_first else 1
            start = (index * max_chars_in_line_two) + offset_in_start
            end = ((index + 1) * max_chars_in_line_two) + 1
            parts.append(line[start:end] if is_first else " " + line[start:end])

        return linebreak.join(parts)
