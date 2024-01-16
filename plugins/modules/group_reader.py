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
module: group_reader

short_description: Keepass group_reader module

version_added: "1.0.0"

description: 
    This module read a group secrets from keepass database and return a dumped list of dictionaries for the group.

options:
    db_path:
        description: Keepass database path.
        required: true
        type: str
    db_password:
        description: Keepass database password.
        required: true
        type: str
    group_path:
        description: Keepass group path.
        required: true
        type: str
author:
    - Hasni Mehdi (@hasnimehdi91)
    - hasnimehdi@outlook.com
'''

EXAMPLES = r'''
# Read group secrets
- name: Read group secrets
  hasnimehdi91.keepass.group_reader:
    db_path: "keys.kdbx"
    db_password: "password"
    group_path: "/foo/bar"
  register: group
- debug: var=group
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
    description: Groups secrets list
    path:
        description: Group path
        type: str
    group:
        description: List of dict containing the group secrets
        type: [dic]
        returned: always
'''


def run_module():
    """
    Keepass group_reader module
    Returns:
    """
    group_secret_dic = dict()

    # Keepass group_reader module arguments
    module_args = dict(
        db_path=dict(type='str', required=True),
        db_password=dict(type='str', required=True, no_log=True),
        group_path=dict(type='str', required=True),
    )

    # Keepass module result initialization
    result = dict(
        changed=True,
        group=group_secret_dic,
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

        group_secret_dic = group_to_dic(db, module.params['group_path'])
    except Exception as e:
        module.fail_json(msg="Failed to read keepass group secrets", exception=e)

    result['group'] = group_secret_dic
    result['path'] = module.params['group_path']

    # Exit with result
    module.exit_json(**result)


def group_to_dic(db: PyKeePass, group_path: str) -> dict:
    """
    Read group secrets from Keepass and convert them to  list of dictionary [dic]
    Args:
        db: Keepass database
        group_path: Secret path
    Returns: [dic]
    """
    # Init group secrets list
    group_secrets = []

    # Check if the groups path was provided
    if group_path is None or group_path == '' or group_path.isspace():
        raise ValueError("secret_path is required")

    # Extract group path
    path = group_path.split("/")

    # Remove white spaces
    if path is not None and len(path) > 0:
        path = [e for e in path if e]
    else:
        return group_secrets

    # Find group
    group = db.find_groups(path=path, first=True)

    # Check if group exists
    if group is None:
        return group_secrets

    # Extract entries
    entries = group.entries

    # Find all entries and map them to dict and then append them to the group list
    for entry in entries:
        secret = dict()
        entry = db.find_entries_by_path(path=entry.path)
        if entry is None:
            continue

        secret[entry.path[-1]] = dict()

        if entry.username:
            secret[entry.path[-1]]["username"] = entry.username
        if entry.password:
            secret[entry.path[-1]]["password"] = entry.password

        if entry.custom_properties and type(entry.custom_properties) is dict:
            for k in entry.custom_properties:
                secret[entry.path[-1]][k] = entry.custom_properties[k]
        group_secrets.append(secret)

    return group_secrets


def main():
    """
    Execute keepass group_reader module
    Returns:

    """
    run_module()


if __name__ == '__main__':
    """
    Module main
    """
    main()
