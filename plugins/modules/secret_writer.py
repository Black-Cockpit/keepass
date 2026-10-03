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
    from pykeepass import PyKeePass, create_database

    HAS_LIB = True
except (ModuleNotFoundError, NameError):
    HAS_LIB = False
    LIB_IMP_ERR = traceback.format_exc()

DOCUMENTATION = r'''
---
module: secret_writer

short_description: Keepass secret_writer module

version_added: "1.0.0"

description:
    - This module write a secret to a keepass database and return dictionary for the secret.
    - If the database does not exist, a new one will be created.
    - The url of the secret is stored in the database and is not returned.

options:
    db_path:
        description: Keepass database path.
        required: true
        type: str
    db_password:
        description: Keepass database password.
        required: true
        type: str
    secret_path:
        description: Keepass secret path.
        required: true
        type: str
    secret_value:
        description: dict containing the secret data. If not provided a empty secret will be created.
        required: false
        type: dict
        suboptions:
            username:
                description: Secret username.
                required: false
                type: str
            password:
                description: Secret password.
                required: false
                type: str
            url:
                description: Secret url.
                required: false
                type: str
            custom_properties:
                description: Secret custom properties.
                required: false
                type: dict
    force:
        description: If set to true the secret will be overridden.
        required: false
        type: bool
        default: false
author:
    - Mehdi Hasni (@hasnimehdi91)
'''

EXAMPLES = r'''
# Write secret to database
#
# Define secret
- set_fact:
    secret:
        username: "John"
        password: "Doe"
        custom_properties:
            gender: "Male"

# Write secret
- name: Write secret
  hasnimehdi91.keepass.secret_writer:
    db_path: "keys.kdbx"
    db_password: "password"
    secret_path: "/foo/bar"
    secret_value: "{{ secret }}"
    force: false
  register: created_secret
- debug: var=created_secret
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
    description: Secret path
    type: str
    returned: always
secret:
    description: Dictionary containing the secret data, keyed by the secret title
    type: dict
    returned: always
'''


def run_module():
    """
    Keepass secret_writer module
    Returns:
    """
    # Init secret dictionary
    secret_dic = dict()

    # Init changed state
    changed = False

    # Keepass secret_writer module arguments
    module_args = dict(
        db_path=dict(type='str', required=True),
        db_password=dict(type='str', required=True, no_log=True),
        secret_path=dict(type='str', required=True, no_log=False),
        secret_value=dict(
            type='dict',
            required=False,
            no_log=False,
            options=dict(
                username=dict(type='str', required=False),
                password=dict(type='str', required=False, no_log=False),
                url=dict(type='str', required=False),
                custom_properties=dict(type='dict', required=False),
            ),
        ),
        force=dict(type='bool', required=False, default=False),
    )

    # Keepass module result initialization
    result = dict(changed=False, secret=secret_dic, failed=False)

    # Keepass module initialization
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    # Fail if the pykeepass library is missing
    if not HAS_LIB:
        module.fail_json(msg=missing_required_lib("pykeepass"), exception=LIB_IMP_ERR)

    # Return module result in check mode
    if module.check_mode:
        module.exit_json(**result)

    # Open the database and write the secret
    try:
        # Read database path
        db_path = module.params['db_path']

        # Read database password
        db_password = module.params['db_password']

        # Create database if it does not exist
        if not os.path.isfile(db_path):
            create_database(db_path, db_password)

        # Connect to database
        db = PyKeePass(filename=db_path, password=db_password)

        # Init secret value with an empty dictionary when it is omitted
        secret_value = module.params['secret_value'] or {}

        # Init force override
        force = True if (('force' in module.params) and (module.params['force'] is True)) else False

        # Write secret
        secret_dic, changed = secret_write(
            secret_path=module.params['secret_path'],
            db=db,
            db_path=db_path,
            username=secret_value.get('username'),
            password=secret_value.get('password'),
            url=secret_value.get('url'),
            custom_properties=secret_value.get('custom_properties'),
            force=force,
        )
    except Exception as e:
        # Fail with the error message and its traceback
        module.fail_json(msg="Failed to write keepass secret: {0}".format(str(e)), exception=traceback.format_exc())

    # Append secret to result
    result['secret'] = secret_dic

    # Append changed state to result
    result['changed'] = changed is True

    # Append secret path to result
    result['path'] = module.params['secret_path']

    # Exit with result
    module.exit_json(**result)


def secret_write(
    secret_path: str,
    db: "PyKeePass",
    db_path: str,
    username: str = None,
    password: str = None,
    url: str = None,
    custom_properties: dict = None,
    force: bool = False,
) -> (dict, bool):
    """
    Write a secret to Keepass and return its data as a dict
    Args:
        secret_path: Secret path
        db: Keepass database
        db_path: Database path
        username: Secret username
        password: Secret password
        url: Secret url
        url: Secret url
        custom_properties: Secret custom properties
        force: Indicates if the secret should be replaced if it exists or not.
    Returns: dict
    """

    # Default an unset username to an empty string, as pykeepass cannot handle None
    username = username or ''

    # Default an unset password to an empty string, as pykeepass cannot handle None
    password = password or ''

    # Check if secret path was not provided
    if secret_path is None or secret_path == '' or secret_path.isspace():
        raise ValueError("secret_path is required")

    # Extract secret path
    path = secret_path.split("/")

    # Remove white spaces
    if path is not None and len(path) > 1:
        path = [e for e in path if e]

    # Write the secret in the root group if the path has no groups
    elif len(path) == 1:
        # Fetch entry
        entry = db.find_entries_by_path(path=path)

        # Return, replace or create the secret
        if entry is not None and not force:
            # Return entry of it exists and not forced to be replaced
            return _convert_secret_to_dic(path, entry, False)
        elif entry is not None and force:
            # Delete the existing entry as it is forced to be replaced
            db.delete_entry(entry)

            # Create the replacement entry
            entry = db.add_entry(
                destination_group=db.root_group,
                title=path[len(path) - 1],
                username=username,
                password=password,
                url=url,
                force_creation=True,
            )

            # Set entry custom properties
            if custom_properties is not None and isinstance(custom_properties, dict):
                for k in custom_properties:
                    entry.set_custom_property(key=str(k), value=str(custom_properties[k]))

            # Save database
            _save_database(db, db_path)

            # Return replaced secret
            return _convert_secret_to_dic(path, entry, True)
        else:
            # Create new secret
            entry = db.add_entry(
                destination_group=db.root_group,
                title=path[len(path) - 1],
                username=username,
                password=password,
                url=url,
                force_creation=True,
            )

            # Set entry custom properties
            if custom_properties and isinstance(custom_properties, dict):
                for k in custom_properties:
                    entry.set_custom_property(key=str(k), value=str(custom_properties[k]))

            # Save database
            _save_database(db, db_path)

            # Return created secret
            return _convert_secret_to_dic(path, entry, True)
    else:
        # Return an empty result when the path has no segment
        return None, False

    # Init group path
    group_path = []

    # Init parent group with the root group
    parent_group = db.root_group

    # Init depth counter
    i = 0

    # Create parent and subsequent groups if they don't exist and then create the secret
    for item in path:
        # Append item to the group path
        group_path.append(item)

        # Break on the last item as it is the secret name
        if item == path[len(path) - 1] and i == (len(path) - 1):
            break

        # Fetch group
        group = db.find_groups(path=group_path, first=True)

        # Create group if it does not exist and move to next node
        if group is None:
            parent_group = db.add_group(destination_group=parent_group, group_name=item)
        else:
            parent_group = group

        # Increment depth counter
        i = i + 1

    # Fetch entry
    entry = db.find_entries_by_path(path=path)

    # Return, replace or create the secret
    if entry is not None and not force:
        # Return entry of it exists and not forced to be replaced
        return _convert_secret_to_dic(path, entry, False)
    elif entry is not None and force:
        # Delete the existing entry as it is forced to be replaced
        db.delete_entry(entry)

        # Create the replacement entry
        entry = db.add_entry(
            destination_group=parent_group, title=path[len(path) - 1], username=username, password=password, url=url
        )

        # Set entry custom properties
        if custom_properties and isinstance(custom_properties, dict):
            for k in custom_properties:
                entry.set_custom_property(key=str(k), value=str(custom_properties[k]))

        # Save database
        _save_database(db, db_path)
    else:
        # Create new secret
        entry = db.add_entry(
            destination_group=parent_group, title=path[len(path) - 1], username=username, password=password, url=url
        )

        # Set entry custom properties
        if custom_properties and isinstance(custom_properties, dict):
            for k in custom_properties:
                entry.set_custom_property(key=str(k), value=str(custom_properties[k]))

        # Save database
        _save_database(db, db_path)

    # Return written secret
    return _convert_secret_to_dic(path, entry, True)


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


def _convert_secret_to_dic(path: [], entry: dict, changed: bool) -> (dict, bool):
    # Init secret value
    secret = dict()

    # Append secret key
    secret[path[-1]] = dict()

    # Append secret username
    if entry.username:
        secret[path[-1]]["username"] = entry.username

    # Append secret password
    if entry.password:
        secret[path[-1]]["password"] = entry.password

    # Append secret custom properties
    if entry.custom_properties and isinstance(entry.custom_properties, dict):
        for k in entry.custom_properties:
            secret[path[-1]][k] = entry.custom_properties[k]

    # Return secret
    return secret, changed


def main():
    """
    Execute keepass secret_writer module
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
