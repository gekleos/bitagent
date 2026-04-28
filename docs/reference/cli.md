# CLI reference

The BitAgent binary is named `bitagent`. Commands are sorted alphabetically by the underlying `urfave/cli` runtime. Run with no arguments — or `--help` — for the live command list:

```bash
bitagent --help
```text
The command set is small and stable. Anything not on this page does not exist.

## Top-level commands

| Command | Purpose |
|---|---|
| `worker run` | Start one or more workers and block (the container default) |
| `worker list` | Print the registered worker keys |
| `classifier show` | Print the currently loaded classifier workflow source |
| `classifier schema` | Print the JSON schema describing the workflow source |
| `config show` | Render every resolved config path with values, defaults, and source |
| `process` | One-shot: run the classification + persistence pipeline once over enqueued items, then exit |
| `reprocess` | Re-classify already-indexed torrents through the current classifier |
| `attribution` | Attribution sub-commands (powers wantbridge + `*arr` grab attribution) |
| `migrate` | (dev) database migrations — wraps goose; the worker auto-migrates on startup |
| `gorm` | (dev) GORM tooling |

## `bitagent worker`

The entry point for running BitAgent. The container's default command is `worker run --all`.

### `worker run`

```text
worker run [--all] [--keys k1,k2,...]
```text
| Flag | Purpose |
|---|---|
| `--all` | Enable every registered worker |
| `--keys` | Comma-separated list of worker keys (use `worker list` to discover) |

Examples:

```bash
# Production — all workers (default for the container)
bitagent worker run --all

# Debug a single worker locally
bitagent worker run --keys dht_crawler

# Subset
bitagent worker run --keys dht_crawler,classifier,evidence_arr_poller
```text
The command blocks. SIGINT/SIGTERM stops all workers cleanly.

### `worker list`

```bash
bitagent worker list
```text
One key per line. Useful for confirming which workers a build registered.

## `bitagent classifier`

Inspect the live classifier without restarting the worker.

### `classifier show`

```text
classifier show [--format yaml|json]
```text
Prints the loaded classifier workflow source — CEL rules + content-type mapping.

```bash
# Default — yaml
bitagent classifier show

# Export to a file for diff'ing
bitagent classifier show > current-rules.yaml

# JSON for programmatic consumers
bitagent classifier show --format json | jq '.rules[0]'
```text
### `classifier schema`

```text
classifier schema [--format yaml|json]
```text
Prints the JSON Schema describing the workflow source. Useful for IDE auto-complete and validation when you're writing/editing rules.

```bash
bitagent classifier schema --format json > classifier.schema.json
```text
## `bitagent config show`

```bash
bitagent config show
```text
Renders every resolved configuration path. Output is a wide table:

| Column | Meaning |
|---|---|
| `path` | Dot-notation config key (e.g. `dht.scaling_factor`) |
| `Type` | Go type |
| `Value` | Currently resolved value |
| `Default` | Default if no override applies |
| `From` | Which resolver produced the value (env-var name, `default`, or `file`) |

The `From` column is the most useful single signal — it tells you exactly why a config has the value it does, including whether your env-var override actually took effect.

```bash
# Pipe to less when your terminal is narrow
bitagent config show | less -S

# Grep for a specific subsystem
bitagent config show | grep -i csam
```text
## `bitagent process`

```bash
bitagent process
```text
One-shot batch processor: runs the classification + persistence pipeline once over enqueued items, then exits. Useful for catch-up runs after a long downtime, or for scripted batch jobs.

## `bitagent reprocess`

```bash
bitagent reprocess
```text
Re-classifies already-indexed torrents through the current classifier. Idempotent. Run after editing CEL rules to apply the new logic to existing data without re-crawling.

The operation is staged through the queue, so it can be safely interrupted and resumed. Watch progress via Prometheus (`bitagent_classifier_examined_total`).

## `bitagent attribution`

Sub-commands powering the wantbridge and `*arr` grab-attribution flow. Not normally invoked by an operator — exposed for diagnostic use during incident response.

## `bitagent migrate` (dev)

Wraps goose for dev/CI use. The worker auto-applies migrations on startup, so you don't need this in normal operation. Available for integration tests and local DB setup.

## `bitagent gorm` (dev)

GORM tooling. Internal use; the surface is unstable.

## Running inside the container

In a deployed environment, run any CLI command via `docker exec`:

```bash
docker exec bitagent bitagent <subcommand>
```text
For example, to dump the resolved config of a running container:

```bash
docker exec bitagent bitagent config show
```text
To re-classify after editing rules in the container:

```bash
docker exec bitagent bitagent reprocess
```text
## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Application error (the worker, the resolver, or a sub-command failed) |
| `2` | CLI flag parsing error (urfave/cli convention) |

A subcommand that runs to completion always exits `0`. SIGTERM/SIGINT during `worker run` exits `0` after a clean shutdown.

## See also

- [Configuration](../configuration.md)
- [Deployment](../deployment.md)
- [Operations / upgrade](../operations/upgrade.md)
- [Concepts / classification](../concepts/classification.md)
