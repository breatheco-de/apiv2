import sys
from unittest.mock import patch, MagicMock
from pre_commit.main import main

ENVIRONMENT_DIR = 'py_env'


def install_environment_mock():
    # from pre_commit.prefix import Prefix
    from pre_commit.languages import helpers
    from pre_commit.languages.python import norm_version
    from pre_commit.util import cmd_output_b

    def install_environment(
            prefix,
            version,
            additional_dependencies,
    ) -> None:
        envdir = prefix.path(helpers.environment_dir(ENVIRONMENT_DIR, version))
        venv_cmd = [sys.executable, '-mvirtualenv', envdir]
        python = norm_version(version)
        if python is not None:
            venv_cmd.extend(('-p', python))

        with clean_path_on_failure(envdir):
            cmd_output_b(*venv_cmd, cwd='/')

    return MagicMock(side_effect=install_environment)

if __name__ == '__main__':
    from pre_commit.languages import python
    with patch.object(python, 'install_environment', new=install_environment_mock()) as mock:
        exit(main())
