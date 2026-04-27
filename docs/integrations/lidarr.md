# Lidarr integration

BitAgent's Torznab caps declare music-search support; Lidarr consumes it as a Custom Torznab indexer.

## Setup

1. **Open Lidarr → Settings → Indexers → Add → Torznab → Custom**.
2. Fill in the fields:

   | Field | Value |
   |---|---|
   | Name | `BitAgent` |
   | Enable | ✓ |
   | URL | `http://bitagent:3333/torznab` (compose) or `https://bitagent.example.com/torznab` (public) |
   | API Key | your `TORZNAB_API_KEY` |
   | Categories | `3000` (Audio), `3010` (Audio/MP3), `3020` (Audio/Lossless), `3030` (Audio/Audiobook — optional) |
   | Search modes | `q`, `artist`, `album` (auto-negotiated via caps) |
   | Priority | `25–50` |
   | Early Download Limit | leave default (Lidarr's value) |

3. Click **Test**. Expect green *"Test was successful"*.
4. Save.

`[screenshot: lidarr-add-indexer-form]`

## Search modes

Lidarr calls the Torznab endpoint with these patterns:

- `?t=music&q=Artist+Name` — generic music search
- `?t=music&artist=Pink+Floyd&album=Animals` — discrete artist+album
- `?t=search&q=...` — fallback when artist/album metadata is missing

BitAgent's classifier parses the release name to identify artist + album + format. Releases without recognisable music-shape names (no artist tag, no album-position, etc.) are tagged `unknown` rather than `music`, so they don't pollute Lidarr's results.

`[screenshot: lidarr-indexer-test-success]`

## Categories reference

| Newznab ID | Lidarr label | Notes |
|---|---|---|
| 3000 | Audio | catch-all |
| 3010 | Audio/MP3 | lossy |
| 3020 | Audio/Lossless | FLAC, ALAC, WAV |
| 3030 | Audio/Audiobook | optional; also handled by Readarr |
| 3040 | Audio/Other | rare |

`[screenshot: lidarr-categories-selector]`

## Troubleshooting

**Test fails with "Indexer doesn't support music-search"**
BitAgent's caps endpoint declares `music-search` only when the classifier has at least one music-tagged entry in the index. If you've just deployed and the DHT hasn't surfaced music yet, the cap is omitted. Wait for the first music classification (typically within 10–30 minutes) and re-test.

**0 results on artist+album search**
Verify by hand: `curl "https://bitagent.example.com/torznab?t=music&artist=Pink+Floyd&album=Animals&apikey=$KEY"`. If the XML returns 0 items, BitAgent hasn't crawled that release. If items return but Lidarr still shows 0, it's a category-filter mismatch — check that 3010/3020 are in your indexer config.

**Quality Profile mis-matches**
BitAgent's classifier emits format tags (MP3, FLAC, ALAC) into the Torznab `<info>` block. Lidarr maps these to its quality profile. If your custom Quality Profile expects "FLAC 24bit" specifically, the classifier may need a CEL rule extension to extract bit-depth tags — see [customization](../concepts/classifier.md).

`[screenshot: lidarr-custom-formats]`

## Recommended companions

- **MusicBrainz integration** — Lidarr resolves artist/album metadata via MusicBrainz before querying indexers; BitAgent doesn't change this flow. The combination of MusicBrainz IDs + BitAgent's content tags gives high accuracy.
- **Quality Profiles** — start with Lidarr's defaults; tune later as you see what BitAgent surfaces.
- **Search delays** — leave default; BitAgent's classifier finishes processing within seconds of DHT discovery.
