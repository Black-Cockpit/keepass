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
    format_source_code \
    lint_source_code \
    build_collection \
    publish_collection \
    run_unit_tests \
    run_integration_tests \
    run_sanity_tests \
    run_tests \
    build_wiki \
    publish_wiki

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

# Python version the sanity tests run against
SANITY_PYTHON_VERSION := 3.12

# Collection build output directory
# Notes:
#   - Holds the namespace-name-version.tar.gz artifact produced by
#     build_collection.
#   - Listed in the galaxy.yml build_ignore, so a previous artifact is never
#     packaged into the next one.
COLLECTION_BUILD_DIR := $(CONF_DIR_CONTEXT)/dist

# Collection identity, read from galaxy.yml
# Notes:
#   - Scraped with awk rather than a YAML parser so the Makefile can be
#     parsed before the virtual environment exists.
#   - COLLECTION_ARTIFACT is the file ansible-galaxy produces for the version
#     currently declared in galaxy.yml; bump the version there, never here.
COLLECTION_METADATA := $(CONF_DIR_CONTEXT)/galaxy.yml
COLLECTION_NAMESPACE := $(shell awk '/^namespace:/ {print $$2}' $(COLLECTION_METADATA) 2>/dev/null)
COLLECTION_NAME := $(shell awk '/^name:/ {print $$2}' $(COLLECTION_METADATA) 2>/dev/null)
COLLECTION_VERSION := $(shell awk '/^version:/ {print $$2}' $(COLLECTION_METADATA) 2>/dev/null)
COLLECTION_ARTIFACT := $(COLLECTION_BUILD_DIR)/$(COLLECTION_NAMESPACE)-$(COLLECTION_NAME)-$(COLLECTION_VERSION).tar.gz

# Local test directory
# Notes:
#   - Holds every database the tests create and the collection installed for
#     the integration tests.
#   - Ignored by git and excluded from the built collection.
#   - Never emptied by a target: it is emptied by hand.
TESTS_LOCAL_DIR := $(abspath $(CONF_DIR_CONTEXT)/tests.local)

# Collections directory the built collection is installed into for the
# integration tests
TESTS_COLLECTIONS_DIR := $(TESTS_LOCAL_DIR)/collections

# Wiki build output directory
# Notes:
#   - Written by build_wiki, removed and written again on every run.
#   - Under dist, so it is ignored by git and excluded from the built
#     collection.
WIKI_BUILD_DIR := $(COLLECTION_BUILD_DIR)/wiki

# Git remote of the GitHub wiki
# Notes:
#   - Derived from the origin remote: a GitHub wiki is the repository
#     <name>.wiki.git beside <name>.git.
#   - Override it in the environment to publish to another wiki, or to
#     publish with a token. It is never printed by a recipe.
WIKI_REMOTE ?= $(patsubst %.git,%.wiki.git,$(shell git remote get-url origin 2>/dev/null))

# Ansible Galaxy publication settings
# Notes:
#   - GALAXY_TOKEN is the API token from https://galaxy.ansible.com/ui/token.
#     Pass it in the environment (export GALAXY_TOKEN=...) rather than on the
#     make command line, so it stays out of the shell history.
#   - Leave GALAXY_TOKEN empty to let ansible-galaxy fall back to the token
#     stored in ~/.ansible/galaxy_token.
#   - GALAXY_SERVER overrides the target server for a private Automation Hub;
#     empty means the public galaxy.ansible.com.
GALAXY_TOKEN ?=
GALAXY_SERVER ?=

# Hand the token to the recipe through the environment, so it is never part
# of the ansible-galaxy command line make prints
export GALAXY_TOKEN

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

# --------------------------------------------------------------------------------------------------
# Target: lint_source_code
# --------------------------------------------------------------------------------------------------
# Purpose
#   Checks the formatting and the lint rules of the Python modules and their
#   tests with ruff, after validating that the Python virtual environment is
#   available.
#
# Behavior
#   - Activates the virtual environment, then runs ruff format --check and
#     ruff check from the project root.
#   - The files to check and the rules are read from pyproject.toml.
#   - Fails when a file is not formatted or breaks a lint rule.
#
# Idempotency
#   - Read-only: no file is rewritten.
#
# Dependencies
#   - check_virtual_env
lint_source_code: check_virtual_env
	@source "${CONF_DIR_CONTEXT}/${VIRTUAL_ENV_DIR}/bin/activate" && \
		cd "${CONF_DIR_CONTEXT}" && ruff format --check && ruff check

# --------------------------------------------------------------------------------------------------
# Target: build_collection
# --------------------------------------------------------------------------------------------------
# Purpose
#   Packages the repository into an installable Ansible collection artifact,
#   dist/<namespace>-<name>-<version>.tar.gz.
#
# Behavior
#   - Activates the virtual environment, then runs ansible-galaxy collection
#     build into COLLECTION_BUILD_DIR.
#   - Everything the artifact must not ship is excluded through the
#     galaxy.yml build_ignore list, not through flags here.
#   - --force overwrites an artifact of the same version, so rebuilding after
#     an edit does not require bumping galaxy.yml.
#
# Idempotency
#   - Safe to re-run: the output directory is created on demand and the
#     artifact is rewritten in place.
#
# Dependencies
#   - check_virtual_env
build_collection: check_virtual_env
	@mkdir -p "${COLLECTION_BUILD_DIR}"
	@source "${CONF_DIR_CONTEXT}/${VIRTUAL_ENV_DIR}/bin/activate" && \
		ansible-galaxy collection build "${CONF_DIR_CONTEXT}" \
			--output-path "${COLLECTION_BUILD_DIR}" \
			--force

# --------------------------------------------------------------------------------------------------
# Target: publish_collection
# --------------------------------------------------------------------------------------------------
# Purpose
#   Publishes the built artifact for the version declared in galaxy.yml to
#   Ansible Galaxy (or to the Automation Hub named by GALAXY_SERVER).
#
# Behavior
#   - Rebuilds the artifact first, so what is uploaded always matches the
#     working tree and the galaxy.yml build_ignore list.
#   - Authenticates with GALAXY_TOKEN when set, otherwise leaves
#     ansible-galaxy to use ~/.ansible/galaxy_token.
#   - Announces the collection, version and target server before uploading.
#   - Waits for Galaxy to finish the import, so a rejected import fails the
#     target instead of passing silently.
#
# Idempotency
#   - NOT idempotent: Galaxy refuses a version that already exists. Bump
#     `version` in galaxy.yml before publishing again.
#
# Dependencies
#   - build_collection (and through it check_virtual_env)
#   - A Galaxy API token with rights on the collection namespace
# --------------------------------------------------------------------------------------------------
# ⚠️ CAUTION: This target is public and irreversible. A published version
# cannot be replaced or removed without Galaxy administrator intervention.
# Do NOT execute it unless the release has been approved.
# --------------------------------------------------------------------------------------------------
publish_collection: build_collection
	@echo "Publishing ${COLLECTION_NAMESPACE}.${COLLECTION_NAME} ${COLLECTION_VERSION} to ${if ${GALAXY_SERVER},${GALAXY_SERVER},galaxy.ansible.com}"
	@source "${CONF_DIR_CONTEXT}/${VIRTUAL_ENV_DIR}/bin/activate" && \
		ansible-galaxy collection publish "${COLLECTION_ARTIFACT}" \
			$${GALAXY_TOKEN:+--token "$${GALAXY_TOKEN}"} \
			${if ${GALAXY_SERVER},--server "${GALAXY_SERVER}",} \
			--timeout 120

# --------------------------------------------------------------------------------------------------
# Target: run_unit_tests
# --------------------------------------------------------------------------------------------------
# Purpose
#   Runs the unit and module tests under tests/unit with pytest, after
#   validating that the Python virtual environment is available.
#
# Behavior
#   - Activates the virtual environment, then runs pytest from the project
#     root. The test paths are read from pyproject.toml.
#   - Every database a test creates is written to tests.local with a random
#     name and is left in place.
#
# Idempotency
#   - Safe to re-run: every run works on new databases.
#
# Dependencies
#   - check_virtual_env
run_unit_tests: check_virtual_env
	@source "${CONF_DIR_CONTEXT}/${VIRTUAL_ENV_DIR}/bin/activate" && \
		cd "${CONF_DIR_CONTEXT}" && pytest

# --------------------------------------------------------------------------------------------------
# Target: run_integration_tests
# --------------------------------------------------------------------------------------------------
# Purpose
#   Proves the built collection from a playbook: builds the artifact, installs
#   it, and runs tests/integration/playbook.yml on localhost.
#
# Behavior
#   - Installs the artifact into TESTS_COLLECTIONS_DIR, replacing the copy of
#     a previous run.
#   - Runs the playbook with ANSIBLE_COLLECTIONS_PATH pointing at that
#     directory, so the modules are resolved by their fully qualified name
#     from the installed collection and not from the checkout.
#   - The playbook creates its database in tests.local with a random name.
#
# Idempotency
#   - Safe to re-run: every run works on a new database.
#
# Dependencies
#   - build_collection (and through it check_virtual_env)
run_integration_tests: build_collection
	@mkdir -p "${TESTS_COLLECTIONS_DIR}"
	@source "${CONF_DIR_CONTEXT}/${VIRTUAL_ENV_DIR}/bin/activate" && \
		ansible-galaxy collection install "${COLLECTION_ARTIFACT}" -p "${TESTS_COLLECTIONS_DIR}" --force && \
		export ANSIBLE_COLLECTIONS_PATH="${TESTS_COLLECTIONS_DIR}" && \
		ansible-playbook -i localhost, "${CONF_DIR_CONTEXT}/tests/integration/playbook.yml" \
			-e "tests_local_directory=${TESTS_LOCAL_DIR}"

# --------------------------------------------------------------------------------------------------
# Target: run_sanity_tests
# --------------------------------------------------------------------------------------------------
# Purpose
#   Runs the ansible-test sanity checks against the built collection, which
#   validate the DOCUMENTATION, EXAMPLES and RETURN blocks of every module.
#
# Behavior
#   - Installs the artifact into a temporary directory outside the
#     repository, which gives the ansible_collections/<namespace>/<name>
#     layout ansible-test requires. ansible-test lists its targets with git,
#     so a copy inside the repository, under the git-ignored tests.local
#     directory, is skipped entirely.
#   - Copies tests/sanity into the installed collection, because the built
#     artifact ships no tests and ansible-test reads its ignore file there.
#   - Runs ansible-test sanity from the installed collection. --venv makes
#     ansible-test build its own virtual environments and download the
#     requirements of each check, so the first run needs network access.
#   - Removes the temporary directory when the run ends, on success and on
#     failure.
#
# Idempotency
#   - Safe to re-run.
#
# Dependencies
#   - build_collection (and through it check_virtual_env)
run_sanity_tests: build_collection
	@source "${CONF_DIR_CONTEXT}/${VIRTUAL_ENV_DIR}/bin/activate" && \
		sanity_dir="$$(mktemp -d)" && \
		trap 'rm -rf "$${sanity_dir}"' EXIT && \
		ansible-galaxy collection install "$(abspath ${COLLECTION_ARTIFACT})" -p "$${sanity_dir}" --force && \
		mkdir -p "$${sanity_dir}/ansible_collections/${COLLECTION_NAMESPACE}/${COLLECTION_NAME}/tests" && \
		cp -r "$(abspath ${CONF_DIR_CONTEXT}/tests/sanity)" "$${sanity_dir}/ansible_collections/${COLLECTION_NAMESPACE}/${COLLECTION_NAME}/tests/" && \
		cd "$${sanity_dir}/ansible_collections/${COLLECTION_NAMESPACE}/${COLLECTION_NAME}" && \
		ansible-test sanity --venv --python "${SANITY_PYTHON_VERSION}"

# --------------------------------------------------------------------------------------------------
# Target: run_tests
# --------------------------------------------------------------------------------------------------
# Purpose
#   Runs the lint checks, the unit tests, the integration tests and the
#   sanity tests in that order, and stops at the first one that fails.
#
# Behavior
#   - Delegates to lint_source_code, run_unit_tests, run_integration_tests
#     and run_sanity_tests.
#
# Idempotency
#   - Safe to re-run.
#
# Dependencies
#   - lint_source_code
#   - run_unit_tests
#   - run_integration_tests
#   - run_sanity_tests
run_tests:
	@$(MAKE) --no-print-directory lint_source_code
	@$(MAKE) --no-print-directory run_unit_tests
	@$(MAKE) --no-print-directory run_integration_tests
	@$(MAKE) --no-print-directory run_sanity_tests

# --------------------------------------------------------------------------------------------------
# Target: build_wiki
# --------------------------------------------------------------------------------------------------
# Purpose
#   Builds the pages of the GitHub wiki from README.md, CONTRIBUTING.md,
#   SECURITY.md and every page under docs/.
#
# Behavior
#   - Activates the virtual environment, then runs the wiki build script
#     (scripts/01_build_wiki.py).
#   - Names each wiki page after the title of its source page, rewrites the
#     links between pages into wiki links, and writes the Home page, the
#     sidebar and the footer.
#   - Fails when a page links to a file that does not exist, or when two
#     pages have the same title.
#
# Idempotency
#   - Safe to re-run: WIKI_BUILD_DIR is removed and written again.
#
# Dependencies
#   - check_virtual_env
build_wiki: check_virtual_env
	@source "${CONF_DIR_CONTEXT}/${VIRTUAL_ENV_DIR}/bin/activate" && \
		python "${CONF_DIR_CONTEXT}/scripts/01_build_wiki.py"

# --------------------------------------------------------------------------------------------------
# Target: publish_wiki
# --------------------------------------------------------------------------------------------------
# Purpose
#   Publishes the built wiki pages to the GitHub wiki of the repository.
#
# Behavior
#   - Rebuilds the wiki pages first, so what is published always matches the
#     documentation of the working tree.
#   - Clones WIKI_REMOTE into a temporary directory, replaces every page of
#     the wiki by the built pages, commits and pushes.
#   - Pushes nothing when the wiki already holds the built pages.
#   - Removes the temporary directory when the run ends, on success and on
#     failure.
#
# Idempotency
#   - Safe to re-run: a second run with unchanged documentation pushes
#     nothing.
#
# Dependencies
#   - build_wiki (and through it check_virtual_env)
#   - The wiki enabled on the GitHub repository, with its first page created,
#     and push rights on it.
# --------------------------------------------------------------------------------------------------
# ⚠️ CAUTION: This target is public. The pages are visible to everyone as soon
# as they are pushed, and a page edited by hand in the wiki is overwritten.
# --------------------------------------------------------------------------------------------------
publish_wiki: build_wiki
	@wiki_dir="$$(mktemp -d)" && \
		trap 'rm -rf "$${wiki_dir}"' EXIT && \
		git clone --quiet "${WIKI_REMOTE}" "$${wiki_dir}" && \
		find "$${wiki_dir}" -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} + && \
		cp "${WIKI_BUILD_DIR}"/*.md "$${wiki_dir}/" && \
		cd "$${wiki_dir}" && \
		git add --all && \
		if git diff --cached --quiet; then \
			echo "The wiki is already up to date."; \
		else \
			git commit --quiet -m ":bulb: Updated wiki from the documentation" && \
			git push --quiet && \
			echo "Published the wiki."; \
		fi
