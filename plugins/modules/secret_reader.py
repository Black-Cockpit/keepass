#!/usr/bin/python

# Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
# SPDX-License-Identifier: MIT
from __future__ import absolute_import, division, print_function

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
module: secret_reader

short_description: Keepass secret_reader module

version_added: "1.0.0"

description: This module read from keepass database and return a dumped dictionary for the secret.

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
author:
    - Mehdi Hasni (@hasnimehdi91)
    - mehdi@black-cockpit.com
'''

EXAMPLES = r'''
# Read secret
- name: Read secret
  hasnimehdi91.keepass.secret_reader:
    db_path: "keys.kdbx"
    db_password: "password"
    secret_path: "/foo/bar"
  register: secret
- debug: var=secret
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
        type: dic
        returned: always
'''


def run_module():
    """
    Keepass secret_reader module
    Returns:
    """
    # Init secret dictionary
    secret_dic = dict()

    # Keepass secret_reader module arguments
    module_args = dict(
        db_path=dict(type='str', required=True),
        db_password=dict(type='str', required=True, no_log=True),
        secret_path=dict(type='str', required=True),
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

    # Open the database and read the secret
    try:
        # Read database path
        db_path = module.params['db_path']

        # Read database password
        db_password = module.params['db_password']

        # Connect to database
        db = PyKeePass(filename=db_path, password=db_password)

        # Read secret
        secret_dic = secret_to_dic(db, module.params['secret_path'])
    except Exception as e:
        # Fail with the error message and its traceback
        module.fail_json(msg="Failed to read keepass secret: {0}".format(str(e)), exception=traceback.format_exc())

    # Append secret to result
    result['secret'] = secret_dic

    # Append secret path to result
    result['path'] = module.params['secret_path']

    # Exit with result
    module.exit_json(**result)


def secret_to_dic(db: "PyKeePass", secret_path: str) -> dict:
    """
    Read secret from Keepass and convert it to a dic
    Args:
        db: Keepass database
        secret_path: Secret path
    Returns: dic
    """

    # Init secret value
    secret = dict()

    # Check if path is not provided
    if secret_path is None or secret_path == '' or secret_path.isspace():
        raise ValueError("secret_path is required")

    # Extract secret path
    path = secret_path.split("/")

    # Remove white spaces
    if path is not None and len(path) > 0:
        path = [e for e in path if e]
    else:
        return secret

    # Find secret
    entry = db.find_entries_by_path(path=path)

    # Check if secret does not exist
    if entry is None:
        return secret

    # Append secret key
    secret[path[-1]] = dict()

    # Append secret username
    if entry.username:
        secret[path[-1]]["username"] = entry.username

    # Append secret password
    if entry.password:
        secret[path[-1]]["password"] = entry.password

    # Append secret custom properties
    if entry.custom_properties and type(entry.custom_properties) is dict:
        for k in entry.custom_properties:
            secret[path[-1]][k] = entry.custom_properties[k]

    # Return secret
    return secret


def main():
    """
    Execute keepass secret_reader module
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
