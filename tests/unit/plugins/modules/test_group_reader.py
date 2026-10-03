# Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
# SPDX-License-Identifier: MIT
import group_reader
import pytest
from conftest import DATABASE_PASSWORD, open_database, run_module


def test_worker_returns_group_secrets(database: str):
    """
    The worker returns the secrets stored directly in a group
    Args:
        database: Database path
    Returns:
    """
    # Read group secrets
    group_secrets = group_reader.group_to_dic(open_database(database), "foo")

    # Check group secrets
    assert group_secrets == [
        {"bar": {"username": "John", "password": "Doe", "gender": "Male"}},
        {"dup": {"username": "dup", "password": "dup"}},
    ]


def test_worker_returns_nested_group_secrets(database: str):
    """
    The worker returns the secrets of a nested group
    Args:
        database: Database path
    Returns:
    """
    # Read group secrets
    group_secrets = group_reader.group_to_dic(open_database(database), "foo/baz")

    # Check group secrets
    assert group_secrets == [{"qux": {"username": "Jane", "password": "Roe"}}]


def test_worker_ignores_leading_slash(database: str):
    """
    The worker returns the same secrets with and without a leading slash
    Args:
        database: Database path
    Returns:
    """
    # Open database
    db = open_database(database)

    # Check both path forms
    assert group_reader.group_to_dic(db, "/foo/baz") == group_reader.group_to_dic(db, "foo/baz")


def test_worker_returns_empty_list_for_empty_group(database: str):
    """
    The worker returns an empty list for a group that holds no secret
    Args:
        database: Database path
    Returns:
    """
    # Check empty group
    assert group_reader.group_to_dic(open_database(database), "foo/empty") == []


def test_worker_returns_empty_list_when_missing(database: str):
    """
    The worker returns an empty list for a group that does not exist
    Args:
        database: Database path
    Returns:
    """
    # Check missing group
    assert group_reader.group_to_dic(open_database(database), "foo/missing") == []


@pytest.mark.parametrize("group_path", [None, "", "   "])
def test_worker_requires_group_path(database: str, group_path: str):
    """
    The worker raises an error when the group path is not provided
    Args:
        database: Database path
        group_path: Group path
    Returns:
    """
    # Check the raised error
    with pytest.raises(ValueError):
        group_reader.group_to_dic(open_database(database), group_path)


def test_module_returns_group_unchanged(database: str):
    """
    The module returns the group secrets and reports no change
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("group_reader", dict(db_path=database, db_password=DATABASE_PASSWORD, group_path="foo/baz"))

    # Check changed state
    assert result["changed"] is False

    # Check group secrets
    assert result["group"] == [{"qux": {"username": "Jane", "password": "Roe"}}]

    # Check group path
    assert result["path"] == "foo/baz"


def test_module_reports_no_change_in_check_mode(database: str):
    """
    The module reports no change in check mode
    Args:
        database: Database path
    Returns:
    """
    # Run module in check mode
    result = run_module(
        "group_reader",
        dict(db_path=database, db_password=DATABASE_PASSWORD, group_path="foo"),
        check_mode=True,
    )

    # Check changed state
    assert result["changed"] is False


def test_module_fails_with_wrong_password(database: str):
    """
    The module fails with the credentials error when the password is wrong
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("group_reader", dict(db_path=database, db_password="wrong", group_path="foo"))

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
        "group_reader",
        dict(db_path=database, db_password=DATABASE_PASSWORD, group_path="foo"),
        missing_library=True,
    )

    # Check failed state
    assert result["failed"] is True

    # Check failure message
    assert "Failed to import the required Python library (pykeepass)" in result["msg"]
