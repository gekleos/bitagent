# Legal Disclaimer

**This document is for informational purposes only and does not constitute legal advice.** The authors, contributors, and maintainers of BitAgent are not attorneys. Operators are solely responsible for understanding and complying with all laws that apply to their jurisdiction, infrastructure, network configuration, and intended use.

---

## DISCLAIMER OF WARRANTIES AND LIMITATION OF LIABILITY

**THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT. IN NO EVENT SHALL THE AUTHORS, COPYRIGHT HOLDERS, CONTRIBUTORS, OR MAINTAINERS OF BITAGENT BE LIABLE FOR ANY CLAIM, DAMAGE, OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE, ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE, MISUSE, OR INABILITY TO USE THE SOFTWARE.**

**TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE AUTHORS AND MAINTAINERS OF BITAGENT EXPRESSLY DISCLAIM ALL LIABILITY FOR:**

- **ANY ACT OF COPYRIGHT INFRINGEMENT, TRADEMARK INFRINGEMENT, OR VIOLATION OF ANY INTELLECTUAL PROPERTY RIGHT COMMITTED BY AN OPERATOR OR END USER OF THIS SOFTWARE;**
- **ANY CLAIM BROUGHT BY A THIRD PARTY — INCLUDING RIGHTS HOLDERS, CONTENT OWNERS, COLLECTING SOCIETIES, OR GOVERNMENT AUTHORITIES — ARISING FROM THE OPERATOR'S USE OR DEPLOYMENT OF THIS SOFTWARE;**
- **ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES ARISING FROM THE OPERATOR'S INDEXING, DOWNLOADING, REDISTRIBUTION, OR MAKING AVAILABLE OF ANY CONTENT;**
- **ANY HARM RESULTING FROM THE OPERATOR'S FAILURE TO COMPLY WITH APPLICABLE COPYRIGHT, DATA PROTECTION, OR NETWORK REGULATION.**

**THIS DISCLAIMER APPLIES REGARDLESS OF WHETHER SUCH LIABILITY IS BASED ON CONTRACT, TORT (INCLUDING NEGLIGENCE), STRICT LIABILITY, STATUTE, OR ANY OTHER LEGAL THEORY, AND REGARDLESS OF WHETHER THE AUTHORS HAVE BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.**

The operator assumes full and exclusive responsibility for all actions taken with this software, including the selection, retrieval, redistribution, and storage of any content.

---

## What BitAgent Is and Is Not

**BitAgent is a distributed metadata indexer.** It passively crawls the public BitTorrent Distributed Hash Table (DHT), collects publicly announced metadata (infohashes, torrent names, peer counts, and availability signals), and indexes it for operator search. BitAgent functions as a passive observation and retrieval layer. It does not connect to traditional trackers, download files, distribute content, seed, peer, or facilitate file transfers. **BitAgent is not a content host, a tracker, a download client, a CDN, or a piracy tool.** It is a network utility that indexes publicly broadcast information, analogous to a web search engine indexing publicly available URLs.

## The BitTorrent Protocol and Public Metadata

**The BitTorrent protocol itself is a lawful, standardized data transfer technology.** It is used by Linux distributions, software publishers, game studios (including Blizzard Entertainment), the Internet Archive, scientific research consortia, IPFS gateways, and academic institutions. The protocol was designed to distribute large datasets efficiently and predates modern copyright enforcement disputes. The technology remains a foundational networking standard for peer-to-peer data delivery. Using the BitTorrent protocol does not inherently violate any law, nor does it constitute infringement by virtue of its implementation.

## Indexing Public DHT Metadata

**Indexing publicly broadcast DHT metadata is widely recognized as lawful.** Courts and regulatory frameworks in multiple jurisdictions have consistently treated the indexing of publicly announced network data under the same principles that govern traditional search engines, library catalogs, and archival systems. The act of recording and cataloging metadata that a network voluntarily broadcasts does not constitute copyright infringement or secondary liability. An operator indexing public DHT announcements is legally analogous to a search engine indexing publicly available pages: the index itself carries no liability for the subsequent use of its entries.

## Downloading Content and Operator Responsibility

**Downloading content is entirely separate from indexing metadata.** BitAgent does not download files. Any content retrieval is performed exclusively by the operator's own client. The lawfulness of downloading any specific file depends entirely on the operator, the jurisdiction, the nature of the content, and whether the operator holds the necessary rights or authorization. Many torrents are lawfully distributed; many are not. **Operators assume full and exclusive responsibility for verifying the legal status of any content they choose to retrieve.** Running an indexer does not grant immunity for downstream downloads.

## Copyright Takedown Procedures

**BitAgent does not operate as a service provider and does not receive copyright notices on behalf of users.** Because BitAgent is self-hosted software, operators control their own indexes, network exposure, and data retention. If an operator receives a copyright infringement notice or wishes to remove specific data from their local index, they must handle the request internally. BitAgent provides operator-facing tools to remove specific infohashes from the local catalog via the dashboard and REST API (`/api/torrents/{infohash}/forget`). Operators should implement their own takedown procedures consistent with their jurisdiction's copyright regime. The authors do not mediate disputes, process third-party claims, or act as an intermediary for DMCA or equivalent notices.

## Data Protection and Privacy

**BitAgent does not collect, store, or transmit user data.** The software only indexes metadata that is publicly announced on the BitTorrent DHT. This data is openly broadcast by participating nodes and is not personally identifiable. Operators who run BitAgent behind a proxy, expose it to other users, or integrate it with third-party dashboards should consult applicable data protection regulations (such as GDPR, CCPA, or local privacy statutes) and disclose the nature of the indexing service to end users where required by law. No logs of operator search queries are retained by the core software.

## Software License vs. Intended Use

**The MIT License permits the use, modification, and distribution of BitAgent, but it does not authorize unlawful conduct.** Software licensing grants permissions over the code itself; it does not grant immunity from copyright law, data protection regulations, or terms of service applicable to the operator's infrastructure or network activity. Compliance with applicable law remains the operator's responsibility. Open-source availability does not constitute a license to bypass legal restrictions on content distribution or commercial aggregation.

## Recommendations for Operators

**Comply with local copyright and data protection laws.** Use BitAgent only with content you have a legal right to access or distribute. Maintain clear audit trails of your indexing and download practices, and implement reasonable takedown mechanisms where required. If your use case involves commercial aggregation, redistribution, large-scale processing of copyrighted material, or cross-border data routing, consult qualified legal counsel.

**Use a VPN or dedicated network interface for all DHT traffic — this is strongly recommended.** When your node participates in the BitTorrent DHT, your node's IP address is visible to every peer and monitoring entity that sweeps the swarm. Without network isolation, your real IP address is associated with DHT crawling activity. The authors strongly recommend:

- Routing BitAgent's DHT traffic through a reputable VPN provider that supports port forwarding (Mullvad, AirVPN, ProtonVPN, and similar privacy-focused providers are commonly used) and does not log connection data.
- Matching `BITAGENT_PEER_PORT` to the port-forwarded port assigned by your VPN provider for best DHT connectivity.
- Keeping BitAgent on a dedicated VLAN, VM, or container network segment isolated from your primary devices.
- Reviewing your VPN provider's Terms of Service and privacy policy before routing peer-to-peer traffic through their network.

**Failure to use a VPN or network isolation means your real IP address participates in the DHT swarm.** This may expose you to monitoring by rights holders, anti-piracy agencies, or your ISP, regardless of whether you download any content. **The authors accept no liability for network exposure or consequences arising from an operator's choice not to use a VPN or equivalent network isolation.**

## Frequently Asked Questions

**Can I run this on my home server?**
Yes. Running BitAgent is lawful in most jurisdictions. Operators are responsible for complying with local copyright and network regulations. We strongly recommend routing DHT traffic through a VPN — see above.

**Will I get sued?**
Running BitAgent itself carries no inherent legal risk. Legal exposure depends entirely on what content you download, how you use it, and your jurisdiction. The project makes no guarantee of immunity from third-party claims.

**Does the project endorse piracy?**
No. The project endorses lawful indexing of publicly broadcast metadata and the continued development of open, standards-compliant networking tools.

**Do I need a VPN?**
**Yes, we strongly recommend one.** Without a VPN, your real IP address participates in the BitTorrent DHT and is visible to other peers, including rights-holder monitoring services. Use a no-log VPN provider that supports port forwarding (Mullvad, AirVPN, ProtonVPN, etc.) and configure `BITAGENT_PEER_PORT` to match your assigned forwarded port. The authors accept no liability for consequences arising from operating without network isolation.

**I received a DMCA notice — what do I do?**
Handle notices internally. Use BitAgent's dashboard or API endpoint `/api/torrents/{infohash}/forget` to remove the specific infohash from your local index. Consult local counsel if your notice involves third-party claims or commercial liability. The authors are not a service provider under the DMCA and do not receive or process notices on your behalf.

## TL;DR

**BitAgent is a self-hosted metadata indexer for the public BitTorrent DHT — not a download client or content host.** Indexing publicly broadcast network metadata is lawful in most jurisdictions. Downloading content is your responsibility and depends on the file, your jurisdiction, and your rights.

**The authors accept no liability for copyright infringement, intellectual property claims, or any harm arising from your use of this software.** Operators bear full and exclusive responsibility for their own actions.

**Use a VPN.** Without one, your real IP is visible in the DHT swarm.
