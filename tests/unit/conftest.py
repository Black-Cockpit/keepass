# Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
# SPDX-License-Identifier: MIT
import json
import os
import subprocess
import sys
import uuid

import pytest
from pykeepass import PyKeePass, create_database

# Repository root directory
REPOSITORY_DIRECTORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Directory holding the modules of the collection
MODULES_DIRECTORY = os.path.join(REPOSITORY_DIRECTORY, "plugins", "modules")

# Directory holding every database created by the tests
TESTS_LOCAL_DIRECTORY = os.path.join(REPOSITORY_DIRECTORY, "tests.local")

# Directory holding a pykeepass module that cannot be imported
MISSING_LIBRARY_DIRECTORY = os.path.join(REPOSITORY_DIRECTORY, "tests", "unit", "stubs", "missing_pykeepass")

# Password of every database created by the tests
DATABASE_PASSWORD = "password"


@pytest.fixture
def database_path() -> str:
    """
    Return the path of a database with a random name in the tests.local directory
    Returns: str
    """
    # Create the tests.local directory if it does not exist
    os.makedirs(TESTS_LOCAL_DIRECTORY, exist_ok=True)

    # Return a database path with a random name
    return os.path.join(TESTS_LOCAL_DIRECTORY, "{0}.kdbx".format(uuid.uuid4().hex))


@pytest.fixture
def database(database_path: str) -> str:
    """
    Create a database holding secrets in the root group and in nested groups
    Args:
        database_path: Database path
    Returns: str
    """
    # Create empty database
    db = create_database(database_path, DATABASE_PASSWORD)

    # Create foo group
    foo_group = db.add_group(destination_group=db.root_group, group_name="foo")

    # Create foo/baz group
    baz_group = db.add_group(destination_group=foo_group, group_name="baz")

    # Create foo/empty group
    db.add_group(destination_group=foo_group, group_name="empty")

    # Create foo/dup group
    db.add_group(destination_group=foo_group, group_name="dup")

    # Create root secret
    db.add_entry(destination_group=db.root_group, title="rootsecret", username="root", password="toor")

    # Create foo/bar secret
    bar_entry = db.add_entry(destination_group=foo_group, title="bar", username="John", password="Doe")

    # Set foo/bar custom property
    bar_entry.set_custom_property(key="gender", value="Male")

    # Create foo/dup secret with the name of the foo/dup group
    db.add_entry(destination_group=foo_group, title="dup", username="dup", password="dup")

    # Create foo/baz/qux secret
    db.add_entry(destination_group=baz_group, title="qux", username="Jane", password="Roe")

    # Save database
    db.save()

    # Return database path
    return database_path


def open_database(db_path: str, db_password: str = DATABASE_PASSWORD) -> PyKeePass:
    """
    Open a database
    Args:
        db_path: Database path
        db_password: Database password
    Returns: PyKeePass
    """
    # Return the opened database
    return PyKeePass(filename=db_path, password=db_password)


def run_module(name: str, arguments: dict, check_mode: bool = False, missing_library: bool = False) -> dict:
    """
    Run a module of the collection the way Ansible runs it and return its result
    Args:
        name: Module name
        arguments: Module arguments
        check_mode: Indicates if the module should run in check mode.
        missing_library: Indicates if the module should run without the pykeepass library.
    Returns: dict
    """
    # Init module arguments
    module_arguments = dict(arguments)

    # Enable check mode
    if check_mode:
        module_arguments["_ansible_check_mode"] = True

    # Init module environment
    environment = dict(os.environ)

    # Shadow the pykeepass library with a module that cannot be imported
    if missing_library:
        environment["PYTHONPATH"] = MISSING_LIBRARY_DIRECTORY

    # Run module
    process = subprocess.run(
        [sys.executable, os.path.join(MODULES_DIRECTORY, "{0}.py".format(name))],
        input=json.dumps({"ANSIBLE_MODULE_ARGS": module_arguments}),
        capture_output=True,
        text=True,
        env=environment,
    )

    # Extract the result printed by the module
    output = [line for line in process.stdout.splitlines() if line.startswith("{")]

    # Check if the module printed a result
    assert output, "module {0} printed no result: {1} {2}".format(name, process.stdout, process.stderr)

    # Return module result
    return json.loads(output[-1])
