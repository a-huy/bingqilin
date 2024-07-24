#!/bin/bash

. .devcontainer/colors.sh

WORKSPACE_ROOT=`pwd`
DEVCONTAINER_DIR=$WORKSPACE_ROOT/.devcontainer

post_create_abort () {
    # First arg is abort message
    echo -e "${RED}!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!${COLOROFF}"
    echo -e "${RED}Handoffs dev container setup could not be completed:${COLOROFF}"
    echo -e "${YELLOW}$1${COLOROFF}"
    echo -e "${RED}Aborting.${COLOROFF}"
    echo -e "${RED}!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!${COLOROFF}"
}

post_create_info () {
    # First arg is info message
    echo -e "${CYAN}##################################################${COLOROFF}"
    echo -e "${CYAN}$1${COLOROFF}"
    echo -e "${CYAN}##################################################${COLOROFF}"
}

post_create_log_info () {
    # First arg is log message
    echo -e "* ${CYAN}$1${COLOROFF} *"
}
