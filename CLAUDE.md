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
- Nested keys of a dictionary option are documented under that option
  as `suboptions`, and declared as `options` in the argument spec.
- The `author` list is always:

  ```yaml
  author:
      - Mehdi Hasni (@hasnimehdi91)
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

- A function body is a sequence of blocks. A block is one statement
  or one compound statement: an assignment, a call, an `if`, a `for`,
  a `try`, a `return`. A call or assignment that spans several lines
  is one block.
- Every block is separated from the previous block by one blank line
  and is preceded by a one-line `#` comment: a short capitalised
  phrase that names the block, with no trailing period. The first
  block of a body or of a branch takes the comment without the blank
  line.
- The rule applies at every nesting level: when a branch of an `if`,
  `else`, `for`, `try` or `except` holds several blocks, they are
  separated and commented the same way. A branch that holds a single
  block is covered by the comment of the statement that owns it.

  ```python
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
  if custom_properties is not None and type(custom_properties) is dict:
      for k in custom_properties:
          entry.set_custom_property(key=str(k), value=str(custom_properties[k]))

  # Save database
  db.save(db_path)

  # Return replaced secret
  return _convert_secret_to_dic(path, entry, True)
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
2. The two-line copyright and licence header. The collection is MIT
   licensed, and the licence line is identical in every module:

   ```python
   # Copyright (c) 2023 Black Cockpit LLC <mehdi@black-cockpit.com>
   # SPDX-License-Identifier: MIT
   ```

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

- A new module is added in these places in the same commit:
  `plugins/modules/<module>.py`, the `action_groups.all` list in
  `meta/runtime.yml`, its test file, its page under `docs/modules/`
  with its line in `docs/modules/README.md`, its row in the
  `## Operations` table of the README, its example playbook under
  `docs/examples/`, and its two lines in the sanity ignore file.
- `meta/runtime.yml` holds the lowest supported ansible-core version in
  `requires_ansible`. The README installation section states the same
  version.
- `galaxy.yml` holds the collection version. A release bumps `version`
  there in its own commit.
- Files that must not reach Galaxy are listed in `build_ignore` in
  `galaxy.yml`.
- `requirements.txt` lists direct dependencies only: a version range
  for `ansible` and an exact `==` pin for `pykeepass`. The `pykeepass`
  version in `requirements.txt` equals the version in the README
  installation section.
- `ansible.cfg` is a local development file. It points `library` at
  `./plugins/modules` so the modules run from a checkout without
  installing the collection.

---

## 4. README and docs rules

### 4.1 Written for people

- Docs are written for the people who use and change the collection,
  not for the code. Short sentences, plain words, one idea per
  sentence. A page gives every detail a reader needs to act, and
  nothing they do not.
- Pages stay short. A page that grows past one subject is split, and
  the pages link to each other.
- A page states only what the code does today. A change of behaviour
  changes its page in the same commit.

### 4.2 README

- The README stays at a high level and is the hub of the docs, in this
  fixed order: `# Ansible Collection - hasnimehdi91.keepass` → three
  opening bullets (**What it is**, **How it runs**, **How it is
  shaped**) → `## Architecture` → `## Installation` → `## Operations`
  → `## Documentation` → `## Process And Policy` → `## Scope`.
- `## Architecture` is one Mermaid flowchart of the playbook, the
  modules, the library and the database.
- `## Operations` is a table
  `| Operation | Module | Detailed Description |`, one row per module,
  each linking to the page of the module.
- Details never live in the README. They live on one page under
  `docs/`, and the README links to it.
- No badges, no emoji in headings.

### 4.3 Pages under `docs/`

- Files are `kebab-case.md`, grouped by subject: `docs/architecture/`,
  `docs/modules/`, `docs/development/`, `docs/ci/`, and
  `docs/runbook.md`.
- Every page has one `#` title and `##` sections in Title Case.
- Every page opens with bullets in the form
  `- **Lead-in:** explanation.` that say what the subject is and what
  matters most about it.
- Every page except a hub page holds at least one Mermaid `flowchart`
  with `classDef` colours in the form `fill:#RRGGBB22,stroke:#RRGGBB`.
- Body text is bullet lists of `- **Lead-in:** explanation.`. Options
  and return values are tables.
- Every page closes with a `## Related Documentation` list. A hub page,
  the `README.md` of a `docs/` directory, holds a
  `## Documentation Map` and a `## Reading Path` instead.
- A module page is named after the module with dashes, and has these
  sections in this order: `## Flow`, `## Options`, `## Behaviour`,
  `## Return Values`, `## Examples`, `## Related Documentation`.
- A module page and the `DOCUMENTATION`, `EXAMPLES` and `RETURN`
  blocks of the module say the same thing.
- `docs/runbook.md` lists every `make` target with what it does and
  what it changes. A new target adds its row in the same commit.

### 4.4 Wiki

- The GitHub wiki is generated from the README, `CONTRIBUTING.md`,
  `SECURITY.md` and the pages under `docs/` by `make build_wiki`, and
  published by `make publish_wiki`. A wiki page is never edited by hand.
- A wiki page is named after the title of its source page, so every
  page title is unique.
- Links between pages are relative links to the `.md` file. The build
  turns them into wiki links.

### 4.5 Examples

- `docs/examples/` holds one runnable playbook per module, named
  `<module>.yml`, and a `README.md` that indexes them.
- Every YAML example is valid YAML. Quotes and brackets are closed.
- Examples use placeholder values only.

---

## 5. Test rules

- A change to a module changes its tests in the same commit. A new
  module ships with its test file.
- Unit and module tests live in `tests/unit/plugins/modules/`, one
  `test_<module>.py` per module, and run with `pytest`.
  - Tests named `test_worker_*` call the worker functions directly.
  - Tests named `test_module_*` run the module file as Ansible runs
    it, through `run_module` in `tests/unit/conftest.py`, and check
    the JSON it prints.
- Tests use real databases, never mocks. Every database a test creates
  goes through the `database_path` or `database` fixture, which places
  it in `tests.local/` with a random file name.
- Tests never delete anything from `tests.local/`. The directory is
  emptied by hand.
- Integration tests live in `tests/integration/playbook.yml`. Every
  module call uses the fully qualified collection name, registers its
  result, and is followed by an `assert` task.
- Test functions follow the docstring and inline comment rules of
  section 1.
- The `make` targets are the only entry points: `lint_source_code`,
  `run_unit_tests`, `run_integration_tests`, `run_sanity_tests`, and
  `run_tests`, which runs the first three.

---

## 6. Workflow rules

- Workflow files live in `.github/workflows/`, named in `snake_case`
  after what they do, and open with a comment header that states the
  purpose, the triggers and the requirements.
- A workflow step never holds logic of its own. It runs a `make`
  target, so the same command reproduces the step on a workstation.
- Publishing workflows run on a published GitHub release and on a
  manual run, and carry a `concurrency` group so two runs never
  publish at the same time.
- The collection is published only after the test workflow passes.
- A secret reaches a `make` target through the environment, never on a
  command line, and is never printed.
- Every action is pinned to a major version. Dependabot keeps those
  versions current.
- A new workflow, trigger or secret updates
  `docs/ci/github-actions.md` in the same commit.

---

## 7. Git rules

- Default branch: `master`. Work happens on `snake_case` topic
  branches, merged via pull request.
- Commit subjects: `:emoji_shortcode: Past-tense sentence`,
  capitalised, no scope, no body. Established vocabulary:
  `:100:` fixes and releases, `:alien:` new capabilities,
  `:bulb:` docs and structure.
- A release commit reads `:100: Deploy release v<version>` and carries
  the `galaxy.yml` version bump.
