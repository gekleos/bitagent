# DHT crawler

The DHT crawler is BitAgent's discovery engine. Rather than relying on tracker lists or external indexer feeds, the crawler participates directly in the global BitTorrent Distributed Hash Table — gossiping with peers, building its own routing table, and sampling candidate infohashes from neighbours. When a candidate looks worth fetching, it opens a real peer connection and pulls the torrent's metadata via BEP-9. Decentralised sampling followed by targeted metadata retrieval, with no central coordination point.

This page explains what the crawler does, what the wire protocols are, and how to tune it.

## BEP compliance

BitAgent implements seven BEPs, each with a specific job in the discovery pipeline.

| BEP | What it is | Why we use it |
|---|---|---|
| BEP-5 | DHT Protocol | Mainline Kademlia routing table, RPC exchange, node discovery |
| BEP-9 | Extension for Peers to Send Metadata Files | Pulls `.torrent` metadata over a peer connection (no tracker needed) |
| BEP-10 | Extension Protocol | Negotiates BEP-9 + BEP-33 during the BitTorrent handshake |
| BEP-33 | DHT Scrapes | Peer counts for an infohash without joining the swarm — keeps our IP off the swarm peer lists |
| BEP-42 | DHT Security Extension | Node ID derived from IP — anti-Sybil hardening |
| BEP-43 | Read-only DHT Nodes | We participate in routing but explicitly don't claim to seed |
| BEP-51 | DHT Infohash Indexing | The `sample_infohashes` RPC is the discovery fast path |

## How discovery works

1. **Bootstrap.** On startup, the crawler resolves a deterministic seed list — `dht.transmissionbt.com:6881`, `router.bittorrent.com:6881`, `router.utorrent.com:6881` — and sends `ping` RPCs. After the first gossip cycle, the crawler transitions to DHT-native bootstrap: the routing table itself is the source of new peers.

2. **k-table construction.** A parallel `find_node` walk against each bootstrap seed populates the initial Kademlia routing table. Buckets are organised by the prefix length shared between the crawler's node ID and peer IDs.

3. **BEP-51 sampling.** Once the k-table reaches a working threshold (typically a few hundred nodes), the crawler issues `sample_infohashes` RPCs to neighbours. Each neighbour returns a small batch of infohashes from their own routing tables. We dedupe and queue them.

4. **Deferred metadata fetch.** Queued infohashes do *not* trigger immediate peer connections. They first pass through the CEL classifier (cheap drops on banned-keyword regex), the CSAM blocklist (pre-fetch double-hash filter), and any retention rules. Only survivors get a BEP-9 metainfo fetch — a real TCP/uTP handshake to a peer claiming to seed.

This deferred-fetch design is deliberate. The DHT is noisy; most discovered infohashes are dead, private, or unwanted. Pre-fetch filtering keeps our network footprint proportional to genuinely interesting traffic.

## Routing table sizing

The k-table uses a prefix-bucket structure. Each bucket holds at most `K` live nodes (mainline default: 20). Buckets fill as new peers respond to find_node walks; buckets prune as nodes go silent.

Eviction follows last-seen timestamps combined with periodic refresh cycles. When a bucket is full and a new node responds, the oldest unresponsive node is replaced. During failure bursts, the crawler applies exponential backoff to refresh RPCs — preventing a runaway ping storm against an unresponsive segment of the network.

RAM cost scales linearly with active buckets and the configured `DHT_SCALING_FACTOR`. At `DHT_SCALING_FACTOR=1` on a 4 GB host, expect ~150 MB of routing-table state. At `DHT_SCALING_FACTOR=10`, expect ~1 GB.

## Wire identity

BitAgent advertises itself with the peer ID prefix `-BA0001-` (was `-BM0001-` before the 2026-04-24 rebrand). Other DHT nodes can recognise the client and apply BitAgent-specific compatibility rules if any are warranted.

For Sybil resistance, the 20-byte node ID is hardened per BEP-42: it's derived from the public IP, ensuring exactly one logical identity per external IP. An attacker can't trivially create thousands of fake nodes by rotating ephemeral ports.

## Network requirements

| Direction | Protocol | Port (default) | Required? |
|---|---|---|---|
| Outbound | UDP | DHT (random ephemeral) → remote `:6881` | Yes — without UDP egress, no DHT |
| Inbound | UDP/TCP | `BITAGENT_PEER_PORT` (default `3334`) | Helpful, not required |

DHT discovery is outbound-dominant — the crawler initiates almost every conversation. Behind a NAT or VPN with no inbound port forward, BitAgent still works. You'll see a marginally lower BEP-9 fetch success rate (some peers won't be reachable for the metainfo handshake) but the crawl itself proceeds.

If you're running behind a VPN that supports port forwarding (Mullvad, AirVPN, Proton, etc.), enabling the forward and matching `BITAGENT_PEER_PORT` to the forwarded port restores peer symmetry. The advanced reference compose file (`deploy/docker-compose.yml`) wires this through; the public quickstart does not.

## Failure modes

**DHT starvation.** Peer count below 100 after 10 minutes of operation almost always means UDP egress is being filtered — by an ISP, a corporate proxy, a misconfigured firewall, or a VPN with stricter rules than expected. Test with `nc -u router.bittorrent.com 6881 < /dev/null && echo OK`.

**Routing table thrash.** `DHT_SCALING_FACTOR` set too high for the host's bandwidth or CPU. Symptom: high request volume but `bitagent_dht_client_request_duration_seconds` p95 keeps climbing. Lower the scaling factor.

**Sustained zero peers despite UDP egress.** Rare but possible — some ISPs do active DHT-port DPI. Workaround: VPN, or change `BITAGENT_PEER_PORT` to an obscure value (port-randomisation defeats most port-based DPI).

## Relevant metrics

| Metric | What it tells you |
|---|---|
| `bitagent_dht_ktable_hashes_added_total` | Cumulative discovery rate. The headline pulse metric — if this stops climbing, the crawler is wedged. |
| `bitagent_dht_crawler_persisted_total{entity="torrent"}` | Successful BEP-9 fetches that survived classifier filters and made it to Postgres. |
| `bitagent_dht_client_request_concurrency` | Active in-flight DHT requests. Sum across labels ≈ effective DHT peer count. |
| `bitagent_dht_client_request_duration_seconds` | RPC + metainfo fetch latency histogram. Watch p95 — if it's growing, you're saturating something. |

Full catalog in [reference/metrics.md](../reference/metrics.md).

## Tuning guidance

| Host class | `DHT_SCALING_FACTOR` | Notes |
|---|---|---|
| 4 GB / 2 vCPU | `1` | Personal use, ~5–10K torrents/day discovery |
| 8 GB / 4 vCPU | `2`–`4` | Small media stack, ~20–40K torrents/day |
| 16 GB / 8 vCPU | `4`–`8` | Real workload, ~50–100K torrents/day |
| Dedicated 32+ GB | `8`–`10` | Production scale, 100K+/day |

The inflection point is where adding scaling no longer adds throughput — usually marked by `bitagent_dht_client_request_duration_seconds` p95 ticking up while `bitagent_dht_ktable_hashes_added_total` plateaus. Back off one notch from there.

## Honest limits

The DHT is inherently noisy. Most sampled infohashes go nowhere — dead swarms, private torrents, unwanted content, partial dupes. The crawler is a high-throughput firehose; expect 90%+ of what it pulls to be dropped before persistence.

Signal extraction, dedup, quality scoring, and retention are the classifier pipeline's job, not the crawler's. The crawler's job is to make sure no infohash *of interest* slips past unsampled. If you find yourself wishing the crawler were more selective, you probably want to tune the classifier rules instead — see [concepts/classification.md](classification.md).

## See also

- [Concepts / Classification](classification.md)
- [Concepts / Wantbridge](wantbridge.md)
- [Configuration](../configuration.md) — `DHT_SCALING_FACTOR`, `BITAGENT_PEER_PORT`
- [Troubleshooting](../troubleshooting.md) — DHT starvation playbook
- [Reference / Metrics](../reference/metrics.md)
