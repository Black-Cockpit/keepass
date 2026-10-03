# Architecture

- **What this directory holds:** the two pages that explain how the collection works. One
  shows the parts and how a task flows through them, the other shows how a path is read and
  what the modules return.
- **How they relate:** the high level page names the parts, the paths page describes the data
  that moves between them. Every module page builds on both.

## Documentation Map

- [High Level Architecture](high-level-architecture.md): the playbook, the five modules, the
  `pykeepass` library, the database file, and where a module runs.
- [Paths And Return Values](paths-and-return-values.md): how a path addresses a secret or a
  group, the shape of a returned secret, and what a missing target returns.

## Reading Path

- **First,** the [High Level Architecture](high-level-architecture.md), to place every part.
- **Second,** [Paths And Return Values](paths-and-return-values.md), to read and write the
  data the modules exchange.
- **Then,** the [module pages](../modules/README.md), one per module.
