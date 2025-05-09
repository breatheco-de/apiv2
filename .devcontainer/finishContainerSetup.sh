#!/usr/bin/env bash

# Check if Oh My Fish is installed by looking for its directory in the current user's $HOME
OMF_DIR="$HOME/.local/share/omf"

if [ ! -d "$OMF_DIR" ]; then
  echo "Oh My Fish not found in $OMF_DIR. Attempting installation..."
  # Check if fish shell is available
  if command -v fish &> /dev/null; then
    # Download and execute the Oh My Fish installer script using fish
    # curl: -s for silent (suppress progress meter), -L to follow redirects.
    # The OMF installer (get.oh-my.fish) is designed to be piped to fish
    # and handles non-interactive installation.
    # The exit status of the pipeline will be the exit status of the 'fish' command.
    if curl -sL https://get.oh-my.fish | fish; then
      # Verify installation by checking for the directory again
      if [ -d "$OMF_DIR" ]; then
        echo "Oh My Fish installed successfully to $OMF_DIR."
      else
        # This case might occur if 'fish' exited successfully but OMF was not installed as expected.
        echo "Oh My Fish installation command ran, but $OMF_DIR was not found. Please check for errors." >&2
      fi
    else
      # This case occurs if the 'fish' command itself (running the installer) fails.
      echo "Oh My Fish installation script failed to execute properly." >&2
    fi
  else
    echo "Error: 'fish' command not found. Cannot install Oh My Fish." >&2
  fi
else
  echo "Oh My Fish is already installed in $OMF_DIR."
fi
