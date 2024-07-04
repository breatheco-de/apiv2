#!/bin/env python

import os
from shutil import which
import subprocess

if which("pg_config"):
    exit()

if not which("uname"):
    exit(
        "Auto installation of pg_config in windows is not implemented yet, try install PostgreSQL "
        "and add C:\\Program Files\\PostgreSQL\\12\\bin to the PATH"
    )

output = subprocess.check_output(["cat", "/etc/os-release"]).decode()
pending = True

ARCH_BASE = ["Arch Linux", "Manjaro Linux"]
REDHAT_BASE = ["Red Hat Enterprise Linux", "Fedora Linux", "CentOS Linux"]
SUSE_BASE = ["SLES", "openSUSE"]
DEBIAN_BASE = ["Debian GNU/Linux", "Ubuntu"]


# notify the command will be executed
def system(command):
    print(command)
    return os.system(command)


if pending:
    for name in DEBIAN_BASE:
        if f'NAME="{name}"' in output:
            system("sudo apt-get update")
            system("sudo apt-get install libpq-dev -y")
            pending = False

if pending:
    for name in ARCH_BASE:
        if f'NAME="{name}"' in output:
            system("sudo pacman -S postgresql-libs --noconfirm")
            pending = False

if pending:
    for name in REDHAT_BASE:
        if f'NAME="{name}"' in output:
            system("sudo yum install libpq-devel -y")
            pending = False

if pending:
    for name in SUSE_BASE:
        if f'NAME="{name}' in output:
            system("sudo zypper --non-interactive in postgresql-server-devel")
            pending = False

# assuming this command is running in macos
if pending:
    if not which("brew"):
        exit("brew is not installed on this system")

    # I don't know which argument to bypass the prompt
    system("sudo brew install postgresql -y")
    pending = False
