# Contributing

- **What this page is:** how to propose a change to the `hasnimehdi91.keepass` collection.
- **How a change lands:** as a pull request against `master`, with its tests and its docs,
  reviewed by a maintainer.

## Before You Start

- **Open an issue first** for a new module or a change of behaviour, at
  <https://github.com/Black-Cockpit/keepass/issues>, so the design is agreed before the work.
- **Security flaws are not issues.** Report them privately, see [SECURITY.md](SECURITY.md).

## Make A Change

1. **Branch:** create a topic branch from `master`.
2. **Environment:** run any `make` target. The virtual environment is built on the first run,
   see [Development Environment](docs/development/development-environment.md).
3. **Code:** follow the rules in [CLAUDE.md](CLAUDE.md). They cover the module skeleton, the
   documentation blocks, the docstrings, and the comments.
4. **Tests:** add or update the tests of the module you change, see
   [Testing](docs/development/testing.md).
5. **Docs:** update the page of the module under `docs/modules/` and its documentation
   blocks, so both say the same thing.
6. **Check:** run `make format_source_code`, then `make run_tests`. Every layer must pass.

## Open The Pull Request

- **One subject per pull request.** A fix and an unrelated refactor are two pull requests.
- **Commit subjects** follow the form `:emoji_shortcode: Past-tense sentence`, for example
  `:100: Fixed secret writer`.
- **Describe the behaviour change** and how you tested it. Say so plainly when a change can
  break an existing playbook.
- **Never commit a real database, password, or secret.** Examples and tests use placeholder
  values only.

## License

By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE)
of this repository.
