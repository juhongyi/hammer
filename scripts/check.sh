#!/bin/sh
set -eu

# Run from the repository root. APP_SERVICES can narrow pre-commit checks.
mode=${1:-all}
case "$mode" in
  quick|all) ;;
  *) exit 2 ;;
esac

compose() {
  docker compose --env-file "${COMPOSE_ENV_FILE:-.env.example}" "$@"
}

compose config --quiet
compose run --rm --no-deps presentation-web sh -n /dev/stdin < scripts/check.sh
for service in ${APP_SERVICES:-presentation-web ontology-web presentation-api ontology-api}; do
  case "$service" in
    *-web)
      commands='pnpm install --frozen-lockfile && pnpm lint && pnpm format:check && pnpm architecture'
      if [ "$mode" = all ]; then
        commands="$commands && pnpm test && pnpm build && pnpm typecheck"
      fi
      # Give builds a disposable output directory, separate from the dev server.
      compose run --build --rm --no-deps --volume /workspace/.next "$service" sh -c "$commands"
      ;;
    *-api)
      commands='uv sync --locked && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked lint-imports'
      if [ "$mode" = all ]; then
        commands="$commands && uv run --locked ty check && uv run --locked pytest"
      fi
      compose run --build --rm --no-deps "$service" sh -c "$commands"
      ;;
    *) exit 2 ;;
  esac
done

if [ "$mode" = quick ] && [ "${CHECK_HARNESS:-0}" = 1 ]; then
  compose run --build --rm e2e sh -c 'pnpm install --frozen-lockfile && pnpm lint && pnpm format:check && pnpm typecheck'
fi

if [ "$mode" = all ]; then
  compose up --build --wait --wait-timeout 240
  compose run --build --rm e2e
fi
