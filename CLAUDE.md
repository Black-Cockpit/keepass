# CLAUDE.md — hasnimehdi91.keepass Ansible collection

This document is **rules only**. It defines how every artifact in this
repository is written: the Ansible modules, their embedded
documentation, the README, the examples, and the collection metadata.
Every rule applies to every commit.

The collection is deliberately small. Each module is one self-contained
Python file under `plugins/modules/` that talks to a KeePass database
through `pykeepass`. There is no shared `module_utils` code, no action
plugin, and no lookup plugin.

---

## 1. Documentation-first · hard rule (non-negotiable)

> **Every module is a documented artifact. Every module ships its
> `DOCUMENTATION`, `EXAMPLES` and `RETURN` blocks, every function
> carries a docstring, and every logical step inside a function carries
> its own comment. Undocumented options, functions or steps do not
> ship.**

### 1.1 Embedded Ansible documentation

- The three blocks are module-level raw strings (`r'''`), declared in
  the fixed order `DOCUMENTATION` → `EXAMPLES` → `RETURN`, after the
  guarded import and before the first function.
- `DOCUMENTATION` opens with `---` and carries these keys in this
  order: `module`, `short_description`, `version_added`,
  `description`, `options`, `author`.
- `module` equals the file name without `.py`.
- `short_description` follows the form `Keepass <module_name> module`.
- `description` states what the module does and what it returns, in
  the present tense.
- Every option is documented with `description`, `required` and `type`,
  in that order. `default` is added when the argument spec sets one.
  Option descriptions are short sentences that end with a period.
- Nested keys of a dictionary option are documented under that option.
- The `author` list is always:

  ```yaml
  author:
      - Hasni Mehdi (@hasnimehdi91)
      - hasnimehdi@outlook.com
  ```

- `EXAMPLES` opens with a `#` comment naming the scenario. Every task
  has a `name:`, calls the module by its fully qualified collection
  name (`hasnimehdi91.keepass.<module>`), registers its result, and is
  followed by a `debug` task that prints the registered variable.
- `RETURN` opens with the comment
  `# These are the attributes that can be returned by the module.` and
  documents `changed` and `failed` first, then the payload keys.
- The documented options are identical to the `argument_spec`, and the
  documented return keys are identical to the keys the module puts in
  `result`. A change to one changes the other in the same commit.

### 1.2 Docstrings

- Every function has a triple-double-quoted docstring. The summary
  starts on the line after the opening quotes.
- The house format is:

  ```python
  def secret_to_dic(db: PyKeePass, secret_path: str) -> dict:
      """
      Read secret from Keepass and convert it to a dic
      Args:
          db: Keepass database
          secret_path: Secret path
      Returns: dic
      """
  ```

- `Args:` lists every parameter exactly once, in signature order, as
  `name: Description`.
- `Returns:` names the returned type on the same line. Functions that
  return nothing keep an empty `Returns:` line.
- Every function signature carries type hints for its parameters and
  its return value.

### 1.3 Inline comments

- Every logical step inside a function is preceded by a one-line `#`
  comment: a short capitalised phrase that names the step, with no
  trailing period.

  ```python
  # Find secret
  entry = db.find_entries_by_path(path=path)

  # Check if secret does not exist
  if entry is None:
      return secret
  ```

- Comments state what the step does. They never narrate history,
  never explain who asked for a change, and never describe states the
  code is not in.
- A comment never drifts from the code below it. If the step changes,
  the comment changes in the same commit.
- Dead code is deleted, not commented out.

---

## 2. Module rules

### 2.1 File skeleton

Every module follows the same top-to-bottom order:

1. `#!/usr/bin/python` on line 1, then a blank line.
2. The two-line copyright and licence header.
3. `from __future__ import (absolute_import, division, print_function)`.
4. Standard library imports, then the `ansible.module_utils.basic`
   import.
5. `__metaclass__ = type` and `LIB_IMP_ERR = None`.
6. The guarded third-party import (§2.2).
7. `DOCUMENTATION`, `EXAMPLES`, `RETURN`.
8. `run_module()`, then the worker functions, then `main()`, then the
   `if __name__ == '__main__':` guard that calls `main()`.

### 2.2 Guarded third-party import

- `pykeepass` is the only third-party import, and it is always guarded:

  ```python
  try:
      from pykeepass import PyKeePass

      HAS_LIB = True
  except (ModuleNotFoundError, NameError):
      HAS_LIB = False
      LIB_IMP_ERR = traceback.format_exc()
  ```

- The exception types are a tuple. The form
  `except ModuleNotFoundError or NameError` is never written.
- `run_module()` fails with
  `module.fail_json(msg=missing_required_lib("pykeepass"), exception=LIB_IMP_ERR)`
  when `HAS_LIB` is false, before any other work.

### 2.3 `run_module()` sequence

`run_module()` performs these steps in this order, each under its own
comment:

1. Declare `module_args` with `dict(...)` calls.
2. Initialise `result` with `changed`, the payload key and `failed`.
3. Build `AnsibleModule` with `supports_check_mode=True`.
4. Fail when the library is missing.
5. Exit with `result` when `module.check_mode` is true, before the
   database is opened.
6. Open the database and call the worker function inside one
   `try` / `except Exception` that ends in `module.fail_json`.
7. Put the payload and `path` into `result`.
8. Call `module.exit_json(**result)`.

`main()` only calls `run_module()`. The KeePass logic lives in worker
functions that take the open database as a parameter, never in
`run_module()` itself.

### 2.4 Naming

- Module files are `snake_case`, `<noun>_<role>.py`: `secret_reader`,
  `group_reader`, `secret_writer`.
- Functions and variables are `snake_case`. Helpers private to a
  module start with an underscore (`_convert_secret_to_dic`).
- Shared options keep the same name in every module: `db_path`,
  `db_password`, and `<noun>_path` for the target inside the database.
- Failure messages follow `Failed to <verb> keepass <noun>`.

### 2.5 Paths and return shape

- A path is a `/`-separated string. It is split on `/` and empty
  segments are dropped, so `foo/bar` and `/foo/bar` address the same
  target.
- An empty or whitespace-only path raises `ValueError`.
- A secret is returned as a dictionary keyed by the entry title:
  `{<title>: {username, password, <custom property>...}}`. `username`
  and `password` are present only when they are set on the entry.
- A group is returned as a list of those dictionaries.
- A target that does not exist returns the empty payload. It is not a
  failure.

### 2.6 Secrets

- Every argument that carries a secret value sets `no_log=True` in the
  argument spec.
- No real database, password or secret value is committed. `*.kdbx`
  files are gitignored and excluded from the built collection.
- Examples use placeholder values only (`keys.kdbx`, `password`,
  `/foo/bar`).

---

## 3. Collection metadata rules

- A new module is added in four places in the same commit:
  `plugins/modules/<module>.py`, the `action_groups.all` list in
  `meta/runtime.yml`, the `## Modules` and `## Usage` sections of the
  README, and `docs/examples/`.
- `galaxy.yml` holds the collection version. A release bumps `version`
  there in its own commit.
- Files that must not reach Galaxy are listed in `build_ignore` in
  `galaxy.yml`.
- `requirements.txt` pins every package with an exact `==` version.
  The `pykeepass` version in `requirements.txt` equals the version in
  the README installation section.
- `ansible.cfg` is a local development file. It points `library` at
  `./plugins/modules` so the modules run from a checkout without
  installing the collection.

---

## 4. README and docs rules

- The README is short and operational, in this fixed order:
  `# Ansible Collection - hasnimehdi91.keepass` → `## How it works` →
  `## Installation` → `## Modules` → `## Usage`. No badges, no emoji in
  headings.
- `## Modules` lists every module as `- **Module** : \`<fqcn>\``
  followed by one indented bullet per option, `\`option\` : description`.
  Entries are separated by `---`.
- `## Usage` has one `####` subsection per module. Each subsection
  holds a fenced `yaml` example followed by the fenced `bash` command
  that runs it.
- README examples match the module's `EXAMPLES` block.
- `docs/examples/playbook.yml` is a runnable playbook: one play per
  module, each with `hosts: all`, `become: no` and
  `connection: local`.
- Every YAML example is valid YAML. Quotes and brackets are closed.

---

## 5. Git rules

- Default branch: `master`. Work happens on `snake_case` topic
  branches, merged via pull request.
- Commit subjects: `:emoji_shortcode: Past-tense sentence`,
  capitalised, no scope, no body. Established vocabulary:
  `:100:` fixes and releases, `:alien:` new capabilities,
  `:bulb:` docs and structure.
- A release commit reads `:100: Deploy release v<version>` and carries
  the `galaxy.yml` version bump.
