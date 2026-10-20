# Development Guidelines

- Run dependency installation, development, and verification inside Docker
  Compose. Host Lefthook invokes container commands.
- If a host port is occupied, select a free arbitrary port through the
  Compose environment variables.
- For every change, start with a failing test or automated check, make it
  pass with minimal changes, then refactor.
- Apply SOLID, DRY, KISS, and YAGNI pragmatically. Keep responsibilities
  focused, changes small, and abstractions justified by actual needs.
- Follow the dependency boundaries defined in each web app's
  `.dependency-cruiser.cjs` and each API's `pyproject.toml`.
- Read `lefthook.yaml` for checks and tests. Run relevant checks during
  development and the full `pre-push` suite before opening a PR.
- Run each web app's `e2e/` Playwright tests inside its web service.
- Ask the user before implementing changes to architecture, layers,
  or major dependencies.
- Create atomic commits, each containing one coherent, independently
  verifiable change.
- Write commit messages and PR titles as natural English sentences without
  prefixes such as `feat:` or `docs:`.
