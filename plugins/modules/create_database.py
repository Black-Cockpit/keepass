#!/usr/bin/python

# Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
# SPDX-License-Identifier: MIT
from __future__ import absolute_import, division, print_function

import os
import tempfile
import traceback

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

__metaclass__ = type
LIB_IMP_ERR = None
try:
    from pykeepass import PyKeePass, create_database

    HAS_LIB = True
except (ModuleNotFoundError, NameError):
    HAS_LIB = False
    LIB_IMP_ERR = traceback.format_exc()

DOCUMENTATION = r'''
---
module: create_database

short_description: Keepass create_database module

version_added: "1.1.0"

description:
    - This module creates a fresh empty keepass database and stores it in a path.
    - An existing database is never replaced or modified unless force is set to true.
    - The database settings are applied only when the database is created.
    - The encryption algorithm, the key derivation and the database format are the ones of the pykeepass blank database.

options:
    db_path:
        description: Keepass database path. The parent directory must exist.
        required: true
        type: path
    db_password:
        description: Keepass database password.
        required: true
        type: str
    force:
        description: If set to true an existing database is replaced by an empty one and all its secrets are lost.
        required: false
        type: bool
        default: false
    mode:
        description: Permissions of the database file.
        required: false
        type: raw
        default: "0600"
    db_name:
        description: Database name.
        required: false
        type: str
        default: ""
    db_description:
        description: Database description.
        required: false
        type: str
        default: ""
    db_default_username:
        description: Username proposed for new entries.
        required: false
        type: str
        default: ""
    recycle_bin_enabled:
        description: Indicates if removed entries and groups are moved to the recycle bin.
        required: false
        type: bool
        default: true
    history_max_items:
        description: Number of history versions kept per entry.
        required: false
        type: int
        default: 10
    history_max_size:
        description: Size in bytes of the history kept per entry.
        required: false
        type: int
        default: 6291456
extends_documentation_fragment:
    - ansible.builtin.files
author:
    - Hasni Mehdi (@hasnimehdi91)
    - mehdi@black-cockpit.com
'''

EXAMPLES = r'''
# Create database
- name: Create database
  hasnimehdi91.keepass.create_database:
    db_path: "keys.kdbx"
    db_password: "password"
  register: database
- debug: var=database

# Create database with settings and file ownership
- name: Create database with settings
  hasnimehdi91.keepass.create_database:
    db_path: "/foo/bar/keys.kdbx"
    db_password: "password"
    db_name: "Foo"
    db_description: "Foo secrets"
    db_default_username: "John"
    recycle_bin_enabled: false
    history_max_items: 5
    owner: "john"
    group: "john"
    mode: "0640"
  register: database
- debug: var=database

# Replace an existing database by an empty one
- name: Replace database
  hasnimehdi91.keepass.create_database:
    db_path: "keys.kdbx"
    db_password: "password"
    force: true
  register: database
- debug: var=database
'''

RETURN = r'''
# These are the attributes that can be returned by the module.
changed:
    description: The state of the task.
    type: bool
    returned: always
failed:
    description: Indicate if the task failed
    type: bool
    returned: always
path:
    description: Database path
    type: str
    returned: always
'''


def run_module():
    """
    Keepass create_database module
    Returns:
    """
    # Init changed state
    changed = False

    # Keepass create_database module arguments
    module_args = dict(
        db_path=dict(type='path', required=True),
        db_password=dict(type='str', required=True, no_log=True),
        force=dict(type='bool', required=False, default=False),
        mode=dict(type='raw', required=False, default='0600'),
        db_name=dict(type='str', required=False, default=''),
        db_description=dict(type='str', required=False, default=''),
        db_default_username=dict(type='str', required=False, default=''),
        recycle_bin_enabled=dict(type='bool', required=False, default=True),
        history_max_items=dict(type='int', required=False, default=10),
        history_max_size=dict(type='int', required=False, default=6291456),
    )

    # Keepass module result initialization
    result = dict(changed=False, failed=False)

    # Keepass module initialization
    module = AnsibleModule(argument_spec=module_args, add_file_common_args=True, supports_check_mode=True)

    # Fail if the pykeepass library is missing
    if not HAS_LIB:
        module.fail_json(msg=missing_required_lib("pykeepass"), exception=LIB_IMP_ERR)

    # Read database path
    db_path = module.params['db_path']

    # Create the database
    try:
        changed = database_create(
            db_path=db_path,
            db_password=module.params['db_password'],
            force=module.params['force'],
            check_mode=module.check_mode,
            db_name=module.params['db_name'],
            db_description=module.params['db_description'],
            db_default_username=module.params['db_default_username'],
            recycle_bin_enabled=module.params['recycle_bin_enabled'],
            history_max_items=module.params['history_max_items'],
            history_max_size=module.params['history_max_size'],
        )
    except Exception as e:
        # Fail with the error message and its traceback
        module.fail_json(msg="Failed to create keepass database: {0}".format(str(e)), exception=traceback.format_exc())

    # Apply the permissions, the owner and the group of the database file
    if os.path.isfile(db_path):
        # Load file attributes
        file_args = module.load_file_common_arguments(module.params, path=db_path)

        # Set file attributes if they are different
        changed = module.set_fs_attributes_if_different(file_args, changed)

    # Append changed state to result
    result['changed'] = changed is True

    # Append database path to result
    result['path'] = db_path

    # Exit with result
    module.exit_json(**result)


def database_create(
    db_path: str,
    db_password: str,
    force: bool = False,
    check_mode: bool = False,
    db_name: str = '',
    db_description: str = '',
    db_default_username: str = '',
    recycle_bin_enabled: bool = True,
    history_max_items: int = 10,
    history_max_size: int = 6291456,
) -> bool:
    """
    Create an empty Keepass database and return its changed state
    Args:
        db_path: Database path
        db_password: Database password
        force: Indicates if the database should be replaced if it exists or not.
        check_mode: Indicates if the database should not be written.
        db_name: Database name
        db_description: Database description
        db_default_username: Username proposed for new entries
        recycle_bin_enabled: Indicates if removed entries and groups are moved to the recycle bin.
        history_max_items: Number of history versions kept per entry
        history_max_size: Size in bytes of the history kept per entry
    Returns: bool
    """

    # Check if database path was not provided
    if db_path is None or db_path == '' or db_path.isspace():
        raise ValueError("db_path is required")

    # Extract database directory
    db_directory = os.path.dirname(os.path.abspath(db_path))

    # Check if database directory does not exist
    if not os.path.isdir(db_directory):
        raise ValueError("directory {0} does not exist".format(db_directory))

    # Check if database path is a directory
    if os.path.isdir(db_path):
        raise ValueError("{0} is a directory".format(db_path))

    # Keep the existing database if it is not forced to be replaced
    if os.path.isfile(db_path) and not force:
        # Check if the existing database opens with the password
        try:
            PyKeePass(filename=db_path, password=db_password)
        except Exception as e:
            raise ValueError("{0} exists and is not a database that the password opens".format(db_path)) from e

        # Return unchanged state
        return False

    # Return changed state without writing the database in check mode
    if check_mode:
        return True

    # Create temporary database file in the database directory
    temp_descriptor, temp_path = tempfile.mkstemp(prefix=".", suffix=".kdbx", dir=db_directory)

    # Close temporary database file
    os.close(temp_descriptor)

    # Create the database in the temporary file and move it to its path
    try:
        # Create empty database
        db = create_database(temp_path, db_password)

        # Set database name
        _set_database_setting(db, "DatabaseName", db_name)

        # Set database description
        _set_database_setting(db, "DatabaseDescription", db_description)

        # Set database default username
        _set_database_setting(db, "DefaultUserName", db_default_username)

        # Set recycle bin state
        _set_database_setting(db, "RecycleBinEnabled", "True" if recycle_bin_enabled else "False")

        # Set history max items
        _set_database_setting(db, "HistoryMaxItems", str(history_max_items))

        # Set history max size
        _set_database_setting(db, "HistoryMaxSize", str(history_max_size))

        # Save database
        db.save()

        # Restrict database permissions to its owner
        os.chmod(temp_path, 0o600)

        # Move database to its path
        os.replace(temp_path, db_path)
    finally:
        # Remove temporary database file if it was not moved
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # Return changed state
    return True


def _set_database_setting(db: "PyKeePass", name: str, value: str):
    """
    Set a setting in the Keepass database metadata
    Args:
        db: Keepass database
        name: Setting name
        value: Setting value
    Returns:
    """
    # Fetch database metadata
    metadata = db.tree.xpath("/KeePassFile/Meta")[0]

    # Fetch setting
    setting = metadata.find(name)

    # Create setting if it does not exist
    if setting is None:
        # Init setting
        setting = metadata.makeelement(name)

        # Append setting to database metadata
        metadata.append(setting)

    # Set setting value
    setting.text = value


def main():
    """
    Execute keepass create_database module
    Returns:

    """
    # Run module
    run_module()


if __name__ == '__main__':
    """
    Module main
    """
    # Execute module
    main()
