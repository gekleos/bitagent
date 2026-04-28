# Changelog

Release history for BitAgent. Newest first. The longer-form decision log lives in [`HISTORY.md`](https://github.com/gekleos/bitagent/blob/main/HISTORY.md) at the repo root.

## v1.0.0 — 2026-04-28 — First public release

The first publicly-shipped BitAgent release.

- Operator dashboard with a six-tab sidebar layout (Dashboard / Library / Wants / Evidence / Settings / System)
- Real-data integration verified against a production-scale corpus (3M+ torrents indexed, hundreds of live DHT peers, full category breakdown across audiobook / ebook / movie / music / tv_show)
- Torznab API key gate (`TORZNAB_API_KEY`) for any internet-exposed deployment
- Dashboard API key gate (`DASHBOARD_API_KEY`) — three auth modes: open, reverse-proxy header, or bearer key
- Public quickstart compose file (`examples/compose.public.yml`) plus optional Authelia and tailnet variants
- Documentation site live at <https://gekleos.github.io/bitagent/>
- MIT-licensed; multi-arch Docker images (amd64 + arm64) published with cosign keyless signing, CycloneDX SBOM, and SLSA provenance attestations

## Lineage

BitAgent is a 2026 fork of [bitmagnet-io/bitmagnet](https://github.com/bitmagnet-io/bitmagnet), based on commit `2b9e8ea` (2025-07-01). After 9+ months of upstream dormancy, the project rebranded from `bitmagnet` to `bitagent` on 2026-04-24 and now pursues an independent roadmap.

The DHT primitives, Postgres schema, and core indexing engine carry over from upstream. The classifier preempt path, the retention pipeline, the LLM rerank stage, and the evidence ingestor are BitAgent-specific extensions added during the divergence phase.

For the full pre-v1.0.0 divergence log — including the Prometheus namespace migration, the Angular webui strip, the `pgstats` collector, and the evidence-ingestor architecture — see [`HISTORY.md`](https://github.com/gekleos/bitagent/blob/main/HISTORY.md) at the repo root.
