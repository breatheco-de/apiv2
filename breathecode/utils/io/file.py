from io import StringIO, BytesIO, BufferedReader, TextIOWrapper
import logging
import os
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from typing import Optional, overload

__all__ = ["cut_csv", "count_csv_rows", "count_file_lines"]

logger = logging.getLogger(__name__)


@overload
def _cut_csv(f: StringIO | TextIOWrapper, *, start: int, end: int) -> StringIO: ...


@overload
def _cut_csv(f: BytesIO | BufferedReader | InMemoryUploadedFile, *, start: int, end: int) -> BytesIO: ...


def _cut_csv(
    f: StringIO | BytesIO | BufferedReader | TextIOWrapper | InMemoryUploadedFile, *, start: int, end: int
) -> StringIO | BytesIO:
    """Cut a csv file from start to end line ignoring the header in the row count."""

    f.seek(0)

    if isinstance(f, StringIO) or isinstance(f, TextIOWrapper):
        res = StringIO()

    elif (
        isinstance(f, BytesIO)
        or isinstance(f, BufferedReader)
        or isinstance(f, InMemoryUploadedFile)
        or isinstance(f, TemporaryUploadedFile)
    ):
        res = BytesIO()

    if isinstance(f, InMemoryUploadedFile):
        f = f.file

    if isinstance(f, TemporaryUploadedFile):
        f = f.file.file

    header = f.readline()

    res.write(header)

    for _ in range(start):
        next(f)

    try:
        for _ in range(end - start):
            res.write(next(f))

    except StopIteration:
        pass

    res.seek(0)

    return res


@overload
def _first_lines_of_csv(f: StringIO | TextIOWrapper, *, last: int) -> StringIO: ...


@overload
def _first_lines_of_csv(f: BytesIO | BufferedReader | InMemoryUploadedFile, *, last: int) -> BytesIO: ...


def _first_lines_of_csv(f: StringIO | BytesIO | BufferedReader | TextIOWrapper, *, first: int) -> StringIO | BytesIO:

    f.seek(0)

    if isinstance(f, StringIO) or isinstance(f, TextIOWrapper):
        res = StringIO()

    elif (
        isinstance(f, BytesIO)
        or isinstance(f, BufferedReader)
        or isinstance(f, InMemoryUploadedFile)
        or isinstance(f, TemporaryUploadedFile)
    ):
        res = BytesIO()

    if isinstance(f, InMemoryUploadedFile):
        f = f.file

    if isinstance(f, TemporaryUploadedFile):
        f = f.file.file

    header = f.readline()

    res.write(header)

    try:
        for _ in range(first):
            res.write(next(f))

    except StopIteration:
        pass

    res.seek(0)

    return res


@overload
def _last_lines_of_csv(f: StringIO | TextIOWrapper, *, last: int) -> StringIO: ...


@overload
def _last_lines_of_csv(f: BytesIO | BufferedReader | InMemoryUploadedFile, *, last: int) -> BytesIO: ...


def _last_lines_of_csv(f: StringIO | BytesIO | BufferedReader | TextIOWrapper, *, last: int) -> StringIO | BytesIO:

    if isinstance(f, StringIO) or isinstance(f, TextIOWrapper):
        res = StringIO()
        line = ""

    elif (
        isinstance(f, BytesIO)
        or isinstance(f, BufferedReader)
        or isinstance(f, InMemoryUploadedFile)
        or isinstance(f, TemporaryUploadedFile)
    ):
        res = BytesIO()
        line = b""

    if isinstance(f, InMemoryUploadedFile):
        f = f.file

    if isinstance(f, TemporaryUploadedFile):
        f = f.file.file

    f.seek(0)
    header = f.readline()
    res.write(header)

    f.seek(0, os.SEEK_END)

    position = f.tell()
    lines = []

    n = 0
    while position >= 0:
        f.seek(position)
        next_char = f.read(1)
        if next_char == "\n":
            if line != "":
                lines.append(line[::-1])

            line = ""

        if next_char == b"\n":
            if line != b"":
                lines.append(line[::-1])

            line = b""

        else:
            line += next_char

        position -= 1
        n += 1

        if last and len(lines) == last:
            break

    for line in reversed(lines):
        res.write(line)

        if isinstance(line, bytes):
            res.write(b"\r\n")

        else:
            res.write("\r\n")

    res.seek(0)

    return res


@overload
def cut_csv(f: StringIO | TextIOWrapper, *, start: int, end: int) -> StringIO: ...


@overload
def cut_csv(f: BytesIO | BufferedReader | InMemoryUploadedFile, *, start: int, end: int) -> BytesIO: ...


@overload
def cut_csv(f: StringIO | TextIOWrapper, *, first: int) -> StringIO: ...


@overload
def cut_csv(f: BytesIO | BufferedReader | InMemoryUploadedFile, *, first: int) -> BytesIO: ...


@overload
def cut_csv(f: StringIO | TextIOWrapper, *, last: int) -> StringIO: ...


@overload
def cut_csv(f: BytesIO | BufferedReader | InMemoryUploadedFile, *, last: int) -> BytesIO: ...


def cut_csv(
    f: StringIO | BytesIO | BufferedReader | TextIOWrapper | InMemoryUploadedFile,
    *,
    start: Optional[int] = None,
    end: Optional[int] = None,
    first: Optional[int] = None,
    last: Optional[int] = None
) -> StringIO | BytesIO:
    """Cut a csv file."""

    if isinstance(start, int) and isinstance(end, int) and isinstance(last, int):
        raise Exception("You cannot use start/end and last at the same time")

    if isinstance(first, int) and isinstance(end, int) and isinstance(first, int):
        raise Exception("You cannot use first/end and first at the same time")

    if isinstance(first, int) and isinstance(last, int):
        raise Exception("You cannot use first and last at the same time")

    if isinstance(start, int) and isinstance(end, int):
        return _cut_csv(f, start=start, end=end)

    elif isinstance(last, int):
        return _last_lines_of_csv(f, last=last)

    else:
        return _first_lines_of_csv(f, first=first)


def count_file_lines(f: StringIO | BytesIO | BufferedReader | TextIOWrapper | InMemoryUploadedFile) -> int:
    if isinstance(f, InMemoryUploadedFile):
        f = f.file

    if isinstance(f, TemporaryUploadedFile):
        f = f.file.file

    f.seek(0)

    n = 0

    try:
        while True:
            next(f)
            n += 1

    except StopIteration:
        pass

    f.seek(0)

    return n


def count_csv_rows(f: StringIO | BytesIO | BufferedReader | TextIOWrapper | InMemoryUploadedFile) -> int:
    return count_file_lines(f) - 1
