#!/bin/env python

from __future__ import absolute_import
import os
import random
import sys
import argparse
import subprocess


def parse_arguments():
    parser = argparse.ArgumentParser(description="Run pytest with optional seed.")
    parser.add_argument("--seed", type=int, help="Seed for randomness")
    parser.add_argument("pytest_args", nargs="*", help="Arguments to pass to pytest")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    if args.seed is None:
        seed = random.randint(0, 4294967295)
    else:
        seed = args.seed

    pytest_args = " ".join(args.pytest_args)
    command = f"pytest {pytest_args} --disable-pytest-warnings -n auto --durations=1"

    env = os.environ.copy()
    env["ENV"] = "test"
    env["RANDOM_SEED"] = str(seed)

    exit_code = subprocess.run(command, env=env, shell=True).returncode

    print()
    print(f"Seed {seed} used, you can provide it locally to reproduce random errors")

    # python doesn't return 256
    if exit_code:
        sys.exit(1)
