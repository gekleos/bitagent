# Contributing to BitAgent

Thanks for your interest. BitAgent is a small, focused project with a narrow scope: stay accurate and non-rotting as a DHT crawler / content indexer / Torznab adapter / *arr-evidence pipeline. We deliberately do not chase generic self-hosting features.

If you are about to file a security issue, **stop** and read [`SECURITY.md`](SECURITY.md) instead — public issues are not the right channel.

## Local development

### Prerequisites

- Go 1.22+
- Python 3.12+ (for the `bitagent-ui` dashboard repo)
- Postgres 14+ (16 recommended)
- Docker + Docker Compose (for the local stack)
- `task` (https://taskfile.dev) — used as the build entrypoint

### Getting the code running

```bash
git clone https://github.com/gekleos/bitagent.git
git clone https://github.com/gekleos/bitagent-ui.git
cd bitagent
cp .env.example .env       # adjust DATABASE_URL etc.
task dev:up                # postgres + a dev container
task run                   # bitagent up against the dev DB
```

For the dashboard:

```bash
cd ../bitagent-ui
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
REQUIRE_AUTH=false python -m bitagent_ui

# -> http://localhost:8080

```

### Running the test suite

```bash
go test ./... -race -count=1                      # bitagent
pytest -q                                         # bitagent-ui
```

CI runs the same invocations plus `golangci-lint run` and the build/push chain. All must pass on every PR.

## Branch + commit conventions

- Branch from `main`. Branch names: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`.
- One logical change per PR. If you find a drive-by fix, file it separately or call it out in the description.
- Conventional Commits subject line (`feat(torznab): …`, `fix(dht): …`, `docs(security): …`). Body wraps at ~72 cols.
- **DCO sign-off required.** Use `git commit --signoff` (or `git commit -s`). We do **not** require a CLA. Sign-off certifies the [Developer Certificate of Origin](https://developercertificate.org).
- Commit messages explain *why*, not *what* the diff already shows.

## PR description template

Every PR must include the following sections:

```markdown

## What changed

<concise summary of the diff>

## Why

<motivation: which issue, what symptom, what's the user story>

## Impact

<who's affected, breaking changes, migration steps>

## Version

<current> → <new> (<patch | minor | major>)
Reason: <why this bump level>

## Test results

<paste relevant `go test` / `pytest` output or attach evidence>
```

PRs missing the template are sent back for revision.

## Code style

- **Go:** `gofmt -s` enforced by CI. `golangci-lint run` clean — config at `.golangci.yml`. Public types and functions get doc comments. `context.Context` is the first arg of any function that does I/O. Errors wrapped with `%w` and a stable string prefix.
- **Python:** `ruff check` + `mypy --strict` on new modules; gradual on legacy. Type hints required on public functions.
- Both: keep diffs focused. Don't reformat unrelated files.

## Test discipline

- Bug fixes ship with a regression test.
- New behaviour ships with at least one happy-path and one error-path test.
- Table-driven tests are preferred for branchy logic.
- Integration tests that need a Postgres should use `testcontainers` or an ephemeral compose; do not assume a DB is running.
- Don't mock what you don't own — prefer the real thing in a container.

## Code review

- CI runs on every push (lint + tests + build). All must pass before review.
- One maintainer approval is required to merge to `main`.
- Squash-merge is the default; the squash commit follows Conventional Commits.
- Force-push to `main` is **not** allowed. Force-push to your own branch is fine after a rebase.

## Communication

- GitHub Issues for tracked work.
- GitHub Discussions for design + roadmap conversations.
- A real-time chat channel may open after sustained interest; it does not exist yet.

## Licensing

BitAgent is licensed under the MIT License (see [`LICENSE`](LICENSE)). The original work it derives from — `bitmagnet-io/bitmagnet` — is also MIT, with attribution preserved in [`NOTICE`](NOTICE). By contributing, you agree your work is released under the same MIT terms.

## Out-of-scope contributions

Some changes we will close without merging:

- A bundled web UI inside the `bitagent` Go repo — the dashboard lives in `bitagent-ui` on purpose.
- New social features, account systems, multi-tenant auth.
- Speculative LLM-everywhere refactors. The LLM stage is opt-in, shadow-first, and bounded.
- Code-style sweeps that mix many files — they create review pain.

If you are unsure whether a contribution is in scope, open a small issue describing the idea before writing the code.
