#!/usr/bin/python

# Copyright: (c) 2023, Hasni Mehdi <hasnimehdi@outlook.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)

import os.path
import traceback

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

__metaclass__ = type
LIB_IMP_ERR = None
try:
    from pykeepass import PyKeePass, create_database

    HAS_LIB = True
except ModuleNotFoundError or NameError:
    HAS_LIB = False
    LIB_IMP_ERR = traceback.format_exc()

DOCUMENTATION = r'''
---
module: secret_writer

short_description: Keepass secret_writer module

version_added: "1.0.0"

description: 
    This module write a secret to a keepass database and return dictionary for the secret.
    Note: If the database does not exist, a new one will be created.

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
        username:
            description: Secret username
            type: str
            required: false
        password:
            description: Secret password
            type: str
            required: false
        url:
            description: Secret url
            type: str
            required: false
        custom_properties:
            description: Secret custom properties
            type: dict
            required: false
    force:
        description: If set to true the secret will be overridden
        required: false
        type: bool
        default: false
author:
    - Hasni Mehdi (@hasnimehdi91)
    - hasnimehdi@outlook.com
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
    secret_value: "{{ secret }}
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
data:
    description: Secret data.
    path:
        description: Secret path
        type: str
    secret:
        description: Dictionary containing the secret data
        type: dict
        returned: always
'''


def run_module():
    """
    Keepass secret_writer module
    Returns:
    """
    secret_dic = dict()
    changed = False

    # Keepass secret_writer module arguments
    module_args = dict(
        db_path=dict(type='str', required=True),
        db_password=dict(type='str', required=True, no_log=False),
        secret_path=dict(type='str', required=True),
        secret_value=dict(
            type='dict',
            required=False,
            no_log=False,
            username=dict(type='str', required=False),
            password=dict(type='str', required=False, no_log=False),
            url=dict(type='str', required=False),
            custom_properties=dict(type='dict', required=False)
        ),
        force=dict(type='bool', required=False, default=False)
    )

    # Keepass module result initialization
    result = dict(
        changed=False,
        secret=secret_dic,
        failed=False
    )

    # Keepass module initialization
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if not HAS_LIB:
        module.fail_json(msg=missing_required_lib("pykeepass"), exception=LIB_IMP_ERR)

    # Return module result
    if module.check_mode:
        module.exit_json(**result)

    try:
        db_path = module.params['db_path']
        db_password = module.params['db_password']

        # Create database if it does not exist
        if not os.path.isfile(db_path):
            create_database(db_path, db_password)

        # Connect to database
        db = PyKeePass(filename=db_path, password=db_password)

        # Init secret username
        secret_username = module.params['secret_value']['username'] if (
                ('secret_value' in module.params) and ('username' in module.params['secret_value'])) else None

        # Init secret password
        secret_password = module.params['secret_value']['password'] if (
                ('secret_value' in module.params) and ('password' in module.params['secret_value'])) else None

        # Init secret url
        secret_url = module.params['secret_value']['url'] if (
                ('secret_value' in module.params) and ('url' in module.params['secret_value'])) else None

        # Init secret custom_properties
        secret_custom_properties = module.params['secret_value']['custom_properties'] if (
                ('secret_value' in module.params) and ('custom_properties' in module.params['secret_value'])) else None

        # Init force override
        force = True if (('force' in module.params) and (module.params['force'] is True)) else False

        secret_dic, changed = secret_write(secret_path=module.params['secret_path'], db=db, db_path=db_path,
                                           username=secret_username, password=secret_password, url=secret_url,
                                           custom_properties=secret_custom_properties, force=force)
    except Exception as e:
        module.fail_json(msg="Failed to write keepass secret", exception=e)

    result['secret'] = secret_dic
    result['changed'] = changed is True
    result['path'] = module.params['secret_path']

    # Exit with result
    module.exit_json(**result)


def secret_write(secret_path: str, db: PyKeePass, db_path: str, username: str = None, password: str = None,
                 url: str = None, custom_properties: dict = None, force: bool = False) -> (dict, bool):
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

    # Check if secret path was not provided
    if secret_path is None or secret_path == '' or secret_path.isspace():
        raise ValueError("secret_path is required")

    path = secret_path.split("/")

    # Remove white spaces
    if path is not None and len(path) > 1:
        path = [e for e in path if e]

    # Write the secret in the root group if the path has no groups
    elif len(path) == 1:
        # Fetch entry
        entry = db.find_entries_by_path(path=path)

        if entry is not None and not force:
            # Return entry of it exists and not forced to be replaced
            return _convert_secret_to_dic(path, entry, False)
        elif entry is not None and force:
            # Replace entry it is forced
            db.delete_entry(entry)
            entry = db.add_entry(destination_group=db.root_group, title=path[len(path) - 1], username=username, password=password,
                                 url=url, force_creation=True)
            if custom_properties is not None and type(custom_properties) is dict:
                for k in custom_properties:
                    entry.set_custom_property(key=str(k), value=str(custom_properties[k]))
            db.save(db_path)
            return _convert_secret_to_dic(path, entry, True)
        else:
            # Create new secret
            entry = db.add_entry(destination_group=db.root_group, title=path[len(path) - 1], username=username, password=password,
                                 url=url, force_creation=True)
            if custom_properties and type(custom_properties) is dict:
                for k in custom_properties:
                    entry.set_custom_property(key=str(k), value=str(custom_properties[k]))
            db.save(db_path)
            return _convert_secret_to_dic(path, entry, True)
    else:
        return None, False

    # Init group path
    group_path = []

    # Init parent group
    parent_group = None

    # Init depth counter
    i = 0

    # Create parent and subsequent groups if they don't exist and then create the secret
    for item in path:
        group_path.append(item)
        # Break on the last item as it is the secret name
        if item == path[len(path) - 1] and i == (len(path) - 1):
            break

        # Fetch group
        group = db.find_groups(path=group_path, first=True)

        # Create group if it does not exist and move to next node
        if group is None:
            if parent_group is None:
                parent_group = db.root_group
            parent_group = db.add_group(destination_group=parent_group, group_name=item)
        else:
            parent_group = group
        i = i + 1

    # Fetch entry
    entry = db.find_entries_by_path(path=path)

    if entry is not None and not force:
        # Return entry of it exists and not forced to be replaced
        return _convert_secret_to_dic(path, entry, False)
    elif entry is not None and force:
        # Replace entry it is forced
        db.delete_entry(entry)

        entry = db.add_entry(destination_group=parent_group, title=path[0], username=username, password=password,
                             url=url)
        if custom_properties and type(custom_properties) is dict:
            for k in custom_properties:
                entry.set_custom_property(key=str(k), value=str(custom_properties[k]))
        db.save(db_path)
    else:
        # Create new secret
        entry = db.add_entry(destination_group=parent_group, title=path[0], username=username, password=password,
                             url=url)
        if custom_properties and type(custom_properties) is dict:
            for k in custom_properties:
                entry.set_custom_property(key=str(k), value=str(custom_properties[k]))
        db.save(db_path)

    return _convert_secret_to_dic(path, entry, True)


def _convert_secret_to_dic(path: [], entry: dict, changed: bool) -> (dict, bool):
    secret = dict()
    # Append secret key
    secret[path[-1]] = dict()

    # Append secret username, password and extra attributes
    if entry.username:
        secret[path[-1]]["username"] = entry.username
    if entry.password:
        secret[path[-1]]["password"] = entry.password
    if entry.custom_properties and type(entry.custom_properties) is dict:
        for k in entry.custom_properties:
            secret[path[-1]][k] = entry.custom_properties[k]

    # Return secret
    return secret, changed


def main():
    """
    Execute keepass secret_writer module
    Returns:

    """
    run_module()


if __name__ == '__main__':
    """
    Module main
    """
    main()
