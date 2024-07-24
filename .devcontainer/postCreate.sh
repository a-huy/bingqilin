#!/bin/bash

WORKSPACE_ROOT=/workspaces/bingqilin
DEVCONTAINER_DIR=$WORKSPACE_ROOT/.devcontainer

. .devcontainer/colors.sh
. .devcontainer/utils.sh

post_create_info "Setting up the bingqilin dev container"

sudo apt-get -y update
sudo apt-get -y upgrade

pip install --upgrade pip
pip install poetry
poetry config virtualenvs.in-project true

###
# Set up bingqilin dependencies
###
post_create_info "Setting up bingqilin dependencies"
poetry install --no-interaction --no-ansi

# Add the git bash completion script for convenience
curl -o ~/.git-completion.bash https://raw.githubusercontent.com/git/git/master/contrib/completion/git-completion.bash
echo "source ~/.git-completion.bash" >> ~/.bashrc

# Initialize an ipython profile if it doesn't exist
if [ ! -d ~/.ipython/profile_default ]; then
    post_create_info "Creating the default ipython profile"
    poetry run ipython profile create
fi

if test -f ./devcontainer/postCreate.sh; then
    . ./devcontainer/postCreate.sh
fi
