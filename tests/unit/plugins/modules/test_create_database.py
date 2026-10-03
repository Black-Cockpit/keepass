# Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
# SPDX-License-Identifier: MIT
import os
import stat

import create_database
import pytest
from conftest import DATABASE_PASSWORD, open_database, run_module


def read_setting(db_path: str, name: str) -> str:
    """
    Read a setting from the metadata of a database
    Args:
        db_path: Database path
        name: Setting name
    Returns: str
    """
    # Fetch setting
    setting = open_database(db_path).tree.xpath("/KeePassFile/Meta/{0}".format(name))[0]

    # Return setting value
    return setting.text


def read_mode(path: str) -> int:
    """
    Read the permissions of a file
    Args:
        path: File path
    Returns: int
    """
    # Return file permissions
    return stat.S_IMODE(os.stat(path).st_mode)


def test_worker_creates_database(database_path: str):
    """
    The worker creates an empty database that the password opens
    Args:
        database_path: Database path
    Returns:
    """
    # Create database
    changed = create_database.database_create(db_path=database_path, db_password=DATABASE_PASSWORD)

    # Check changed state
    assert changed is True

    # Check the database holds no secret
    assert open_database(database_path).entries == []

    # Check the database permissions
    assert read_mode(database_path) == 0o600


def test_worker_applies_default_settings(database_path: str):
    """
    The worker applies the default settings to a new database
    Args:
        database_path: Database path
    Returns:
    """
    # Create database
    create_database.database_create(db_path=database_path, db_password=DATABASE_PASSWORD)

    # Check recycle bin state
    assert read_setting(database_path, "RecycleBinEnabled") == "True"

    # Check history max items
    assert read_setting(database_path, "HistoryMaxItems") == "10"

    # Check history max size
    assert read_setting(database_path, "HistoryMaxSize") == "6291456"


def test_worker_applies_settings(database_path: str):
    """
    The worker applies the provided settings to a new database
    Args:
        database_path: Database path
    Returns:
    """
    # Create database
    create_database.database_create(
        db_path=database_path,
        db_password=DATABASE_PASSWORD,
        db_name="Foo",
        db_description="Foo secrets",
        db_default_username="John",
        recycle_bin_enabled=False,
        history_max_items=5,
        history_max_size=1048576,
    )

    # Check database name
    assert read_setting(database_path, "DatabaseName") == "Foo"

    # Check database description
    assert read_setting(database_path, "DatabaseDescription") == "Foo secrets"

    # Check database default username
    assert read_setting(database_path, "DefaultUserName") == "John"

    # Check recycle bin state
    assert read_setting(database_path, "RecycleBinEnabled") == "False"

    # Check history max items
    assert read_setting(database_path, "HistoryMaxItems") == "5"

    # Check history max size
    assert read_setting(database_path, "HistoryMaxSize") == "1048576"


def test_worker_keeps_existing_database_without_force(database: str):
    """
    The worker leaves an existing database as it is when it is not forced to be replaced
    Args:
        database: Database path
    Returns:
    """
    # Create database
    changed = create_database.database_create(db_path=database, db_password=DATABASE_PASSWORD, db_name="Other")

    # Check changed state
    assert changed is False

    # Check the database still holds its secrets
    assert open_database(database).find_entries_by_path(path=["foo", "bar"]) is not None


def test_worker_fails_on_existing_database_with_wrong_password(database: str):
    """
    The worker raises an error when the password does not open the existing database
    Args:
        database: Database path
    Returns:
    """
    # Check the raised error
    with pytest.raises(ValueError):
        create_database.database_create(db_path=database, db_password="wrong")

    # Check the database still holds its secrets
    assert open_database(database).find_entries_by_path(path=["foo", "bar"]) is not None


def test_worker_replaces_existing_database_with_force(database: str):
    """
    The worker replaces an existing database by an empty one when it is forced
    Args:
        database: Database path
    Returns:
    """
    # Create database
    changed = create_database.database_create(db_path=database, db_password="other", force=True)

    # Check changed state
    assert changed is True

    # Check the database holds no secret and opens with the new password
    assert open_database(database, "other").entries == []


def test_worker_fails_when_directory_is_missing(database_path: str):
    """
    The worker raises an error that names the missing directory
    Args:
        database_path: Database path
    Returns:
    """
    # Init a database path in a directory that does not exist
    db_path = os.path.join("{0}.missing".format(database_path), "keys.kdbx")

    # Check the raised error
    with pytest.raises(ValueError, match="does not exist"):
        create_database.database_create(db_path=db_path, db_password=DATABASE_PASSWORD)


def test_worker_does_not_write_in_check_mode(database_path: str):
    """
    The worker reports a change without creating the database in check mode
    Args:
        database_path: Database path
    Returns:
    """
    # Create database in check mode
    changed = create_database.database_create(db_path=database_path, db_password=DATABASE_PASSWORD, check_mode=True)

    # Check changed state
    assert changed is True

    # Check the database was not created
    assert not os.path.exists(database_path)


def test_worker_leaves_no_temporary_file(database_path: str):
    """
    The worker leaves only the database in its directory
    Args:
        database_path: Database path
    Returns:
    """
    # List the directory content before the creation
    content = set(os.listdir(os.path.dirname(database_path)))

    # Create database
    create_database.database_create(db_path=database_path, db_password=DATABASE_PASSWORD)

    # Check the database is the only new file
    assert set(os.listdir(os.path.dirname(database_path))) - content == {os.path.basename(database_path)}


def test_module_creates_database(database_path: str):
    """
    The module creates the database and returns its path
    Args:
        database_path: Database path
    Returns:
    """
    # Run module
    result = run_module("create_database", dict(db_path=database_path, db_password=DATABASE_PASSWORD, db_name="Foo"))

    # Check changed state
    assert result["changed"] is True

    # Check database path
    assert result["path"] == database_path

    # Check database name
    assert read_setting(database_path, "DatabaseName") == "Foo"

    # Check the database permissions
    assert read_mode(database_path) == 0o600


def test_module_reports_no_change_on_second_run(database_path: str):
    """
    The module reports no change when the database already exists
    Args:
        database_path: Database path
    Returns:
    """
    # Run module
    run_module("create_database", dict(db_path=database_path, db_password=DATABASE_PASSWORD))

    # Run module again
    result = run_module("create_database", dict(db_path=database_path, db_password=DATABASE_PASSWORD))

    # Check changed state
    assert result["changed"] is False


def test_module_applies_mode(database_path: str):
    """
    The module applies the provided permissions to the database file
    Args:
        database_path: Database path
    Returns:
    """
    # Run module
    run_module("create_database", dict(db_path=database_path, db_password=DATABASE_PASSWORD, mode="0640"))

    # Check the database permissions
    assert read_mode(database_path) == 0o640


def test_module_corrects_mode_of_existing_database(database_path: str):
    """
    The module corrects the permissions of an existing database and reports a change
    Args:
        database_path: Database path
    Returns:
    """
    # Run module
    run_module("create_database", dict(db_path=database_path, db_password=DATABASE_PASSWORD))

    # Change the database permissions
    os.chmod(database_path, 0o644)

    # Run module again
    result = run_module("create_database", dict(db_path=database_path, db_password=DATABASE_PASSWORD))

    # Check changed state
    assert result["changed"] is True

    # Check the database permissions
    assert read_mode(database_path) == 0o600


def test_module_fails_on_existing_database_with_wrong_password(database: str):
    """
    The module fails when the password does not open the existing database
    Args:
        database: Database path
    Returns:
    """
    # Run module
    result = run_module("create_database", dict(db_path=database, db_password="wrong"))

    # Check failed state
    assert result["failed"] is True

    # Check failure message
    assert "exists and is not a database that the password opens" in result["msg"]


def test_module_does_not_write_in_check_mode(database_path: str):
    """
    The module reports a change without creating the database in check mode
    Args:
        database_path: Database path
    Returns:
    """
    # Run module in check mode
    result = run_module("create_database", dict(db_path=database_path, db_password=DATABASE_PASSWORD), check_mode=True)

    # Check changed state
    assert result["changed"] is True

    # Check the database was not created
    assert not os.path.exists(database_path)


def test_module_masks_database_password(database_path: str):
    """
    The module masks the database password in its invocation output
    Args:
        database_path: Database path
    Returns:
    """
    # Run module
    result = run_module("create_database", dict(db_path=database_path, db_password=DATABASE_PASSWORD))

    # Check the database password is masked
    assert result["invocation"]["module_args"]["db_password"] != DATABASE_PASSWORD


def test_module_fails_without_library(database_path: str):
    """
    The module fails with the missing library message when pykeepass is not installed
    Args:
        database_path: Database path
    Returns:
    """
    # Run module without the pykeepass library
    result = run_module(
        "create_database", dict(db_path=database_path, db_password=DATABASE_PASSWORD), missing_library=True
    )

    # Check failed state
    assert result["failed"] is True

    # Check failure message
    assert "Failed to import the required Python library (pykeepass)" in result["msg"]
