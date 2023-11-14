# Ansible Collection - keepass.reader

This collection provides modules that allows to read data from KeePass file.

## How it works

The secret_reader module, read secret based on a given path and covert its data to a dictionary.

## Installation

Requirements: `python 3`, `pykeepass==4.0.6`

    pip install 'pykeepass==4.0.6' --user
    ansible-galaxy collection install keepass.reader


## Variables

- `db_path`     : Path to KeePass file
- `db_password` : Password of KeePass file
- `secret_path` : Path to secret in of KeePass file


## Usage

```yaml
- name: Test
  hosts: all
  become: no
  connection: local
  tasks:
  - keepass.reader.secret_reader:
      db_path: "secrets.kdbx"
      db_password: "password"
      secret_path: "foo/bar"
    register: test
  - debug:
      msg: "{{ test.secret }}"
      
```

```bash
ansible-playbook playbook.yml
```