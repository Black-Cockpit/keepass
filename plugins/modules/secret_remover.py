#!/usr/bin/python

# Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
# SPDX-License-Identifier: MIT
from __future__ import absolute_import, division, print_function

import os
import stat
import traceback

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

__metaclass__ = type
LIB_IMP_ERR = None
try:
    from pykeepass import PyKeePass

    HAS_LIB = True
except (ModuleNotFoundError, NameError):
    HAS_LIB = False
    LIB_IMP_ERR = traceback.format_exc()

DOCUMENTATION = r'''
---
module: secret_remover

short_description: Keepass secret_remover module

version_added: "1.1.0"

description:
    - This module removes a secret or a group from a keepass database and returns the removed paths.
    - The removal is permanent, the secret or the group is not moved to the recycle bin.
    - A secret or a group that does not exist is not a failure, the task reports no change.
    - The root group is never removed.

options:
    db_path:
        description: Keepass database path. The database must exist.
        required: true
        type: str
    db_password:
        description: Keepass database password.
        required: true
        type: str
    secret_path:
        description: Keepass path of the secret or the group to remove.
        required: true
        type: str
    target:
        description:
            - Indicates what may be removed at the path.
            - With C(any) the secret or the group at the path is removed, and the task fails if both exist.
            - With C(entry) only a secret is removed, a group at the path is left in place.
            - With C(group) only a group is removed, a secret at the path is left in place.
        required: false
        type: str
        choices: [any, entry, group]
        default: any
    recurse:
        description:
            - If set to true a group is removed together with all its secrets and sub groups.
            - If set to false the task fails when the group is not empty.
        required: false
        type: bool
        default: false
author:
    - Mehdi Hasni (@hasnimehdi91)
'''

EXAMPLES = r'''
# Remove secret
- name: Remove secret
  hasnimehdi91.keepass.secret_remover:
    db_path: "keys.kdbx"
    db_password: "password"
    secret_path: "/foo/bar"
  register: removed_secret
- debug: var=removed_secret

# Remove a group and all its content
- name: Remove group
  hasnimehdi91.keepass.secret_remover:
    db_path: "keys.kdbx"
    db_password: "password"
    secret_path: "/foo"
    target: group
    recurse: true
  register: removed_group
- debug: var=removed_group
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
    description: Path of the secret or the group
    type: str
    returned: always
removed:
    description: Paths that were removed
    type: dict
    returned: always
    contains:
        entries:
            description: Paths of the removed secrets
            type: list
            elements: str
        groups:
            description: Paths of the removed groups
            type: list
            elements: str
'''


def run_module():
    """
    Keepass secret_remover module
    Returns:
    """
    # Init removed paths
    removed = dict(entries=[], groups=[])

    # Init changed state
    changed = False

    # Keepass secret_remover module arguments
    module_args = dict(
        db_path=dict(type='str', required=True),
        db_password=dict(type='str', required=True, no_log=True),
        secret_path=dict(type='str', required=True, no_log=False),
        target=dict(type='str', required=False, default='any', choices=['any', 'entry', 'group']),
        recurse=dict(type='bool', required=False, default=False),
    )

    # Keepass module result initialization
    result = dict(changed=False, removed=removed, failed=False)

    # Keepass module initialization
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    # Fail if the pykeepass library is missing
    if not HAS_LIB:
        module.fail_json(msg=missing_required_lib("pykeepass"), exception=LIB_IMP_ERR)

    # Open the database and remove the secret
    try:
        # Read database path
        db_path = module.params['db_path']

        # Read database password
        db_password = module.params['db_password']

        # Check if database does not exist
        if not os.path.isfile(db_path):
            raise ValueError("database {0} does not exist".format(db_path))

        # Connect to database
        db = PyKeePass(filename=db_path, password=db_password)

        # Remove secret
        removed, changed = secret_remove(
            secret_path=module.params['secret_path'],
            db=db,
            db_path=db_path,
            target=module.params['target'],
            recurse=module.params['recurse'],
            check_mode=module.check_mode,
        )
    except Exception as e:
        # Fail with the error message and its traceback
        module.fail_json(msg="Failed to remove keepass secret: {0}".format(str(e)), exception=traceback.format_exc())

    # Append removed paths to result
    result['removed'] = removed

    # Append changed state to result
    result['changed'] = changed is True

    # Append secret path to result
    result['path'] = module.params['secret_path']

    # Exit with result
    module.exit_json(**result)


def secret_remove(
    secret_path: str,
    db: "PyKeePass",
    db_path: str,
    target: str = 'any',
    recurse: bool = False,
    check_mode: bool = False,
) -> tuple:
    """
    Remove a secret or a group from Keepass and return the removed paths
    Args:
        secret_path: Path of the secret or the group
        db: Keepass database
        db_path: Database path
        target: Indicates what may be removed at the path, any, entry or group.
        recurse: Indicates if a group should be removed with all its content or not.
        check_mode: Indicates if the database should not be written.
    Returns: tuple
    """

    # Init removed paths
    removed = dict(entries=[], groups=[])

    # Check if secret path was not provided
    if secret_path is None or secret_path == '' or secret_path.isspace():
        raise ValueError("secret_path is required")

    # Extract secret path
    path = secret_path.split("/")

    # Remove white spaces
    path = [e for e in path if e]

    # Check if the path is the root group
    if len(path) == 0:
        raise ValueError("the root group cannot be removed")

    # Init entry
    entry = None

    # Find entry if the target allows it
    if target in ('any', 'entry'):
        entry = db.find_entries_by_path(path=path)

    # Init group
    group = None

    # Find group if the target allows it
    if target in ('any', 'group'):
        group = db.find_groups(path=path, first=True)

    # Check if the path matches both an entry and a group
    if entry is not None and group is not None:
        raise ValueError("{0} matches an entry and a group, set target to entry or group".format(secret_path))

    # Return unchanged state if nothing matches the path
    if entry is None and group is None:
        return removed, False

    # Remove the entry or the group
    if entry is not None:
        # Append entry path to the removed paths
        removed['entries'].append(_path_to_string(entry.path))

        # Delete entry if the database should be written
        if not check_mode:
            db.delete_entry(entry)
    else:
        # Check if the group is not empty and not forced to be removed with its content
        if (len(group.entries) > 0 or len(group.subgroups) > 0) and not recurse:
            raise ValueError("group {0} is not empty, set recurse to true".format(secret_path))

        # Append group path and its content paths to the removed paths
        _collect_group_paths(group, removed)

        # Delete group if the database should be written
        if not check_mode:
            db.delete_group(group)

    # Save database if it should be written
    if not check_mode:
        _save_database(db, db_path)

    # Return removed paths
    return removed, True


def _save_database(db: "PyKeePass", db_path: str):
    """
    Save the Keepass database and keep the permissions and the owner of its file
    Args:
        db: Keepass database
        db_path: Database path
    Returns:
    """
    # Read database file attributes
    attributes = os.stat(db_path)

    # Restrict the permissions of the files created while the database is saved
    previous_umask = os.umask(0o077)

    # Save database and restore the permissions mask
    try:
        db.save(db_path)
    finally:
        os.umask(previous_umask)

    # Restore database file permissions
    os.chmod(db_path, stat.S_IMODE(attributes.st_mode))

    # Restore database file owner and group if the user is allowed to
    try:
        os.chown(db_path, attributes.st_uid, attributes.st_gid)
    except PermissionError:
        pass


def _collect_group_paths(group, removed: dict):
    """
    Append the paths of a group, its entries and its sub groups to the removed paths
    Args:
        group: Keepass group
        removed: Dictionary containing the removed entries and groups paths
    Returns:
    """
    # Append group path
    removed['groups'].append(_path_to_string(group.path))

    # Append entries paths
    for entry in group.entries:
        removed['entries'].append(_path_to_string(entry.path))

    # Append sub groups paths
    for subgroup in group.subgroups:
        _collect_group_paths(subgroup, removed)


def _path_to_string(path: list) -> str:
    """
    Convert a Keepass path to a string
    Args:
        path: List containing the path segments
    Returns: str
    """
    # Return path segments joined by a slash
    return "/".join(str(segment) for segment in path)


def main():
    """
    Execute keepass secret_remover module
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
