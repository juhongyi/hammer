# Development Guidelines

## Execution Environment
- Run dependency installation, applications, tests, linting, type checks, and builds inside Docker Compose containers.
- Git and Lefthook may run on the host.
- If a Compose host port conflicts, temporarily use an available host port while keeping the container port unchanged.

## Development Principles
- TDD: For features and bug fixes, follow failing test → minimal implementation → refactoring.
- Validate configuration and documentation changes with the relevant checks.
- KISS/YAGNI: Choose the simplest solution that meets current requirements; avoid speculative abstractions.
- Minimal changes: Keep changes focused on the request and avoid unrelated refactoring.
- Single responsibility and clear naming: Keep functions and modules focused, with names that express their purpose.
- Abstract proven duplication: Extract shared code only after a recurring pattern is established.

## Git Workflow
- Keep each commit atomic and focused on one logical change.
- Do not use prefixes such as `feat:` or `docs:` in commit messages or PR titles.
- Pass all pre-commit checks before committing and all pre-push checks before pushing.
