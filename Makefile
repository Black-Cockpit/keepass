# --------------------------------------------------------------------------------------------------
# Makefile for the hasnimehdi91.keepass collection development workflow
# --------------------------------------------------------------------------------------------------
# Wraps the numbered development scripts behind stable snake_case targets.
# Every operational target depends on check_virtual_env so the Python
# virtual environment is provisioned on demand before any target runs.
# --------------------------------------------------------------------------------------------------

# Define the shell to be used for commands
SHELL := /bin/bash

# Targets that are not associated with files
.PHONY: \
    install_virtual_env \
    check_virtual_env \
    format_source_code

# Extract the name of the current Makefile
# Useful for debugging or referencing the Makefile itself
CURRENT_MK := $(lastword $(MAKEFILE_LIST))

# --------------------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------------------

# Virtual environment directory name
# Notes:
#   - (Re)created by install_virtual_env and used by all subsequent targets.
#   - Unquoted on purpose: a quoted value embeds the quotes in the path and
#     breaks the existence check in check_virtual_env.
VIRTUAL_ENV_DIR := ops.venv

# Directory context for the project
# Notes:
#   - All relative paths are resolved from this root path.
#   - If running make from another directory, adjust accordingly.
CONF_DIR_CONTEXT := .

# Python version used to build the virtual environment
PYTHON_VERSION_12 := python3.12

# --------------------------------------------------------------------------------------------------
# Target: install_virtual_env
# --------------------------------------------------------------------------------------------------
# Purpose
#   Rebuilds the Python virtual environment from scratch and installs all
#   pip packages the collection is developed and tested with.
#
# Behavior
#   - Exports PYTHON_VERSION and delegates to the bootstrap script.
#
# Idempotency
#   - Destructive by design: the existing virtual environment is removed and
#     rebuilt on every invocation.
#
# Dependencies
#   - None (this is the bootstrap entry point).
install_virtual_env:
	@export PYTHON_VERSION=${PYTHON_VERSION_12} && bash scripts/00_install_pipeline_dependencies.sh

# --------------------------------------------------------------------------------------------------
# Target: check_virtual_env
# --------------------------------------------------------------------------------------------------
# Purpose
#   Guard target: ensures the virtual environment exists before any
#   operational target runs, provisioning it on demand.
#
# Behavior
#   - Checks for the virtual environment directory.
#   - Triggers install_virtual_env only when the directory is missing.
#
# Dependencies
#   - install_virtual_env (invoked only when the venv is missing).
check_virtual_env:
	@if [ ! -d "${CONF_DIR_CONTEXT}/${VIRTUAL_ENV_DIR}" ]; then \
		echo "Virtual environment directory ${CONF_DIR_CONTEXT}/${VIRTUAL_ENV_DIR} not found."; \
		echo "Creating virtual environment..."; \
		$(MAKE) install_virtual_env; \
	fi

# --------------------------------------------------------------------------------------------------
# Target: format_source_code
# --------------------------------------------------------------------------------------------------
# Purpose
#   Formats the Python modules of the collection with ruff, after validating
#   that the Python virtual environment is available.
#
# Behavior
#   - Activates the virtual environment, then runs ruff format from the
#     project root.
#   - The files to format and the formatting style are read from
#     pyproject.toml, not passed as flags here.
#   - Rewrites the files in place.
#
# Idempotency
#   - Idempotent: a second run on formatted sources changes nothing.
#
# Dependencies
#   - check_virtual_env
format_source_code: check_virtual_env
	@source "${CONF_DIR_CONTEXT}/${VIRTUAL_ENV_DIR}/bin/activate" && \
		cd "${CONF_DIR_CONTEXT}" && ruff format
