# Radarr integration

BitAgent's Torznab endpoint speaks Radarr's wire format natively. Add it as a Custom Indexer; no special bridge needed.

## Setup

1. **Open Radarr → Settings → Indexers → Add → Torznab → Custom**.
2. Fill in the connection fields:

   | Field | Value |
   |---|---|
   | Name | `BitAgent` |
   | Enable | ✓ |
   | URL | `http://bitagent:3333/torznab` (compose) or `https://bitagent.example.com/torznab` (public) |
   | API Key | your `TORZNAB_API_KEY` |
   | Categories | `2000` (Movies), `2030` (Movies/SD), `2040` (Movies/HD), `2050` (Movies/UHD) |
   | Multi Languages | leave blank unless you index regional releases |
   | Priority | `25–50` per your stack |

3. Click **Test**. Expect a green *"Test was successful"*.
4. Save.

`[screenshot: radarr-add-indexer-form]`

## TMDB ID-based search

Radarr's movie searches typically include both `q=` (title) and `tmdbid=` parameters. BitAgent's Torznab caps declare `movie-search: [q, imdbid, tmdbid]`, so Radarr automatically uses the more accurate ID-based query when available.

A title-only query falls back when Radarr doesn't have a TMDB ID for the movie yet (newly added, custom imports, etc.). BitAgent's classifier still parses the year + title from the release name, so accuracy stays high.

`[screenshot: radarr-tmdb-search]`

## Categories reference

| Newznab ID | Radarr label | Notes |
|---|---|---|
| 2000 | Movies | catch-all |
| 2030 | Movies/SD | < 720p |
| 2040 | Movies/HD | 720p+ |
| 2045 | Movies/UHD | 2160p+ |
| 2050 | Movies/BluRay | source-tagged |
| 2060 | Movies/3D | rare |

`[screenshot: radarr-categories-selector]`

## Troubleshooting

**Searches return 0 results**
Verify in the BitAgent dashboard that the Library tab shows recent classifications tagged as `movie`. Empty Library means the DHT crawler hasn't found relevant content yet (typical first-day behaviour) or the classifier is mis-routing into `tv_show` (classifier rules need tuning — see the classifier documentation).

**Custom Formats not matching**
BitAgent emits source/resolution/HDR tags via Torznab `<info>` attributes. If Radarr's Custom Format engine isn't picking them up, check that your CFs match BitAgent's exact tag names (case-sensitive). The reference table is in the Torznab API reference.

**Quality Profile doesn't show expected upgrades**
BitAgent doesn't fabricate quality info — it parses what's in the release name. If a release is mis-tagged at the source, BitAgent inherits that. For known-bad sources, add a CEL filter rule to the classifier to suppress them.

`[screenshot: radarr-custom-formats]`

## Recommended companions

- **Quality Definitions** — keep Radarr's defaults; they map cleanly to BitAgent's resolution tags.
- **Indexer flags** — same as Sonarr.
- **Search delays** — set `Search Delay` to 30s if you want to wait for BitAgent's classifier to finish processing very recent releases before Radarr grabs them.
