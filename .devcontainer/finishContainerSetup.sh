#!/usr/bin/env bash

# This script is run once when the container is created.
# It's used to set up the environment, install dependencies, etc.

# Fix permissions for mounted volumes to avoid issues with user vscode
# These paths are derived from the "mounts" section in .devcontainer/ubuntu/devcontainer.json
# The remoteUser is "vscode".
echo "Updating ownership of mounted volumes for user vscode..."
sudo chown -R vscode:vscode /home/vscode/.local/share/fish || echo "Failed to chown /home/vscode/.local/share/fish, continuing..."
sudo chown -R vscode:vscode /home/vscode/.config/fish || echo "Failed to chown /home/vscode/.config/fish, continuing..."
sudo chown -R vscode:vscode /home/vscode/.cache/fish || echo "Failed to chown /home/vscode/.cache/fish, continuing..."
sudo chown -R vscode:vscode /home/vscode/.cache/pypoetry || echo "Failed to chown /home/vscode/.cache/pypoetry, continuing..."
sudo chown -R vscode:vscode /home/vscode/.local/share/pypoetry || echo "Failed to chown /home/vscode/.local/share/pypoetry, continuing..."
sudo chown -R vscode:vscode /home/vscode/.local/share/omf || echo "Failed to chown /home/vscode/.local/share/omf, continuing..."
sudo chown -R vscode:vscode /home/vscode/.config/omf || echo "Failed to chown /home/vscode/.config/omf, continuing..."
sudo chown -R vscode:vscode /home/vscode/.cache/pipx || echo "Failed to chown /home/vscode/.cache/pipx, continuing..."
sudo chown -R vscode:vscode /home/vscode/.cache/pip || echo "Failed to chown /home/vscode/.cache/pip, continuing..."
sudo chown -R vscode:vscode /home/vscode/.local/share/virtualenv || echo "Failed to chown /home/vscode/.local/share/virtualenv, continuing..."
sudo chown -R vscode:vscode /home/vscode/.cache/pre-commit || echo "Failed to chown /home/vscode/.cache/pre-commit, continuing..."
echo "Ownership update complete."

curl https://raw.githubusercontent.com/oh-my-fish/oh-my-fish/master/bin/install -o /tmp/install-omf.fish
fish /tmp/install-omf.fish --noninteractive -y
rm /tmp/install-omf.fish

fish -c "omf install fish-spec nvm foreign-env"
