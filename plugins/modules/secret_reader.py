#!/usr/bin/python

# Copyright: (c) 2023, Hasni Mehdi <hasnimehdi@outlook.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)

import traceback
from ansible.module_utils.basic import AnsibleModule, missing_required_lib

__metaclass__ = type
LIB_IMP_ERR = None
try:
    from pykeepass import PyKeePass

    HAS_LIB = True
except ModuleNotFoundError or NameError:
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
    - Hasni Mehdi (@hasnimehdi91)
    - hasnimehdi@outlook.com
'''

EXAMPLES = r'''
# Pass in a message
- name: Test with a message
  keepass.reader.secret_reader:
    db_path: "keys.kdbx"
    db_password: "password"
    secret_path: "/foo/bar"
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
changed:
    description: The state of the task.
    type: bool
    returned: always
failed:
    description: Indicate if the task failed
    type: bool
    returned: always
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
    secret_dic = dict()

    # Keepass secret_reader module arguments
    module_args = dict(
        db_path=dict(type='str', required=True),
        db_password=dict(type='str', required=True, no_log=True),
        secret_path=dict(type='str', required=True),
    )

    # Keepass module result initialization
    result = dict(
        changed=True,
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
        db = PyKeePass(filename=db_path, password=db_password)

        secret_dic = secret_to_dic(db, module.params['secret_path'])
    except Exception as e:
        module.fail_json(msg="Failed to read keepass secret", exception=e)

    result['secret'] = secret_dic

    # Exit with result
    module.exit_json(**result)


def secret_to_dic(db: PyKeePass, secret_path: str) -> dict:
    """
    Read secret from Keepass and convert it to a dic
    Args:
        db: Keepass database
        secret_path: Secret path
    Returns: dic
    """
    secret = dict()
    if secret_path is None or secret_path == '' or secret_path.isspace():
        raise ValueError("secret_path is required")
    path = secret_path.split("/")
    entry = db.find_entries_by_path(path=path)
    if entry is None:
        return secret

    secret[path[-1]] = dict()
    if entry.username:
        secret[path[-1]]["username"] = entry.username
    if entry.password:
        secret[path[-1]]["password"] = entry.password
    if entry.custom_properties and type(entry.custom_properties) is dict:
        for k in entry.custom_properties:
            secret[path[-1]][k] = entry.custom_properties[k]
    return secret


def main():
    """
    Execute keepass secret_reader module
    Returns:

    """
    run_module()


if __name__ == '__main__':
    """
    Module main
    """
    main()
