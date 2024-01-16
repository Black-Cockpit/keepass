# Ansible Collection - hasnimehdi91.keepass

This collection provides modules that allows to read data from KeePass file.

## How it works

The secret_reader, group_reader  and secret_writer helps on managing the secrets of a keepass database with the ability to integrate it in automated tasks.
## Installation

Requirements: `python 3`, `pykeepass==4.0.6`

    pip install 'pykeepass==4.0.6' --user
    ansible-galaxy collection install hasnimehdi91.keepass


## Modules

---
- **Module** : `hasnimehdi91.keepass.secret_reader`
  - `db_path`     : Path to KeePass file
  - `db_password` : Password of KeePass file
  - `secret_path` : Path to secret in of KeePass file
---
- **Module** : `hasnimehdi91.keepass.secret_reader`
  - `db_path`     : Path to KeePass file
  - `db_password` : Password of KeePass file
  - `secret_path` : Path to secret in of KeePass file
---
- **Module** : `hasnimehdi91.keepass.secret_writer`
  - `db_path`       : Path to KeePass file
  - `db_password`   : Password of KeePass file
  - `secret_path`   : Path to secret in of KeePass file
  -  `secret_value` : Dictionary containing the secret data. If not provided a empty secret will be created.
  - `secret_value.username`: Secret username
  - `secret_value.password:`: Secret password
  - `secret_value.url:`: Secret password
  - `secret_value.custom_properties:`: Secret customer properties (key, value)
  -  `force`: If set to true the secret will be overridden, Default is false
---

## Usage

#### Read single secret

```yaml
- name: Read secret
  hosts: all
  become: no
  connection: local
  tasks:
  - hasnimehdi91.keepass.secret_reader:
      db_path: "secrets.kdbx"
      db_password: "password"
      secret_path: "foo/bar/secret"
    register: test
  - debug:
      msg: "{{ test.secret }}"
      
```

```bash
ansible-playbook playbook.yml
```
---

#### Read group secrets

```yaml
- name: Read group secrets
  hosts: all
  become: no
  connection: local
  tasks:
  - hasnimehdi91.keepass.group_reader:
      db_path: "secrets.kdbx"
      db_password: "password"
      group_path: "foo/bar"
    register: test
  - debug:
      msg: "{{ test.group }}"
      
```

```bash
ansible-playbook playbook.yml
```
---

#### Write secret

```yaml
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
```

```bash
ansible-playbook playbook.yml
```