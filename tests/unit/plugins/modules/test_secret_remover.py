# Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
# SPDX-License-Identifier: MIT
import os
import stat

import pytest
import secret_remover
from conftest import DATABASE_PASSWORD, open_database, run_module


def remove(database: str, secret_path: str, **options) -> tuple:
    """
    Remove a secret or a group with the worker
    Args:
        database: Database path
        secret_path: Path of the secret or the group
        options: Worker options
    Returns: tuple
    """
    # Return the removed paths and the changed state
    return secret_remover.secret_remove(
        secret_path=secret_path, db=open_database(database), db_path=database, **options
    )


def test_worker_removes_entry(database: str):
    """
    The worker removes a secret and returns its path
    Args:
        database: Database path
    Returns:
    """
    # Remove secret
    removed, changed = remove(database, "foo/bar")

    # Check changed state
    assert changed is True

    # Check removed paths
    assert removed == {"entries": ["foo/bar"], "groups": []}

    # Check the secret was removed
    assert open_database(database).find_entries_by_path(path=["foo", "bar"]) is None


def test_worker_removes_root_entry_with_leading_slash(database: str):
    """
    The worker removes a secret of the root group addressed with a leading slash
    Args:
        database: Database path
    Returns:
    """
    # Remove secret
    removed, changed = remove(database, "/rootsecret")

    # Check removed paths
    assert removed == {"entries": ["rootsecret"], "groups": []}

    # Check the secret was removed
    assert open_database(database).find_entries_by_path(path=["rootsecret"]) is None


def test_worker_removes_empty_group(database: str):
    """
    The worker removes an empty group without recurse
    Args:
        database: Database path
    Returns:
    """
    # Remove group
    removed, changed = remove(database, "foo/empty")

    # Check changed state
    assert changed is True

    # Check removed paths
    assert removed == {"entries": [], "groups": ["foo/empty"]}

    # Check the group was removed
    assert open_database(database).find_groups(path=["foo", "empty"], first=True) is None


def test_worker_fails_on_non_empty_group_without_recurse(database: str):
    """
    The worker raises an error for a group that is not empty when recurse is false
    Args:
        database: Database path
    Returns:
    """
    # Check the raised error
    with pytest.raises(ValueError, match="is not empty"):
        remove(database, "foo/baz")

    # Check the group was not removed
    assert open_database(database).find_groups(path=["foo", "baz"], first=True) is not None


def test_worker_removes_group_with_content(database: str):
    """
    The worker removes a group with all its content when recurse is true
    Args:
        database: Database path
    Returns:
    """
    # Remove group
    removed, changed = remove(database, "foo", target="group", recurse=True)

    # Check changed state
    assert changed is True

    # Check removed secrets paths
    assert sorted(removed["entries"]) == ["foo/bar", "foo/baz/qux", "foo/dup"]

    # Check removed groups paths
    assert sorted(removed["groups"]) == ["foo", "foo/baz", "foo/dup", "foo/empty"]

    # Open database
    db = open_database(database)

    # Check the group was removed
    assert db.find_groups(path=["foo"], first=True) is None

    # Check the root secret was kept
    assert db.find_entries_by_path(path=["rootsecret"]) is not None


def test_worker_reports_no_change_when_missing(database: str):
    """
    The worker reports no change for a path that matches nothing
    Args:
        database: Database path
    Returns:
    """
    # Remove secret
    removed, changed = remove(database, "foo/missing")

    # Check changed state
    assert changed is False

    # Check removed paths
    assert removed == {"entries": [], "groups": []}


def test_worker_fails_on_ambiguous_path(database: str):
    """
    The worker raises an error when the path matches an entry and a group
    Args:
        database: Database path
    Returns:
    """
    # Check the raised error
    with pytest.raises(ValueError, match="matches an entry and a group"):
        remove(database, "foo/dup")


def test_worker_removes_only_entry_with_entry_target(database: str):
    """
    The worker removes the entry and keeps the group of the same name with the entry target
    Args:
        database: Database path
    Returns:
    """
    # Remove secret
    removed, changed = remove(database, "foo/dup", target="entry")

    # Check removed paths
    assert removed == {"entries": ["foo/dup"], "groups": []}

    # Open database
    db = open_database(database)

    # Check the secret was removed
    assert db.find_entries_by_path(path=["foo", "dup"]) is None

    # Check the group was kept
    assert db.find_groups(path=["foo", "dup"], first=True) is not None


def test_worker_removes_only_group_with_group_target(database: str):
    """
    The worker removes the group and keeps the entry of the same name with the group target
    Args:
        database: Database path
    Returns:
    """
    # Remove group
    removed, changed = remove(database, "foo/dup", target="group")

    # Check removed paths
    assert removed == {"entries": [], "groups": ["foo/dup"]}

    # Open database
    db = open_database(database)

    # Check the group was removed
    assert db.find_groups(path=["foo", "dup"], first=True) is None

    # Check the secret was kept
    assert db.find_entries_by_path(path=["foo", "dup"]) is not None


def test_worker_keeps_group_with_entry_target(database: str):
    """
    The worker reports no change when only a group matches the path with the entry target
    Args:
        database: Database path
    Returns:
    """
    # Remove secret
    removed, changed = remove(database, "foo/empty", target="entry")

    # Check changed state
    assert changed is False

    # Check the group was kept
    assert open_database(database).find_groups(path=["foo", "empty"], first=True) is not None


def test_worker_keeps_entry_with_group_target(database: str):
    """
    The worker reports no change when only an entry matches the path with the group target
    Args:
        database: Database path
    Returns:
    """
    # Remove group
    removed, changed = remove(database, "foo/bar", target="group")

    # Check changed state
    assert changed is False

    # Check the secret was kept
    assert open_database(database).find_entries_by_path(path=["foo", "bar"]) is not None


@pytest.mark.parametrize("secret_path", ["/", "//"])
def test_worker_never_removes_root_group(database: str, secret_path: str):
    """
    The worker raises an error when the path is the root group
    Args:
        database: Database path
        secret_path: Path of the root group
    Returns:
    """
    # Check the raised error
    with pytest.raises(ValueError, match="root group"):
        remove(database, secret_path, recurse=True)


def test_worker_does_not_write_in_check_mode(database: str):
    """
    The worker reports the removed paths without writing the database in check mode
    Args:
        database: Database path
    Returns:
    """
    # Remove group in check mode
    removed, changed = remove(database, "foo/baz", recurse=True, check_mode=True)

    # Check changed state
    assert changed is True

    # Check removed paths
    assert removed == {"entries": ["foo/baz/qux"], "groups": ["foo/baz"]}

    # Check the group was kept
    assert open_database(database).find_groups(path=["foo", "baz"], first=True) is not None


def test_module_removes_secret(database: str):
    """
    The module removes a secret and reports no change on a second run
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("secret_remover", dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar"))

    # Check changed state
    assert result["changed"] is True

    # Check removed paths
    assert result["removed"] == {"entries": ["foo/bar"], "groups": []}

    # Check secret path
    assert result["path"] == "foo/bar"

    # Run module again
    result = run_module("secret_remover", dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar"))

    # Check changed state
    assert result["changed"] is False


def test_module_keeps_database_permissions(database: str):
    """
    The module keeps the permissions of the database file when it removes a secret
    Args:
        database: Database path
    Returns:
    """
    # Restrict the database permissions to its owner
    os.chmod(database, 0o600)

    # Run module
    result = run_module("secret_remover", dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar"))

    # Check changed state
    assert result["changed"] is True

    # Check the database permissions
    assert stat.S_IMODE(os.stat(database).st_mode) == 0o600


def test_module_fails_on_non_empty_group_without_recurse(database: str):
    """
    The module fails for a group that is not empty when recurse is false
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("secret_remover", dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/baz"))

    # Check failed state
    assert result["failed"] is True

    # Check failure message
    assert "is not empty" in result["msg"]


def test_module_rejects_unknown_target(database: str):
    """
    The module fails when the target is not any, entry or group
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module(
        "secret_remover",
        dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar", target="other"),
    )

    # Check failed state
    assert result["failed"] is True


def test_module_fails_when_database_is_missing(database_path: str):
    """
    The module fails and does not create the database when it does not exist
    Args:
        database_path: Database path
    Returns:
    """
    # Run module
    result = run_module(
        "secret_remover", dict(db_path=database_path, db_password=DATABASE_PASSWORD, secret_path="foo/bar")
    )

    # Check failed state
    assert result["failed"] is True

    # Check failure message
    assert "does not exist" in result["msg"]

    # Check the database was not created
    assert not os.path.exists(database_path)


def test_module_does_not_write_in_check_mode(database: str):
    """
    The module reports the removed paths without writing the database in check mode
    Args:
        database: Database path
    Returns:
    """
    # Run module in check mode
    result = run_module(
        "secret_remover",
        dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar"),
        check_mode=True,
    )

    # Check changed state
    assert result["changed"] is True

    # Check removed paths
    assert result["removed"] == {"entries": ["foo/bar"], "groups": []}

    # Check the secret was kept
    assert open_database(database).find_entries_by_path(path=["foo", "bar"]) is not None


def test_module_fails_with_wrong_password(database: str):
    """
    The module fails with the credentials error when the password is wrong
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("secret_remover", dict(db_path=database, db_password="wrong", secret_path="foo/bar"))

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
        "secret_remover",
        dict(db_path=database, db_password=DATABASE_PASSWORD, secret_path="foo/bar"),
        missing_library=True,
    )

    # Check failed state
    assert result["failed"] is True

    # Check failure message
    assert "Failed to import the required Python library (pykeepass)" in result["msg"]
