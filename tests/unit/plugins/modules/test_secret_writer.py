# Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
# SPDX-License-Identifier: MIT
import os
import stat

import pytest
import secret_writer
from conftest import DATABASE_PASSWORD, open_database, run_module


def test_worker_creates_secret_and_groups(database: str):
    """
    The worker creates the secret and the groups of its path
    Args:
        database: Database path
    Returns:
    """
    # Write secret
    secret, changed = secret_writer.secret_write(
        secret_path="new/nested/secret",
        db=open_database(database),
        db_path=database,
        username="Ada",
        password="Lovelace",
        url="https://example.com",
        custom_properties={"role": "admin"},
    )

    # Check changed state
    assert changed is True

    # Check returned secret
    assert secret == {"secret": {"username": "Ada", "password": "Lovelace", "role": "admin"}}

    # Read the stored entry
    entry = open_database(database).find_entries_by_path(path=["new", "nested", "secret"])

    # Check the stored url
    assert entry.url == "https://example.com"


@pytest.mark.parametrize("secret_path", ["/rootname", "rootname"])
def test_worker_writes_to_root_group(database: str, secret_path: str):
    """
    The worker writes a secret to the root group with and without a leading slash
    Args:
        database: Database path
        secret_path: Secret path
    Returns:
    """
    # Write secret
    secret, changed = secret_writer.secret_write(
        secret_path=secret_path, db=open_database(database), db_path=database, username="Ada", password="Lovelace"
    )

    # Check changed state
    assert changed is True

    # Check the stored entry
    assert open_database(database).find_entries_by_path(path=["rootname"]) is not None


def test_worker_keeps_existing_secret_without_force(database: str):
    """
    The worker returns an existing secret unchanged when it is not forced to be replaced
    Args:
        database: Database path
    Returns:
    """
    # Write secret
    secret, changed = secret_writer.secret_write(
        secret_path="foo/bar", db=open_database(database), db_path=database, username="Other", password="Other"
    )

    # Check changed state
    assert changed is False

    # Check returned secret
    assert secret == {"bar": {"username": "John", "password": "Doe", "gender": "Male"}}


def test_worker_replaces_existing_secret_with_force(database: str):
    """
    The worker replaces an existing secret when it is forced
    Args:
        database: Database path
    Returns:
    """
    # Write secret
    secret, changed = secret_writer.secret_write(
        secret_path="foo/bar",
        db=open_database(database),
        db_path=database,
        username="Other",
        password="Other",
        force=True,
    )

    # Check changed state
    assert changed is True

    # Check returned secret
    assert secret == {"bar": {"username": "Other", "password": "Other"}}


@pytest.mark.parametrize("secret_path", [None, "", "   "])
def test_worker_requires_secret_path(database: str, secret_path: str):
    """
    The worker raises an error when the secret path is not provided
    Args:
        database: Database path
        secret_path: Secret path
    Returns:
    """
    # Check the raised error
    with pytest.raises(ValueError):
        secret_writer.secret_write(secret_path=secret_path, db=open_database(database), db_path=database)


def test_module_creates_missing_database(database_path: str):
    """
    The module creates the database when it does not exist
    Args:
        database_path: Database path
    Returns:
    """
    # Run module
    result = run_module(
        "secret_writer",
        dict(
            db_path=database_path,
            db_password=DATABASE_PASSWORD,
            secret_path="foo/bar",
            secret_value=dict(username="John", password="Doe", custom_properties=dict(gender="Male")),
        ),
    )

    # Check changed state
    assert result["changed"] is True

    # Check returned secret
    assert result["secret"] == {"bar": {"username": "John", "password": "Doe", "gender": "Male"}}

    # Check the database was created
    assert os.path.isfile(database_path)


def test_module_creates_empty_secret_without_secret_value(database: str):
    """
    The module creates an empty secret when the secret value is omitted
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("secret_writer", dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/blank"))

    # Check changed state
    assert result["changed"] is True

    # Check returned secret
    assert result["secret"] == {"blank": {}}


def test_module_creates_secret_with_username_only(database: str):
    """
    The module creates a secret when the secret value holds only a username
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module(
        "secret_writer",
        dict(
            db_path=database,
            db_password=DATABASE_PASSWORD,
            secret_path="foo/useronly",
            secret_value=dict(username="John"),
        ),
    )

    # Check changed state
    assert result["changed"] is True

    # Check returned secret
    assert result["secret"] == {"useronly": {"username": "John"}}


def test_module_does_not_write_in_check_mode(database_path: str):
    """
    The module does not create the database in check mode
    Args:
        database_path: Database path
    Returns:
    """
    # Run module in check mode
    result = run_module(
        "secret_writer",
        dict(db_path=database_path, db_password=DATABASE_PASSWORD, secret_path="foo/bar"),
        check_mode=True,
    )

    # Check changed state
    assert result["changed"] is False

    # Check the database was not created
    assert not os.path.exists(database_path)


def test_module_masks_database_password(database: str):
    """
    The module masks the database password in its invocation output
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("secret_writer", dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar"))

    # Check the database password is masked
    assert result["invocation"]["module_args"]["db_password"] != DATABASE_PASSWORD


def test_module_keeps_database_permissions(database: str):
    """
    The module keeps the permissions of the database file when it writes a secret
    Args:
        database: Database path
    Returns:
    """
    # Restrict the database permissions to its owner
    os.chmod(database, 0o600)

    # Run module
    result = run_module(
        "secret_writer",
        dict(
            db_path=database,
            db_password=DATABASE_PASSWORD,
            secret_path="foo/permissions",
            secret_value=dict(username="John"),
        ),
    )

    # Check changed state
    assert result["changed"] is True

    # Check the database permissions
    assert stat.S_IMODE(os.stat(database).st_mode) == 0o600


def test_module_rejects_unknown_secret_value_key(database: str):
    """
    The module fails when the secret value holds a key that is not an option
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module(
        "secret_writer",
        dict(
            db_path=database,
            db_password=DATABASE_PASSWORD,
            secret_path="foo/unknown",
            secret_value=dict(username="John", notes="unknown"),
        ),
    )

    # Check failed state
    assert result["failed"] is True

    # Check the secret was not created
    assert open_database(database).find_entries_by_path(path=["foo", "unknown"]) is None


def test_module_fails_with_wrong_password(database: str):
    """
    The module fails with the credentials error when the password is wrong
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("secret_writer", dict(db_path=database, db_password="wrong", secret_path="foo/bar"))

    # Check failed state
    assert result["failed"] is True

    # Check failure message
    assert "Invalid credentials" in result["msg"]


def test_module_fails_without_library(database: str):
    """
    The module fails with the missing library message when pykeepass is not installed
    Args:
        database: Database path
    Returns:
    """
    # Run module without the pykeepass library
    result = run_module(
        "secret_writer",
        dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar"),
        missing_library=True,
    )

    # Check failed state
    assert result["failed"] is True

    # Check failure message
    assert "Failed to import the required Python library (pykeepass)" in result["msg"]
