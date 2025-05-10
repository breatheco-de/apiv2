#!/usr/bin/env bash

TARGET_PYTHON_VERSION=$(cat ./.python-version)
# Check if the target python version is listed by 'poetry python list -m'.
# -q: quiet mode, suppresses output.
# -F: treat PATTERN as a fixed string.
# --: signifies the end of options, useful if $TARGET_PYTHON_VERSION could start with a hyphen.
if ! poetry python list -m | grep -qF -- "$TARGET_PYTHON_VERSION"; then
    # If grep returns a non-zero status (version not found), then install it.
    poetry python install "$TARGET_PYTHON_VERSION"
fi

poetry env use "$TARGET_PYTHON_VERSION"

python -m scripts.install
