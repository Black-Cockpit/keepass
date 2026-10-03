# Release

- **What it is:** the steps that turn the repository into a new version of the collection on
  Ansible Galaxy.
- **Who does it:** a maintainer with rights on the `hasnimehdi91` namespace of Galaxy.
- **What cannot be undone:** a published version cannot be replaced. A mistake is fixed by
  publishing a higher version.

## Flow

```mermaid
flowchart LR
    tests["make run_tests"] --> bump["Bump version<br/>in galaxy.yml"]
    bump --> build["make build_collection"]
    build --> artifact["dist/<br/>hasnimehdi91-keepass-version.tar.gz"]
    artifact --> publish["Publish to<br/>Ansible Galaxy"]

    classDef step fill:#4477DD22,stroke:#4477DD
    classDef file fill:#B7791F22,stroke:#B7791F
    classDef out fill:#2E7D3222,stroke:#2E7D32
    class tests,bump,build step
    class artifact file
    class publish out
```

## Steps

1. **Test:** run `make run_tests`. Every layer must pass.
2. **Version:** set `version` in `galaxy.yml`. A new module or option raises the middle
   number, a fix raises the last one.
3. **Commit:** commit the version bump alone, with the subject
   `:100: Deploy release v<version>`.
4. **Build:** run `make build_collection`. The artifact is written to `dist/`.
5. **Publish:** upload the artifact with `ansible-galaxy collection publish`, using the Galaxy
   API token of the namespace.

## What The Artifact Contains

- **Included:** `plugins/`, `meta/`, `docs/`, `README.md`, and `LICENSE`.
- **Excluded:** the tests, the virtual environment, the `Makefile`, the scripts, the
  configuration files, and every database. The list is `build_ignore` in `galaxy.yml`.

## Related Documentation

- [Testing](testing.md)
- [Runbook](../runbook.md), every `make` target.
