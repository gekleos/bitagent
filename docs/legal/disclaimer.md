# Legal Disclaimer

**This document is for informational purposes only and does not constitute legal advice.** The authors, contributors, and maintainers of BitAgent (including primary maintainer `gekleos`) are not attorneys. All references to copyright, liability, jurisdiction, and compliance are derived from publicly available legal frameworks, established industry practice, and open-source networking standards. Operators are solely responsible for understanding and complying with the laws that apply to their jurisdiction, infrastructure, network configuration, and intended use case.

## What BitAgent Is and Is Not

**BitAgent is a distributed metadata indexer.** It passively crawls the public BitTorrent Distributed Hash Table (DHT), collects publicly announced metadata (infohashes, torrent names, peer counts, and availability signals), and indexes it for operator search. BitAgent functions as a passive observation and retrieval layer. It does not connect to traditional trackers, download files, distribute content, seed, peer, or facilitate file transfers. **BitAgent is not a content host, a tracker, a download client, a CDN, or a piracy tool.** It is a network utility that indexes publicly broadcast information, analogous to a web search engine indexing publicly available URLs.

## The BitTorrent Protocol and Public Metadata

**The BitTorrent protocol itself is a lawful, standardized data transfer technology.** It is used by Linux distributions, software publishers, game studios (including Blizzard Entertainment), the Internet Archive, scientific research consortia, IPFS gateways, and academic institutions. The protocol was designed to distribute large datasets efficiently and predates modern copyright enforcement disputes. The technology remains a foundational networking standard for peer-to-peer data delivery. Using the BitTorrent protocol does not inherently violate any law, nor does it constitute infringement by virtue of its implementation.

## Indexing Public DHT Metadata

**Indexing publicly broadcast DHT metadata is widely recognized as lawful.** Courts and regulatory frameworks in multiple jurisdictions have consistently treated the indexing of publicly announced network data under the same principles that govern traditional search engines, library catalogs, and archival systems. The act of recording and cataloging metadata that a network voluntarily broadcasts does not constitute copyright infringement or secondary liability. This follows established safe-harbor frameworks and the legal precedent that an index or catalog is a neutral intermediary tool. An operator indexing public DHT announcements is legally analogous to a search engine indexing pages on pirate sites: the index itself carries no liability for the subsequent use of its entries; only the underlying content does.

## Downloading Content and Operator Responsibility

**Downloading content is entirely separate from indexing metadata.** BitAgent does not download files. Any content retrieval is performed exclusively by the operator's own client. The lawfulness of downloading any specific file depends entirely on the operator, the jurisdiction, the nature of the content, and whether the operator holds the necessary rights or authorization. Many torrents are lawfully distributed; many are not. Operators assume full responsibility for verifying the legal status of any content they choose to retrieve. Running an indexer does not grant immunity for downstream downloads.

## Copyright Takedown Procedures

**BitAgent does not operate as a service provider and does not receive copyright notices on behalf of users.** Because BitAgent is self-hosted software, operators control their own indexes, network exposure, and data retention. If an operator receives a copyright infringement notice or wishes to remove specific data from their local index, they must handle the request internally. BitAgent provides operator-facing tools to forget and exclude specific infohashes from the local catalog via the dashboard and REST API. Operators should implement their own takedown procedures consistent with their jurisdiction's copyright regime. We do not mediate disputes, process third-party claims, or act as an intermediary for DMCA or equivalent notices.

## Data Protection and Privacy

**BitAgent does not collect, store, or transmit user data.** The software only indexes metadata that is publicly announced on the BitTorrent DHT. This data is openly broadcast by participating nodes and is not personally identifiable. Operators who run BitAgent behind a proxy, expose it to other users, or integrate it with third-party dashboards should consult applicable data protection regulations (such as GDPR, CCPA, or local privacy statutes) and disclose the nature of the indexing service to end users where required by law. No logs of operator search queries are retained by the core software.

## Software License vs. Intended Use

**The MIT License permits the use, modification, and distribution of BitAgent, but it does not authorize unlawful conduct.** Software licensing grants permissions over the code itself; it does not grant immunity from copyright law, data protection regulations, or terms of service applicable to the operator's infrastructure or network activity. Compliance with applicable law remains the operator's responsibility. Open-source availability does not constitute a license to bypass legal restrictions on content distribution or commercial aggregation.

## Recommendations for Operators

**Operators should comply with local copyright and data protection laws.** Use BitAgent only with content you have a legal right to access or distribute. Maintain clear audit trails of your indexing and download practices, and implement reasonable takedown mechanisms where required. If your use case involves commercial aggregation, redistribution, large-scale processing of copyrighted material, or cross-border data routing, consult qualified legal counsel. Keep your indexer isolated from your primary download client, and configure firewall rules to restrict DHT exposure to your local network where operationally appropriate.

## Frequently Asked Questions

**Can I run this on my home server?**
Yes. Running BitAgent is lawful. Operators are responsible for complying with local copyright and network regulations for their own infrastructure.

**Will I get sued?**
Running BitAgent itself carries no inherent legal risk. Legal exposure depends entirely on what content you download, how you use it, and your jurisdiction. The project does not guarantee immunity from third-party claims.

**Does the project endorse piracy?**
No. The project endorses lawful indexing of publicly broadcast metadata and the continued development of open, standards-compliant networking tools.

**What about my ISP/VPN?**
This is out of scope for this documentation. Consult your ISP's Terms of Service, applicable privacy laws, and network security policies before routing traffic through third-party providers.

**I received a DMCA notice — what do I do?**
Handle notices internally. Use BitAgent's dashboard or API endpoint `/api/torrents/{infohash}/forget` to remove the specific infohash from your local index. Consult local counsel if your notice involves third-party claims or commercial liability.

## TL;DR

**TL;DR:** BitAgent is a self-hosted metadata indexer for the public BitTorrent DHT, not a download client or content host. The BitTorrent protocol and the indexing of publicly broadcast network data are lawful in most jurisdictions. Downloading content is your responsibility and depends entirely on the file, your jurisdiction, and your rights to it. BitAgent does not receive copyright notices, store user data, or authorize unlawful conduct. Operators must comply with local law, implement their own takedown procedures, and consult counsel for commercial or high-risk use cases. This document is informational, not legal advice.
