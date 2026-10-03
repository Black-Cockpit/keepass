# Modules

- **What this directory holds:** one page per module of the collection, with its options, its
  behaviour, what it returns, and examples.
- **How to call a module:** by its fully qualified name, `hasnimehdi91.keepass.<module>`.
- **What they share:** every module takes `db_path` and `db_password`, masks the password in
  its output, and supports check mode.

## Documentation Map

- [create_database](create-database.md): creates a fresh, empty database.
- [secret_writer](secret-writer.md): writes a secret, and creates the groups of its path.
- [secret_reader](secret-reader.md): reads one secret.
- [group_reader](group-reader.md): reads the secrets of one group.
- [secret_remover](secret-remover.md): removes a secret or a group.

## Reading Path

- **First,** [Paths And Return Values](../architecture/paths-and-return-values.md), which
  every module page relies on.
- **To store secrets,** [create_database](create-database.md), then
  [secret_writer](secret-writer.md).
- **To use secrets,** [secret_reader](secret-reader.md) and [group_reader](group-reader.md).
- **To clean up,** [secret_remover](secret-remover.md).
