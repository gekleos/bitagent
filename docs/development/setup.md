# Local development setup

A local BitAgent dev environment needs Go, Python, Postgres, and the [Task](https://taskfile.dev) build tool. The repo ships a Nix flake for reproducibility; manual install also works.

This page is for contributors. For runtime configuration see [configuration.md](../configuration.md).

## Prerequisites

| Tool | Version |
|---|---|
| Go | 1.22+ |
| Python | 3.11+ |
| Postgres | 16 |
| Task | latest |
| Docker (optional) | latest, for compose-based dev |

## Clone

```bash
gh repo clone gekleos/bitagent
cd bitagent
```

## Option A: Nix flake (recommended)

The `flake.nix` provides a reproducible shell with everything pinned.

```bash
nix develop
```

Drops you into a shell with Go, Python, Postgres, Task, and the Go module dependencies preinstalled.

## Option B: Manual install

If you don't use Nix:

- **Go** — [go.dev/dl/](https://go.dev/dl/) (1.22+)
- **Python** — [python.org](https://www.python.org/) or `pyenv install 3.11`
- **Task** — `brew install go-task/tap/go-task` or [taskfile.dev/installation/](https://taskfile.dev/installation/)
- **Postgres** — `brew install postgresql@16` (macOS) or `apt install postgresql-16` (Debian/Ubuntu)

## Local Postgres setup

Create the user and database BitAgent expects.

```bash
createuser bitmagnet
createdb -O bitmagnet bitmagnet
psql -c "ALTER USER bitmagnet WITH PASSWORD 'devpass';"
```

## Environment file

```bash
cp examples/.env.public.example .env
```

Edit `.env` and set:

```env
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=devpass
LOG_LEVEL=debug
```

## Build and run

The repo's `Taskfile.yml` is the build entry point.

```bash
# Build the binary
task build

# Run all workers in the foreground
./bitagent worker run --all
```

You should see DHT bootstrap logs within ~30 seconds, and `bitagent_dht_ktable_hashes_added_total` start ticking up after ~3 minutes (visible at `http://localhost:3333/metrics`).

## Run tests

```bash
# All tests
task test

# A subset
go test ./internal/classifier/...
```

The classifier tests are the slowest because they cover the CEL rule chain end-to-end. Most other packages run in seconds.

## Vet and lint

```bash
task vet           # go vet
task lint          # golangci-lint (if installed)
golangci-lint run  # explicitly
```

## Dashboard development

The dashboard is a separate Python FastAPI app in the `ui/` subdirectory. Open a second terminal:

```bash
cd ui
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

BITAGENT_GRAPHQL_URL=http://localhost:3333/graphql \
BITAGENT_METRICS_URL=http://localhost:3333/metrics \
  uvicorn app:app --reload
```

Dashboard is at `http://localhost:8000`. The `--reload` flag picks up Python changes; restart for env-var changes.

## Working with the GraphQL schema

Schema files live at `graphql/schema/*.graphqls`. Generated bindings are in `internal/gql/gql.gen.go`.

After editing a schema file, regenerate:

```bash
task graphql:generate
# or directly
go run github.com/99designs/gqlgen generate
```

Then run `task vet` to catch any resolver gaps.

## Database migrations

Migrations live in `migrations/` as `NNNNN_name.sql` (goose format). The worker auto-applies them on startup, so during dev you don't usually invoke goose manually.

If you need to run migrations explicitly (e.g., to test a new migration in isolation):

```bash
./bitagent migrate up
```

Down migrations are best-effort — for a clean reset during dev, drop and recreate the database.

```bash
dropdb bitmagnet
createdb -O bitmagnet bitmagnet
psql -c "ALTER USER bitmagnet WITH PASSWORD 'devpass';"
```

## Common dev tasks

**Reload classifier rules.** The CEL rules are bundled in the binary; rebuild and restart:

```bash
task build && ./bitagent worker run --all
```

**Inspect resolved config.** The `From` column tells you which env var or default produced a given value:

```bash
./bitagent config show
```

**View the loaded classifier workflow:**

```bash
./bitagent classifier show --format yaml | head -50
```

**Probe live metrics during dev:**

```bash
curl -s http://localhost:3333/metrics | grep -E '^bitagent_' | head -30
```

## Submitting a pull request

1. Fork the repo (`gekleos/bitagent`).
2. Branch from `main` — name like `feat/your-feature` or `fix/issue-NNN`.
3. Run `task vet test lint` before pushing.
4. Push and open a PR. Reference any related issue in the description.
5. The CI pipeline runs vet + tests + lint on every push.
6. See [`CONTRIBUTING.md`](https://github.com/gekleos/bitagent/blob/main/CONTRIBUTING.md) at the repo root for style and process notes.

## See also

- [Reference / CLI](../reference/cli.md)
- [Concepts / Architecture](../concepts/architecture.md)
- [Concepts / Classification](../concepts/classification.md) — when editing CEL rules
- `CONTRIBUTING.md` at the repo root
