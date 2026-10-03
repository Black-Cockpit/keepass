# Security

- **What this page is:** how to report a security flaw in the `hasnimehdi91.keepass`
  collection, and what the collection does and does not protect.
- **Which versions are fixed:** the latest version published on Ansible Galaxy.

## Report A Vulnerability

- **Report privately.** Do not open a public issue or pull request for a security flaw.
- **Where:** email <mehdi@black-cockpit.com>.
- **What to include:** the version of the collection, of Ansible, and of `pykeepass`, what
  you observed, and the smallest playbook that shows it. Never include a real database, a
  real password, or a real secret.

## What The Collection Protects

- **The database password:** `db_password` is masked in the task output and in the logs of
  every module.
- **Existing data:** a database, a secret, or a group that is not empty is never replaced or
  removed unless the task asks for it with `force` or `recurse`.
- **File permissions:** `create_database` creates the database readable and writable by its
  owner only, unless `mode` says otherwise. `secret_writer` and `secret_remover` keep the
  permissions of the file when they save it.

## What You Must Protect

- **Returned secrets are in clear text.** `secret_reader`, `group_reader`, and
  `secret_writer` return usernames, passwords, and custom properties. Set `no_log: true` on
  every task that reads, writes, registers, or prints a secret.
- **`secret_value` is not masked.** The content passed to `secret_writer` appears in the task
  output unless the task sets `no_log: true`.
- **The database password is yours to store.** Take `db_password` from Ansible Vault or from
  a prompt, never from a file committed in clear text.
- **The database file is as safe as its host.** Keep it out of git, and restrict its
  permissions.
