# Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
# SPDX-License-Identifier: MIT
import pytest
import secret_reader
from conftest import DATABASE_PASSWORD, open_database, run_module


def test_worker_returns_secret(database: str):
    """
    The worker returns the username, the password and the custom properties of a secret
    Args:
        database: Database path
    Returns:
    """
    # Read secret
    secret = secret_reader.secret_to_dic(open_database(database), "foo/bar")

    # Check secret
    assert secret == {"bar": {"username": "John", "password": "Doe", "gender": "Male"}}


def test_worker_ignores_leading_slash(database: str):
    """
    The worker returns the same secret with and without a leading slash
    Args:
        database: Database path
    Returns:
    """
    # Open database
    db = open_database(database)

    # Check both path forms
    assert secret_reader.secret_to_dic(db, "/foo/bar") == secret_reader.secret_to_dic(db, "foo/bar")


def test_worker_returns_root_secret(database: str):
    """
    The worker returns a secret stored in the root group
    Args:
        database: Database path
    Returns:
    """
    # Read secret
    secret = secret_reader.secret_to_dic(open_database(database), "/rootsecret")

    # Check secret
    assert secret == {"rootsecret": {"username": "root", "password": "toor"}}


def test_worker_returns_empty_secret_when_missing(database: str):
    """
    The worker returns an empty dictionary for a secret that does not exist
    Args:
        database: Database path
    Returns:
    """
    # Check missing secret
    assert secret_reader.secret_to_dic(open_database(database), "foo/missing") == {}


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
        secret_reader.secret_to_dic(open_database(database), secret_path)


def test_module_returns_secret_unchanged(database: str):
    """
    The module returns the secret and reports no change
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("secret_reader", dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar"))

    # Check changed state
    assert result["changed"] is False

    # Check secret
    assert result["secret"] == {"bar": {"username": "John", "password": "Doe", "gender": "Male"}}

    # Check secret path
    assert result["path"] == "foo/bar"


def test_module_returns_empty_secret_when_missing(database: str):
    """
    The module does not fail for a secret that does not exist
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module(
        "secret_reader", dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/missing")
    )

    # Check failed state
    assert result["failed"] is False

    # Check secret
    assert result["secret"] == {}


def test_module_reports_no_change_in_check_mode(database: str):
    """
    The module reports no change in check mode
    Args:
        database: Database path
    Returns:
    """
    # Run module in check mode
    result = run_module(
        "secret_reader",
        dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar"),
        check_mode=True,
    )

    # Check changed state
    assert result["changed"] is False


def test_module_masks_database_password(database: str):
    """
    The module masks the database password in its invocation output
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module(
        "secret_reader", dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/missing")
    )

    # Check the database password is masked
    assert result["invocation"]["module_args"]["db_password"] != DATABASE_PASSWORD


def test_module_fails_with_wrong_password(database: str):
    """
    The module fails with the credentials error when the password is wrong
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("secret_reader", dict(db_path=database, db_password="wrong", secret_path="foo/bar"))

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
        "secret_reader",
        dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar"),
        missing_library=True,
    )

    # Check failed state
    assert result["failed"] is True

    # Check failure message
    assert "Failed to import the required Python library (pykeepass)" in result["msg"]
