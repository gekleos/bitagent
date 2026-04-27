# BitAgent

**Self-hosted BitTorrent DHT crawler with native Sonarr/Radarr Torznab integration.**

A small, focused tool that turns the public DHT into a structured indexer for the *arr ecosystem. Self-hosted, MIT-licensed, and explicitly read-only relative to your existing media stack.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/gekleos/bitagent-staging/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-526CFE.svg)](https://gekleos.github.io/bitagent-staging/)
[![Sanitize](https://github.com/gekleos/bitagent-staging/actions/workflows/sanitize.yml/badge.svg)](https://github.com/gekleos/bitagent-staging/actions/workflows/sanitize.yml)

---

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Quickstart**

    ---

    Up and running in 15 minutes — Docker Compose, one API key, and a Sonarr indexer entry.

    [:octicons-arrow-right-24: Get started](quickstart.md)

-   :material-graph:{ .lg .middle } **Architecture**

    ---

    How the Go core, Python dashboard, classifier, and evidence pipeline fit together.

    [:octicons-arrow-right-24: System overview](concepts/architecture.md)

-   :material-checkbox-multiple-marked:{ .lg .middle } **Why BitAgent**

    ---

    Ten concrete improvements over upstream `bitmagnet`, with before / after / measure framing.

    [:octicons-arrow-right-24: See the portfolio](project/improvements.md)

-   :material-account-multiple:{ .lg .middle } **Get involved**

    ---

    Local dev setup, branch conventions, and PR template — straight from the contributing guide.

    [:octicons-arrow-right-24: Contribute](https://github.com/gekleos/bitagent-staging/blob/main/CONTRIBUTING.md)

</div>

---

## What it does

- **Crawls the public DHT** (BEP-5/9/10/33/42/43/51) and indexes the metadata.
- **Classifies content** with a CEL rule engine; optional LLM rerank for ambiguous cases.
- **Speaks Torznab** to Sonarr, Radarr, Prowlarr, Lidarr, and Readarr — drop in as a custom indexer.
- **Learns from your *arr stack** via webhook-driven evidence; ground-truth labels preempt the classifier on subsequent matches.
- **Stores in Postgres** with a clean schema, GORM-backed migrations, and connection pooling.

## What it deliberately doesn't do

- Doesn't host content. Doesn't seed. Doesn't download. It indexes; your torrent client handles the bytes.
- Doesn't replace Prowlarr — it complements your tracker list with broad DHT coverage.
- Doesn't ship invite-system or community features. It's an indexer, not a tracker.

## A note on supporting children

If BitAgent saves you time, please consider donating to [Children's International](https://www.children.org/) — they sponsor children in some of the world's poorest communities. **BitAgent has no affiliation with the charity**; we just think the cause is worth a visible call-to-action.

## Status

This is the first public-facing release candidate. Track tagged releases at [github.com/gekleos/bitagent-staging/releases](https://github.com/gekleos/bitagent-staging/releases) and join the conversation in [Discussions](https://github.com/gekleos/bitagent-staging/discussions).

A 2026 fork of [bitmagnet-io/bitmagnet](https://github.com/bitmagnet-io/bitmagnet) — credit to the upstream contributors whose foundation we built on.
