FROM gitpod/workspace-postgres

RUN sudo apt-get update \
    && sudo apt-get update \
    && sudo apt-get install -y redis-server \
    && sudo apt-get clean \
    && sudo rm -rf /var/cache/apt/* /var/lib/apt/lists/* /tmp/*

RUN pyenv update && pyenv install 3.10.5 && pyenv global 3.10.5
RUN pip install pdm yapf

# remove PIP_USER environment
USER gitpod
RUN if ! grep -q "export PIP_USER=no" "$HOME/.bashrc"; then printf '%s\n' "export PIP_USER=no" >> "$HOME/.bashrc"; fi
