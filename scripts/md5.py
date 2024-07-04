#!/bin/env python

from __future__ import absolute_import
import hashlib
import sys

if __name__ == "__main__":
    args = ""

    if len(sys.argv) <= 1:
        Exception("No arguments passed")

    with open(sys.argv[1], "rb") as f:
        content = f.read()

    hash = hashlib.md5(content).hexdigest()
    print(hash)
