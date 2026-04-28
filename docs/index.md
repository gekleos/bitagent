---
hide:
  - navigation
---

Self-hosted, high-performance BitTorrent DHT crawler and content indexer.
Drop it into your *arr stack as a Torznab-compatible indexer and let the
public DHT fill the gaps your private trackers miss.

MIT-licensed. No telemetry. No accounts. Just an indexer you own.

**VPN strongly recommended** — DHT participation exposes your node's IP to the swarm. See [Legal / Disclaimer](legal/disclaimer.md) for the full network-isolation and liability notice.

---

## Feature highlights

- **DHT crawling** --
  Full BEP-5/9/10/33/42/43/51 compliance for broad,
  resilient peer discovery
- **CEL-based classifier with optional LLM rerank** --
  Rule-driven content classification that can escalate ambiguous
  matches to a language model for a second opinion
- **Evidence pipeline** --
  Webhook feedback from Sonarr, Radarr, and the rest of the *arr
  family becomes ground-truth, so the classifier improves over time
- **Multi-tier auth** --
  API-key, reverse-proxy header, forwarded-user, and SSO --
  pick the layer that fits your network
- **Operator dashboard** --
  FastAPI + vanilla JS with six tabs covering crawl health,
  classifier metrics, evidence review, retention, and more
- **TMDB poster integration** --
  Movie and series results include poster art pulled from TMDB
- **Retention controls** --
  Age-off, category filters, and manual purge so your database
  stays the size you want
- **Wantbridge** --
  Active content acquisition that prioritizes torrents matching
  items your *arr clients are actually searching for
- **Torznab API** --
  First-class compatibility with Sonarr, Radarr, Prowlarr,
  Lidarr, and Readarr -- add BitAgent as a custom indexer
  and you are done

---

## Quick links

- [Quickstart](quickstart.md) --
  Docker Compose, one API key, and a working indexer in 15 minutes
- [Architecture](concepts/architecture.md) --
  How the Go core, Python dashboard, classifier, and evidence
  pipeline fit together
- [FAQ](faq.md) --
  Common questions about crawling, legality, resource usage,
  and integration
- [Integrations](integrations/sonarr.md) --
  Per-app setup guides for Sonarr, Radarr, Prowlarr, Lidarr,
  and Readarr
  Walkthrough of the operator dashboard and the improvements
  over upstream bitmagnet

---

## License and lineage

BitAgent is released under the
[MIT License](https://github.com/gekleos/bitagent/blob/main/LICENSE).
It is a fork of
[bitmagnet-io/bitmagnet](https://github.com/bitmagnet-io/bitmagnet) --
full credit to the upstream contributors whose work made this possible.
