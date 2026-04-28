# Contributing to BitAgent

Thanks for your interest. BitAgent is a small, focused project with a narrow scope: stay accurate and non-rotting as a DHT crawler / content indexer / Torznab adapter / *arr-evidence pipeline. We deliberately do not chase generic self-hosting features.

If you are about to file a security issue, **stop** and read [`SECURITY.md`](SECURITY.md) instead — public issues are not the right channel.

## What's in this repository

This is the **public release repository**. It contains:

| Path | Purpose |
| --- | --- |
| `ui/` | Operator dashboard — FastAPI + Jinja2 + static assets. Built into [`docker.io/gekleos/bitagent-ui`](https://hub.docker.com/r/gekleos/bitagent-ui) by `.github/workflows/publish.yml`. |
| `docs/` | MkDocs-Material source for [gekleos.github.io/bitagent](https://gekleos.github.io/bitagent/). |
| `examples/` | Reference Compose deployments (`compose.public.yml`, `compose.authelia.yml`, `compose.tailnet.yml`) and a Prowlarr `applicationCustomDefinition` snippet. |
| `scripts/sanitize.py` | Sanitize-scan tool that prevents private hostnames / tokens / personal references from landing in any committed file. Runs on every PR via `.github/workflows/sanitize.yml`. |
| `mkdocs.yml`, `static/v1/` | Docs-site build config + brand assets. |

The DHT-crawler / classifier / Torznab Go core that backs the published image is a fork of [`bitmagnet-io/bitmagnet`](https://github.com/bitmagnet-io/bitmagnet). The fork's source is not in this repository at this time. If you need to modify core behaviour, start from upstream bitmagnet and open an issue here describing the proposed change.

## Local development — operator dashboard (`ui/`)

### Prerequisites

- Python 3.12+
- A running BitAgent core (or upstream `bitmagnet`) with GraphQL on `:3333` for end-to-end testing — optional; the UI can boot in `REQUIRE_AUTH=false` against a stubbed core for layout work.
- Docker + Docker Compose (only if you want to test the published image shape).

### Run the dashboard locally

```bash
cd ui
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
REQUIRE_AUTH=false uvicorn app:app --host 127.0.0.1 --port 8080 --reload
# → http://127.0.0.1:8080
```

### Build the dashboard image locally

```bash
cd ui
docker build -t bitagent-ui:local .
docker run --rm -p 8080:8080 -e REQUIRE_AUTH=false bitagent-ui:local
```

## Local development — docs

```bash
python3.12 -m venv .venv-docs
source .venv-docs/bin/activate
pip install mkdocs-material==9.5.* mkdocs-mermaid2-plugin==1.2.* mkdocs-glightbox==0.4.*
mkdocs serve   # → http://127.0.0.1:8000
mkdocs build --strict   # what CI runs
```

## What CI checks

The full gate is `.github/workflows/ci.yml` (job `CI gate`); fan-in jobs:

| Job | What it enforces |
| --- | --- |
| Python lint (ruff + format) | `ruff check` and `ruff format --check` clean against `ui/pyproject.toml`. |
| Python deps audit (pip-audit) | No new known CVEs in `ui/requirements.txt`. (Five existing CVEs are explicitly allow-listed pending a dependency-bump PR; do not add to that list without a corresponding tracked issue.) |
| Dockerfile lint (hadolint) | `ui/Dockerfile` clean at warning threshold. |
| Compose file validation | `docker compose -f X config -q` succeeds on every `examples/*.yml`. |
| Docker build | The dashboard image builds and `/healthz` responds inside 30s. |
| Trivy filesystem scan | No HIGH or CRITICAL vulnerabilities in the repo tree. |
| Repo lint (yamllint + actionlint) | Workflow correctness + YAML hygiene. |

Plus separate workflows: **CodeQL** (Python `security-and-quality` pack), **OSSF Scorecard**, **Sanitize Scan**, **Deploy Docs** (build + GitHub Pages publish), **Publish** (multi-arch Docker Hub push with cosign signing + SBOM + SLSA provenance on push to `main` and on tagged releases).

A PR cannot merge unless `CI gate` and `Sanitize Scan` are green. There are no required human approvals, but `CODEOWNERS` directs review traffic.

## Branch + commit conventions

- Branch from `main`. Branch names: `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `chore/<topic>`, `ci/<topic>`.
- One logical change per PR. If you find a drive-by fix, file it separately or call it out in the description.
- Conventional Commits subject line (`feat(ui): …`, `fix(torznab-docs): …`, `docs(security): …`, `ci: …`). Body wraps at ~72 cols.
- Commit messages explain *why*, not *what* the diff already shows.

## Pull request expectations

`.github/PULL_REQUEST_TEMPLATE.md` is auto-rendered for every PR. Fill in **What changed**, **Why** (with linked issue/discussion if any), the change-type checkbox, and **How was this tested?**. For UI changes, attach a before/after screenshot.

Force-push to `main` is **not** allowed. Force-push to your own branch is fine — and expected — after a rebase.

## Code style

- **Python:** `ruff check` + `ruff format` enforced by CI; configuration lives in `ui/pyproject.toml`. Type hints on public functions are encouraged but not gated.
- **YAML:** `yamllint` (relaxed profile) + `actionlint` for workflows.
- **Markdown (docs):** `markdownlint-cli2` per `.markdownlint.json` for everything under `docs/`.
- **Dockerfile:** `hadolint` warning threshold.

Keep diffs focused. Don't reformat unrelated files — the formatter pass already happened.

## Tests

This repository does not yet ship a Python test suite. If you add behaviour to `ui/`, contributing the first `pytest` setup — a tiny `tests/test_app.py` with a couple of `httpx.AsyncClient` requests against the FastAPI app — is welcome and will be merged eagerly.

## Communication

- **GitHub Issues** for tracked work. Use the templates: bug / feature / integration / docs.
- **GitHub Discussions** for usage questions, roadmap conversations, and "show and tell".
- **GitHub Security Advisories** for vulnerabilities — see [`SECURITY.md`](SECURITY.md).
- A real-time chat channel may open after sustained interest; it does not exist yet.

## Licensing

BitAgent is licensed under the MIT License (see [`LICENSE`](LICENSE)). The original work it derives from — `bitmagnet-io/bitmagnet` — is also MIT, with attribution preserved in [`NOTICE`](NOTICE). By contributing, you agree your work is released under the same MIT terms.

## Out-of-scope contributions

Some changes we will close without merging:

- Re-importing the Go core into this repository — the public release intentionally publishes the dashboard + docs + deployment scaffolding only. Core changes belong upstream.
- New social features, account systems, multi-tenant auth on the dashboard.
- Speculative LLM-everywhere refactors. The classifier's LLM stage is opt-in, shadow-first, and bounded.
- Code-style sweeps that mix many files — they create review pain. Open a discussion first if you think a sweep is warranted.

If you are unsure whether a contribution is in scope, open a small issue describing the idea before writing the code.
