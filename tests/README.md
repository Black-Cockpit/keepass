# Tests

The collection has four kinds of checks. Each one is a `make` target, and all of them run
inside the `ops.venv` virtual environment, which `make` creates when it is missing.

| Target | What it checks |
| --- | --- |
| `make lint_source_code` | The Python code is formatted and passes the `ruff` lint rules. |
| `make run_unit_tests` | The worker functions and the modules behave as documented. |
| `make run_integration_tests` | The built and installed collection works from a playbook. |
| `make run_sanity_tests` | The module documentation passes `ansible-test sanity`. |
| `make run_tests` | Runs the first three, in that order. |

## Unit And Module Tests

They live in `tests/unit/plugins/modules/`, one file per module, and run with `pytest`.

- **Worker tests** (`test_worker_*`) call the worker functions directly against a real
  database.
- **Module tests** (`test_module_*`) run the module file the way Ansible runs it and check
  the JSON it prints. They cover the arguments, check mode, the failure messages, the
  masking of the database password, and the message shown when `pykeepass` is missing.

Run one file or one test with `pytest` from the repository root:

```bash
source ops.venv/bin/activate
pytest tests/unit/plugins/modules/test_secret_remover.py
pytest -k test_worker_removes_entry
```

## Integration Tests

`tests/integration/playbook.yml` runs every module by its fully qualified name and asserts
each result. `make run_integration_tests` builds the collection, installs it into
`tests.local/collections`, and runs the playbook on localhost against that installed copy.

## Sanity Tests

`make run_sanity_tests` installs the built collection into a temporary directory and runs
`ansible-test sanity` there. The first run needs network access, because `ansible-test`
downloads the requirements of its checks.

## Test Databases

Every database the tests create is written to `tests.local/` at the repository root, with a
random file name. The tests never delete anything from that directory, so a database can be
opened after a failure. Empty it by hand when it grows. It is ignored by git and is not part
of the built collection. The password of every test database is `password`.
